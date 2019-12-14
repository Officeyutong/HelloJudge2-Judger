from main import app, JUDGE_CLIENTS, config
from celery.app.task import Task
from typing import Dict
from remote_runners.luogu import LuoguJudgeClient
from remote_runners.common import JudgeClient
from urllib.parse import urljoin
from remote_runners.common import LoginResult, SubmitResult
from common.utils import encode_json
import time
import requests


@app.task(bind=True)
def submit(self: Task,
           hj2_submission_id: str,
           oj_type: str,
           session: Dict[str, str],
           problem_id: str,
           lang: str,
           code: str,
           login_captcha: str,
           submit_captcha: str,
           client_session_id: str,
           remote_username: str,
           remote_password: str,
           countdown: int
           ):
    """
        Web端尝试提交代码，先用预存的cookies试图提交
        如果提交需求登录,则尝试登录
        如果登录成功则进行提交,如果登录需要验证码则通知Web端并终止。
        若提交需要验证码则通知客户端并终止提交

    """
    client = requests.session()

    def update_status(ok, data: dict):
        client.post(urljoin(config.WEB_URL, "/api/judge/remote_judge/update"),
                    json={"ok": ok, "data": data, "uuid": config.JUDGER_UUID, "client_session_id": client_session_id})
    # 抛出异常时调用

    def on_failure(exc, task_id, args, kwargs, einfo):
        update_status(False, {"message": f"{exc}: {einfo}"})
    self.on_failure = on_failure
    module = JUDGE_CLIENTS[oj_type]
    client: JudgeClient = module.get_judge_client()
    session_object = module.as_session_data(session)
    if not client.has_login(session_object):
        # 尝试登录
        login_result = client.login(
            session_object, remote_username, remote_password, login_captcha)
        if not login_result.ok:
            update_status(False, login_result.as_dict())
            return
        session_object = login_result.new_session
    # 已登录,尝试提交
    submit_result: SubmitResult = client.submit(
        session_object, problem_id, code, lang, submit_captcha
    )
    if not submit_result.ok:
        update_status(False, submit_result.as_dict())
        return
    # 提交成功
    update_status(True, submit_result.as_dict())
    # 开始跟踪
    app.send_task("judgers.remote.track_submission", [
        oj_type, session, submit_result.submit_id, hj2_submission_id,  countdown
    ])


@app.task(bind=True)
def track_submission(self: Task,
                     oj_type: str,
                     session: Dict[str, str],
                     remote_submission_id: str,
                     hj2_submission_id: str,
                     countdown: int
                     ):
    if countdown == 0:
        return
    client = requests.session()

    def update_status(judge_result, message, extra_status=""):
        client.post(urljoin(config.WEB_URL, "/api/judge/update"), data={
            "uuid": config.JUDGER_UUID, "judge_result": encode_json(judge_result), "submission_id": hj2_submission_id, "message": message, "extra_status": extra_status})

    # 抛出异常时调用

    def on_failure(exc, task_id, args, kwargs, einfo):
        update_status(False, {"message": f"{exc}: {einfo}"})
    self.on_failure = on_failure
    module = JUDGE_CLIENTS[oj_type]
    client: JudgeClient = module.get_judge_client()
    session_object = module.as_session_data(session)
    result: dict = client.get_submission_status(
        session_object, remote_submission_id)
    update_status(result["subtasks"], result["message"],
                  result["extra_message"])
    time.sleep(1)
    app.send_task("judgers.remote.track_submission", [
        oj_type, session, remote_submission_id, hj2_submission_id,  countdown-1
    ])
