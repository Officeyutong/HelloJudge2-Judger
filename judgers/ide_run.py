from main import app, basedir, docker_client, config
import requests
from urllib.parse import urljoin
import os
import importlib
from common.runner import DockerRunner, RunnerResult
import shutil
@app.task(bind=True)
def run(self, lang_id: str, run_id: str, code: str, input: str, run_config: dict):
    http_client = requests.session()

    def update_status(msg, status):
        http_client.post(urljoin(config.WEB_URL, "/api/ide/update"), data={
            "uuid": config.JUDGER_UUID, "message": msg, "run_id": run_id, "status": status
        })

    def on_failure(exc, task_id, args, kwargs, einfo):
        update_status(f"{exc}: {einfo}", "running")
    self.on_failure = on_failure
    try:
        import tempfile
        import pathlib
        work_dir = pathlib.Path(tempfile.mkdtemp())
        print("Working dir: "+str(work_dir))
        basedir = pathlib.Path(".")
        # 下载语言定义
        update_status("下载语言配置中", "running")
        os.makedirs(basedir/"langs", exist_ok=True)
        with open(os.path.join("langs", lang_id+".py"), "wb") as file:
            file.write(http_client.post(urljoin(config.WEB_URL, "/api/judge/get_lang_config"), data={
                "lang_id": lang_id, "uuid": config.JUDGER_UUID}).content)
        lang = importlib.import_module(f"langs.{lang_id}")
        # 编译程序
        update_status("编译程序中", "running")
        # 用户程序源文件名
        app_source_file = lang.SOURCE_FILE.format(filename="run")
        # 用户程序目标文件名
        app_output_file = lang.OUTPUT_FILE.format(filename="run")
        with open(work_dir/app_source_file, "w") as file:
            file.write(code)
        compile_runner = DockerRunner(config.DOCKER_IMAGE, work_dir.absolute(), lang.COMPILE.format(
            source=app_source_file, output=app_output_file, extra=run_config["parameter"]), 512*1024*1024, run_config["compile_time_limit"], "Compile", 512*1024*1024, docker_client)
        print("Compile with "+lang.COMPILE.format(
            source=app_source_file, output=app_output_file, extra=""))
        compile_result: RunnerResult = compile_runner.run()
        print(f"Compile result = {compile_result}")
        if compile_result.exit_code:
            update_status(
                f"编译失败！\n{compile_result.output}\n时间开销:{compile_result.time_cost}ms\n内存开销:{compile_result.memory_cost}Bytes\nExit code:{compile_result.exit_code}", "done")
            return
        input_file = "in"
        output_file = "out"
        with open(work_dir/input_file, "w") as f:
            f.write(input)
        update_status("运行中...", "running")
        runner = DockerRunner(
            config.DOCKER_IMAGE,
            work_dir.absolute(),
            lang.RUN.format(program=app_output_file, redirect=(
                f"< {input_file} > {output_file}")),
            int(run_config["memory_limit"])*1024*1024,
            int(run_config["time_limit"]),
            "Run",
            int(run_config["memory_limit"])*1024*1024,
            docker_client
        )
        run_result = runner.run()
        with open(work_dir/output_file, "r") as f:
            output = f.read(run_config["result_length_limit"])
        update_status(
            f"运行完成！\n退出代码:{run_result.exit_code}\n内存开销:{run_result.memory_cost} bytes\n时间开销:{run_result.time_cost} ms\n标准输出:\n{output}\n标准错误:\n{run_result.output}", "done")
        print("Done")
    finally:
        print("Cleaning up..")
        shutil.rmtree(work_dir)
