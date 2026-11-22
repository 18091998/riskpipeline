from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any


def get_props(node: dict[str, Any]) -> dict[str, Any]:
    """Safely returns the props dictionary from a graph node."""
    props = node.get("props")
    return props if isinstance(props, dict) else {}


def parse_iso_date(value: Any) -> date | None:
    """Safely parses an ISO date string (YYYY-MM-DD) into a date object."""
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        text = value.strip()[:10]
        if not text:
            return None
        try:
            return date.fromisoformat(text)
        except ValueError:
            return None
    return None


def add_business_days(
    start_date: date,
    days: int,
    extra_holidays: set[date] | None = None,
    weekend_days: set[int] | None = None,
) -> date:
    """Adds (or subtracts) working days skipping weekends and any extra holidays.

    By default, weekend_days is {5, 6} (Saturday=5, Sunday=6 in Python weekday()).
    """
    holidays = extra_holidays or set()
    weekends = weekend_days if weekend_days is not None else {5, 6}

    if days == 0:
        return start_date

    step = 1 if days > 0 else -1
    remaining = abs(days)
    current = start_date

    while remaining > 0:
        current = current + timedelta(days=step)
        if current.weekday() not in weekends and current not in holidays:
            remaining -= 1

    return current


def _nodes_by_type(nodes: list[dict[str, Any]], node_type: str) -> list[dict[str, Any]]:
    return [n for n in nodes if n.get("type") == node_type]


def compute_control_rating(
    linked_controls: list[dict[str, Any]],
    linked_tests: list[dict[str, Any]],
) -> str:
    """Deterministically rates control effectiveness from linked controls and tests."""
    if not linked_controls and not linked_tests:
        return "Needs Improvement"

    statuses: list[str] = []
    for item in [*linked_controls, *linked_tests]:
        props = get_props(item)
        for key in ("effectiveness", "rating", "result", "status", "outcome"):
            val = props.get(key)
            if val is not None:
                statuses.append(str(val).strip().lower())

    if any(any(bad in s for bad in ("ineffective", "unsatisfactory", "fail", "breach", "deficien")) for s in statuses):
        return "Unsatisfactory"
    if any(any(mid in s for mid in ("partial", "needs improvement", "amber", "develop", "warn")) for s in statuses):
        return "Needs Improvement"
    if statuses and all(any(good in s for good in ("effective", "satisfactory", "pass", "strong")) for s in statuses):
        return "Effective"
    return "Needs Improvement"


def evaluate_issue_rules(
    context: dict[str, Any],
    all_nodes: list[dict[str, Any]] | None = None,
    default_run_date: str | None = None,
) -> dict[str, Any]:
    """Applies deterministic rule checks to an issue and its graph context."""
    issue = context.get("issue", {})
    issue_props = get_props(issue)
    neighbors = context.get("neighbors", [])
    meta = context.get("graph_meta", {})
    global_nodes = all_nodes or []

    run_date = (
        parse_iso_date(meta.get("run_date_for_test"))
        or parse_iso_date(default_run_date)
        or date.today()
    )

    linked_controls = _nodes_by_type(neighbors, "Control")
    linked_tests = _nodes_by_type(neighbors, "ControlTest")
    linked_roles = _nodes_by_type(neighbors, "Role")
    linked_people = _nodes_by_type(neighbors, "Person")
    linked_sites = _nodes_by_type(neighbors, "Site")
    linked_findings = _nodes_by_type(neighbors, "AuditFinding")
    linked_plans = _nodes_by_type(neighbors, "ContinuityPlan")

    # Global rule/scale nodes available for deterministic reference
    control_effect_rules = _nodes_by_type(global_nodes, "ControlEffectRule")
    escalation_rules = _nodes_by_type(global_nodes, "EscalationRule")
    appetite_statements = _nodes_by_type(global_nodes, "AppetiteStatement")
    treatment_rules = _nodes_by_type(global_nodes, "TreatmentRule")

    control_rating = compute_control_rating(linked_controls, linked_tests)

    target_date = None
    for key in ("target_date", "due_date", "remediation_date", "closure_date", "SLA_due_date"):
        parsed = parse_iso_date(issue_props.get(key) or issue.get(key))
        if parsed:
            target_date = parsed
            break

    days_until_due = (target_date - run_date).days if target_date else None
    is_overdue = days_until_due is not None and days_until_due < 0

    severity_raw = str(
        issue_props.get("severity") or issue_props.get("priority") or issue_props.get("impact") or ""
    ).strip().lower()
    is_high_severity = any(word in severity_raw for word in ("high", "critical", "severe", "major"))

    escalation_required = (
        control_rating == "Unsatisfactory"
        or is_overdue
        or is_high_severity
        or len(linked_findings) > 0
    )

    return {
        "issue_id": issue.get("id"),
        "issue_label": issue.get("label"),
        "run_date": run_date.isoformat(),
        "control_rating": control_rating,
        "target_date": target_date.isoformat() if target_date else None,
        "days_until_due": days_until_due,
        "is_overdue": is_overdue,
        "escalation_required": escalation_required,
        "counts": {
            "controls": len(linked_controls),
            "control_tests": len(linked_tests),
            "roles": len(linked_roles),
            "people": len(linked_people),
            "sites": len(linked_sites),
            "audit_findings": len(linked_findings),
            "continuity_plans": len(linked_plans),
            "global_control_effect_rules": len(control_effect_rules),
            "global_escalation_rules": len(escalation_rules),
            "global_appetite_statements": len(appetite_statements),
            "global_treatment_rules": len(treatment_rules),
        },
    }