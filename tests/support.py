"""Sealed hand reports and an independent declarative transition-table oracle."""

import copy
import hashlib
import json
from pathlib import Path

FIXTURE_SHA = "95f24e80b3c2198904ba03dd32f4d8696122f1a9d4ed66920f19294d25529e64"
FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "cases.json"
OBSERVATION = {
    ("closed", "success"): "clear_failures",
    ("closed", "failure"): "count_failure",
    ("closed", "ignored"): "neutral",
    ("probe", "success"): "count_recovery",
    ("probe", "failure"): "reopen",
    ("probe", "ignored"): "neutral",
}


def cases():
    raw = FIXTURE_PATH.read_bytes()
    if hashlib.sha256(raw).hexdigest() != FIXTURE_SHA:
        raise ValueError("frozen fixture mismatch")
    return json.loads(raw)["cases"]


def document(actions=(("attempt", 1, 0, None),), policy=(2, 10, 2)):
    return {"schema_version": 1, "source_kind": "synthetic", "profile": "breaker-serial-probe/1",
            "breaker_id": "lab-breaker-0001", "policy": dict(zip(
                ("failure_threshold", "cooldown_ms", "success_threshold"), policy, strict=True)),
            "actions": [{"action_id": f"lab-action-{index:04d}", "kind": kind,
                         "attempt_id": f"lab-attempt-{attempt:04d}", "time_ms": timestamp,
                         **({"outcome": outcome} if kind == "complete" else {})}
                        for index, (kind, attempt, timestamp, outcome) in enumerate(actions)]}


def encode(doc):
    return json.dumps(doc, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def table_oracle(doc):
    """Independent table + numeric-mode replay; no production helpers/imports.

    Returns per-action snapshots or 'trace.invalid'. Assumes valid structure.
    """
    mode, failures, recovery, opening, pending, last = 0, 0, 0, None, None, None
    policy = doc["policy"]

    def snapshot():
        return {"mode": ("closed", "open", "half_open")[mode], "closed_failure_streak": failures,
                "recovery_success_streak": recovery, "opened_at_ms": opening,
                "eligible_at_ms": None if opening is None else opening + policy["cooldown_ms"],
                "pending": copy.deepcopy(pending), "last_action_time_ms": last}

    result = []
    for action in doc["actions"]:
        before = snapshot()
        timestamp, identifier = action["time_ms"], action["attempt_id"]
        if action["kind"] == "attempt":
            if mode == 0 and pending is not None:
                return "trace.invalid"
            can_enter = mode != 1 or timestamp - opening >= policy["cooldown_ms"]
            if mode == 1 and can_enter:
                mode, recovery = 2, 0
            accepted = can_enter and pending is None
            if accepted:
                pending = {"attempt_id": identifier, "role": "closed" if mode == 0 else "probe",
                           "admitted_at_ms": timestamp}
        else:
            if pending is None or pending["attempt_id"] != identifier:
                return "trace.invalid"
            rule = OBSERVATION[pending["role"], action["outcome"]]
            pending = None
            if rule == "clear_failures":
                failures = 0
            elif rule == "count_failure":
                failures += 1
                if failures == policy["failure_threshold"]:
                    mode, opening, recovery = 1, timestamp, 0
            elif rule == "reopen":
                mode, opening, recovery = 1, timestamp, 0
            elif rule == "count_recovery":
                recovery += 1
                if recovery == policy["success_threshold"]:
                    mode, failures, recovery, opening = 0, 0, 0, None
        last = timestamp
        result.append((before, snapshot()))
    return result
