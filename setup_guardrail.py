"""Create (or delete) the Module 4 Bedrock Guardrail via boto3.

Module 4 needs a guardrail to attach to the agent. This creates a realistic one
-- a prompt-attack (injection/jailbreak) filter plus PII redaction -- and prints
the env vars to export.

Note what it deliberately does NOT include: a "deny refunds/discounts" topic.
That would be the wrong control twice over -- it breaks the app's legitimate job
(authorized customers *do* get refunds), and you cannot topic-filter your way out
of an authorization problem. This is a *probabilistic* Layer-2 control; it only
shifts the odds, and only for what its classifiers recognize. The deterministic
boundary (Modules 2-3) is what actually stops harm.

    AWS_PROFILE=ai-workshop python setup_guardrail.py            # create (or reuse)
    AWS_PROFILE=ai-workshop python setup_guardrail.py --delete   # tear down

The guardrail is a single deletable resource; --delete removes it cleanly so the
account isn't left with an orphaned control.
"""

from __future__ import annotations

import argparse
import os
import time

import boto3

NAME = "ai-workshop-guardrail"
REGION = os.environ.get("AWS_REGION") or "eu-central-1"


def _client():
    return boto3.client("bedrock", region_name=REGION)


def _find(client) -> str | None:
    token = None
    while True:
        kwargs = {"nextToken": token} if token else {}
        resp = client.list_guardrails(**kwargs)
        for g in resp.get("guardrails", []):
            if g.get("name") == NAME:
                return g.get("id")
        token = resp.get("nextToken")
        if not token:
            return None


def _wait_ready(client, gid: str, timeout: int = 60) -> str:
    for _ in range(timeout):
        status = client.get_guardrail(guardrailIdentifier=gid).get("status")
        if status in ("READY", "FAILED"):
            return status
        time.sleep(1)
    return "TIMEOUT"


def create() -> None:
    client = _client()
    gid = _find(client)
    if gid:
        print(f"Guardrail '{NAME}' already exists: {gid}")
    else:
        resp = client.create_guardrail(
            name=NAME,
            description="AI security workshop Module 4 -- probabilistic Layer-2 control.",
            blockedInputMessaging="Blocked by guardrail.",
            blockedOutputsMessaging="Blocked by guardrail.",
            contentPolicyConfig={
                "filtersConfig": [
                    {"type": "PROMPT_ATTACK", "inputStrength": "HIGH", "outputStrength": "NONE"},
                ]
            },
            sensitiveInformationPolicyConfig={
                "piiEntitiesConfig": [
                    {"type": "EMAIL", "action": "ANONYMIZE"},
                    {"type": "ADDRESS", "action": "ANONYMIZE"},
                ]
            },
        )
        gid = resp["guardrailId"]
        print(f"Created guardrail '{NAME}': {gid}")
        status = _wait_ready(client, gid)
        print(f"Status: {status}")

    print()
    print("Point the app at it:")
    print(f"  export BEDROCK_GUARDRAIL_ID={gid}")
    print("  export BEDROCK_GUARDRAIL_VERSION=DRAFT")


def delete() -> None:
    client = _client()
    gid = _find(client)
    if not gid:
        print(f"No guardrail named '{NAME}' to delete.")
        return
    client.delete_guardrail(guardrailIdentifier=gid)
    print(f"Deleted guardrail '{NAME}' ({gid}).")


def main() -> None:
    ap = argparse.ArgumentParser(description="Create or delete the Module 4 workshop guardrail.")
    ap.add_argument("--delete", action="store_true", help="Delete the workshop guardrail.")
    args = ap.parse_args()
    (delete if args.delete else create)()


if __name__ == "__main__":
    main()
