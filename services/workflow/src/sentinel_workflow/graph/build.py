"""Assemble the bounded typed LangGraph."""

from __future__ import annotations

from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from sentinel_workflow.graph import nodes
from sentinel_workflow.graph.state import WorkflowState


def build_workflow_graph() -> StateGraph:
    graph: StateGraph = StateGraph(WorkflowState)

    graph.add_node("load_input", nodes.load_input)
    graph.add_node("collect_evidence", nodes.collect_evidence)
    graph.add_node("plan", nodes.plan)
    graph.add_node("budget_exhausted", nodes.budget_exhausted)
    graph.add_node("policy_check", nodes.policy_check)
    graph.add_node("approval_gate", nodes.approval_gate)
    graph.add_node("execute_ledger", nodes.execute_ledger)
    graph.add_node("verify", nodes.verify)
    graph.add_node("wait_external", nodes.wait_external)
    graph.add_node("deliver", nodes.deliver)

    graph.add_edge(START, "load_input")
    graph.add_edge("load_input", "collect_evidence")
    graph.add_conditional_edges(
        "collect_evidence",
        lambda s: "deliver" if s.get("terminal") else "plan",
        {"deliver": "deliver", "plan": "plan"},
    )
    graph.add_conditional_edges(
        "plan",
        nodes._route_after_plan,
        {
            "policy": "policy_check",
            "clarify": "deliver",
            "escalate": "deliver",
            "budget": "budget_exhausted",
        },
    )
    graph.add_edge("budget_exhausted", "deliver")
    graph.add_conditional_edges(
        "policy_check",
        nodes._route_after_policy,
        {
            "approval": "approval_gate",
            "execute": "execute_ledger",
            "clarify": "deliver",
            "escalate": "deliver",
        },
    )
    graph.add_conditional_edges(
        "approval_gate",
        lambda s: "deliver" if s.get("terminal") else "policy_check",
        {"deliver": "deliver", "policy_check": "policy_check"},
    )
    graph.add_conditional_edges(
        "execute_ledger",
        lambda s: "deliver" if s.get("terminal") else "verify",
        {"deliver": "deliver", "verify": "verify"},
    )
    graph.add_conditional_edges(
        "verify",
        nodes._route_after_verify,
        {
            "wait": "wait_external",
            "resolved": "deliver",
            "escalate": "deliver",
        },
    )
    graph.add_conditional_edges(
        "wait_external",
        lambda s: "verify" if s.get("event") == "RECHECK" and not s.get("terminal") else "deliver",
        {"verify": "verify", "deliver": "deliver"},
    )
    graph.add_edge("deliver", END)
    return graph


def compile_workflow(checkpointer: BaseCheckpointSaver | None = None) -> Any:
    return build_workflow_graph().compile(checkpointer=checkpointer)


def resume_command(value: dict[str, Any]) -> Command:
    return Command(resume=value)
