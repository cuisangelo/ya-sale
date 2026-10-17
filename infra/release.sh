#!/usr/bin/env bash
# Points the Lambda function at an image already in ECR, waits for the update and smoke-tests it.
# Used by deploy.sh locally and by the CD job. Configuration (VPC, env, URL) lives in lambda.sh.
set -euo pipefail

REGION="${AWS_REGION:-us-east-1}"
FUNCTION="ya-sale-api"
IMAGE="${1:?usage: release.sh <ecr-image-uri>}"
aws() { command aws ${AWS_PROFILE:+--profile "$AWS_PROFILE"} --region "$REGION" "$@"; }

echo "== update $FUNCTION to $IMAGE"
aws lambda update-function-code --function-name "$FUNCTION" --image-uri "$IMAGE" >/dev/null
aws lambda wait function-updated-v2 --function-name "$FUNCTION"

URL=$(aws lambda get-function-url-config --function-name "$FUNCTION" --query FunctionUrl --output text)
URL="${URL%/}"
echo "== smoke test $URL"
# The first call after an update pays the cold start (image pull + uvicorn), so allow it time.
curl -fsS -m 90 --retry 3 --retry-all-errors "$URL/api/health"
echo
curl -fsS -m 60 -o /dev/null -w "mcp %{http_code}\n" -X POST "$URL/mcp" \
  -H 'Accept: application/json, text/event-stream' -H 'content-type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
echo "API_URL=$URL"
