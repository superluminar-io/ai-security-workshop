#!/usr/bin/env python3
from __future__ import annotations

import os
import sys

# Ensure the project root is on sys.path so `infra` package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import aws_cdk as cdk
from infra.stack import AiSecurityWorkshopStack

app = cdk.App()
AiSecurityWorkshopStack(
    app,
    "AiSecurityWorkshopStack",
    env=cdk.Environment(
        account=app.account,
        region=app.region,
    ),
)
app.synth()
