# AWS Credentials

The workshop agent uses Amazon Bedrock, which requires AWS credentials. You will be given a set of IAM credentials — an **Access Key ID** and a **Secret Access Key** — by the workshop facilitator.

---

## Configure a named profile

**In your terminal**, run:

```bash
aws configure --profile ai-workshop
```

You will be prompted for four values:

```
AWS Access Key ID [None]:     <paste your Access Key ID>
AWS Secret Access Key [None]: <paste your Secret Access Key>
Default region name [None]:   eu-central-1
Default output format [None]: json
```

> **Region is important.** The Bedrock model used in this workshop is hosted in the AWS EU region. Enter `eu-central-1` exactly — anything else will cause a model validation error when you start the agent.

---

## Verify

**In your terminal**, confirm the credentials work:

```bash
aws sts get-caller-identity --profile ai-workshop
```

You should see a JSON response containing your account ID and user ARN:

```json
{
    "UserId": "AIDA...",
    "Account": "123456789012",
    "Arn": "arn:aws:iam::123456789012:user/workshop-user"
}
```

If you see an error, double-check for typos — keys are case-sensitive.

---

Once credentials are verified, move on to **Start the Agent**.
