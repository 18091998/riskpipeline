from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def export_pipeline_outputs(
    pipeline_output: dict[str, Any],
    output_dir: str | Path = "output",
) -> dict[str, Path]:
    """Writes risks.json and run_log.json to the output directory."""
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    risks_file = out_path / "risks.json"
    run_log_file = out_path / "run_log.json"

    risks_file.write_text(
        json.dumps(pipeline_output.get("results", []), indent=2, default=str),
        encoding="utf-8",
    )

    run_log = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "graph_meta": pipeline_output.get("graph_meta", {}),
        "graph_anomalies_count": len(pipeline_output.get("graph_anomalies", [])),
        "issue_count": pipeline_output.get("issue_count", 0),
        "output_files": [str(risks_file.name), str(run_log_file.name)],
    }
    run_log_file.write_text(
        json.dumps(run_log, indent=2, default=str),
        encoding="utf-8",
    )

    return {
        "risks_json": risks_file,
        "run_log_json": run_log_file,
    }