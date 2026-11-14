import hmac
import json
import os
import secrets
from threading import Lock
from time import monotonic

from pydantic import BaseModel, ConfigDict, Field


SESSION_COOKIE = "crew_session"
SESSION_SECONDS = 8 * 60 * 60


class CrewLogin(BaseModel):
    model_config = ConfigDict(extra="forbid")
    crew_id: str = Field(max_length=16)
    access_code: str = Field(max_length=256)


class CrewSessions:
    def __init__(self, crew_ids):
        crew_ids = set(crew_ids)
        raw = os.environ.get("CREW_HEALTH_ACCESS_CODES")
        self.codes = None if raw is None else json.loads(raw)
        if self.codes is not None and (
            not isinstance(self.codes, dict)
            or set(self.codes) != crew_ids
            or any(not isinstance(code, str) or not 16 <= len(code) <= 256 for code in self.codes.values())
            or len(set(self.codes.values())) != len(crew_ids)
        ):
            raise ValueError("Configure one distinct access code of 16–256 characters for each crew member.")
        self.sessions = {}
        self.lock = Lock()

    def login(self, login):
        crew_id = login.crew_id.lower()
        expected = self.codes.get(crew_id)
        if expected is None or not hmac.compare_digest(expected.encode(), login.access_code.encode()):
            return None
        token = secrets.token_urlsafe(32)
        with self.lock:
            now = monotonic()
            self.sessions = {key: value for key, value in self.sessions.items() if value[1] > now}
            self.sessions[token] = (crew_id, now + SESSION_SECONDS)
        return token

    def member_id(self, token):
        with self.lock:
            session = self.sessions.get(token)
            if session is not None and session[1] > monotonic():
                return session[0]
            self.sessions.pop(token, None)
        return None

    def logout(self, token):
        with self.lock:
            self.sessions.pop(token, None)
