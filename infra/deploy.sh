#!/usr/bin/env bash
# Local deploy from a Mac: builds the image, pushes it to ECR and releases it with release.sh.
# CI does the same build and push with GitHub actions and then calls release.sh too.
set -euo pipefail

export AWS_PROFILE="${AWS_PROFILE:-default}"
export AWS_REGION="${AWS_REGION:-us-east-1}"
APP="ya-sale"
TAG="${1:?usage: deploy.sh <image-tag>}"

ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
REGISTRY="$ACCOUNT.dkr.ecr.$AWS_REGION.amazonaws.com"
IMAGE="$REGISTRY/$APP:$TAG"

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

bash "$(dirname "$0")/release.sh" "$IMAGE"
