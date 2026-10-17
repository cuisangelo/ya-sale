#!/usr/bin/env bash
# One-time AWS setup for Ya Sale: private Postgres reachable only from App Runner, NAT egress,
# image registry, IAM roles and generated secrets. Safe to re-run: each step skips what exists.
set -euo pipefail

PROFILE="${AWS_PROFILE:-default}"
REGION="${AWS_REGION:-us-east-1}"
APP="ya-sale"
aws() { command aws --profile "$PROFILE" --region "$REGION" "$@"; }
tag() { echo "ResourceType=$1,Tags=[{Key=Name,Value=$2},{Key=Project,Value=$APP}]"; }
by_name() { aws ec2 "describe-$1" --filters "Name=tag:Name,Values=$2" --query "$3" --output text; }

VPC_ID=$(aws ec2 describe-vpcs --filters Name=isDefault,Values=true --query 'Vpcs[0].VpcId' --output text)
PUBLIC_SUBNET=$(aws ec2 describe-subnets --filters Name=default-for-az,Values=true Name=availability-zone,Values="${REGION}a" \
  --query 'Subnets[0].SubnetId' --output text)

echo "== private subnets"
PRIVATE_SUBNETS=()
for spec in "a:172.31.96.0/20" "b:172.31.112.0/20" "c:172.31.128.0/20"; do
  az="${REGION}${spec%%:*}"; cidr="${spec#*:}"; name="$APP-private-${spec%%:*}"
  id=$(by_name subnets "$name" 'Subnets[0].SubnetId' 2>/dev/null || true)
  if [ -z "$id" ] || [ "$id" = "None" ]; then
    id=$(aws ec2 create-subnet --vpc-id "$VPC_ID" --cidr-block "$cidr" --availability-zone "$az" \
      --tag-specifications "$(tag subnet "$name")" --query Subnet.SubnetId --output text)
  fi
  PRIVATE_SUBNETS+=("$id")
done

echo "== NAT gateway (outbound internet for Tavily, Exa and Claude)"
NAT_ID=$(aws ec2 describe-nat-gateways --filter "Name=tag:Name,Values=$APP-nat" "Name=state,Values=available,pending" --query "NatGateways[0].NatGatewayId" --output text)
if [ -z "$NAT_ID" ] || [ "$NAT_ID" = "None" ]; then
  EIP=$(aws ec2 allocate-address --domain vpc --tag-specifications "$(tag elastic-ip "$APP-nat")" --query AllocationId --output text)
  NAT_ID=$(aws ec2 create-nat-gateway --subnet-id "$PUBLIC_SUBNET" --allocation-id "$EIP" \
    --tag-specifications "$(tag natgateway "$APP-nat")" --query NatGateway.NatGatewayId --output text)
fi
aws ec2 wait nat-gateway-available --nat-gateway-ids "$NAT_ID"

echo "== private route table"
RT_ID=$(by_name route-tables "$APP-private" 'RouteTables[0].RouteTableId' 2>/dev/null || true)
if [ -z "$RT_ID" ] || [ "$RT_ID" = "None" ]; then
  RT_ID=$(aws ec2 create-route-table --vpc-id "$VPC_ID" --tag-specifications "$(tag route-table "$APP-private")" \
    --query RouteTable.RouteTableId --output text)
  aws ec2 create-route --route-table-id "$RT_ID" --destination-cidr-block 0.0.0.0/0 --nat-gateway-id "$NAT_ID" >/dev/null
fi
for subnet in "${PRIVATE_SUBNETS[@]}"; do
  aws ec2 associate-route-table --route-table-id "$RT_ID" --subnet-id "$subnet" >/dev/null 2>&1 || true
done

echo "== security groups: the database only accepts the App Runner connector"
security_group() {
  local name=$1 description=$2 id
  id=$(aws ec2 describe-security-groups --filters Name=group-name,Values="$name" Name=vpc-id,Values="$VPC_ID" \
    --query 'SecurityGroups[0].GroupId' --output text)
  if [ "$id" = "None" ]; then
    id=$(aws ec2 create-security-group --group-name "$name" --description "$description" --vpc-id "$VPC_ID" \
      --tag-specifications "$(tag security-group "$name")" --query GroupId --output text)
  fi
  echo "$id"
}
CONNECTOR_SG=$(security_group "$APP-connector" "Ya Sale App Runner VPC connector")
DB_SG=$(security_group "$APP-db" "Ya Sale Postgres, reachable only from the connector")
aws ec2 authorize-security-group-ingress --group-id "$DB_SG" --protocol tcp --port 5432 \
  --source-group "$CONNECTOR_SG" >/dev/null 2>&1 || true

echo "== database subnet group"
aws rds describe-db-subnet-groups --db-subnet-group-name "$APP" >/dev/null 2>&1 || \
  aws rds create-db-subnet-group --db-subnet-group-name "$APP" --db-subnet-group-description "Ya Sale private" \
    --subnet-ids "${PRIVATE_SUBNETS[@]}" --tags Key=Project,Value="$APP" >/dev/null

echo "== database password (SSM SecureString, never printed)"
aws ssm get-parameter --name "/$APP/DB_PASSWORD" >/dev/null 2>&1 || \
  aws ssm put-parameter --name "/$APP/DB_PASSWORD" --type SecureString --value "$(openssl rand -hex 24)" >/dev/null

echo "== private Postgres 16 db.t4g.micro"
if ! aws rds describe-db-instances --db-instance-identifier "$APP" >/dev/null 2>&1; then
  aws rds create-db-instance --db-instance-identifier "$APP" --engine postgres --engine-version 16 \
    --db-instance-class db.t4g.micro --allocated-storage 20 --storage-type gp3 --storage-encrypted \
    --master-username yasale \
    --master-user-password "$(aws ssm get-parameter --name "/$APP/DB_PASSWORD" --with-decryption --query Parameter.Value --output text)" \
    --db-name yasale --db-subnet-group-name "$APP" --vpc-security-group-ids "$DB_SG" --no-publicly-accessible \
    --backup-retention-period 1 --no-multi-az --no-deletion-protection --tags Key=Project,Value="$APP" >/dev/null
fi

echo "== App Runner VPC connector"
aws apprunner list-vpc-connectors --query "VpcConnectors[?VpcConnectorName=='$APP' && Status=='ACTIVE'].VpcConnectorArn" \
  --output text | grep -q arn || \
  aws apprunner create-vpc-connector --vpc-connector-name "$APP" --subnets "${PRIVATE_SUBNETS[@]}" \
    --security-groups "$CONNECTOR_SG" --tags Key=Project,Value="$APP" >/dev/null

echo "== ECR repository"
aws ecr describe-repositories --repository-names "$APP" >/dev/null 2>&1 || \
  aws ecr create-repository --repository-name "$APP" --image-scanning-configuration scanOnPush=true \
    --tags Key=Project,Value="$APP" >/dev/null

echo "== IAM role App Runner uses to pull from ECR"
if ! aws iam get-role --role-name "$APP-ecr-access" >/dev/null 2>&1; then
  aws iam create-role --role-name "$APP-ecr-access" --tags Key=Project,Value="$APP" --assume-role-policy-document \
    '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"build.apprunner.amazonaws.com"},"Action":"sts:AssumeRole"}]}' >/dev/null
  aws iam attach-role-policy --role-name "$APP-ecr-access" \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSAppRunnerServicePolicyForECRAccess
fi

echo "== IAM role the running service uses to read only its own secrets"
ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
if ! aws iam get-role --role-name "$APP-instance" >/dev/null 2>&1; then
  aws iam create-role --role-name "$APP-instance" --tags Key=Project,Value="$APP" --assume-role-policy-document \
    '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"tasks.apprunner.amazonaws.com"},"Action":"sts:AssumeRole"}]}' >/dev/null
  aws iam put-role-policy --role-name "$APP-instance" --policy-name read-own-secrets --policy-document "{
    \"Version\":\"2012-10-17\",
    \"Statement\":[
      {\"Effect\":\"Allow\",\"Action\":[\"ssm:GetParameters\",\"ssm:GetParameter\"],\"Resource\":\"arn:aws:ssm:$REGION:$ACCOUNT:parameter/$APP/*\"},
      {\"Effect\":\"Allow\",\"Action\":\"kms:Decrypt\",\"Resource\":\"*\",\"Condition\":{\"StringEquals\":{\"kms:ViaService\":\"ssm.$REGION.amazonaws.com\"}}}
    ]}"
fi

echo "== auto scaling: exactly one instance (the rate limiter lives in memory)"
aws apprunner list-auto-scaling-configurations --auto-scaling-configuration-name "$APP-single" \
  --query 'AutoScalingConfigurationSummaryList[0].AutoScalingConfigurationArn' --output text | grep -q arn || \
  aws apprunner create-auto-scaling-configuration --auto-scaling-configuration-name "$APP-single" \
    --min-size 1 --max-size 1 --max-concurrency 100 --tags Key=Project,Value="$APP" >/dev/null

echo "== fingerprint salt (SSM SecureString, never printed)"
aws ssm get-parameter --name "/$APP/FINGERPRINT_SALT" >/dev/null 2>&1 || \
  aws ssm put-parameter --name "/$APP/FINGERPRINT_SALT" --type SecureString --value "$(openssl rand -hex 32)" >/dev/null

echo "== database status"
aws rds describe-db-instances --db-instance-identifier "$APP" --query 'DBInstances[0].DBInstanceStatus' --output text
