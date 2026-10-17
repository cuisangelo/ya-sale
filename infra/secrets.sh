#!/usr/bin/env bash
# Copies the provider keys from backend/.env into SSM SecureStrings and stores the database URL.
# Values are never printed.
set -euo pipefail

PROFILE="${AWS_PROFILE:-default}"
REGION="${AWS_REGION:-us-east-1}"
APP="ya-sale"
ENV_FILE="$(dirname "$0")/../backend/.env"
aws() { command aws --profile "$PROFILE" --region "$REGION" "$@"; }

for name in ANTHROPIC_API_KEY TAVILY_API_KEY EXA_API_KEY GOOGLE_MAPS_API_KEY AERODATABOX_API_KEY; do
  value=$(grep -E "^$name=" "$ENV_FILE" | head -1 | cut -d= -f2- || true)
  if [ -z "$value" ]; then
    echo "missing $name in backend/.env" >&2
    exit 1
  fi
  aws ssm put-parameter --name "/$APP/$name" --type SecureString --overwrite --value "$value" >/dev/null
  echo "stored /$APP/$name"
done

endpoint=$(aws rds describe-db-instances --db-instance-identifier "$APP" --query 'DBInstances[0].Endpoint.Address' --output text)
if [ -z "$endpoint" ] || [ "$endpoint" = "None" ]; then
  echo "database endpoint not ready yet; re-run when the RDS instance is available" >&2
  exit 1
fi
password=$(aws ssm get-parameter --name "/$APP/DB_PASSWORD" --with-decryption --query Parameter.Value --output text)
aws ssm put-parameter --name "/$APP/DATABASE_URL" --type SecureString --overwrite \
  --value "postgresql://yasale:$password@$endpoint:5432/yasale?sslmode=require" >/dev/null
echo "stored /$APP/DATABASE_URL"
