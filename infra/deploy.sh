#!/usr/bin/env bash
# Local deploy from a Mac: builds and pushes the image, then releases it to Lambda.
# CI does the same build with GitHub actions and then calls release.sh too.
set -euo pipefail

export AWS_PROFILE="${AWS_PROFILE:-default}"
export AWS_REGION="${AWS_REGION:-us-east-1}"
IMAGE=$(bash "$(dirname "$0")/build.sh" "${1:?usage: deploy.sh <image-tag>}" | tail -1)
bash "$(dirname "$0")/release.sh" "$IMAGE"
