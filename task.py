from main import app, config, basedir, docker_client
from utils import *
from urllib.parse import urljoin
from celery.app.task import Task
import os
from compare import *
import tempfile
import importlib
from runner import *
import shutil

import sys
sys.path.append(basedir)


@app.task(bind=True)
def judge(self: Task, data: dict, judge_config):
    # 更新评测状态
    def update_status(judge_result, message):
        http_post(urljoin(config.WEB_URL, "/api/judge/update"), data={
                  "uuid": config.JUDGER_UUID, "judge_result": encode_json(judge_result), "submission_id": data["id"], "message": message})
    # 抛出异常时调用

    def on_failure(exc, task_id, args, kwargs, einfo):
        update_status({}, f"{exc}: {einfo}")
    self.on_failure = on_failure
    print(f"Got a judge task {data}")
    problem_data: dict = decode_json(http_post(
        urljoin(config.WEB_URL, "/api/judge/get_problem_info"), {"uuid": config.JUDGER_UUID, "problem_id": data["problem_id"]}).decode())["data"]

    # 同步题目文件
    update_status(data["judge_result"], "同步题目文件中...")
    file_list = decode_json(http_post(urljoin(config.WEB_URL, "/api/judge/get_file_list"), {
                            "uuid": config.JUDGER_UUID, "problem_id": data["problem_id"]}).decode())["data"]
    # 题目文件目录
    path = os.path.join(config.DATA_DIR, str(data["problem_id"]))
    os.makedirs(path, exist_ok=True)
    if judge_config["auto_sync_files"]:
        for file in file_list:
            current_file = os.path.join(path, file["name"])
            # 不存在 或者时间早于更新时间
            if not os.path.exists(current_file+".lock") or float(read_file(current_file+".lock")) < float(file["last_modified_time"]):
                update_status(data["judge_result"], f"下载 {file['name']} 中..")
                print(f"Downloading {file}")
                with open(current_file, "wb") as target:
                    target.write(http_post(urljoin(config.WEB_URL, "/api/judge/download_file"), {
                        "problem_id": data["problem_id"], "filename": file["name"], "uuid": config.JUDGER_UUID}))
                with open(current_file+".lock", "w") as f:
                    import time
                    f.write(f"{time.time()}")
        update_status(data["judge_result"], "文件同步完成")
    else:
        update_status(data["judge_result"], "文件同步跳过")
    print(problem_data)
    if problem_data["spj_filename"]:
        spj_lang = problem_data["spj_filename"][4:problem_data["spj_filename"].rindex(
            ".")]
        update_status(data["judge_result"], "下载SPJ语言配置中")
        os.makedirs(os.path.join(basedir, "langs"), exist_ok=True)
        with open(os.path.join("langs", spj_lang+".py"), "wb") as file:
            file.write(http_post(urljoin(config.WEB_URL, "/api/judge/get_lang_config"), {
                "lang_id": spj_lang, "uuid": config.JUDGER_UUID}))
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
        file.write(http_post(urljoin(config.WEB_URL, "/api/judge/get_lang_config"), {
                             "lang_id": data["language"], "uuid": config.JUDGER_UUID}))
    # 创建临时工作目录，用于挂载到docker内进行评测
    opt_dir = tempfile.mkdtemp()
    print(f"Working directory: {opt_dir}")
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
        source=app_source_file, output=app_output_file, extra=judge_config["extra_compile_parameter"]), 512*1024*1024, judge_config["compile_time_limit"], "Compile", docker_client)
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
            {}, f"编译失败！\n{compile_result.output}\n时间开销:{compile_result.time_cost}ms\n内存开销:{compile_result.memory_cost}Bytes\nExit code:{compile_result.exit_code}")
        return
    update_status(data["judge_result"], "编译完成")
    judge_result = data["judge_result"]
    # 依次评测每一个子任务
    for subtask in problem_data["subtasks"]:
        print(subtask)
        subtask_result = judge_result[subtask["name"]]
        skip = False
        # 评测子任务的每一个测试点
        for i, testcase in enumerate(subtask["testcases"]):
            testcase_result = subtask_result["testcases"][i]
            if skip:
                # 取min时跳过余下的所有测试点
                testcase_result["score"] = 0
                testcase_result["status"] = "skipped"
                testcase_result["message"] = "跳过"
                continue
            # 程序的输入和输出文件名，trick：使用重定向实现非文件IO
            input_file = problem_data["input_file_name"] if problem_data["using_file_io"] else "in"
            output_file = problem_data["output_file_name"] if problem_data["using_file_io"] else "out"
            shutil.copy(os.path.join(
                path, testcase["input"]), os.path.join(opt_dir, input_file))
            # print(
            #     f'Copy {os.path.join(path, testcase["input"])} to {os.path.join(opt_dir, problem_data["input_file_name"])}')
            subtask["time_limit"] = int(int(subtask["time_limit"])*1.05)
            runner = DockerRunner(
                config.DOCKER_IMAGE,
                opt_dir,
                lang.RUN.format(program=app_output_file, redirect=(
                    "" if problem_data["using_file_io"] else f"< {input_file} > {output_file}")),
                int(subtask["memory_limit"])*1024*1024,
                int(int(subtask["time_limit"])),
                "Judge",
                docker_client
            )
            # 运行用户程序
            result: RunnerResult = runner.run()
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
                        user_output.split("\n"), file.readlines(), full_score)

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
    update_status(
        judge_result, f"{compile_result.output}\n编译时间开销:{int(compile_result.time_cost)}ms\n编译内存开销:{int(compile_result.memory_cost/1024/1024)}MB\nExit code:{compile_result.exit_code}")
    print("Removing files..")
    shutil.rmtree(opt_dir)
    print("Ok")
