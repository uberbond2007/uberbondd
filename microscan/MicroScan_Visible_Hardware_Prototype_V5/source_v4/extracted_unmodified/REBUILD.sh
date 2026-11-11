#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [[ "${1:-}" == "--full" ]]; then
  python cad/build_hardware_v2.py
  python templates/generate_drawings.py
fi
python checks/validate_exported_meshes.py | tee logs/latest_validation.log
