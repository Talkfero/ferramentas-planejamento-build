# -*- coding: utf-8 -*-
"""Valida um `latest.json` do jeito que o APP o valida, antes de publicar.

Motivo (23/09/2026): a publicacao da 1.3.5 saiu com a URL escrita com UMA
barra invertida inicial em vez de duas. Sem o prefixo UNC completo,
``looks_like_fs_path`` devolve False e o app recusa com ``url_invalida``.
Como `min_version` obriga a atualizar, o usuario ficou bloqueado E sem
conseguir atualizar -- o pior caso possivel.

A validacao daquela publicacao passou mesmo assim porque conferia so o NOME
do arquivo (`PurePath(url).name`), jogando fora o caminho. Ou seja: **nao
falharia com o defeito presente**, que e' a definicao de ruido verde.

Este script fecha isso usando as funcoes REAIS do Cadastro -- as mesmas que
decidem se o download vai acontecer. Nao reimplementa a regra: se o app mudar
de criterio, o validador muda junto.

Uso:
    python scripts/check_latest_json.py <caminho do latest.json>
    python scripts/check_latest_json.py            # le o publicado na rede

Sai com codigo 1 se algo estiver errado.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import sys

REDE = pathlib.Path(
    "//fs-celpa-02/GEPLP/COPLD/10 - SOFTWARES/Ferramentas de Planejamento"
)


def _carregar_funcoes_do_app():
    """Importa `looks_like_fs_path`/`fs_path_from` do Sistema de Cadastro.

    De proposito do repo de origem, e nao uma copia: o ponto do validador e'
    usar a MESMA regra que o app usa em producao.
    """
    raiz = pathlib.Path(__file__).resolve().parents[2]
    mw = raiz / "sistemadecadastro" / "main_web"
    if not (mw / "mw_base.py").exists():
        raise SystemExit(
            f"[erro] nao achei {mw / 'mw_base.py'}.\n"
            "       O validador precisa do repo do Cadastro como pasta irma."
        )
    sys.path.insert(0, str(mw))
    from mw_base import fs_path_from, looks_like_fs_path  # noqa: PLC0415

    return looks_like_fs_path, fs_path_from


def _sha256(caminho: pathlib.Path) -> str:
    h = hashlib.sha256()
    with caminho.open("rb") as fh:
        for bloco in iter(lambda: fh.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def conferir(caminho_json: pathlib.Path) -> int:
    looks_like_fs_path, fs_path_from = _carregar_funcoes_do_app()
    dados = json.loads(caminho_json.read_text(encoding="utf-8"))

    print(f"Validando {caminho_json}")
    problemas: list[str] = []
    hashes: dict[str, str] = {}

    for app, bloco in dados.items():
        erros: list[str] = []

        for campo in ("version", "url", "sha256", "notes", "min_version"):
            if not str(bloco.get(campo, "")).strip():
                erros.append(f"campo '{campo}' vazio ou ausente")

        url = str(bloco.get("url", ""))
        # A pergunta que importa: o APP aceitaria esta URL?
        if not looks_like_fs_path(url) and not url.startswith(
            ("http://", "https://")
        ):
            erros.append(
                "url recusada por looks_like_fs_path -- o app diria "
                "'url_invalida'. Caminho UNC precisa dos DOIS contrabarras "
                f"iniciais. Veio: {url[:40]!r}"
            )
        elif looks_like_fs_path(url):
            alvo = pathlib.Path(fs_path_from(url))
            if not alvo.exists():
                erros.append(f"url aponta para arquivo inexistente: {alvo}")
            else:
                # Hash do arquivo que a URL RESOLVE, nao de um caminho montado
                # aqui -- foi essa diferenca que deixou o defeito passar.
                if url not in hashes:
                    hashes[url] = _sha256(alvo)
                if hashes[url] != str(bloco.get("sha256", "")).lower():
                    erros.append(
                        f"sha256 nao confere: JSON diz {bloco.get('sha256')}, "
                        f"arquivo tem {hashes[url]}"
                    )

        # min_version maior que version tranca todo mundo para sempre.
        if bloco.get("min_version") and bloco.get("version"):
            def partes(v: str) -> tuple:
                return tuple(int(x) for x in str(v).split(".") if x.isdigit())

            try:
                if partes(bloco["min_version"]) > partes(bloco["version"]):
                    erros.append(
                        f"min_version ({bloco['min_version']}) e' MAIOR que "
                        f"version ({bloco['version']}): ninguem consegue sair "
                        "do bloqueio, nem instalando"
                    )
            except ValueError:
                erros.append("version/min_version nao numericas")

        if erros:
            problemas.extend(f"[{app}] {e}" for e in erros)
            print(f"  {app:<20} PROBLEMA")
            for e in erros:
                print(f"      {e}")
        else:
            print(
                f"  {app:<20} ok  version={bloco['version']} "
                f"min_version={bloco['min_version']}"
            )

    print()
    if problemas:
        print(f"{len(problemas)} problema(s). NAO PUBLICAR assim.")
        return 1
    print("latest.json valido pelas regras do proprio app.")
    return 0


def main() -> int:
    alvo = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else REDE / "latest.json"
    if not alvo.exists():
        print(f"[erro] nao achei {alvo}")
        return 1
    return conferir(alvo)


if __name__ == "__main__":
    raise SystemExit(main())
