from main import app, config, basedir
from utils import *
from urllib.parse import urljoin
from celery.app.task import Task
import os


@app.task(bind=True)
def judge(self: Task, data: dict):
    def update_status(judge_result, message):
        http_post(urljoin(config.WEB_URL, "/api/judge/update"), data={
                  "uuid": config.JUDGER_UUID, "judge_result": encode_json(judge_result), "submission_id": data["id"], "message": message})

    def on_failure(exc, task_id, args, kwargs, einfo):
        update_status({}, f"{exc}: {einfo}")
    self.on_failure = on_failure
    print(f"Got a judge task {data}")
    problem_data: dict = decode_json(http_post(
        urljoin(config.WEB_URL, "/api/judge/get_problem_info"), {"uuid": config.JUDGER_UUID, "problem_id": data["problem_id"]}).decode())
    # 同步题目文件
    update_status(data["judge_result"], "同步题目文件中...")
    file_list = decode_json(http_post(urljoin(config.WEB_URL, "/api/judge/get_file_list"), {
                            "uuid": config.JUDGER_UUID, "problem_id": data["problem_id"]}).decode())["data"]
    path = os.path.join(basedir, config.DATA_DIR, str(data["problem_id"]))
    os.makedirs(path, exist_ok=True)
    for file in file_list:
        current_file = os.path.join(path, file["name"])
        if not os.path.exists(current_file) or os.path.getmtime(current_file) < file["last_modified_time"]:
            update_status(data["judge_result"], f"下载 {file['name']} 中..")
            print(f"Downloading {file}")
            with open(current_file, "wb") as target:
                target.write(http_post(urljoin(config.WEB_URL, "/api/judge/download_file"), {
                             "problem_id": data["problem_id"], "filename": file["name"], "uuid": config.JUDGER_UUID}))
    update_status(data["judge_result"], "文件同步完成")
