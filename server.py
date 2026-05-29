from __future__ import annotations

import json
import os
import secrets
import uuid
from typing import Any

import boto3
from flask import Flask, jsonify, render_template, request, session

import db

app = Flask(__name__, template_folder="templates")
app.secret_key = os.environ.get("FLASK_SECRET_KEY", secrets.token_hex(32))

ACTOR_CUSTOMER_ID = os.environ.get("ACTOR_CUSTOMER_ID", "cust_001")
REGION = os.environ.get("AWS_DEFAULT_REGION", "eu-central-1")
PORT = int(os.environ.get("PORT", 5000))
DB_PATH = os.environ.get("ECOMM_DB", "ecomm.sqlite")

_agentcore_client: Any = None


def _get_client() -> Any:
    global _agentcore_client
    if _agentcore_client is None:
        _agentcore_client = boto3.client("bedrock-agentcore", region_name=REGION)
    return _agentcore_client


@app.route("/")
def index():
    return render_template("index.html", actor_customer_id=ACTOR_CUSTOMER_ID)


@app.route("/api/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json()
        message = data.get("message", "").strip()

        if not message:
            return jsonify({"error": "Empty message"}), 400

        if "session_id" not in session:
            session["session_id"] = str(uuid.uuid4())
        session_id = session["session_id"]

        runtime_arn = os.environ["AGENTCORE_RUNTIME_ARN"]
        payload = json.dumps(
            {"prompt": message, "actorCustomerId": ACTOR_CUSTOMER_ID}
        ).encode("utf-8")

        response = _get_client().invoke_agent_runtime(
            agentRuntimeArn=runtime_arn,
            runtimeSessionId=session_id,
            payload=payload,
            qualifier="DEFAULT",
            contentType="application/json",
        )

        body = json.loads(response["response"].read())
        text = body.get("result", "")
        return jsonify({"response": text, "data": None})

    except KeyError as exc:
        return jsonify({"error": f"Missing configuration: {exc}"}), 500
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "actor_customer_id": ACTOR_CUSTOMER_ID})


def main():
    if not os.environ.get("AGENTCORE_RUNTIME_ARN"):
        raise SystemExit("AGENTCORE_RUNTIME_ARN environment variable is required.\n"
                         "Run: AGENTCORE_RUNTIME_ARN=<arn> python server.py")
    db.initialize(DB_PATH)
    print("Starting chat server...")
    print(f"Logged in as: {ACTOR_CUSTOMER_ID}")
    print(f"Open http://localhost:{PORT} in your browser")
    app.run(debug=False, host="0.0.0.0", port=PORT)


if __name__ == "__main__":
    main()
