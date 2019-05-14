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
    def update_status(judge_result, message):
        http_post(urljoin(config.WEB_URL, "/api/judge/update"), data={
                  "uuid": config.JUDGER_UUID, "judge_result": encode_json(judge_result), "submission_id": data["id"], "message": message})

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
    path = os.path.join(config.DATA_DIR, str(data["problem_id"]))
    os.makedirs(path, exist_ok=True)
    for file in file_list:
        current_file = os.path.join(path, file["name"])
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
    comparator = None
    print(problem_data)
    if problem_data["spj_filename"]:
        comparator = SPJComparator(problem_data["spj_filename"])
    else:
        comparator = SimpleComparator()
    # 下载语言定义
    update_status(data["judge_result"], "下载语言配置中")
    os.makedirs(os.path.join(basedir, "langs"), exist_ok=True)
    if not os.path.exists("langs/__init__.py"):
        with open("langs/__init__.py", "w") as file:
            pass
    with open(os.path.join("langs", data["language"]+".py"), "wb") as file:
        file.write(http_post(urljoin(config.WEB_URL, "/api/judge/get_lang_config"), {
                             "lang_id": data["language"], "uuid": config.JUDGER_UUID}))
    # import langs.cpp11
    opt_dir = tempfile.mkdtemp()
    print(f"Work directory: {opt_dir}")
    # opt_dir = "C:\\Users\\HP\\qwq"
    os.makedirs(opt_dir, exist_ok=True)
    docker_mount_dir = opt_dir
    # docker_mount_dir = opt_dir.replace(
    #     "\\", "/").replace("C", "/c").replace(":", "")
    lang = importlib.import_module(f"langs.{data['language']}")
    # 编译程序
    update_status(data["judge_result"], "编译程序中")
    app_source_file = lang.SOURCE_FILE.format(filename="app")
    app_output_file = lang.OUTPUT_FILE.format(filename="app")
    with open(os.path.join(opt_dir, app_source_file), "w") as file:
        file.write(data["code"])
    compile_runner = DockerRunner(config.DOCKER_IMAGE, docker_mount_dir, lang.COMPILE.format(
        source=app_source_file, output=app_output_file), 512*1024*1024, judge_config["compile_time_limit"], "Compile", docker_client)
    print("Compile with "+lang.COMPILE.format(
        source=app_source_file, output=app_output_file))
    compile_result: RunnerResult = compile_runner.run()
    print(f"Compile result = {compile_result}")
    if compile_result.exit_code:
        update_status(
            {}, f"编译失败！\n{compile_result.output}\n时间开销:{compile_result.time_cost}ms\n内存开销:{compile_result.memory_cost}MB\nExit code:{compile_result.exit_code}")
        return
    update_status(data["judge_result"], "编译完成")
    judge_result = data["judge_result"]
    for subtask in problem_data["subtasks"]:
        print(subtask)
        subtask_result = judge_result[subtask["name"]]
        skip = False
        for i, testcase in enumerate(subtask["testcases"]):
            testcase_result = subtask_result["testcases"][i]
            if skip:
                testcase_result["score"] = 0
                testcase_result["status"] = "skipped"
                testcase_result["message"] = "跳过"
                continue
            input_file = problem_data["input_file_name"] if problem_data["using_file_io"] else "in"
            output_file = problem_data["output_file_name"] if problem_data["using_file_io"] else "out"
            shutil.copy(os.path.join(
                path, testcase["input"]), os.path.join(opt_dir, problem_data["input_file_name"]))
            runner = DockerRunner(
                config.DOCKER_IMAGE,
                docker_mount_dir,
                lang.RUN.format(program=app_output_file, redirect=(
                    "" if problem_data["using_file_io"] else f"< {problem_data['input_file_name']} > {problem_data['output_file_name']}")),
                int(subtask["memory_limit"])*1024*1024,
                int(subtask["time_limit"]),
                "Judge",
                docker_client
            )
            result: RunnerResult = runner.run()
            print(f"Run result = {result}")
            testcase_result["message"] = f"时间: {int(result.time_cost)}ms  内存: {int(result.memory_cost/1024/1024)}MB | "

            if result.memory_cost/1024/1024 >= int(subtask["memory_limit"]):
                testcase_result["status"] = "memory_limit_exceed"
            elif result.time_cost >= int(subtask["time_limit"]):
                testcase_result["status"] = "time_limit_exceed"
            elif result.exit_code:
                testcase_result["status"] = "runtime_error"
                testcase_result["message"] = f"退出代码: {result.exit_code}"
            else:
                with open(os.path.join(opt_dir, problem_data["output_file_name"]), "r") as f:
                    user_output = f.read()

                # 检验答案正确性
                with open(os.path.join(
                        path, testcase["output"]), "r") as file:
                    ok, message = comparator.compare(
                        file.readlines(), user_output.split("\n"))
                if not ok:
                    testcase_result["status"] = "wrong_answer"

                else:
                    testcase_result["status"] = "accepted"
                if testcase_result["status"] == "accepted":
                    testcase_result["score"] = int(
                        subtask["score"])//len(subtask["testcases"])
                else:
                    testcase_result["score"] = 0
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
    print("Ok")
    shutil.rmtree(opt_dir)
