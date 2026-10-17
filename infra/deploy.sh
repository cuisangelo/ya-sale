#!/usr/bin/env bash
# Builds the image, pushes it to ECR, creates or updates the App Runner service and smoke-tests it.
set -euo pipefail

PROFILE="${AWS_PROFILE:-default}"
REGION="${AWS_REGION:-us-east-1}"
APP="ya-sale"
TAG="${1:?usage: deploy.sh <image-tag>}"
aws() { command aws --profile "$PROFILE" --region "$REGION" "$@"; }

ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
REGISTRY="$ACCOUNT.dkr.ecr.$REGION.amazonaws.com"
IMAGE="$REGISTRY/$APP:$TAG"
SSM="arn:aws:ssm:$REGION:$ACCOUNT:parameter/$APP"

echo "== build and push $IMAGE"
# Throwaway docker config: the macOS keychain helper rejects a re-login to the same registry,
# so the ECR token lives only in this temp dir and is removed on exit.
DOCKER_CONFIG=$(mktemp -d)
export DOCKER_CONFIG
trap 'rm -rf "$DOCKER_CONFIG"' EXIT
ln -s "$HOME/.docker/cli-plugins" "$DOCKER_CONFIG/cli-plugins"
ln -s "$HOME/.docker/contexts" "$DOCKER_CONFIG/contexts"
echo '{"currentContext": "orbstack"}' > "$DOCKER_CONFIG/config.json"
# docker falls back to the keychain helper whenever it is on PATH, so hide it from these calls.
NO_HELPER_PATH=$(echo "$PATH" | tr ':' '\n' | grep -v -E '^/usr/local/bin$|/\.orbstack/bin$' | paste -sd: -)
aws ecr get-login-password | PATH="$NO_HELPER_PATH" docker login --username AWS --password-stdin "$REGISTRY" >/dev/null
PATH="$NO_HELPER_PATH" docker buildx build --platform linux/amd64 -t "$IMAGE" --push "$(dirname "$0")/.."

SOURCE=$(cat <<JSON
{
  "AuthenticationConfiguration": {"AccessRoleArn": "arn:aws:iam::$ACCOUNT:role/$APP-ecr-access"},
  "AutoDeploymentsEnabled": false,
  "ImageRepository": {
    "ImageIdentifier": "$IMAGE",
    "ImageRepositoryType": "ECR",
    "ImageConfiguration": {
      "Port": "8080",
      "RuntimeEnvironmentVariables": {"TEAM_FINGERPRINTS": "none"},
      "RuntimeEnvironmentSecrets": {
        "ANTHROPIC_API_KEY": "$SSM/ANTHROPIC_API_KEY",
        "TAVILY_API_KEY": "$SSM/TAVILY_API_KEY",
        "EXA_API_KEY": "$SSM/EXA_API_KEY",
        "DATABASE_URL": "$SSM/DATABASE_URL",
        "FINGERPRINT_SALT": "$SSM/FINGERPRINT_SALT"
      }
    }
  }
}
JSON
)

SERVICE_ARN=$(aws apprunner list-services --query "ServiceSummaryList[?ServiceName=='$APP'].ServiceArn | [0]" --output text)
if [ "$SERVICE_ARN" = "None" ]; then
  echo "== create App Runner service"
  CONNECTOR=$(aws apprunner list-vpc-connectors --query "VpcConnectors[?VpcConnectorName=='$APP' && Status=='ACTIVE'].VpcConnectorArn | [0]" --output text)
  SCALING=$(aws apprunner list-auto-scaling-configurations --auto-scaling-configuration-name "$APP-single" \
    --query 'AutoScalingConfigurationSummaryList[0].AutoScalingConfigurationArn' --output text)
  SERVICE_ARN=$(aws apprunner create-service --service-name "$APP" \
    --source-configuration "$SOURCE" \
    --instance-configuration "{\"Cpu\":\"1 vCPU\",\"Memory\":\"2 GB\",\"InstanceRoleArn\":\"arn:aws:iam::$ACCOUNT:role/$APP-instance\"}" \
    --health-check-configuration '{"Protocol":"HTTP","Path":"/api/health","Interval":10,"Timeout":5,"HealthyThreshold":1,"UnhealthyThreshold":5}' \
    --network-configuration "{\"EgressConfiguration\":{\"EgressType\":\"VPC\",\"VpcConnectorArn\":\"$CONNECTOR\"}}" \
    --auto-scaling-configuration-arn "$SCALING" --tags Key=Project,Value="$APP" \
    --query Service.ServiceArn --output text)
else
  echo "== update App Runner service"
  aws apprunner update-service --service-arn "$SERVICE_ARN" --source-configuration "$SOURCE" >/dev/null
fi

echo "== waiting for RUNNING"
for _ in $(seq 1 90); do
  STATUS=$(aws apprunner describe-service --service-arn "$SERVICE_ARN" --query Service.Status --output text)
  [ "$STATUS" = "RUNNING" ] && break
  case "$STATUS" in *FAILED*) echo "service status $STATUS" >&2; exit 1 ;; esac
  sleep 10
done
URL="https://$(aws apprunner describe-service --service-arn "$SERVICE_ARN" --query Service.ServiceUrl --output text)"

echo "== smoke test $URL"
curl -fsS "$URL/api/health"
echo
curl -fsS -o /dev/null -w "web %{http_code}\n" "$URL/"
echo "YASALE_URL=$URL"
