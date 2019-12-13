from dataclasses import dataclass
from common import LoginResult, SubmitResult, JudgeClient
import requests
import re


@dataclass
class LuoguSessionData:

    client_id: str
    uid: str

    def as_dict(self):
        result = {
            "__client_id": self.client_id
        }
        if self.uid:
            result["_uid"] = self.uid
        return result


class LuoguJudgeClient(JudgeClient):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        "x-requested-with": "XMLHttpRequest"
    }
    @staticmethod
    def has_login(session: LuoguSessionData) -> bool:
        client = requests.session()
        resp = client.get("https://www.luogu.com.cn/record/list",
                          headers=LuoguJudgeClient.headers, cookies=session.as_dict(), allow_redirects=False)
        if resp.status_code == 302 and resp.headers["location"] == "/auth/login":
            return False
        return True

    @staticmethod
    def create_session() -> LuoguSessionData:

        client = requests.session()
        resp = client.get("https://www.luogu.com.cn/auth/login",
                          headers=LuoguJudgeClient.headers)
        return LuoguSessionData(client_id=resp.cookies["__client_id"], uid=None)

    @staticmethod
    def get_login_captcha(session: LuoguSessionData) -> bytes:
        client = requests.session()
        return client.get("https://www.luogu.com.cn/api/verify/captcha?_t=1575787808359.9067", headers=LuoguJudgeClient.headers, cookies=session.as_dict()).content

    @staticmethod
    def get_submit_captcha(session: LuoguSessionData) -> bytes:
        client = requests.session()
        return client.get("https://www.luogu.com.cn/download/captcha", headers=LuoguJudgeClient.headers, cookies=session.as_dict()).content

    @staticmethod
    def login(session: LuoguSessionData, username: str, password: str, captcha: str = None) -> LoginResult:
        if not captcha:
            return LoginResult(ok=False, message="请输入验证码", require_captcha=True)
        client = requests.session()
        regx = re.compile("""<meta name="csrf-token" content="(.*)">""")
        csrf_token = regx.search(client.get(
            "https://www.luogu.com.cn/auth/login", headers=LuoguJudgeClient.headers, cookies=session.as_dict()).text).groups()[0]
        data = {
            "username": username,
            "password": password,
            "captcha": captcha
        }
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36',
            'Accept': '*/*',
            'Accept-Language': 'zh-CN,zh;q=0.9,zh-TW;q=0.8',
            "x-requested-with": "XMLHttpRequest",
            "x-csrf-token": csrf_token,
            "referer": "https://www.luogu.com.cn/auth/login",
            "origin": "https://www.luogu.com.cn/auth/login"
        }
        resp = client.post("https://www.luogu.com.cn/api/auth/userPassLogin",
                           headers=headers, json=data, cookies=session.as_dict())
        if not resp.ok:
            return LoginResult(False, resp.json()["data"], None)
        return LoginResult(True, "登录成功", new_session=LuoguSessionData(session.client_id, resp.cookies["_uid"]))

    @staticmethod
    def submit(session: LuoguSessionData, problem_id: str, code: str, language: str, captcha: str = None) -> SubmitResult:
        client = requests.session()
        csrf_token = re.compile("""<meta name="csrf-token" content="(.*)">""").search(client.get(
            "https://www.luogu.com.cn/auth/login", headers=LuoguJudgeClient.headers, cookies=session.as_dict()).text).groups()[0]
        resp = client.post("https://www.luogu.com.cn/api/problem/submit/"+problem_id,
                           data={
                               "verify": captcha, "enableO2": "", "lang": language, "code": code},
                           cookies=session.as_dict(),
                           headers={"x-csrf-token": csrf_token, "referer": "https://www.luogu.com.cn/problem/" +
                                    problem_id, **LuoguJudgeClient.headers}
                           )
        json_data = resp.json()
        if json_data["status"] != 200:
            return SubmitResult(ok=False, message=json_data["data"], require_captcha="请过3分钟再尝试" in json_data["data"], require_login="没有登录" in json_data["data"])

        return SubmitResult(ok=True, message="提交成功!", require_captcha=False, submit_id=str(json_data["data"]["rid"]))

    @staticmethod
    def logout(session: LuoguSessionData):
        client = requests.session()
        client.get(
            "https://www.luogu.com.cn/api/auth/logout", params={"uid": session.uid}, headers=LuoguJudgeClient.headers, cookies=session.as_dict())

    @staticmethod
    def get_submission_status(session: LuoguSessionData, submission_id: str) -> dict:
        from bs4 import BeautifulSoup
        import re
        import ast
        from pprint import pprint as print
        from typing import Dict, Tuple, List
        resp = requests.get("https://www.luogu.com.cn/recordnew/show/"+submission_id,
                            headers=LuoguJudgeClient.headers, cookies=session.as_dict())
        """
    var flagMap = {
        12: "AC",
        3: "OLE",
        4: "MLE",
        5: "TLE",
        6: "WA",
        7: "RE"
    };
    var longFlagMap = {
        0: "Waiting",
        1: "Judging",
        2: "Compile Error",
        12: "Accepted",
        14: "Unaccepted",
        21: "Hack Success",
        22: "Hack Failure",
        23: "Hack Skipped"
    };
        """
        hj2_status = {
            0: "waiting",
            1: "judging",
            2: "compile_error",
            3: "wrong_answer",
            4: "memory_limit_exceed",
            5: "time_limit_exceed",
            6: "wrong_answer",
            7: "runtime_error",
            12: "accepted",
            14: "unaccepted",
        }
        soup = BeautifulSoup(resp.text, "lxml")
        for item in soup.select("script"):
            if "var showScore = true;" in item.text:
                script = item.text
                break
        regexpr = re.compile(r"""renderData\(\{(.*)\}.*\)""")
        content = "{"+regexpr.search(script).groups()[0]+"}"
        luogu_status: Dict[str, str] = ast.literal_eval(content)
        # print(status)
        result = {
            "subtasks": [], "memory_cost": 0, "time_cost": 0
        }
        for subtask in luogu_status["subtasks"]:
            result["subtasks"].append({
                "memory_cost": subtask["memory"]*1024, "time_cost": subtask["time"], "status": hj2_status[subtask["status"]], "score": subtask["score"], "testcases": []
            })
            result["memory_cost"] = max(
                result["memory_cost"], subtask["memory"]*1024)
            result["time_cost"] += subtask["time"]
        cases: List[Tuple[int, Dict[str, str]]] = []
        for key, value in luogu_status.items():
            if key.startswith("case"):
                cases.append((int(key[4:]), value))
        cases.sort(key=lambda x: x[0])
        for _, testcase in cases:
            current = {
                "message": testcase["desc"], "memory_cost": testcase["memory"]*1024, "time_cost": testcase["time"], "score": testcase["score"], "status": hj2_status[testcase["flag"]]
            }
            result["subtasks"][testcase["subtask"]
                               ]["testcases"].append(current)
        # print(result)
        return result


def get_judge_client()->JudgeClient:
    return LuoguJudgeClient


def as_session_data(data: dict):
    return LuoguSessionData(client_id=data.get("__client_id", None), uid=data.get("_uid", None))
