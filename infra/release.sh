#!/usr/bin/env bash
# Points the App Runner service at an image already in ECR (creating the service the first time),
# waits until it runs and smoke-tests it. Used by deploy.sh locally and by the CD job.
set -euo pipefail

REGION="${AWS_REGION:-us-east-1}"
APP="ya-sale"
IMAGE="${1:?usage: release.sh <ecr-image-uri>}"
aws() { command aws ${AWS_PROFILE:+--profile "$AWS_PROFILE"} --region "$REGION" "$@"; }

ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
SSM="arn:aws:ssm:$REGION:$ACCOUNT:parameter/$APP"

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
        "GOOGLE_MAPS_API_KEY": "$SSM/GOOGLE_MAPS_API_KEY",
        "DATABASE_URL": "$SSM/DATABASE_URL",
        "FINGERPRINT_SALT": "$SSM/FINGERPRINT_SALT"
      }
    }
  }
}
JSON
)

wait_until_settled() {
  local status
  for _ in $(seq 1 120); do
    status=$(aws apprunner describe-service --service-arn "$1" --query Service.Status --output text)
    [ "$status" = "RUNNING" ] && return 0
    case "$status" in *FAILED*|PAUSED|DELETED) echo "service status $status" >&2; return 1 ;; esac
    sleep 10
  done
  echo "timed out waiting for RUNNING (last status $status)" >&2
  return 1
}

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
  wait_until_settled "$SERVICE_ARN"
  aws apprunner update-service --service-arn "$SERVICE_ARN" --source-configuration "$SOURCE" >/dev/null
fi

echo "== waiting for RUNNING"
sleep 20
wait_until_settled "$SERVICE_ARN"
URL="https://$(aws apprunner describe-service --service-arn "$SERVICE_ARN" --query Service.ServiceUrl --output text)"

echo "== smoke test $URL"
curl -fsS "$URL/api/health"
echo
curl -fsS -o /dev/null -w "web %{http_code}\n" "$URL/"
echo "YASALE_URL=$URL"
