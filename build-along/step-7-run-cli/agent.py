"""'Where Did My Money Go?' agent - a LangGraph workflow over tools.py.

load -> categorise -> analyse -> detect anomalies -> insights -> report

Read-only by design: it reads a CSV and writes a report. It has no tool
that can move money, contact a bank or start a payment.
"""
import json
import time
from pathlib import Path
from typing import TypedDict

import pandas as pd
from langgraph.graph import END, START, StateGraph

import tools


class State(TypedDict, total=False):
    csv_path: str
    overrides: dict          # your category corrections {txn_id: category}
    dismissed: list          # alerts you reviewed and dismissed
    df: pd.DataFrame
    load_report: dict
    analysis: dict
    flags: list
    insights: list
    report: dict


def log(step, message):
    print(f"{time.strftime('%H:%M:%S')} | {step:<18} | {message}", flush=True)


def load_transactions(state):
    df, rep = tools.load_transactions(state["csv_path"])
    log("load_transactions", f"{rep['rows_read']} rows read, {rep['rows_dropped']} dropped "
        f"{rep['dropped_ids']}, {rep['rows_clean']} clean")
    return {"df": df, "load_report": rep}


def categorise_expenses(state):
    df = tools.categorise(state["df"], state.get("overrides"))
    log("categorise", f"sources {df['source'].value_counts().to_dict()}")
    return {"df": df}


def analyse_spending(state):
    a = tools.analyse(state["df"])
    log("analyse_spending", f"{a['month']}: Rs {a['total']:,} over {a['txn_count']} debits "
        f"({a['mom_change_pct']:+}% vs {a['prev_month']}), {len(a['recurring'])} recurring")
    return {"analysis": a}


def detect_anomalies(state):
    flags = tools.detect_anomalies(state["df"], state.get("dismissed", []))
    log("detect_anomalies", f"{len(flags)} flagged for review {[f['txn_id'] for f in flags]}")
    return {"flags": flags}


def generate_insights(state):
    insights = tools.generate_insights(state["analysis"], state["flags"])
    log("generate_insights", f"{len(insights)} insights")
    return {"insights": insights}


def prepare_report(state):
    report = {"load": state["load_report"], "analysis": state["analysis"],
              "flags": state["flags"], "insights": state["insights"],
              "categories": tools.CATEGORIES, "transactions": tools.to_records(state["df"])}
    Path("output").mkdir(exist_ok=True)
    Path("output/report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    log("prepare_report", "saved output/report.json")
    return {"report": report}


STEPS = [load_transactions, categorise_expenses, analyse_spending,
         detect_anomalies, generate_insights, prepare_report]


def build_graph():
    graph = StateGraph(State)
    for step in STEPS:
        graph.add_node(step.__name__, step)
    graph.add_edge(START, STEPS[0].__name__)
    for a, b in zip(STEPS, STEPS[1:]):
        graph.add_edge(a.__name__, b.__name__)
    graph.add_edge(STEPS[-1].__name__, END)
    return graph.compile()


def run(csv_path, overrides=None, dismissed=None):
    state = build_graph().invoke({"csv_path": csv_path, "overrides": overrides or {},
                                  "dismissed": dismissed or []})
    return state["report"]
