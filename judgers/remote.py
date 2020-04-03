from main import app, JUDGE_CLIENTS, config
from celery.app.task import Task
from typing import Dict
# from remote_runners.luogu import LuoguJudgeClient
from remote_runners.common import JudgeClient
from urllib.parse import urljoin
from remote_runners.common import LoginResult, SubmitResult
from common.utils import encode_json
import time
import requests


@app.task(bind=True)
def submit(self: Task,
           oj_type: str,  # 远程OJ
           session: Dict[str, str],  # Session字典
           remote_account_id: str,  # 远程账户ID
           problem_id: str,  # 远程题目ID
           lang: str,  # 远程语言ID
           code: str,  # 代码
           login_captcha: str,  # 登录验证码
           submit_captcha: str,  # 提交验证码
           client_session_id: str,  # 客户端sid
           remote_username: str,  # 远程OJ用户名
           remote_password: str,  # 远程OJ密码
           hj2_problem_id: int,  # hj2问题ID
           uid: int,  # 提交用户ID
           public: bool,  # 是否公开提交
           countdowns: list,  # 倒计时时间列表,
           contest_id: int,  # 比赛ID
           contest_problem_id: int  # 比赛题目ID
           ):
    """
        Web端尝试提交代码，先用预存的cookies试图提交
        如果提交需求登录,则尝试登录
        如果登录成功则进行提交,如果登录需要验证码则通知Web端并终止。
        若提交需要验证码则通知客户端并终止提交

    """
    print("Submitting: ", locals())
    http_client = requests.session()

    def update_status(ok, data: dict, new_session="{}"):
        http_client.post(urljoin(config.WEB_URL, "/api/judge/remote_judge/update_submit_status"),
                         json={"ok": ok, "data": data, "uuid": config.JUDGER_UUID, "client_session_id": client_session_id})
    # 抛出异常时调用

    def on_failure(exc, task_id, args, kwargs, einfo):
        update_status(False, {"message": f"{exc}: {einfo}"})
    self.on_failure = on_failure
    # module =
    client: JudgeClient = JUDGE_CLIENTS[oj_type]
    session_object = client.as_session_data(session)
    if not client.check_login_status(session_object):
        print("Login....")
        # 尝试登录
        login_result: LoginResult = client.login(
            session_object, remote_username, remote_password, login_captcha)
        if not login_result.ok:
            # 登录失败时直接开一个client_id
            session_object = client.create_session()
            http_client.post(urljoin(config.WEB_URL, "/api/judge/remote_judge/update_session"),
                             json={"account_id": remote_account_id, "uuid": config.JUDGER_UUID, "session": session_object.as_dict()})
            login_result.captcha = client.get_login_captcha(session_object)
            update_status(False, login_result.as_dict())
            return
        session_object = login_result.new_session
    print(http_client.post(urljoin(config.WEB_URL, "/api/judge/remote_judge/update_session"),
                           json={"account_id": remote_account_id, "uuid": config.JUDGER_UUID, "session": session_object.as_dict()}).text)
    print("Login ok. ", session_object)
    # 已登录,尝试提交
    submit_result: SubmitResult = client.submit(
        session_object, problem_id, code, lang, submit_captcha
    )
    print("Submie result: ", submit_result)
    if submit_result.require_new_session:
        session_object = client.create_session()
        print("new session created.", session_object)
        print(http_client.post(urljoin(config.WEB_URL, "/api/judge/remote_judge/update_session"),
                               json={"account_id": remote_account_id, "uuid": config.JUDGER_UUID, "session": session_object.as_dict()}).text)

    if not submit_result.ok:
        update_status(False, submit_result.as_dict())
        return
    update_result = http_client.post(urljoin(config.WEB_URL, "/api/judge/remote_judge/create_submission"), json={
        "uuid": config.JUDGER_UUID,
        "client_session_id": client_session_id,
        "code": code,
        "language": lang,
        "uid": uid,
        "hj2_problem_id": hj2_problem_id,
        "public": public,
        "message": submit_result.message,
        "contest_id": contest_id,
        "contest_problem_id": contest_problem_id
    }).json()
    print("Submit result: ", submit_result.as_dict())
    # 开始跟踪
    app.send_task("judgers.remote.track_submission", [
        oj_type, session_object.as_dict(), submit_result.submit_id, update_result[
            "data"]["submission_id"],  countdowns
    ])


@app.task(bind=True)
def fetch_problem(self: Task,
                  oj_type: str,
                  remote_problem_id: str,
                  hj2_problem_id: str,
                  client_session_id: str
                  ):
    http_client = requests.session()

    # 抛出异常时调用

    def on_failure(exc, task_id, args, kwargs, einfo):
        http_client.post(urljoin(config.WEB_URL, "/api/judge/remote_judge/update_fetch"), json={
            "uuid": config.JUDGER_UUID, "ok": False, "message": f"{exc}: {einfo}", "hj2_problem_id": hj2_problem_id, "client_session_id": client_session_id
        })
    print("Fetching...", oj_type, remote_problem_id,
          hj2_problem_id, client_session_id)
    self.on_failure = on_failure
    # module =
    client: JudgeClient = JUDGE_CLIENTS[oj_type]
    import json
    import jsonpickle
    fetch_result = client.fetch_problem(
        remote_problem_id)
    # for x in dir(fetch_result):
    #     print(x,getattr(fetch_result,x))
    print(fetch_result)
    # print(jsonpickle.dumps(fetch_result, unpicklable=not False,make_refs=False))
    # result = json.JSONDecoder().decode(
    #     jsonpickle.dumps(fetch_result, unpicklable=not False,make_refs=False)
    # )
    result = json.JSONDecoder().decode(
        jsonpickle.encode(fetch_result, unpicklable=False)
    )
    http_client.post(urljoin(config.WEB_URL, "/api/judge/remote_judge/update_fetch"), json={
        "uuid": config.JUDGER_UUID, "ok": True, "result": result, "hj2_problem_id": hj2_problem_id, "client_session_id": client_session_id
    })
    print("report ok.")


@app.task(bind=True)
def track_submission(self: Task,
                     oj_type: str,
                     session: Dict[str, str],
                     remote_submission_id: str,
                     hj2_submission_id: str,
                     countdowns: list
                     ):
    print("Tracking : ", locals())
    http_client = requests.session()

    def update_status(judge_result, message, extra_status=""):
        http_client.post(urljoin(config.WEB_URL, "/api/judge/update"), data={
            "uuid": config.JUDGER_UUID, "judge_result": encode_json(judge_result), "submission_id": hj2_submission_id, "message": message, "extra_status": extra_status})

    # 抛出异常时调用

    def on_failure(exc, task_id, args, kwargs, einfo):
        update_status({}, f"{exc}: {einfo}", "unaccepted")
    self.on_failure = on_failure
    # module =
    client: JudgeClient = JUDGE_CLIENTS[oj_type]
    session_object = client.as_session_data(session)
    track_result = client.get_submission_status(
        session_object, remote_submission_id)
    print("Track result: ", track_result)
    import json
    import jsonpickle
    result = json.JSONDecoder().decode(
        jsonpickle.encode(track_result, unpicklable=False))
    # message=result["message"]+"\n\n远程提交ID: {}".format(remote_submission_id)
    update_status(result["subtasks"], result["message"]+"\n\n远程提交ID: {}\n\n剩余追踪次数:{}".format(remote_submission_id, countdowns),
                  result["extra_status"])
    if result["extra_status"] not in {"waiting", "judging"}:
        update_status(result["subtasks"], result["message"]+"\n\n远程提交ID: {}\n\n评测完成.".format(remote_submission_id),
                      result["extra_status"])
        return
    if countdowns:
        last = countdowns.pop()
        time.sleep(last)
        app.send_task("judgers.remote.track_submission", [
            oj_type, session, remote_submission_id, hj2_submission_id,  countdowns
        ])
    else:
        update_status(result["subtasks"], result["message"]+"\n\n远程提交ID: {}\n\n已超过追踪时限,请重新提交.".format(remote_submission_id),
                      result["extra_status"])
