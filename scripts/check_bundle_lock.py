# -*- coding: utf-8 -*-
"""Confere se as bibliotecas EMPACOTADAS batem com o requirements.lock.txt.

Motivo (15/10/2026): o workflow do GitHub nao aplicava o lock e o bundle saiu
com numpy 2.5.4, onnxruntime 1.31.0, playwright 1.64.0, snowflake-connector
5.0.0... enquanto o lock (e o build local) tinham 2.4.6, 1.27.0, 1.60.0,
4.7.1. Os self-tests passaram mesmo assim: eles so' importam Coplan e
Elexplan. Esta checagem olha o que de fato foi para o `_internal`.

Le cada `<nome>-<versao>.dist-info` do bundle e compara com a linha
`nome==versao` do lock (nomes normalizados como no PEP 503). Versao diferente
derruba o build. Pacote empacotado que o lock nao trava so' gera aviso: o
lock vem de `pip freeze` e pode ficar atras de uma dependencia nova.

Uso:
    python scripts/check_bundle_lock.py [pasta do bundle] [lock]

Defaults: dist/FerramentasCompartilhadas e requirements.lock.txt na raiz.
Sai com codigo 1 se alguma versao divergir.
"""

from __future__ import annotations

import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent


def _norm(nome: str) -> str:
    return re.sub(r"[-_.]+", "-", nome).lower()


def ler_lock(caminho: pathlib.Path) -> dict[str, str]:
    travas = {}
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        linha = linha.split("#", 1)[0].strip()
        if "==" not in linha:
            continue
        nome, versao = linha.split("==", 1)
        nome = nome.split("[", 1)[0].strip()
        travas[_norm(nome)] = versao.split(";", 1)[0].strip()
    return travas


def ler_bundle(internal: pathlib.Path) -> dict[str, str]:
    achados = {}
    for pasta in internal.glob("*.dist-info"):
        base = pasta.name[: -len(".dist-info")]
        nome, _, versao = base.rpartition("-")
        if nome and versao:
            achados[_norm(nome)] = versao
    return achados


def main() -> int:
    bundle = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else RAIZ / "dist" / "FerramentasCompartilhadas"
    lock = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else RAIZ / "requirements.lock.txt"
    internal = bundle / "_internal" if (bundle / "_internal").is_dir() else bundle

    travas = ler_lock(lock)
    empacotados = ler_bundle(internal)
    if not empacotados:
        print(f"[check_bundle_lock] nenhum .dist-info em {internal}")
        return 1

    divergentes = sorted(
        (nome, versao, travas[nome])
        for nome, versao in empacotados.items()
        if nome in travas and travas[nome] != versao
    )
    sem_trava = sorted(nome for nome in empacotados if nome not in travas)

    print(f"[check_bundle_lock] {len(empacotados)} pacotes no bundle, "
          f"{len(empacotados) - len(sem_trava)} travados no lock")
    for nome in sem_trava:
        print(f"  aviso: {nome} {empacotados[nome]} empacotado sem trava no lock")
    for nome, achado, travado in divergentes:
        print(f"  ERRO: {nome} {achado} no bundle, lock pede {travado}")
    if divergentes:
        print(f"[check_bundle_lock] {len(divergentes)} pacote(s) fora do lock.")
        return 1
    print("[check_bundle_lock] bundle igual ao lock.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
