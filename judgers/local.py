from common.utils import decode_json, encode_json, read_file
from common.compare import SimpleComparator, SPJComparator
from common.runner import DockerRunner, RunnerResult
from main import config, app, basedir, docker_client
from typing import Callable

import tempfile
import importlib
import zipfile
from celery.app.task import Task
import requests
from urllib.parse import urljoin
from requests import Session
import os
import shutil
import io
import base64


def sync_problem_files(problem_id, update: Callable[[str], None], http_client: Session):
    file_list: list = http_client.post(urljoin(config.WEB_URL, "/api/judge/get_file_list"), data={
        "uuid": config.JUDGER_UUID, "problem_id": problem_id}).json()["data"]
    # 同步题目文件
    update("同步题目文件中")
    # 题目文件目录
    path = os.path.join(config.DATA_DIR, str(problem_id))
    os.makedirs(path, exist_ok=True)
    for file in file_list:
        current_file = os.path.join(path, file["name"])
        # 不存在 或者时间早于更新时间
        if not os.path.exists(current_file+".lock") or float(read_file(current_file+".lock")) < float(file["last_modified_time"]):
            update(f"下载 {file['name']} 中..")
            print(f"Downloading {file}")
            with open(current_file, "wb") as target:
                target.write(http_client.post(urljoin(config.WEB_URL, "/api/judge/download_file"), data={
                    "problem_id": problem_id, "filename": file["name"], "uuid": config.JUDGER_UUID}).content)
            with open(current_file+".lock", "w") as f:
                import time
                f.write(f"{time.time()}")


@app.task(bind=True)
def run(self: Task, data: dict, judge_config):
    """

        queue.send_task("judgers.local.run", [submit.to_dict(), {
                        "compile_time_limit": config.COMPILE_TIME_LIMIT,
                        "compile_result_length_limit": config.COMPILE_RESULT_LENGTH_LIMIT,
                        "spj_execute_time_limit": config.SPJ_EXECUTE_TIME_LIMIT,
                        "extra_compile_parameter": submit.extra_compile_parameter,
                        "auto_sync_files": config.AUTO_SYNC_FILES,
                        "output_file_size_limit": config.OUTPUT_FILE_SIZE_LIMIT,
                        "submit_answer": problem.problem_type == "submit_answer",
                        "answer_data": answer_data if problem.problem_type == "submit_answer" else None
                        }])
    """
    import ssl
    ssl._create_default_https_context = ssl._create_unverified_context
    http_client = requests.session()
    # 更新评测状态

    def update_status(judge_result, message, extra_status=""):
        http_client.post(urljoin(config.WEB_URL, "/api/judge/update"), verify=True, data={
            "uuid": config.JUDGER_UUID, "judge_result": encode_json(judge_result), "submission_id": data["id"], "message": message, "extra_status": extra_status})
    # 抛出异常时调用

    def on_failure(exc, task_id, args, kwargs, einfo):
        update_status({}, f"{exc}: {einfo}")
    self.on_failure = on_failure
    opt_dir = None
    try:
        answer_data = judge_config["answer_data"]
        submit_answer = judge_config["submit_answer"]
        judge_config["answer_data"] = "too long, removed"
        print(f"Got a judge task {data}")
        print("Judge config = ", judge_config)
        problem_data: dict = http_client.post(
            urljoin(config.WEB_URL, "/api/judge/get_problem_info"), verify=True, data={"uuid": config.JUDGER_UUID, "problem_id": data["problem_id"]}).json()["data"]

        # 题目文件目录
        path = os.path.join(config.DATA_DIR, str(data["problem_id"]))
        print(problem_data)
        if judge_config["auto_sync_files"]:
            sync_problem_files(
                data["problem_id"], lambda x: update_status(data["judge_result"], x), http_client)
        if submit_answer and not problem_data["spj_filename"]:
            raise Exception("提交答案题必须使用SPJ")
        if problem_data["spj_filename"]:
            spj_lang = problem_data["spj_filename"][4:problem_data["spj_filename"].rindex(
                ".")]
            update_status(data["judge_result"], "下载SPJ语言配置中")
            os.makedirs(os.path.join(basedir, "langs"), exist_ok=True)
            with open(os.path.join("langs", spj_lang+".py"), "wb") as file:
                file.write(http_client.post(urljoin(config.WEB_URL, "/api/judge/get_lang_config"), verify=True, data={
                    "lang_id": spj_lang, "uuid": config.JUDGER_UUID}).content)
            comparator = SPJComparator(os.path.join(
                path,
                problem_data["spj_filename"]),
                lambda x: update_status(data["judge_result"], x),
                data["code"],
                importlib.import_module("langs."+spj_lang),
                judge_config["spj_execute_time_limit"],
                config.DOCKER_IMAGE)
        else:
            # 简单比较器
            comparator = SimpleComparator()
        # 下载语言定义
        update_status(data["judge_result"], "下载语言配置中")
        os.makedirs(os.path.join(basedir, "langs"), exist_ok=True)
        with open(os.path.join("langs", data["language"]+".py"), "wb") as file:
            file.write(http_client.post(urljoin(config.WEB_URL, "/api/judge/get_lang_config"), verify=True, data={
                "lang_id": data["language"], "uuid": config.JUDGER_UUID}).content)
        # 创建临时工作目录，用于挂载到docker内进行评测
        opt_dir = tempfile.mkdtemp()
        print(f"Working directory: {opt_dir}")
        if not submit_answer:
            # 加载语言配置
            lang = importlib.import_module(f"langs.{data['language']}")
            # 编译程序
            update_status(data["judge_result"], "编译程序中")
            # 用户程序源文件名
            app_source_file = lang.SOURCE_FILE.format(filename="app")
            # 用户程序目标文件名
            app_output_file = lang.OUTPUT_FILE.format(filename="app")
            with open(os.path.join(opt_dir, app_source_file), "w") as file:
                file.write(data["code"])
            compile_runner = DockerRunner(config.DOCKER_IMAGE, opt_dir, lang.COMPILE.format(
                source=app_source_file, output=app_output_file, extra=judge_config["extra_compile_parameter"]), 512*1024*1024, judge_config["compile_time_limit"], "Compile", 512*1024*1024, docker_client)
            print("Compile with "+lang.COMPILE.format(
                source=app_source_file, output=app_output_file, extra=judge_config["extra_compile_parameter"]))
            # 编译时提供给程序的文件
            for x in problem_data["provides"]:
                shutil.copy(os.path.join(
                    path, x), os.path.join(opt_dir, x))
            # 编译用户程序
            compile_result: RunnerResult = compile_runner.run()
            print(f"Compile result = {compile_result}")
            if compile_result.exit_code:
                update_status(
                    {}, f"{compile_result.output[:2000]}\n时间开销:{compile_result.time_cost}ms\n内存开销:{compile_result.memory_cost}Bytes\nExit code:{compile_result.exit_code}", extra_status="compile_error")
                return
            update_status(data["judge_result"], "编译完成")
        else:

            # 处理提交答案部分
            data_zip = zipfile.ZipFile(io.BytesIO(
                base64.decodebytes(answer_data.encode())))
            user_answers_mapping = {
                item.filename: item for item in data_zip.filelist}
            print(user_answers_mapping)
        judge_result = data["judge_result"]
        # 依次评测每一个子任务
        for subtask in problem_data["subtasks"]:
            print(subtask)
            subtask_result = judge_result[subtask["name"]]
            # 时限放宽为1.05倍防止卡常
            subtask["time_limit"] = int(int(subtask["time_limit"])*1.05)
            skip = False
            # 评测子任务的每一个测试点
            for i, testcase in enumerate(subtask["testcases"]):
                testcase_result = subtask_result["testcases"][i]
                testcase_result["status"] = "judging"
                update_status(judge_result, f"评测子任务 {subtask['name']} ,测试点{i+1}中")
                if skip:
                    # 取min时跳过余下的所有测试点
                    testcase_result["score"] = 0
                    testcase_result["status"] = "skipped"
                    testcase_result["message"] = "跳过"
                    continue
                if submit_answer:
                    full_score = testcase["full_score"]
                    testcase_result["memory_cost"] = 0
                    testcase_result["time_cost"] = 0
                    testcase_result["message"] = ""
                    input_file_name, output_file_name = testcase["input"], testcase["output"]
                    with open(os.path.join(path, input_file_name), "r") as f:
                        input_lines = f.readlines()
                    with open(os.path.join(path, output_file_name), "r") as f:
                        answer_lines = f.readlines()
                    try:
                        user_answer = data_zip.read(output_file_name).decode()
                    except KeyError:
                        user_answer = ""
                    score, message = comparator.compare(
                        user_answer.split("\n"), answer_lines, input_lines, full_score)

                    if score < full_score:
                        testcase_result["status"] = "wrong_answer"
                    elif score == full_score:
                        testcase_result["status"] = "accepted"
                    else:
                        # ???
                        testcase_result["status"] = "what_happened"
                    if score == -1:
                        # SPJ运行失败
                        testcase_result["status"] = "judge_failed"
                        score = 0
                    testcase_result["score"] = score
                    testcase_result["message"] += message
                else:
                    # 程序的输入和输出文件名，trick：使用重定向实现非文件IO
                    input_file = problem_data["input_file_name"] if problem_data["using_file_io"] else "in"
                    output_file = problem_data["output_file_name"] if problem_data["using_file_io"] else "out"
                    print(input_file, output_file)
                    shutil.copy(os.path.join(
                        path, testcase["input"]), os.path.join(opt_dir, input_file))
                    # print(
                    #     f'Copy {os.path.join(path, testcase["input"])} to {os.path.join(opt_dir, problem_data["input_file_name"])}')
                    with open(os.path.join(path, testcase["input"]), "r") as _input:
                        input_lines = _input.readlines()
                    runner = DockerRunner(
                        config.DOCKER_IMAGE,
                        opt_dir,
                        lang.RUN.format(program=app_output_file, redirect=(
                            "" if problem_data["using_file_io"] else f"< {input_file} > {output_file}")),
                        f"{subtask['memory_limit']}m",
                        int(int(subtask["time_limit"])),
                        "Judge",
                        int(subtask["memory_limit"])*1024*1024,
                        docker_client
                    )
                    # 运行用户程序
                    result: RunnerResult = runner.run()
                    # print(f"Time limit: {subtask['time_limit']},time cost: {result.time_cost}")
                    print(f"Run result = {result}")
                    testcase_result["memory_cost"] = result.memory_cost
                    testcase_result["time_cost"] = result.time_cost
                    testcase_result["message"] = ""
                    # 返回的结果中内存的单位是字节
                    if result.memory_cost/1024/1024 >= int(subtask["memory_limit"]):
                        testcase_result["status"] = "memory_limit_exceed"
                    elif result.time_cost >= int(subtask["time_limit"]):
                        testcase_result["status"] = "time_limit_exceed"
                    elif result.exit_code:
                        testcase_result["status"] = "runtime_error"
                        testcase_result["message"] += f"退出代码: {result.exit_code}"
                    else:
                        try:
                            if os.path.getsize(os.path.join(opt_dir, output_file)) > judge_config["output_file_size_limit"]:
                                testcase_result["status"] = "output_size_limit_exceed"
                                testcase_result["message"] = "Too MANY output!"
                                continue
                            else:
                                with open(os.path.join(opt_dir, output_file), "r") as f:
                                    user_output = f.read()
                        except:
                            user_output = ""
                        # 测试点满分，对于sum，为子任务得分除测试点个数，对于min，为1(为了适配)
                        full_score = testcase["full_score"]
                        # 检验答案正确性
                        with open(os.path.join(
                                path, testcase["output"]), "r") as file:
                            score, message = comparator.compare(
                                user_output.split("\n"), file.readlines(), input_lines, full_score)

                        # 非满分一律判为WA
                        if score < full_score:
                            testcase_result["status"] = "wrong_answer"
                        elif score == full_score:
                            testcase_result["status"] = "accepted"
                        else:
                            # ???
                            testcase_result["status"] = "what_happened"
                        if score == -1:
                            # SPJ运行失败
                            testcase_result["status"] = "judge_failed"
                            score = 0
                        testcase_result["score"] = score
                        testcase_result["message"] += message
                if testcase_result["status"] != "accepted" and subtask["method"] == "min":
                    skip = True
                update_status(judge_result, f"评测子任务 {subtask['name']} ,测试点{i+1}中")
            if subtask["method"] == "min":
                if all(map(lambda x: x["status"] == "accepted", subtask_result["testcases"])):
                    subtask_result["score"] = subtask["score"]
                else:
                    subtask_result["score"] = 0
            else:
                subtask_result["score"] = sum(
                    map(lambda x: x["score"], subtask_result["testcases"]))
            subtask_result["status"] = "accepted" if int(
                subtask_result["score"]) == int(subtask["score"]) else "unaccepted"
        if not submit_answer:
            update_status(
                judge_result, f"{compile_result.output}\n编译时间开销:{int(compile_result.time_cost)}ms\n编译内存开销:{int(compile_result.memory_cost/1024/1024)}MB\nExit code:{compile_result.exit_code}")
        else:
            update_status(
                judge_result, f"")
    finally:
        print("Cleaning up..")
        if opt_dir:
            shutil.rmtree(opt_dir, True)
        print("Judge process finished.")
