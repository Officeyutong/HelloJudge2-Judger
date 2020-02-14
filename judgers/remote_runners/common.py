from dataclasses import dataclass
from typing import Any
from abc import abstractmethod
from datatypes.problem_fetch import ProblemFetchResult
from datatypes.submission_fetch import SubmissionResult
import base64
@dataclass
class LoginResult:
    # 是否登录成功
    ok: bool
    # 发送给前端的消息
    message: str
    # 登陆成功后设置的新Session
    new_session: Any = None
    # 是否需要输入验证码
    require_captcha: bool = None
    # 验证码bytes
    captcha: bytes = None

    def as_dict(self) -> dict:
        return {
            "ok": self.ok,
            "message": self.message,
            "new_session": self.new_session.as_dict() if self.new_session else None,
            "require_login_captcha": self.require_captcha,
            "captcha": base64.encodebytes(self.captcha).decode() if self.captcha else None
        }


@dataclass
class SubmitResult:
    # 是否提交成功
    ok: bool
    # 发送给前端的消息
    message: str
    # 是否需要验证码
    require_captcha: bool = None
    # 提交成功时表示提交ID
    submit_id: str = None
    # 是否需要登录
    require_login: bool = None
    # 提交验证码bytes 
    captcha: bytes = None
    # 是否需要创建新session
    require_new_session: bool = False

    def as_dict(self) -> dict:
        return {
            "submit_id": self.submit_id,
            "ok": self.ok,
            "message": self.message,
            "require_login": self.require_login,
            "require_submit_captcha": self.require_captcha,
            "captcha": base64.encodebytes(self.captcha).decode() if self.captcha else None
        }


class JudgeClient:
    @abstractmethod
    def check_login_status(self, session) -> bool:
        """
        检查用户是否登录。
        返回True表示已登录，返回False表示未登录.
        """
        pass

    @abstractmethod
    def create_session(self):
        """
        创建一个Session对象。
        通常实现为访问远程OJ的主页并记录服务端所设定的SESSIONID之类的东西。

        返回当前客户端所使用的session对象
        """
        pass

    @abstractmethod
    def get_login_captcha(self, session) -> bytes:
        """
        获取一个可用的登录验证码
        返回验证码图片的bytes数组
        """
        pass

    @abstractmethod
    def get_submit_captcha(self, session) -> bytes:
        """
        获取一个可用的提交验证码
        返回验证码图片的bytes数组
        """
        pass

    @abstractmethod
    def login(self, session, username: str, password: str, captcha: str = None) -> LoginResult:
        """
        进行登录
        captcha为登录验证码(不需要请设置为None)
        返回LoginResult，各成员含义见源码
        """
        pass

    @abstractmethod
    def submit(self, session, problem_id: str, code: str, language: str, captcha: str = None) -> SubmitResult:
        """
        进行提交.
        返回SubmitResult，各成员含义见源码。
        """
        pass

    @abstractmethod
    def logout(self, session):
        """
        登出
        """
        pass

    @abstractmethod
    def get_submission_status(self, session, submission_id: str) -> SubmissionResult:
        """
        获取某评测的详细信息
        返回SubmissionResult，各成员含义见源码
        """
        pass

    @abstractmethod
    def fetch_problem(self, problem_id)->ProblemFetchResult:
        """
        爬取题目
        返回ProblemFetchResult，各成员含义见源码
        """
        pass

    @abstractmethod
    def as_session_data(self, data):
        pass
