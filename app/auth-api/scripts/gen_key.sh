#!/usr/bin/env bash

set -euo pipefail

# Resolve important paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"          # .../app
AUTH_API_DIR="${APP_DIR}/auth-api"
API_GATEWAY_DIR="${APP_DIR}/api-gateway"

PRIVATE_KEY_PATH="${APP_DIR}/private.pem"
PUBLIC_KEY_PATH="${APP_DIR}/public.pem"
GATEWAY_PUBLIC_KEY_PATH="${API_GATEWAY_DIR}/public.pem"

echo "App directory: ${APP_DIR}"
echo "Auth API directory: ${AUTH_API_DIR}"
echo "API Gateway directory: ${API_GATEWAY_DIR}"

if ! command -v openssl >/dev/null 2>&1; then
  echo "Error: openssl is required but not installed or not in PATH." >&2
  exit 1
fi

echo "Generating RSA private key..."
openssl genrsa -out "${PRIVATE_KEY_PATH}" 4096

echo "Deriving public key from private key..."
openssl rsa -in "${PRIVATE_KEY_PATH}" -pubout -out "${PUBLIC_KEY_PATH}"

echo "Copying public key to API Gateway..."
cp "${PUBLIC_KEY_PATH}" "${GATEWAY_PUBLIC_KEY_PATH}"

echo "Done."
echo "Private key: ${PRIVATE_KEY_PATH}"
echo "Public key: ${PUBLIC_KEY_PATH}"
echo "API Gateway public key copy: ${GATEWAY_PUBLIC_KEY_PATH}"

