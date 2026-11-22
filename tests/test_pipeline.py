from riskpipe.graph import KnowledgeGraph
from riskpipe.rules import evaluate_issue_rules


def test_graph_and_rules():
    graph = KnowledgeGraph.from_json_file("northgate_knowledge_graph.json")
    assert len(graph.get_issues()) == 11

    first_issue = graph.get_issues()[0]
    context = graph.get_issue_context(first_issue["id"])
    result = evaluate_issue_rules(context, all_nodes=graph.nodes, default_run_date="2026-11-20")
    assert result["issue_id"] == first_issue["id"] 
from pathlib import Path


def test_output_files_exist():
    assert Path("output/risks.json").exists()
    assert Path("output/run_log.json").exists()
    assert Path("output/risks.csv").exists()    