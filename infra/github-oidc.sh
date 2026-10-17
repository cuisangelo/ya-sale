#!/usr/bin/env bash
# Lets GitHub Actions deploy without stored AWS keys: an OIDC trust limited to the main branch of
# cuisangelo/ya-sale, and a role that can only push the ya-sale image and update the ya-sale service.
set -euo pipefail

PROFILE="${AWS_PROFILE:-default}"
REGION="${AWS_REGION:-us-east-1}"
APP="ya-sale"
REPO="cuisangelo/ya-sale"
ROLE="$APP-github-deploy"
aws() { command aws --profile "$PROFILE" --region "$REGION" "$@"; }

ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
PROVIDER="arn:aws:iam::$ACCOUNT:oidc-provider/token.actions.githubusercontent.com"

echo "== GitHub OIDC provider"
aws iam get-open-id-connect-provider --open-id-connect-provider-arn "$PROVIDER" >/dev/null 2>&1 || \
  aws iam create-open-id-connect-provider --url https://token.actions.githubusercontent.com \
    --client-id-list sts.amazonaws.com --tags Key=Project,Value="$APP" >/dev/null

echo "== deploy role, assumable only from $REPO main"
# The repo uses GitHub's immutable subject (owner and repo ids), so a rename cannot spoof it.
SUB_PREFIX=$(gh api "repos/$REPO/actions/oidc/customization/sub" --jq .sub_claim_prefix)
TRUST="{
  \"Version\": \"2012-10-17\",
  \"Statement\": [{
    \"Effect\": \"Allow\",
    \"Principal\": {\"Federated\": \"$PROVIDER\"},
    \"Action\": \"sts:AssumeRoleWithWebIdentity\",
    \"Condition\": {
      \"StringEquals\": {
        \"token.actions.githubusercontent.com:aud\": \"sts.amazonaws.com\",
        \"token.actions.githubusercontent.com:sub\": \"$SUB_PREFIX:ref:refs/heads/main\"
      }
    }
  }]
}"
if aws iam get-role --role-name "$ROLE" >/dev/null 2>&1; then
  aws iam update-assume-role-policy --role-name "$ROLE" --policy-document "$TRUST"
else
  aws iam create-role --role-name "$ROLE" --tags Key=Project,Value="$APP" --assume-role-policy-document "$TRUST" >/dev/null
fi

aws iam put-role-policy --role-name "$ROLE" --policy-name deploy-ya-sale --policy-document "{
  \"Version\": \"2012-10-17\",
  \"Statement\": [
    {\"Effect\": \"Allow\", \"Action\": \"ecr:GetAuthorizationToken\", \"Resource\": \"*\"},
    {\"Effect\": \"Allow\", \"Action\": [
      \"ecr:BatchCheckLayerAvailability\", \"ecr:BatchGetImage\", \"ecr:CompleteLayerUpload\",
      \"ecr:InitiateLayerUpload\", \"ecr:PutImage\", \"ecr:UploadLayerPart\"],
     \"Resource\": \"arn:aws:ecr:$REGION:$ACCOUNT:repository/$APP\"},
    {\"Effect\": \"Allow\", \"Action\": \"apprunner:ListServices\", \"Resource\": \"*\"},
    {\"Effect\": \"Allow\", \"Action\": [\"apprunner:UpdateService\", \"apprunner:DescribeService\"],
     \"Resource\": \"arn:aws:apprunner:$REGION:$ACCOUNT:service/$APP/*\"},
    {\"Effect\": \"Allow\", \"Action\": \"iam:PassRole\", \"Resource\": \"arn:aws:iam::$ACCOUNT:role/$APP-ecr-access\"}
  ]
}"

echo "AWS_DEPLOY_ROLE=arn:aws:iam::$ACCOUNT:role/$ROLE"
