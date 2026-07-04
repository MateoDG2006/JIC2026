#!/usr/bin/env bash
# Descarga ChEMBLdb SQLite al volumen Docker (idempotente).
set -euo pipefail

CONFIG="${CONFIG_PATH:-/app/config/config.yaml}"

if [[ ! -f "${CONFIG}" ]]; then
  echo "[chembl-init] ERROR: no se encontró ${CONFIG}"
  exit 1
fi

mapfile -t _cfg < <(python3 - "${CONFIG}" <<'PY'
import os
import sys
import yaml
from pathlib import Path

config_path = Path(sys.argv[1])
root = config_path.parent.parent
cfg = yaml.safe_load(config_path.read_text(encoding="utf-8"))["chembl"]
db_path = Path(os.environ["CHEMBL_DB_PATH"])
print(cfg["version"])
print(cfg["ftp_url"])
print(db_path)
PY
)

VERSION="${_cfg[0]}"
URL="${_cfg[1]}"
DB_PATH="${_cfg[2]}"
CHEMBL_DIR="$(dirname "${DB_PATH}")"
TAR="${CHEMBL_DIR}/chembl_${VERSION}_sqlite.tar.gz"
MANIFEST="${CHEMBL_DIR}/manifest.json"

mkdir -p "${CHEMBL_DIR}"

if [[ -f "${DB_PATH}" ]]; then
  echo "[chembl-init] Base de datos ya existe: ${DB_PATH}"
  exit 0
fi

if [[ ! -f "${TAR}" ]]; then
  echo "[chembl-init] Descargando ${URL} ..."
  wget -c --progress=dot:giga "${URL}" -O "${TAR}"
else
  echo "[chembl-init] Usando archivo local: ${TAR}"
fi

echo "[chembl-init] Extrayendo (puede tardar varios minutos)..."
tar -xzf "${TAR}" -C "${CHEMBL_DIR}"

EXTRACTED="$(find "${CHEMBL_DIR}" -maxdepth 3 -name "chembl_*.db" -type f | head -1)"
if [[ -z "${EXTRACTED}" ]]; then
  echo "[chembl-init] ERROR: no se encontró chembl_*.db tras extraer el tar."
  exit 1
fi

if [[ "${EXTRACTED}" != "${DB_PATH}" ]]; then
  mv "${EXTRACTED}" "${DB_PATH}"
fi

find "${CHEMBL_DIR}" -type d -empty -delete 2>/dev/null || true

python3 - <<PY
import json
from datetime import datetime, timezone
from pathlib import Path

db = Path("${DB_PATH}")
manifest = {
    "version": "${VERSION}",
    "source_url": "${URL}",
    "db_path": str(db),
    "db_size_bytes": db.stat().st_size if db.exists() else None,
    "installed_at": datetime.now(timezone.utc).isoformat(),
}
Path("${MANIFEST}").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
print(json.dumps(manifest, indent=2))
PY

echo "[chembl-init] Listo: ${DB_PATH}"
