#!/usr/bin/env python3
"""
silent-agent-guard

A tiny local-first guardrail for AI agents.

It decides whether an event deserves an LLM call.

Low-signal event:
-> [STATUS_SILENT]
-> no LLM call
-> no notification
-> no token waste

Critical event:
-> [STATUS_TRIGGERED]
-> generate a compact 28-line plain-text escalation card

Run:
python silent_guard.py
"""

from **future** import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

SEVERITY_SCORE: Dict[str, int] = {
"debug": 0,
"info": 1,
"notice": 1,
"warning": 2,
"critical": 3,
"fatal": 4,
}

@dataclass(frozen=True)
class AgentEvent:
"""
Generic public event schema.

```
No private business fields.
No API keys.
No provider-specific payloads.
"""

event_name: str
severity: str
metrics_snapshot: Dict[str, Any] = field(default_factory=dict)
```

@dataclass(frozen=True)
class GuardPolicy:
"""
Local deterministic policy.

```
Tune these numbers for your own runtime.
"""

min_severity_to_fire: str = "critical"
risk_score_threshold: float = 0.85
error_count_threshold: int = 3
latency_ms_threshold: int = 3000
token_estimate_threshold: int = 2500
drift_score_threshold: float = 0.75
```

@dataclass(frozen=True)
class GuardDecision:
fire: bool
status: str
reason: str
matched_rules: Tuple[str, ...]

def _as_float(value: Any, default: float = 0.0) -> float:
try:
return float(value)
except (TypeError, ValueError):
return default

def _as_int(value: Any, default: int = 0) -> int:
try:
return int(value)
except (TypeError, ValueError):
return default

def should_fire_llm(event: AgentEvent, policy: GuardPolicy) -> GuardDecision:
"""
Decide whether this event deserves an LLM call.

```
This function is intentionally deterministic.
It should run locally before any expensive model invocation.
"""

severity = event.severity.strip().lower()
severity_score = SEVERITY_SCORE.get(severity, 0)
required_score = SEVERITY_SCORE.get(policy.min_severity_to_fire, 3)

metrics = event.metrics_snapshot

risk_score = _as_float(metrics.get("risk_score"))
error_count = _as_int(metrics.get("error_count"))
latency_ms = _as_int(metrics.get("latency_ms"))
token_estimate = _as_int(metrics.get("token_estimate"))
drift_score = _as_float(metrics.get("drift_score"))

matched_rules: List[str] = []

if severity_score >= required_score:
    matched_rules.append(
        f"severity_score:{severity_score}>={required_score}"
    )

if risk_score >= policy.risk_score_threshold:
    matched_rules.append(
        f"risk_score:{risk_score:.2f}>={policy.risk_score_threshold:.2f}"
    )

if error_count >= policy.error_count_threshold:
    matched_rules.append(
        f"error_count:{error_count}>={policy.error_count_threshold}"
    )

if latency_ms >= policy.latency_ms_threshold:
    matched_rules.append(
        f"latency_ms:{latency_ms}>={policy.latency_ms_threshold}"
    )

if token_estimate >= policy.token_estimate_threshold:
    matched_rules.append(
        f"token_estimate:{token_estimate}>={policy.token_estimate_threshold}"
    )

if drift_score >= policy.drift_score_threshold:
    matched_rules.append(
        f"drift_score:{drift_score:.2f}>={policy.drift_score_threshold:.2f}"
    )

if matched_rules:
    return GuardDecision(
        fire=True,
        status="[STATUS_TRIGGERED]",
        reason="local_threshold_crossed",
        matched_rules=tuple(matched_rules),
    )

return GuardDecision(
    fire=False,
    status="[STATUS_SILENT]",
    reason="below_local_threshold",
    matched_rules=(),
)
```

def _format_metrics(metrics: Dict[str, Any]) -> str:
if not metrics:
return "none"

```
parts = []
for key in sorted(metrics):
    parts.append(f"{key}={metrics[key]}")
return ", ".join(parts)
```

def generate_28_line_card(
event: AgentEvent,
decision: GuardDecision,
policy: GuardPolicy,
) -> str:
"""
Generate a strict 28-line plain-text escalation card.

```
This card is designed to be small enough to send to an LLM,
a human operator, a chat channel, or an incident log.
"""

now = datetime.now(timezone.utc).isoformat(timespec="seconds")
metrics = event.metrics_snapshot
risk_score = _as_float(metrics.get("risk_score"))
error_count = _as_int(metrics.get("error_count"))
latency_ms = _as_int(metrics.get("latency_ms"))
token_estimate = _as_int(metrics.get("token_estimate"))
drift_score = _as_float(metrics.get("drift_score"))

matched = "; ".join(decision.matched_rules) or "none"

lines = [
    "01 | [STATUS_TRIGGERED]",
    f"02 | event_name: {event.event_name}",
    f"03 | severity: {event.severity}",
    f"04 | decision_reason: {decision.reason}",
    f"05 | utc_time: {now}",
    f"06 | metric_risk_score: {risk_score:.2f}",
    f"07 | metric_error_count: {error_count}",
    f"08 | metric_latency_ms: {latency_ms}",
    f"09 | metric_token_estimate: {token_estimate}",
    f"10 | metric_drift_score: {drift_score:.2f}",
    f"11 | policy_min_severity: {policy.min_severity_to_fire}",
    f"12 | policy_risk_threshold: {policy.risk_score_threshold:.2f}",
    f"13 | policy_error_threshold: {policy.error_count_threshold}",
    f"14 | policy_latency_threshold_ms: {policy.latency_ms_threshold}",
    f"15 | policy_token_threshold: {policy.token_estimate_threshold}",
    f"16 | policy_drift_threshold: {policy.drift_score_threshold:.2f}",
    f"17 | matched_rules: {matched}",
    f"18 | metrics_snapshot: {_format_metrics(metrics)}",
    "19 | local_guard: passed",
    "20 | llm_permission: allowed",
    "21 | silence_bypass: denied",
    "22 | recommended_payload: compact_event_matrix",
    "23 | recommended_context: no_raw_logs",
    "24 | privacy_boundary: local_metrics_only",
    "25 | operator_message: threshold crossed",
    "26 | failure_mode: unchecked_agent_cost_overrun",
    "27 | safety_note: human_or_llm_review_required",
    "28 | next_action: escalate_to_llm_or_human_operator",
]

if len(lines) != 28:
    raise RuntimeError(f"Card must be exactly 28 lines, got {len(lines)}")

return "\n".join(lines)
```

def process_event(event: AgentEvent, policy: GuardPolicy) -> None:
decision = should_fire_llm(event, policy)

```
if not decision.fire:
    print(
        f"{decision.status} "
        f"event_name={event.event_name} "
        f"reason={decision.reason}"
    )
    return

print(generate_28_line_card(event, decision, policy))
```

def build_mock_events() -> List[AgentEvent]:
"""
Two deterministic mock cases:

```
1. info-only: should stay silent
2. critical: should generate a 28-line card
"""

info_only = AgentEvent(
    event_name="heartbeat_check",
    severity="info",
    metrics_snapshot={
        "error_count": 0,
        "latency_ms": 120,
        "risk_score": 0.05,
        "token_estimate": 180,
        "drift_score": 0.02,
    },
)

critical = AgentEvent(
    event_name="payment_pipeline_error",
    severity="critical",
    metrics_snapshot={
        "error_count": 7,
        "latency_ms": 4200,
        "risk_score": 0.92,
        "token_estimate": 3800,
        "drift_score": 0.81,
    },
)

return [info_only, critical]
```

def main() -> int:
policy = GuardPolicy()
events = build_mock_events()

```
print("=== silent-agent-guard demo ===")
print()

print("--- Case 1: info-only event ---")
process_event(events[0], policy)

print()
print("--- Case 2: critical event ---")
process_event(events[1], policy)

return 0
```

if **name** == "**main**":
raise SystemExit(main())
