from __future__ import annotations

import os

import aws_cdk as cdk
from aws_cdk import (
    CfnOutput,
    Stack,
    aws_bedrockagentcore as agentcore,
    aws_ecr_assets as ecr_assets,
    aws_iam as iam,
)
from constructs import Construct


class AiSecurityWorkshopStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        project_root = os.path.join(os.path.dirname(__file__), "..")

        # Build image and push to ECR on cdk deploy
        image = ecr_assets.DockerImageAsset(
            self,
            "AgentImage",
            directory=project_root,
        )

        # IAM role the AgentCore Runtime container assumes
        role = iam.Role(
            self,
            "AgentRuntimeRole",
            assumed_by=iam.ServicePrincipal("bedrock-agentcore.amazonaws.com"),
            inline_policies={
                "BedrockInvoke": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=[
                                "bedrock:InvokeModel",
                                "bedrock:InvokeModelWithResponseStream",
                            ],
                            resources=["*"],
                        )
                    ]
                )
            },
        )

        # AgentCore Runtime resource (L1 construct — no L2 yet)
        runtime = agentcore.CfnRuntime(
            self,
            "AgentRuntime",
            agent_runtime_name="ai-security-workshop",
            agent_runtime_artifact=agentcore.CfnRuntime.AgentRuntimeArtifactProperty(
                container_configuration=agentcore.CfnRuntime.ContainerConfigurationProperty(
                    container_uri=image.image_uri,
                )
            ),
            network_configuration=agentcore.CfnRuntime.NetworkConfigurationProperty(
                network_mode="PUBLIC",
            ),
            role_arn=role.role_arn,
        )

        CfnOutput(
            self,
            "AgentRuntimeArn",
            value=runtime.attr_agent_runtime_arn,
            description="Set as AGENTCORE_RUNTIME_ARN when running server.py",
        )
