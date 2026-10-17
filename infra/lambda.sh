#!/usr/bin/env bash
# Runs the API on AWS Lambda (container image + Lambda Web Adapter) behind a streaming Function URL,
# inside the same private subnets and security group App Runner used to reach RDS. Safe to re-run.
set -euo pipefail

PROFILE="${AWS_PROFILE:-default}"
REGION="us-east-1"
APP="ya-sale"
FUNCTION="$APP-api"
IMAGE="${1:?usage: lambda.sh <ecr-image-uri>}"
RESERVED_CONCURRENCY=10
aws() { command aws --profile "$PROFILE" --region "$REGION" "$@"; }

ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
ROLE="$APP-lambda"

echo "== execution role (VPC networking + logs only)"
if ! aws iam get-role --role-name "$ROLE" >/dev/null 2>&1; then
  aws iam create-role --role-name "$ROLE" --tags Key=Project,Value="$APP" --assume-role-policy-document \
    '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"lambda.amazonaws.com"},"Action":"sts:AssumeRole"}]}' >/dev/null
  aws iam attach-role-policy --role-name "$ROLE" \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole
  sleep 10
fi

SUBNETS=$(aws ec2 describe-subnets --filters "Name=tag:Name,Values=$APP-private-*" --query 'Subnets[].SubnetId' --output text | tr '\t' ',')
CONNECTOR_SG=$(aws ec2 describe-security-groups --filters "Name=group-name,Values=$APP-connector" --query 'SecurityGroups[0].GroupId' --output text)

echo "== environment from SSM (stored encrypted by Lambda, never printed)"
ENV_FILE=$(mktemp)
trap 'rm -f "$ENV_FILE"' EXIT
python3 -I - "$ENV_FILE" "$PROFILE" "$REGION" "$APP" <<'PY'
import json, subprocess, sys
out, profile, region, app = sys.argv[1:]
names = ["ANTHROPIC_API_KEY", "TAVILY_API_KEY", "EXA_API_KEY", "GOOGLE_MAPS_API_KEY", "AERODATABOX_API_KEY", "DATABASE_URL", "FINGERPRINT_SALT"]
values = {}
for name in names:
    values[name] = subprocess.run(
        ["aws", "--profile", profile, "--region", region, "ssm", "get-parameter", "--name", f"/{app}/{name}",
         "--with-decryption", "--query", "Parameter.Value", "--output", "text"],
        check=True, capture_output=True, text=True).stdout.strip()
values["TEAM_FINGERPRINTS"] = "none"
json.dump({"Variables": values}, open(out, "w"))
PY

echo "== function $FUNCTION"
if ! aws lambda get-function --function-name "$FUNCTION" >/dev/null 2>&1; then
  aws lambda create-function --function-name "$FUNCTION" --package-type Image --code ImageUri="$IMAGE" \
    --role "arn:aws:iam::$ACCOUNT:role/$ROLE" --architectures x86_64 --memory-size 2048 --timeout 300 \
    --vpc-config "SubnetIds=$SUBNETS,SecurityGroupIds=$CONNECTOR_SG" \
    --environment "file://$ENV_FILE" --tags Project="$APP" >/dev/null
  aws lambda wait function-active-v2 --function-name "$FUNCTION"
else
  aws lambda update-function-configuration --function-name "$FUNCTION" --environment "file://$ENV_FILE" >/dev/null
  aws lambda wait function-updated-v2 --function-name "$FUNCTION"
fi
# Caps cost and keeps total Postgres connections bounded (4 per instance).
aws lambda put-function-concurrency --function-name "$FUNCTION" --reserved-concurrent-executions "$RESERVED_CONCURRENCY" >/dev/null

echo "== public streaming Function URL"
if ! aws lambda get-function-url-config --function-name "$FUNCTION" >/dev/null 2>&1; then
  aws lambda create-function-url-config --function-name "$FUNCTION" --auth-type NONE --invoke-mode RESPONSE_STREAM >/dev/null
  aws lambda add-permission --function-name "$FUNCTION" --statement-id public-url --action lambda:InvokeFunctionUrl \
    --principal "*" --function-url-auth-type NONE >/dev/null
  aws lambda add-permission --function-name "$FUNCTION" --statement-id public-invoke --action lambda:InvokeFunction \
    --principal "*" --invoked-via-function-url >/dev/null 2>&1 || true
fi
echo "FUNCTION_URL=$(aws lambda get-function-url-config --function-name "$FUNCTION" --query FunctionUrl --output text)"
