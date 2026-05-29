def test_bedrock_agentcore_importable():
    from bedrock_agentcore.runtime import BedrockAgentCoreApp
    assert BedrockAgentCoreApp is not None


def test_cdk_bedrockagentcore_importable():
    from aws_cdk import aws_bedrockagentcore as agentcore
    assert agentcore.CfnRuntime is not None
