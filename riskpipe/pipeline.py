from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from riskpipe.graph import KnowledgeGraph
from riskpipe.llm import LLMClient
from riskpipe.rules import evaluate_issue_rules
from riskpipe.validators import collect_valid_node_ids, validate_grounded_ids


def load_prompt(prompt_name: str, prompts_dir: str | Path = "prompts") -> str:
    path = Path(prompts_dir) / prompt_name
    return path.read_text(encoding="utf-8").strip()


def _compute_confidence(
    rule_eval: dict[str, Any],
    assessment_ok: bool,
    treatment_ok: bool,
    ids_valid: bool,
) -> float:
    score = 0.20
    counts = rule_eval.get("counts", {})

    if counts.get("roles", 0) > 0 or counts.get("people", 0) > 0:
        score += 0.15
    if counts.get("controls", 0) > 0 or counts.get("control_tests", 0) > 0:
        score += 0.15
    if rule_eval.get("target_date") is not None:
        score += 0.10
    if assessment_ok:
        score += 0.15
    if treatment_ok:
        score += 0.10
    if ids_valid:
        score += 0.15

    return round(min(score, 1.0), 2)


def run_pipeline(
    graph_path: str | Path,
    config: dict[str, Any],
    prompts_dir: str | Path = "prompts",
    limit: int | None = None,
) -> dict[str, Any]:
    graph = KnowledgeGraph.from_json_file(graph_path)
    llm = LLMClient.from_config(config)
    default_run_date = config.get("run_date")
    valid_node_ids = collect_valid_node_ids(graph.nodes)

    assessment_prompt = load_prompt("issue_assessment.txt", prompts_dir)
    treatment_prompt = load_prompt("treatment_plan.txt", prompts_dir)

    issues = graph.get_issues()
    if limit is not None and limit > 0:
        issues = issues[:limit]

    results: list[dict[str, Any]] = []

    for issue in issues:
        issue_id = issue.get("id", "UNKNOWN")
        context = graph.get_issue_context(issue_id)
        context_ids = {
            str(n["id"]) for n in [context["issue"], *context["neighbors"]] if n.get("id")
        }

        rule_eval = evaluate_issue_rules(
            context=context,
            all_nodes=graph.nodes,
            default_run_date=default_run_date,
        )

        payload_text = json.dumps(
            {
                "issue": context["issue"],
                "neighbors": context["neighbors"],
                "edges": context["edges"],
                "rule_evaluation": rule_eval,
            },
            indent=2,
            default=str,
        )

        assessment_data: dict[str, Any] = {}
        assessment_ok = False
        try:
            raw_assessment = llm.chat(
                system_prompt=assessment_prompt,
                user_prompt=payload_text,
                json_mode=True,
            )
            assessment_data = llm.parse_json_response(raw_assessment)
            assessment_ok = True
        except Exception as exc:  # noqa: BLE001
            assessment_data = {"error": str(exc)}

        treatment_data: dict[str, Any] = {}
        treatment_ok = False
        try:
            raw_treatment = llm.chat(
                system_prompt=treatment_prompt,
                user_prompt=json.dumps(
                    {
                        "issue_id": issue_id,
                        "rule_evaluation": rule_eval,
                        "assessment": assessment_data,
                    },
                    indent=2,
                    default=str,
                ),
                json_mode=True,
            )
            treatment_data = llm.parse_json_response(raw_treatment)
            treatment_ok = True
        except Exception as exc:  # noqa: BLE001
            treatment_data = {"error": str(exc)}

        id_validation = validate_grounded_ids(
            response_data={"assessment": assessment_data, "treatment": treatment_data},
            valid_node_ids=valid_node_ids,
            context_node_ids=context_ids,
        )
        ids_valid = bool(id_validation["is_valid"])

        confidence = _compute_confidence(rule_eval, assessment_ok, treatment_ok, ids_valid)
        threshold = float(config.get("thresholds", {}).get("confidence_review_threshold", 0.75))

        results.append(
            {
                "issue_id": issue_id,
                "issue_label": issue.get("label"),
                "rule_evaluation": rule_eval,
                "assessment": assessment_data,
                "treatment": treatment_data,
                "id_validation": id_validation,
                "confidence": confidence,
                "needs_human_review": (
                    confidence < threshold
                    or not (assessment_ok and treatment_ok)
                    or not ids_valid
                ),
            }
        )

    return {
        "graph_meta": graph.meta,
        "graph_anomalies": graph.anomalies,
        "issue_count": len(results),
        "results": results,
    }