from dataclasses import dataclass
from .common import LoginResult, SubmitResult, JudgeClient
import requests
import re
from datatypes.problem_fetch import ProblemFetchResult, ProblemExampleCase

@dataclass
class POJSessionData:
    JSESSIONID: str
    # pgv_pvi: str
    # pgv_si: str
    username: str = None

    def as_dict(self) -> dict:
        return {
            "JSESSIONID": self.JSESSIONID,
            "_username": self.username,
            # "pgv_pvi": self.pgv_pvi,
            # "pgv_si": self.pgv_si
        }


class POJJudgeClient(JudgeClient):
    def check_login_status(self, session: POJSessionData) -> bool:
        print("Checking ", session)
        with requests.get("http://poj.org", cookies=session.as_dict()) as urlf:
            print("result = ", "<td>Password:</td>" not in urlf.text)
            return "Password:" not in urlf.text

    def create_session(self):
        with requests.get("http://poj.org") as urlf:
            return POJSessionData(
                JSESSIONID=urlf.cookies["JSESSIONID"],
                # pgv_pvi=urlf.cookies["pgv_pvi"],
            )

    def login(self, session: POJSessionData, username: str, password: str, captcha: str = None) -> LoginResult:
        if not session.JSESSIONID:
            return LoginResult(ok=False, message="请再次点击提交按钮")
        with requests.post("http://poj.org/login", cookies=session.as_dict(), data={
            "user_id1": username,
            "password1": password,
            "B1": "login",
            "url": "%2F"
        }) as urlf:
            print(urlf.text)
            if urlf.ok:
                return LoginResult(
                    True, "登陆成功", POJSessionData(
                        JSESSIONID=session.JSESSIONID,
                        username=username,),
                    # pgv_pvi=urlf.cookies["pgv_pvi"],
                    # pgv_si=urlf.cookies["pgv_si"])
                    False
                )
            else:
                return LoginResult(False, urlf.text)

    def fetch_problem(self, problem_id: str) -> ProblemFetchResult:
        import jsonpickle
        
        from bs4 import BeautifulSoup
        import json
        with requests.get("http://poj.org/problem?id="+problem_id) as urlf:
            soup = BeautifulSoup(urlf.text, "lxml")
        time_limit: int = int(
            str((soup.find(text="Time Limit:").parent.next_sibling)).replace("MS", "").strip())
        memory_limit: int = int(
            str((soup.find(text="Memory Limit:").parent.next_sibling)).replace("K", "").strip())
        case_time_limit: int = int(
            str((soup.find(text="Case Time Limit:").parent.next_sibling)).replace("MS", "").strip()) if soup.find(text="Case Time Limit:") else None
        return ProblemFetchResult(
                title=f"[POJ{problem_id}]"+soup.select_one(".ptt").text,
                background=(
                    f"数据点时间限制: {case_time_limit}ms" if case_time_limit else ""),
                content="".join(
                    map(str, soup.find(text="Description").parent.next_sibling.contents)),
                hint="".join(
                    map(str, soup.find(text="Hint").parent.next_sibling.contents)) if soup.find(text="Hint") else "",
                inputFormat="".join(
                    map(str, soup.find(text="Input").parent.next_sibling.contents)),
                outputFormat="".join(
                    map(str, soup.find(text="Output").parent.next_sibling.contents)),
                timeLimit=time_limit,
                memoryLimit=memory_limit,
                remoteProblemID=problem_id,
                remoteOJ="poj",
                examples=[
                    ProblemExampleCase(
                        input="".join(
                            map(str, soup.find(text="Sample Input").parent.next_sibling.contents)),
                        output="".join(
                            map(str, soup.find(text="Sample Output").parent.next_sibling.contents)),
                    )
                ]
            )

    def submit(self, session: POJSessionData, problem_id: str, code: str, language: str, captcha: str = None) -> SubmitResult:
        import base64
        import bs4

        with requests.post("http://poj.org/submit", cookies=session.as_dict(), data={
            "problem_id": problem_id,
            "language": language,
            "submit": "Submit",
            "source": base64.encodebytes(code.encode()).decode().strip(),
            "encoded": "1"
        }) as urlf:
            if urlf.ok:
                print(urlf.text)
                if "Error Occurred" in urlf.text:
                    if "Please login first." in urlf.text:
                        return SubmitResult(ok=False, require_login=True, message="请再次提交", require_new_session=True)
                    import re
                    regexpr = re.compile(r"<li>(.*)</li>")
                    if urlf.url != "http://poj.org/status":
                        return SubmitResult(ok=False, message=regexpr.search(urlf.text).groups()[0])

                with requests.get(f"http://poj.org/status?problem_id=&user_id={session.username}&result=&language=", cookies=session.as_dict()) as _urlf:
                    soup = bs4.BeautifulSoup(_urlf.text, "lxml")
                td = soup.select_one("table.a tr:nth-child(2) td")
                return SubmitResult(
                    ok=True,
                    message="提交成功",
                    require_captcha=False,
                    submit_id=td.text
                )
            else:
                return SubmitResult(
                    ok=False,
                    message=urlf.text
                )

    def get_submission_status(self, session: POJSessionData, submission_id: str) -> dict:
        import bs4
        with requests.get("http://poj.org/showsource?solution_id="+submission_id, cookies=session.as_dict()) as urlf:
            soup = bs4.BeautifulSoup(urlf.text, "lxml")
        status_mapping = {
            "Accepted": "accepted",
            "Time Limit Exceeded": "time_limit_exceed",
            "Memory Limit Exceeded": "memory_limit_exceed",
            "Wrong Answer": "wrong_answer",
            "Runtime Error": "runtime_error",
            "Output Limit Exceeded": "wrong_answer",
            "Compile Error": "compile_error",
            "Presentation Error": "wrong_answer",
            "Running & Judging": "judging"
        }
        memory_cost = (soup.find(
            string="Memory:").parent.next_sibling.string.replace("K", "").strip())
        time_cost = (
            soup.find(string="Time:").parent.next_sibling.string.replace("MS", "").strip())
        if memory_cost == "N/A":
            memory_cost = 0
        else:
            memory_cost = int(memory_cost)
        if time_cost == "N/A":
            time_cost = 0
        else:
            time_cost = int(memory_cost)

        status = status_mapping[soup.find(
            string="Result:").parent.parent.select_one("font").string]
        result = {
            "subtasks": {
                "默认子任务": {
                    "score": 0 if status != "accepted" else 100,
                    "status": status,
                    "testcases": [
                        {
                            "memory_cost": memory_cost,
                            "time_cost": time_cost,
                            "status": status,
                            "input": "NotAvailable",
                            "output": "NotAvailable",
                            "description": "",
                            "score": 0 if status != "accepted" else 100,
                            "full_score": 100
                        }
                    ]
                }
            },
            "message": "",
            "extra_status": ""
        }
        if status in {"compile_error", "accepted", "judging"}:
            result["extra_status"] = status
        else:
            result["extra_status"] = "unaccepted"
        return result
        # print(locals())

    def as_session_data(self, data: dict):
        return POJSessionData(
            JSESSIONID=data.get("JSESSIONID", None),
            username=data.get("_username", None),
            # pgv_pvi=data.get("pgv_pvi", None),
            # pgv_si=data.get("pgv_si", None)
        )


def get_judge_client() -> JudgeClient:
    return POJJudgeClient
