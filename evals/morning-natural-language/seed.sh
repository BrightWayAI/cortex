#!/usr/bin/env bash
# Seeds the shared fictional config root (see evals/_fixtures/).
set -euo pipefail
exec bash "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../_fixtures/seed-config-root.sh"
