from .common import JudgeClient, LoginResult, SubmitResult
from dataclasses import dataclass
from datatypes.problem_fetch import ProblemExampleCase, ProblemFetchResult
import requests
@dataclass
class UOJSessionData:
    UOJSESSID: str
    uoj_remember_token: str = None
    uoj_remember_token_checksum: str = None
    uoj_username: str = None
    uoj_username_checksum: str = None

    def as_dict(self) -> dict:
        return {
            "UOJSESSID": self.UOJSESSID,
            "uoj_remember_token": self.uoj_remember_token,
            "uoj_remember_token_checksum": self.uoj_remember_token_checksum,
            "uoj_username": self.uoj_username,
            "uoj_username_checksum": self.uoj_username_checksum
        }


class UOJJudgeClient(JudgeClient):
    headers = {
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.117 Safari/537.36"
    }

    def __init__(self, base_url):
        """
        @param: base_url
        所使用的UOJ的根URL
        """
        self.base_url = base_url

    def make_salted_password(self, password: str, salt: str):
        import hmac
        import hashlib
        message = password.encode("utf-8")
        return hmac.new(salt.encode("utf-8"), message, digestmod=hashlib.md5).hexdigest()

    def make_url(self, addr):
        from urllib.parse import urljoin
        return urljoin(self.base_url, addr)

    def check_login_status(self, session) -> bool:
        with requests.get(self.base_url, cookies=session.as_dict()) as urlf:
            text = urlf.content.decode("utf-8")
            # print(text)
            return "登出</a>" in text

    def create_session(self) -> UOJSessionData:
        with requests.get(self.base_url) as urlf:
            return UOJSessionData(
                UOJSESSID=urlf.cookies["UOJSESSID"]
            )

    def login(self, session: UOJSessionData, username: str, password: str, captcha: str = None) -> LoginResult:
        client = requests.session()
        client.cookies.update(session.as_dict())
        # print(client.cookies)
        with client.get(self.make_url("/login"), cookies=session.as_dict(), headers=self.headers) as urlf:
            import re
            expr = re.compile(r"_token : \"(.*)\",")
            login_token = expr.search(urlf.text).groups()[0]
            salt = re.compile(
                r"md5\(\$\('#input-password'\)\.val\(\), \"(.*)\"\)").search(urlf.text).groups()[0]

        # print(client.)
        # print("login token = ", f'"{login_token}"')
        # print("salt = ", f'"{salt}"')
        with client.post(self.make_url("/login"), data={
                "username": username,
                "_token": login_token,
                "login": "",
                "password": self.make_salted_password(password, salt)
        }, cookies=session.as_dict(), headers=self.headers) as urlf:
            # print(client.cookies)
            message = urlf.text
            # print("message = ", message)
            if message == "ok":
                return LoginResult(
                    ok=True,
                    message="登录成功",
                    new_session=UOJSessionData(
                        UOJSESSID=session.UOJSESSID,
                        uoj_username=urlf.cookies["uoj_username"],
                        uoj_username_checksum=urlf.cookies["uoj_username_checksum"],
                        uoj_remember_token=urlf.cookies["uoj_remember_token"],
                        uoj_remember_token_checksum=urlf.cookies["uoj_remember_token"],
                    ),
                    require_captcha=False,
                    captcha=None
                )
            else:
                message_mapping = {
                    "banned": "用户已封禁",
                    "expired": "请尝试重新登录",
                    "failed": "用户名或密码错误"
                }
                return LoginResult(
                    ok=False,
                    message=message_mapping.get(message),
                    new_session=session
                )

    def fetch_problem(self, problem_id: str) -> ProblemFetchResult:
        import bs4
        import jsonpickle
        import json
        with requests.get(self.make_url("/problem/"+problem_id)) as urlf:
            soup = bs4.BeautifulSoup(urlf.content.decode("utf-8"), "lxml")
        title = soup.select_one("h1.page-header.text-center").string
        description = "".join(
            (str(x) for x in soup.select_one("article.top-buffer-md").contents))
        return ProblemFetchResult(
            title=title,
            background="",
            content=description,
            hint="",
            inputFormat="",
            outputFormat="",
            timeLimit=-1,
            memoryLimit=-1,
            remoteProblemID=problem_id,
            remoteOJ="uoj",
            examples=None
        )
        # return description

    def submit(self, session: UOJSessionData, problem_id: str, code: str, language: str, captcha: str = None) -> SubmitResult:
        client = requests.session()
        client.cookies.update(session.as_dict())
        with client.get(self.make_url("/problem/"+problem_id)) as urlf:
            import bs4
            soup = bs4.BeautifulSoup(urlf.content.decode("utf-8"), "lxml")
        form = soup.select_one("#form-answer")
        token = form.select_one("[name=_token]").attrs["value"]
        print("Token =", token)
        # with client.post(self.make_url("/problem/"+problem_id), cookies=session.as_dict(), data={"check-answer": ""}, headers=self.headers) as urlf:
        #     print(urlf.content.decode("utf-8"))
        with client.post(self.make_url("/problem/"+problem_id), data={
            "_token": token,
            "answer_answer_language": language,
            "answer_answer_upload_type": "editor",
            "answer_answer_editor": code,
            "submit-answer": "answer",
            "answer_answer_file": ""
        }, headers=self.headers) as urlf:
            if not urlf.url.endswith("submissions"):
                import re
                error_text = re.compile(
                    r"<div class=\"uoj-content\">([\s\S]*?)<\/div>").search(urlf.content.decode()).groups()[0]
                return SubmitResult(ok=False, message=error_text, require_captcha=False, require_login=False, require_new_session=False)
            with client.get(self.make_url("/submissions?submitter="+session.uoj_username)) as urlf:
                import bs4
                soup = bs4.BeautifulSoup(urlf.content.decode(), "lxml")
                submission_id = soup.select_one("td>a").string.replace("#", "")
                # print(submission_id)
                return SubmitResult(
                    ok=True,
                    message="提交成功",
                    submit_id=submission_id
                )
            # return urlf
            # print(urlf.content.decode("utf-8"))

    def get_submission_status(self, session: UOJSessionData, submission_id: str) -> dict:
        client = requests.session()
        client.cookies.update(session.as_dict())
        with client.get(self.make_url("/submission/"+submission_id)) as urlf:
            import bs4
            soup = bs4.BeautifulSoup(urlf.content.decode(), "lxml")
        score = soup.select_one(".uoj-score").string

    def as_session_data(self, data: dict) -> UOJSessionData:
        return UOJSessionData(
            UOJSESSID=data.get("UOJSESSID", None),
            uoj_remember_token=data.get("uoj_remember_token", None),
            uoj_remember_token_checksum=data.get(
                "uoj_remember_token_checksum", None),
            uoj_username=data.get("uoj_username", None),
            uoj_username_checksum=data.get("uoj_username_checksum", None)
        )


def get_judge_client() -> JudgeClient:
    return UOJJudgeClient
