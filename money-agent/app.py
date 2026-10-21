"""Dashboard: python app.py  ->  http://localhost:5000"""
import json
from pathlib import Path

from flask import Flask, jsonify, render_template, request

import tools
from agent import run

app = Flask(__name__)
STATE = Path("output/state.json")    # your corrections + dismissed alerts


def load_state():
    if STATE.exists():
        return json.loads(STATE.read_text())
    return {"csv": "data/transactions.csv", "overrides": {}, "dismissed": []}


def analyse(state):
    STATE.parent.mkdir(exist_ok=True)
    STATE.write_text(json.dumps(state, indent=2))
    report = run(state["csv"], state["overrides"], state["dismissed"])
    a = report["analysis"]
    print(f"analysis complete: {report['load']['rows_clean']} transactions, "
          f"Rs {a['total']:,} spent in {a['month']}, {len(report['flags'])} flagged", flush=True)
    return jsonify(report)


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/api/analyse")
def api_analyse():
    upload = request.files["file"]
    path = Path("uploads") / Path(upload.filename).name
    path.parent.mkdir(exist_ok=True)
    upload.save(path)
    return analyse({"csv": str(path), "overrides": {}, "dismissed": []})


@app.post("/api/correct")
def api_correct():
    body, state = request.get_json(), load_state()
    if body["category"] not in tools.CATEGORIES:
        return jsonify(error="unknown category"), 400
    state["overrides"][body["txn_id"]] = body["category"]
    return analyse(state)


@app.post("/api/dismiss")
def api_dismiss():
    state = load_state()
    state["dismissed"].append(request.get_json()["txn_id"])
    return analyse(state)


if __name__ == "__main__":
    app.run(port=5000)
