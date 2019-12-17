from dataclasses import dataclass
from typing import Any
from abc import abstractstaticmethod
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
    @abstractstaticmethod
    def has_login(session) -> bool:
        pass

    @abstractstaticmethod
    def create_session():
        pass

    @abstractstaticmethod
    def get_login_captcha(session) -> bytes:
        pass

    @abstractstaticmethod
    def get_submit_captcha(session) -> bytes:
        pass

    @abstractstaticmethod
    def login(session, username: str, password: str, captcha: str = None) -> LoginResult:
        pass

    @abstractstaticmethod
    def submit(session, problem_id: str, code: str, language: str, captcha: str = None) -> SubmitResult:
        pass

    @abstractstaticmethod
    def logout(session):
        pass

    @abstractstaticmethod
    def get_submission_status(session, submission_id: str) -> dict:
        pass

    @abstractstaticmethod
    def fetch_problem(problem_id):
        pass
