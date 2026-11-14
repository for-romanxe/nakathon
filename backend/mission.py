from datetime import datetime, timedelta

from pydantic import BaseModel, ConfigDict, Field, model_validator

from backend.seed import DEMO_SOL, MISSION_START


DEMO_TIME = MISSION_START + timedelta(days=DEMO_SOL - 1, hours=6, minutes=12)
WINDOW_HOURS = (8, 20)
WINDOW_DURATION = timedelta(minutes=30)


def active_window(timestamp: datetime) -> str | None:
    start = timestamp.replace(minute=0, second=0, microsecond=0)
    if timestamp.hour in WINDOW_HOURS and timestamp < start + WINDOW_DURATION:
        return start.isoformat()
    return None


def mission_sol(timestamp: datetime) -> int:
    return (timestamp.date() - MISSION_START.date()).days + 1


def mission_status(timestamp: datetime) -> dict:
    windows = [timestamp.replace(hour=hour, minute=0, second=0, microsecond=0)
               for hour in WINDOW_HOURS]
    next_window = next((window for window in windows if window > timestamp),
                       windows[0] + timedelta(days=1))
    return {
        "clock": {"sol": mission_sol(timestamp), "time": timestamp.strftime("%H:%M")},
        "environment": "mars_base",
        "one_way_delay_min": 12,
        "next_window": next_window.strftime("%H:%M"),
    }


class ClockUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sol: int | None = Field(default=None, ge=1, le=10000, strict=True)
    time: str | None = Field(default=None, pattern=r"^(?:[01][0-9]|2[0-3]):[0-5][0-9]$")
    advance: str | None = Field(default=None, pattern=r"^[1-9][0-9]{0,3}[hm]$")

    @model_validator(mode="after")
    def validate_update(self) -> "ClockUpdate":
        if self.advance is not None:
            if self.sol is not None or self.time is not None:
                raise ValueError("Use either advance or sol and time.")
        elif self.sol is None or self.time is None:
            raise ValueError("Both sol and time are required.")
        return self

    def apply(self, timestamp: datetime) -> datetime:
        if self.advance is not None:
            amount = int(self.advance[:-1])
            minutes = amount * 60 if self.advance.endswith("h") else amount
            return timestamp + timedelta(minutes=minutes)
        hour, minute = map(int, self.time.split(":"))
        return MISSION_START + timedelta(days=self.sol - 1, hours=hour, minutes=minute)
