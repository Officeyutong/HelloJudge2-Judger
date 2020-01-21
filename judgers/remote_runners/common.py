from dataclasses import dataclass
from typing import Any
from abc import abstractmethod
import base64
@dataclass
class LoginResult:
    ok: bool
    message: str
    new_session: Any = None
    require_captcha: bool = None
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
    ok: bool
    message: str
    require_captcha: bool = None
    submit_id: str = None
    require_login: bool = None
    captcha: bytes = None
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
        pass

    @abstractmethod
    def create_session(self):
        pass

    @abstractmethod
    def get_login_captcha(self, session) -> bytes:
        pass

    @abstractmethod
    def get_submit_captcha(self, session) -> bytes:
        pass

    @abstractmethod
    def login(self, session, username: str, password: str, captcha: str = None) -> LoginResult:
        pass

    @abstractmethod
    def submit(self, session, problem_id: str, code: str, language: str, captcha: str = None) -> SubmitResult:
        pass

    @abstractmethod
    def logout(self, session):
        pass

    @abstractmethod
    def get_submission_status(self, session, submission_id: str) -> dict:
        pass

    @abstractmethod
    def fetch_problem(self, problem_id):
        pass

    @abstractmethod
    def as_session_data(self, data):
        pass
