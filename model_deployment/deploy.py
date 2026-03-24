# WARNING: This snippet is not yet compatible with SageMaker version >= 3.0.0.
# To use this snippet, install a compatible version:
# pip install 'sagemaker<3.0.0'
import json
import os
import sys
import dotenv
dotenv.load_dotenv()
print("import sgaemaker")
import sagemaker
print("done")
import boto3
import logging
from sagemaker.huggingface.llm_utils import get_huggingface_llm_image_uri
from sagemaker.huggingface.model import HuggingFaceModel

from botocore.exceptions import ClientError


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

handler = logging.StreamHandler(sys.stderr)
handler.setLevel(logging.DEBUG)
handler.setFormatter(
    logging.Formatter("%(asctime)s %(name)s %(levelname)s: %(message)s")
)

logger.addHandler(handler)
logger.propagate = False

logging.basicConfig(level=logging.INFO)

ROLE_NAME = "sagemaker-execution-role"

def get_or_create_sagemaker_execution_role():
    iam = boto3.client("iam")

    # First, check if the role already exists
    logger.debug(f"Checking if IAM role '{ROLE_NAME}' already exists")
    try:
        role = iam.get_role(RoleName=ROLE_NAME)
        logger.info(f"IAM role '{ROLE_NAME}' already exists")
        print(f"Role {ROLE_NAME} already exists, reusing it.")
        return role["Role"]["Arn"]
    except ClientError as e:
        if e.response["Error"]["Code"] != "NoSuchEntity":
            logger.exception(f"Error checking for existing role: {e}")
            raise

    # Role doesn't exist, so create it
    logger.info(f"Creating new IAM role: {ROLE_NAME}")
    assume_role_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "sagemaker.amazonaws.com"},
                "Action": "sts:AssumeRole",
            }
        ],
    }

    try:
        print(f"Creating role: {ROLE_NAME}")
        logger.debug(f"Creating IAM role with AssumeRolePolicyDocument")
        role = iam.create_role(
            RoleName=ROLE_NAME,
            AssumeRolePolicyDocument=json.dumps(assume_role_policy),
            Description="Execution role for SageMaker endpoints",
        )
        logger.debug(f"IAM role created: {role['Role']['Arn']}")

        # Attach required AWS managed policies
        logger.debug(f"Attaching AWS managed policies to role: {ROLE_NAME}")
        iam.attach_role_policy(
            RoleName=ROLE_NAME,
            PolicyArn="arn:aws:iam::aws:policy/AmazonSageMakerFullAccess",
        )
        logger.debug("Attached AmazonSageMakerFullAccess policy")

        iam.attach_role_policy(
            RoleName=ROLE_NAME,
            PolicyArn="arn:aws:iam::aws:policy/AmazonS3FullAccess",
        )
        logger.debug("Attached AmazonS3FullAccess policy")

        iam.attach_role_policy(
            RoleName=ROLE_NAME,
            PolicyArn="arn:aws:iam::aws:policy/CloudWatchLogsFullAccess",
        )
        logger.debug("Attached CloudWatchLogsFullAccess policy")

        # Give AWS a few seconds to propagate the role
        import time
        logger.info("Waiting for IAM role propagation...")
        time.sleep(10)
        logger.info(f"IAM role ready: {role['Role']['Arn']}")

        return role["Role"]["Arn"]

    except ClientError as e:
        logger.exception(f"Error creating IAM role: {e}")
        raise


logger.info("Retrieving or creating SageMaker execution role")

iam = boto3.client('iam')
role = get_or_create_sagemaker_execution_role()
logger.info(f"Created new SageMaker execution role: {role}")

logger.info("Configuring Hugging Face model for SageMaker deployment")
# Hub Model configuration. https://huggingface.co/models
hub = {
	'HF_MODEL_ID':'meta-llama/Llama-3.1-8B-Instruct',
	'SM_NUM_GPUS': json.dumps(1),
	'HF_TOKEN': os.getenv('HF_TOKEN'),
}
logger.debug(f"HF_MODEL_ID: {hub['HF_MODEL_ID']}, SM_NUM_GPUS: {hub['SM_NUM_GPUS']}")

assert hub['HF_TOKEN'] != '<REPLACE WITH YOUR TOKEN>', "You have to provide a token."
logger.debug("HF_TOKEN is configured")

logger.info("Creating Hugging Face model instance")
# create Hugging Face Model Class
huggingface_model = HuggingFaceModel(
	image_uri=get_huggingface_llm_image_uri("huggingface",version="3.3.6"),
	env=hub,
	role=role,
)
logger.debug("Hugging Face model instance created")

logger.info("Deploying model to SageMaker Inference endpoint")
# deploy model to SageMaker Inference
predictor = huggingface_model.deploy(
	initial_instance_count=1,
	instance_type="ml.m6g.large",
	container_startup_health_check_timeout=900
)
logger.info("Model endpoint deployed successfully")

logger.info("Testing endpoint with sample prediction request")
# send request
result = predictor.predict({
	"inputs": "Hi, what can you help me with?",
})
logger.info(f"Prediction successful. Response type: {type(result)}")
logger.debug(f"Prediction response: {result}")