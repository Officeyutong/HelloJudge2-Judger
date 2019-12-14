from dataclasses import dataclass
from typing import Any
from abc import abstractstaticmethod
@dataclass
class LoginResult:
    ok: bool
    message: str
    new_session: Any = None
    require_captcha: bool = None
    captcha: bytes = None

    def as_dict(self) -> dict:
        return {
            "ok": self.ok, "message": self.message, "new_session": self.new_session.as_dict(), "require_captcha": self.require_captcha
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
        return {"submit_id": self.submit_id,
                "ok": self.ok, "message": self.message, "require_login": self.require_login, "require_captcha": self.require_captcha
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
