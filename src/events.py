"""Step-level event model for the autonomous diagnostic.

Each signup attempt emits a timeline of events. The diagnostic collector
records them and later scores each run for smoothness, friction, and
which detection signals Google showed.

Events are lightweight dicts so they can travel across process boundaries
and be JSON-serialized for reports and for re-running analysis later.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


STEP_NAMES = [
    "entry",
    "personal_info",
    "birthday",
    "gender",
    "email",
    "password",
    "phone_or_qr",
    "qr",
    "captcha",
    "phone_sms",
    "phone_skip",
    "otp_prompted",
    "otp_sent",
    "creation",
    "final",
]


@dataclass
class Event:
    kind: str  # StepEnter, StepExit, QRSeen, CaptchaSeen, PhonePrompt, ...
    step: str  # which phase of the flow; 'phone_or_qr' is the decision gate
    timestamp: float = field(default_factory=lambda: datetime.now(timezone.utc).timestamp())
    message: str = ""
    # structured payload for later analysis
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kind": self.kind,
            "step": self.step,
            "ts": self.timestamp,
            "message": self.message,
            "payload": self.payload,
        }


class EventTimeline:
    """Append-only list of events from one signup attempt.

    Kept small: only high-signal events, not every mouse move.
    """

    def __init__(self) -> None:
        self.events: List[Event] = []

    def emit(self, kind: str, step: str, message: str = "",
             payload: Optional[Dict[str, Any]] = None) -> None:
        self.events.append(Event(kind=kind, step=step,
                                 message=message,
                                 payload=payload or {}))

    def dump(self) -> List[Dict[str, Any]]:
        return [e.to_dict() for e in self.events]

    def chronological(self) -> List[Dict[str, Any]]:
        return sorted(self.dump(), key=lambda e: e["ts"])
