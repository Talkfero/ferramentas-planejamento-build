from __future__ import annotations

import argparse
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

REQUIRED = {
    "launcher": [
        "apps/launcher/codigo0_ferramentas_planejamento.py",
        "apps/launcher/eng.ico",
    ],
    "elexplan": [
        "apps/elexplan/codigo1_elexplan.py",
        "apps/elexplan/Elexplan.ico",
    ],
    "diag": [
        "apps/diagnostico/diagnostico.py",
        "apps/diagnostico/diagnostico.ico",
    ],
    "imagedx": [
        "apps/imagedx/codigo3_imagedx.py",
        "apps/imagedx/eng.ico",
    ],
    "unif": [
        "apps/unificador/codigo4_unificador_de_arquivos.py",
        "apps/unificador/Unificador.ico",
    ],
    "coplan_web": [
        "apps/coplan/scripts/build/coplan_launcher.py",
        "apps/coplan/frontend/index.html",
        "apps/coplan/frontend/assets/cadastro-de-obras.ico",
        "apps/coplan/requirements-web.txt",
    ],
    "capex": [
        "apps/capex/_nina_ceo/builds/capex_web_launcher.py",
        "apps/capex/web/main_web.py",
        "apps/capex/web/frontend/index.html",
        "apps/capex/web/requirements-web.txt",
        "apps/capex/capex.ico",
    ],
    "status": [
        "apps/status_medicao/status_medicao.py",
    ],
    "cadastro": [
        "apps/cadastro_viabilidades/main_web/main_web.py",
        "apps/cadastro_viabilidades/main_web/index.html",
        "apps/cadastro_viabilidades/main_web/requirements-web.txt",
        "apps/cadastro_viabilidades/Sistema_Cadastro.ico",
    ],
}


def selected(raw: str) -> list[str]:
    raw = (raw or "all").strip().lower().replace(";", ",")
    if raw in {"", "all"}:
        return list(REQUIRED)
    keys = []
    for item in raw.split(","):
        key = item.strip()
        if key == "coplan":
            key = "coplan_web"
        if key:
            keys.append(key)
    invalid = sorted(set(keys) - set(REQUIRED))
    if invalid:
        raise SystemExit(f"Chaves invalidas: {invalid}. Chaves validas: {sorted(REQUIRED)}")
    return keys


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apps", default="all")
    args = parser.parse_args()

    missing = []
    for key in selected(args.apps):
        for rel in REQUIRED[key]:
            if not (ROOT / rel).is_file():
                missing.append(rel)

    if missing:
        print("Layout incompleto para o build:")
        for rel in missing:
            print(f"  - {rel}")
        print("\nNo GitHub Actions, rode scripts/prepare_apps.ps1 antes do build.")
        return 1

    print("Layout OK.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
