"""Frozen admitted records and bounded, owned-outcome serial transitions."""

from dataclasses import dataclass
import json
import re

from .admission import LabError, MAX_OUTPUT, check_tree, parse

PROFILE = "breaker-serial-probe/1"
MAX_ACTIONS = 128
MAX_ATTEMPTS = 64
MAX_COMPLETIONS = 64
MAX_TIME = 3_600_000
SUMMARY_FIELDS = ("actions", "attempts", "admitted", "denied", "closed_admissions",
                  "probe_admissions", "completed", "success_observations", "failure_observations",
                  "ignored_observations", "opens", "closes", "half_open_entries", "pending")
LABELS = {kind: re.compile("lab-" + kind + r"-[0-9]{4}", re.ASCII)
          for kind in ("breaker", "action", "attempt")}


@dataclass(frozen=True)
class Policy:
    failure_threshold: int
    cooldown_ms: int
    success_threshold: int


@dataclass(frozen=True)
class Action:
    action_id: str
    kind: str
    attempt_id: str
    time_ms: int
    outcome: str | None


@dataclass(frozen=True)
class Trace:
    breaker_id: str
    policy: Policy
    actions: tuple[Action, ...]


@dataclass(frozen=True)
class Pending:
    attempt_id: str
    role: str
    admitted_at_ms: int


@dataclass
class State:
    mode: str = "closed"
    closed_failure_streak: int = 0
    recovery_success_streak: int = 0
    opened_at_ms: int | None = None
    pending: Pending | None = None
    last_action_time_ms: int | None = None


def _shape(value, names):
    if type(value) is not dict or set(value) != set(names):
        raise LabError("schema.invalid")


def _integer(value, minimum, maximum):
    if type(value) is not int or not minimum <= value <= maximum:
        raise LabError("schema.invalid")
    return value


def _enum(value, values):
    if type(value) is not str or value not in values:
        raise LabError("schema.invalid")
    return value


def _label(value, kind):
    if type(value) is not str or LABELS[kind].fullmatch(value) is None:
        raise LabError("schema.invalid")
    return value


def _validate(document):
    """Internal: exact bounded tree admitted before full structural validation."""
    _shape(document, ("schema_version", "source_kind", "profile", "breaker_id", "policy", "actions"))
    _integer(document["schema_version"], 1, 1)
    _enum(document["source_kind"], {"synthetic"})
    _enum(document["profile"], {PROFILE})
    breaker = _label(document["breaker_id"], "breaker")
    policy = document["policy"]
    _shape(policy, ("failure_threshold", "cooldown_ms", "success_threshold"))
    admitted_policy = Policy(_integer(policy["failure_threshold"], 1, 5),
                             _integer(policy["cooldown_ms"], 1, 60_000),
                             _integer(policy["success_threshold"], 1, 3))
    actions = document["actions"]
    if type(actions) is not list:
        raise LabError("schema.invalid")
    if len(actions) > MAX_ACTIONS:
        raise LabError("input.limit")
    action_ids, attempt_ids, records = set(), set(), []
    previous = completions = 0
    for item in actions:
        if type(item) is not dict:
            raise LabError("schema.invalid")
        kind = _enum(item.get("kind"), {"attempt", "complete"})
        fields = ("action_id", "kind", "attempt_id", "time_ms")
        _shape(item, fields + (("outcome",) if kind == "complete" else ()))
        action_id = _label(item["action_id"], "action")
        attempt_id = _label(item["attempt_id"], "attempt")
        timestamp = _integer(item["time_ms"], 0, MAX_TIME)
        if action_id in action_ids or timestamp < previous:
            raise LabError("schema.invalid")
        action_ids.add(action_id)
        previous = timestamp
        outcome = None
        if kind == "attempt":
            if attempt_id in attempt_ids:
                raise LabError("schema.invalid")
            attempt_ids.add(attempt_id)
            if len(attempt_ids) > MAX_ATTEMPTS:
                raise LabError("input.limit")
        else:
            completions += 1
            if completions > MAX_COMPLETIONS:
                raise LabError("input.limit")
            outcome = _enum(item["outcome"], {"success", "failure", "ignored"})
        records.append(Action(action_id, kind, attempt_id, timestamp, outcome))
    return Trace(breaker, admitted_policy, tuple(records))


def _snapshot(state, policy):
    pending = state.pending
    return {"mode": state.mode, "closed_failure_streak": state.closed_failure_streak,
            "recovery_success_streak": state.recovery_success_streak, "opened_at_ms": state.opened_at_ms,
            "eligible_at_ms": None if state.opened_at_ms is None else state.opened_at_ms + policy.cooldown_ms,
            "pending": None if pending is None else {"attempt_id": pending.attempt_id, "role": pending.role,
                                                     "admitted_at_ms": pending.admitted_at_ms},
            "last_action_time_ms": state.last_action_time_ms}


def _switch(state, mode, summary, transitions):
    transitions.append(state.mode + "->" + mode)
    state.mode = mode
    summary[{"open": "opens", "closed": "closes", "half_open": "half_open_entries"}[mode]] += 1


def _open(state, timestamp, summary, transitions):
    _switch(state, "open", summary, transitions)
    state.opened_at_ms = timestamp
    state.recovery_success_streak = 0


def _attempt(state, policy, action, summary, transitions):
    summary["attempts"] += 1
    if state.mode == "closed":
        if state.pending is not None:
            raise LabError("trace.invalid")
        role, reason = "closed", "closed_allowed"
    else:
        if state.mode == "open":
            if action.time_ms < state.opened_at_ms + policy.cooldown_ms:
                summary["denied"] += 1
                return "deny", "cooldown_active"
            _switch(state, "half_open", summary, transitions)
            state.recovery_success_streak = 0
        if state.pending is not None:
            summary["denied"] += 1
            return "deny", "probe_in_flight"
        role, reason = "probe", "probe_allowed"
    state.pending = Pending(action.attempt_id, role, action.time_ms)
    summary["admitted"] += 1
    summary[role + "_admissions"] += 1
    return "admit", reason


def _complete(state, policy, action, summary, transitions):
    pending = state.pending
    if pending is None or pending.attempt_id != action.attempt_id:
        raise LabError("trace.invalid")
    role = pending.role
    state.pending = None
    summary["completed"] += 1
    summary[action.outcome + "_observations"] += 1
    if role == "closed":
        if action.outcome == "success":
            state.closed_failure_streak = 0
        elif action.outcome == "failure":
            state.closed_failure_streak += 1
            if state.closed_failure_streak >= policy.failure_threshold:
                _open(state, action.time_ms, summary, transitions)
    elif action.outcome == "failure":
        _open(state, action.time_ms, summary, transitions)
    elif action.outcome == "success":
        state.recovery_success_streak += 1
        if state.recovery_success_streak >= policy.success_threshold:
            _switch(state, "closed", summary, transitions)
            state.closed_failure_streak = state.recovery_success_streak = 0
            state.opened_at_ms = None
    # Ignored is deliberately neutral in both roles, never a success handler.
    return "observed", role + "_" + action.outcome


def _simulate(trace):
    state, rows = State(), []
    summary = {field: 0 for field in SUMMARY_FIELDS}
    for action in trace.actions:
        before, transitions = _snapshot(state, trace.policy), []
        handler = _attempt if action.kind == "attempt" else _complete
        decision, reason = handler(state, trace.policy, action, summary, transitions)
        state.last_action_time_ms = action.time_ms
        summary["actions"] += 1
        rows.append({"action_id": action.action_id, "kind": action.kind, "attempt_id": action.attempt_id,
                     "time_ms": action.time_ms, "result": {"decision": decision, "reason": reason,
                                                            "outcome": action.outcome},
                     "transitions": transitions, "before": before, "after": _snapshot(state, trace.policy)})
    summary["pending"] = int(state.pending is not None)
    report = {"schema_version": 1, "source_kind": "synthetic", "profile": PROFILE,
              "breaker_id": trace.breaker_id, "policy": {"failure_threshold": trace.policy.failure_threshold,
               "cooldown_ms": trace.policy.cooldown_ms, "success_threshold": trace.policy.success_threshold},
              "status": "modeled", "effects": "unmodeled", "actual_service_health": "unverified",
              "rows": rows, "summary": summary, "final_state": _snapshot(state, trace.policy)}
    render(report)  # Enforce report cap for library callers as well as CLI sinks.
    return report


def model(raw: bytes) -> dict:
    """Admit bytes, validate all structure, replay completely, then return report.

    Late semantic errors discard provisional rows. No real calls/time/effects.
    """
    return _simulate(_validate(parse(raw)))


def model_document(document) -> dict:
    """Accept only bounded exact builtin JSON trees, without caller mutation.

    Native allocation/concurrent mutation is not isolated. Alias visits count;
    cyclic/custom objects are rejected before canonical serialization or hooks.
    """
    check_tree(document)
    raw = json.dumps(document, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return model(raw)


def render(report: dict) -> str:
    """Internal report serialization; defensive cap, never truncation."""
    output = json.dumps(report, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"
    if len(output.encode("utf-8")) > MAX_OUTPUT:
        raise LabError("output.error")
    return output
