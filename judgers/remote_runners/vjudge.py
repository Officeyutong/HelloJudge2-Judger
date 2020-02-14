from dataclasses import dataclass
from .common import LoginResult, SubmitResult, JudgeClient
import requests
import re


@dataclass
class VJudgeSessionData:
    JSESSIONID: str = None
    JAX_Q: str = None

    def as_dict(self):
        return {
            "JSESSIONID": self.JSESSIONID,
            "Jax.Q": self.JAX_Q
        }


def get_judge_client() -> JudgeClient:
    return VJudgeJudgeClient


def as_session_data(data: dict):
    return VJudgeSessionData(JSESSIONID=data["JSESSIONID"], JAX_Q=data["Jax.Q"])


class VJudgeJudgeClient(JudgeClient):
    headers = {

    }
    @staticmethod
    def check_login_status(session: VJudgeSessionData) -> bool:
        resp = requests.get("https://vjudge.net/user/checkLogInStatus",
                            headers=VJudgeJudgeClient.headers, cookies=session.as_dict())
        return resp.text == "true"

    @staticmethod
    def create_session() -> VJudgeSessionData:
        resp = requests.get("https://vjudge.net/",
                            headers=VJudgeJudgeClient.headers)
        return VJudgeSessionData(JSESSIONID=resp.cookies["JSESSIONID"])

    @staticmethod
    def login(session: VJudgeSessionData, username: str, password: str, captcha: str = None) -> LoginResult:
        resp = requests.post("https://vjudge.net/user/login", headers=VJudgeJudgeClient.headers, cookies=session.as_dict(), data={
            "username": username, "password": password
        })
        if not resp.ok:
            return LoginResult(False, message="登录失败!\n"+resp.text)
        return LoginResult(True, message="登录成功!", new_session=VJudgeSessionData(session.JSESSIONID, resp.cookies["Jax.Q"]))

    @staticmethod
    def get_login_captcha(session: VJudgeSessionData) -> bytes:
        raise NotImplementedError("VJudge不需要使用此功能")

    @staticmethod
    def get_submit_captcha(session: VJudgeSessionData) -> bytes:
        raise NotImplementedError("VJudge不需要使用此功能")

    @staticmethod
    def logout(session: VJudgeSessionData):
        resp = requests.post("https://vjudge.net/user/logout",
                             headers=VJudgeJudgeClient.headers, cookies=session.as_dict())
        return resp.ok

    @staticmethod
    def fetch_problem(problem_id: str) -> dict:
        client = requests.session()
        from bs4 import BeautifulSoup

        soup_main = BeautifulSoup(client.get(
            "https://vjudge.net/problem/"+problem_id, headers=VJudgeJudgeClient.headers).text, "lxml")
        description_url = soup_main.select(
            "#frame-description")[0].attrs["src"]
        # print(description)
        description_soup = BeautifulSoup(client.get(
            "https://vjudge.net/"+description_url, headers=VJudgeJudgeClient.headers).text, "lxml")
        print(description_soup)