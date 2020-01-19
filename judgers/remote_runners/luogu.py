from dataclasses import dataclass
from .common import LoginResult, SubmitResult, JudgeClient
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
    def check_login_status(session: LuoguSessionData) -> bool:
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
        import random
        return client.get("https://www.luogu.com.cn/api/verify/captcha?_t={}".format(random.random()), headers=LuoguJudgeClient.headers, cookies=session.as_dict()).content

    @staticmethod
    def get_submit_captcha(session: LuoguSessionData) -> bytes:
        client = requests.session()
        return client.get("https://www.luogu.com.cn/download/captcha", headers=LuoguJudgeClient.headers, cookies=session.as_dict()).content

    @staticmethod
    def login(session: LuoguSessionData, username: str, password: str, captcha: str = None) -> LoginResult:
        if not captcha:
            return LoginResult(ok=False, message="请输入验证码", require_captcha=True, captcha=LuoguJudgeClient.get_login_captcha(session))
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
        print("Login with captcha: ", captcha)
        print("Login response: ", resp.json())
        if not resp.ok:
            resp_data = resp.json()["data"]
            print(resp_data)
            captcha_data = LuoguJudgeClient.get_login_captcha(session)
            with open("qwq.png", "wb") as f:
                f.write(captcha_data)
            return LoginResult(
                False,
                resp_data,
                None,
                require_captcha="验证码错误" in resp_data,
                captcha=captcha_data if ("验证码错误" in resp_data) else None
            )
        print("Response cookies", dict(resp.cookies))
        return LoginResult(True, "登录成功", new_session=LuoguSessionData(session.client_id, resp.cookies["_uid"]))

    @staticmethod
    def submit(session: LuoguSessionData, problem_id: str, code: str, language: str, captcha: str = None) -> SubmitResult:
        client = requests.session()
        csrf_token = re.compile("""<meta name="csrf-token" content="(.*)">""").search(client.get(
            "https://www.luogu.com.cn/auth/login", headers=LuoguJudgeClient.headers, cookies=session.as_dict()).text).groups()[0]
        resp = client.post("https://www.luogu.com.cn/fe/api/problem/submit/"+problem_id,
                           json={
                               "verify": captcha, "enableO2": 0, "lang": int(language), "code": code},
                           cookies=session.as_dict(),
                           headers={"x-csrf-token": csrf_token, "referer": "https://www.luogu.com.cn/problem/" +
                                    problem_id, **LuoguJudgeClient.headers}
                           )
        json_data = resp.json()
        print("Luogu response: ", json_data)
        if not resp.ok:
            return SubmitResult(ok=False,
                                message=json_data["errorMessage"],
                                require_captcha="请过3分钟再尝试" in json_data["errorMessage"],
                                require_login="没有登录" in json_data["errorMessage"],
                                captcha=LuoguJudgeClient.get_submit_captcha(session) if (
                                    "请过3分钟再尝试" in json_data["errorMessage"]) else None
                                )

        return SubmitResult(ok=True, message="提交成功!", require_captcha=False, submit_id=str(json_data["rid"]))

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
        from urllib.parse import unquote
        from json import JSONDecoder, JSONEncoder
        resp = requests.get("https://www.luogu.com.cn/record/"+submission_id,
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
            script = item.text
            break
        regexpr = re.compile(
            r"""JSON.parse\(decodeURIComponent\(\"(.*)\"\)\)""")
        # print(regexpr.search(script).groups()[0])
        content = unquote(regexpr.search(script).groups()[0])
        # print(JSONDecoder().decode(content))
        try:
            luogu_status: Dict[str, str] = JSONDecoder().decode(content)[
                "currentData"]
            print(JSONEncoder().encode(luogu_status))
        except Exception as ex:
            import traceback
            traceback.print_exc()
            return {
                "subtasks": {}, "message": "", "extra_status": "waiting"
            }
        # print(status)
        # print(luogu_status)
        result = {
            "subtasks": {}, "message": "", "extra_status": ""
        }
        if "record" not in luogu_status:
            return {
                "subtasks": {}, "message": "", "extra_status": "waiting"
            }
        result["extra_status"] = hj2_status[luogu_status["record"]
                                            ["status"]]
        if luogu_status["record"]["status"] in {0}:
            return result
        if not luogu_status["record"]["detail"]["compileResult"]["success"]:
            result["message"] = luogu_status["record"]["detail"]["compileResult"]["message"]
            return result
        subtask_count = sum((len(x) for x in luogu_status["testCaseGroup"]))
        for i, subtask in enumerate(luogu_status["record"]["detail"]["judgeResult"]["subtasks"]):
            testcases = []
            current_subtask = {
                "score": 0,
                "status": "waiting",
                "testcases": testcases
            }
            all_ok = True
            has_any_waiting_or_judging = False
            for idx, current in subtask["testCases"].items():
                testcases.append({
                    "memory_cost": current["memory"]*1024,
                    "time_cost": current["time"],
                    "status": hj2_status[current["status"]],
                    "input": "NotAvailable",
                    "output": "NotAvailable",
                    "description": current["description"],
                    "score": current["score"],
                    "full_score": 100//subtask_count
                })
                current_subtask["score"] += current["score"]
                all_ok = all_ok and (current["status"] == 12)
            if all_ok:
                current_subtask["status"] = "accepted"
            elif has_any_waiting_or_judging:
                current_subtask["status"] = "waiting"
            else:
                current_subtask["status"] = "unaccepted"
            result["subtasks"]["Subtask{}".format(
                subtask["id"]+1)] = current_subtask

        return result

    @staticmethod
    def fetch_problem(problem_id: str) -> dict:
        resp = requests.get(
            "https://www.luogu.com.cn/problem/"+str(problem_id), headers=LuoguJudgeClient.headers)
        from bs4 import BeautifulSoup
        import re
        import ast
        from pprint import pprint as print
        from typing import Dict, Tuple, List
        from urllib.parse import unquote
        from datatypes.problem_fetch import ProblemExampleCase, ProblemFetchResult
        import jsonpickle
        import json
        soup = BeautifulSoup(resp.text, "lxml")
        for elem in soup.select("script"):
            if "window._feInjection" in elem.text:
                regexp = re.compile(
                    r"JSON.parse\(decodeURIComponent\(\"(.*)\"\)\)")
                text = regexp.search(elem.text).groups()[0]
                problem_data = json.JSONDecoder().decode(unquote(
                    text))["currentData"]["problem"]
        # result = {
        #     "title": "[洛谷 {}]".format(problem_data["pid"])+" "+problem_data["title"],
        #     "background": problem_data["background"],
        #     "content": problem_data["description"],
        #     "hint": problem_data["hint"],
        #     "inputFormat": problem_data["inputFormat"],
        #     "outputFormat": problem_data["outputFormat"],
        #     "timeLimit": problem_data["limits"]["time"][0],
        #     "memoryLimit": problem_data["limits"]["memory"][0],
        #     "remoteProblemID": problem_data["pid"],
        #     "remoteOJ": "luogu",
        #     "examples": [{"input": val[0], "output":val[1]} for val in problem_data["samples"]]
        # }
        return json.JSONDecoder().decode(
            jsonpickle.dumps(ProblemFetchResult(
                title="[洛谷 {}]".format(problem_data["pid"]) +
                " "+problem_data["title"],
                background=problem_data["background"],
                content=problem_data["description"],
                hint=problem_data["hint"],
                inputFormat=problem_data["inputFormat"],
                outputFormat=problem_data["outputFormat"],
                timeLimit=problem_data["limits"]["time"][0],
                memoryLimit=problem_data["limits"]["memory"][0],
                remoteProblemID=problem_data["pid"],
                remoteOJ="luogu",
                examples=[
                    ProblemExampleCase(
                        input=val[0], output=val[1]
                    ) for val in problem_data["samples"]
                ]
            ), unpicklable=False)
        )


def get_judge_client() -> JudgeClient:
    return LuoguJudgeClient


def as_session_data(data: dict):
    return LuoguSessionData(client_id=data.get("__client_id", None), uid=data.get("_uid", None))
