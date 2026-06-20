#!/usr/bin/env bash
# Descarga e instala ChEMBLdb SQLite (idempotente).
set -euo pipefail

CHEMBL_DIR="${CHEMBL_DIR:-/data/chembl}"
VERSION="${CHEMBL_VERSION:-37}"
URL="${CHEMBL_FTP_URL:-https://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/latest/chembl_${VERSION}_sqlite.tar.gz}"
TAR="${CHEMBL_DIR}/chembl_${VERSION}_sqlite.tar.gz"
DB_PATH="${CHEMBL_DIR}/chembl_${VERSION}.db"
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

# Limpiar directorios vacíos del tar
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
