#!/usr/bin/env python3
"""Arranca el servidor FastAPI del visor (usa el venv del proyecto).

Wrapper sobre uvicorn que:
    1. Añade la raíz del repo al PYTHONPATH (uvicorn --reload lanza
       subprocesos sin el cwd correcto).
    2. Comprueba que el puerto está libre antes de bindar (Windows suele
       reservar puertos para WSL/Docker incluso si están "libres").
    3. Soporta ``--check-only`` para CI: solo importa la app sin levantar
       servidor (usado por ``make test-viz``).

Uso:
    python scripts/fase4/viz_serve.py                       # local :8000
    python scripts/fase4/viz_serve.py --host 0.0.0.0        # exposicion LAN
    python scripts/fase4/viz_serve.py --reload              # hot reload (dev)
    python scripts/fase4/viz_serve.py --check-only          # solo importa
"""

from __future__ import annotations

import argparse
import os
import socket
import sys
from pathlib import Path

# Raiz del repo en PYTHONPATH (uvicorn --reload lanza un subproceso sin el cwd)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
_ROOT = str(PROJECT_ROOT)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
_prev_pp = os.environ.get("PYTHONPATH", "")
os.environ["PYTHONPATH"] = _ROOT if not _prev_pp else f"{_ROOT}{os.pathsep}{_prev_pp}"


def port_available(host: str, port: int) -> tuple[bool, str]:
    """Verifica si ``host:port`` se puede bindar.

    Returns:
        (True, "")        si el puerto está libre
        (False, mensaje)  si ya está en uso (OSError convertido a string)
    """
    bind_host = "" if host in ("0.0.0.0", "::") else host
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind((bind_host, port))
            return True, ""
        except OSError as exc:
            return False, str(exc)


def main() -> None:
    parser = argparse.ArgumentParser(description="Servidor GNN-Tox Viewer")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true")
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Solo verifica que la app FastAPI importa correctamente",
    )
    args = parser.parse_args()

    if args.check_only:
        from viz.app import app  # noqa: F401

        print("OK - FastAPI app cargada (visor GNN + analytics)")
        return

    ok, err = port_available(args.host, args.port)
    if not ok:
        print(f"ERROR: puerto {args.port} no disponible ({err})", file=sys.stderr)
        print(
            f"  El puerto esta ocupado o bloqueado por Windows.\n"
            f"  Prueba otro puerto: make viz VIZ_PORT=8000\n"
            f"  O solo local:       make viz",
            file=sys.stderr,
        )
        sys.exit(1)

    import uvicorn

    url_host = "localhost" if args.host in ("0.0.0.0", "::") else args.host
    print(f"Servidor: http://{url_host}:{args.port}")
    if args.host == "0.0.0.0":
        print(f"  (acceso LAN: http://<tu-ip>:{args.port})")

    uvicorn.run(
        "viz.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        reload_dirs=[str(PROJECT_ROOT / "viz")] if args.reload else None,
    )


if __name__ == "__main__":
    main()
