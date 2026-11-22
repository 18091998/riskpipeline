from __future__ import annotations

import argparse
import json
from pathlib import Path

from riskpipe.exporters import export_pipeline_outputs
from riskpipe.pipeline import run_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the RiskPipe pipeline.")
    parser.add_argument("--graph", default="northgate_knowledge_graph.json")
    parser.add_argument("--config", default="config.json")
    parser.add_argument("--prompts-dir", default="prompts")
    parser.add_argument("--out", default="output")
    parser.add_argument("--limit", type=int, default=None)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    pipeline_out = run_pipeline(
        graph_path=args.graph,
        config=config,
        prompts_dir=args.prompts_dir,
        limit=args.limit,
    )
    written = export_pipeline_outputs(pipeline_out, output_dir=args.out)
    print(f"Processed {pipeline_out['issue_count']} issue(s).")
    for name, path in written.items():
        print(f"Wrote {name}: {path}")


if __name__ == "__main__":
    main()