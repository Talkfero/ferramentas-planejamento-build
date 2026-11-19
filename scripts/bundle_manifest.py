# -*- coding: utf-8 -*-
"""Base publicada: o que reaproveitar quando so' um app muda.

Decisao WS-20261118-base-publicada (usuario, 18/11/2026): *"se eu atualizar o
Coplan [...] nao precisar rodar todos os programas de novo [...] se eles ja
foram rodados e estao no repositorio e eu nao os atualizei, e' so' pegar"*.

Cada publicacao guarda o bundle publicado numa release fixa ``base-<versao>``
com um ``manifest.json``: commit de cada app, codigo do conjunto de
dependencias e SHA-256 de cada ``.exe``. Num build com ``rebuild_only``:

* os apps escolhidos saem do ``main``;
* os outros voltam ao commit da base (``fixar``) -- nunca o ``main``, que pode
  ter trabalho pela metade -- e, se as dependencias nao mudaram, o ``.exe``
  deles vem da base byte a byte (o ``gerar`` confere);
* dependencias mudaram: recompila tudo, ainda com os nao escolhidos fixados.

Subcomandos (so' biblioteca padrao: roda antes do venv do build):

    deps-hash    imprime o codigo do conjunto de dependencias de ``--root``
    normalizar   imprime a lista canonica de apps (aliases resolvidos)
    ultima-base  imprime a tag ``base-*`` mais nova da release (via ``gh``)
    fixar        volta os apps nao escolhidos ao commit da base
    gerar        escreve o ``manifest.json`` do bundle montado
    conferir-modulos
                 reprova um .exe recompilado que perdeu modulos de terceiros
                 ou da biblioteca padrao em relacao ao .exe da base
    pendentes    (local) lista os commits de cada app ainda nao publicados
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

SCHEMA = 1


@dataclass(frozen=True)
class App:
    chave: str
    exe: str
    pasta: str          # relativa a raiz do repo de build (layout de apps/)
    repo: str | None    # pasta irma no workspace; None = vive neste repo


APPS: dict[str, App] = {
    a.chave: a
    for a in (
        App("launcher", "Ferramentas de Planejamento.exe", "apps/launcher", "Ferramenta_plan"),
        App("elexplan", "Elexplan.exe", "apps/elexplan", "elexplan"),
        App("unif", "Unificador de arquivos.exe", "apps/unificador", None),
        App("coplan_web", "Coplan Web.exe", "apps/coplan", "coplanweb"),
        App("cadastro", "Sistema de Cadastro.exe", "apps/cadastro_viabilidades", "sistemadecadastro"),
    )
}

# Os mesmos de build_all_shared.bat / Setup_turbinado.iss.
ALIASES = {
    "coplan": "coplan_web",
    "capex": "coplan_web",
    "diag": "coplan_web",
    "imagedx": "coplan_web",
    "status": "elexplan",
}

# O que define o conjunto de dependencias do _internal compartilhado. Mesma
# lista que a chave do antigo cache do bundle (bundle-v2). O codigo-fonte dos
# apps fica de fora de proposito: e' isso que deixa reaproveitar o bundle.
DEPS_ARQUIVOS = ("requirements.lock.txt", "multi_apps.spec", "build_all_shared.bat")
DEPS_PASTAS = ("runtime_hooks", "app_configs")
_IGNORAR_PARTES = {".git", "__pycache__", "node_modules"}

REPO_PADRAO = "Talkfero/ferramentas-planejamento-build"
_TAG_BASE = re.compile(r"^base-(\d+)\.(\d+)\.(\d+)$")


# ---------------------------------------------------------------------------
# Apps
# ---------------------------------------------------------------------------
def normalizar(texto: str) -> list[str]:
    """``"coplan, Elexplan"`` -> ``["coplan_web", "elexplan"]``; ``all`` -> todos."""
    saida: list[str] = []
    for bruto in re.split(r"[,;\s]+", (texto or "").strip().lower()):
        if not bruto:
            continue
        if bruto == "all":
            return list(APPS)
        chave = ALIASES.get(bruto, bruto)
        if chave not in APPS:
            raise SystemExit(
                f"[bundle_manifest] app desconhecido: {bruto!r}. "
                f"Validos: {', '.join(APPS)} (aliases: {', '.join(ALIASES)})."
            )
        if chave not in saida:
            saida.append(chave)
    return saida


# ---------------------------------------------------------------------------
# Dependencias
# ---------------------------------------------------------------------------
def _ignorado(p: Path, raiz: Path) -> bool:
    return any(parte in _IGNORAR_PARTES for parte in p.relative_to(raiz).parts) or p.suffix == ".pyc"


def arquivos_de_dependencia(raiz: Path) -> list[Path]:
    achados: set[Path] = set()
    for nome in DEPS_ARQUIVOS:
        p = raiz / nome
        if p.is_file():
            achados.add(p)
    for pasta in DEPS_PASTAS:
        base = raiz / pasta
        if base.is_dir():
            achados.update(p for p in base.rglob("*") if p.is_file() and not _ignorado(p, raiz))
    apps = raiz / "apps"
    if apps.is_dir():
        achados.update(
            p for p in apps.rglob("requirements*.txt") if p.is_file() and not _ignorado(p, raiz)
        )
    return sorted(achados, key=lambda p: p.relative_to(raiz).as_posix())


def deps_hash(raiz: Path) -> str:
    """Codigo do conjunto de dependencias. Fim de linha normalizado (CRLF/LF)."""
    h = hashlib.sha256()
    for p in arquivos_de_dependencia(raiz):
        rel = p.relative_to(raiz).as_posix()
        conteudo = p.read_bytes().replace(b"\r\n", b"\n")
        h.update(rel.encode("utf-8") + b"\0" + hashlib.sha256(conteudo).hexdigest().encode() + b"\n")
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------
def sha256_arquivo(caminho: Path) -> str:
    h = hashlib.sha256()
    with caminho.open("rb") as fh:
        for bloco in iter(lambda: fh.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def _git(pasta: Path, *args: str, checar: bool = True) -> str:
    r = subprocess.run(
        ["git", "-C", str(pasta), *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if checar and r.returncode != 0:
        raise SystemExit(f"[bundle_manifest] git {' '.join(args)} falhou em {pasta}:\n{r.stderr.strip()}")
    return r.stdout.strip()


def carregar_manifesto(caminho: Path) -> dict:
    m = json.loads(caminho.read_text(encoding="utf-8"))
    if m.get("schema") != SCHEMA:
        raise SystemExit(f"[bundle_manifest] manifesto com schema {m.get('schema')!r}; esperado {SCHEMA}.")
    return m


def _versao_tag(tag: str) -> tuple[int, int, int] | None:
    m = _TAG_BASE.match(tag.strip())
    return tuple(int(x) for x in m.groups()) if m else None  # type: ignore[return-value]


def escolher_ultima_base(tags: list[str]) -> str:
    validas = [(v, t) for t in tags if (v := _versao_tag(t))]
    return max(validas)[1] if validas else ""


# ---------------------------------------------------------------------------
# fixar
# ---------------------------------------------------------------------------
def fixar(base: dict, escolhidos: list[str], raiz: Path) -> list[tuple[str, str]]:
    """Volta cada app NAO escolhido ao commit registrado na base."""
    feitos: list[tuple[str, str]] = []
    for chave, app in APPS.items():
        if chave in escolhidos:
            continue
        entrada = base.get("apps", {}).get(chave)
        if not entrada or not entrada.get("commit"):
            raise SystemExit(
                f"[fixar] {chave} nao esta na base {base.get('versao_instalador')}. "
                f"Inclua-o em rebuild_only ou rode o build completo."
            )
        commit = entrada["commit"]
        if app.repo is None:
            # Vive neste repo: restaura so' a pasta dele no commit da base.
            _git(raiz, "fetch", "--depth", "1", "origin", commit)
            _git(raiz, "checkout", commit, "--", app.pasta)
        else:
            pasta = raiz / app.pasta
            _git(pasta, "fetch", "--depth", "1", "origin", commit)
            _git(pasta, "checkout", "--detach", commit)
        print(f"[fixar] {chave}: commit da base {commit[:7]}")
        feitos.append((chave, commit))
    return feitos


# ---------------------------------------------------------------------------
# gerar
# ---------------------------------------------------------------------------
def gerar(
    *,
    bundle: Path,
    raiz: Path,
    versao: str,
    modo: str,
    escolhidos: list[str],
    deps: str,
    instalador: Path,
    build_sha: str,
    run_id: str,
    base: dict | None,
    base_tag: str,
) -> dict:
    if modo not in ("full", "incremental"):
        raise SystemExit(f"[gerar] modo invalido: {modo!r}")
    if modo == "incremental" and base is None:
        raise SystemExit("[gerar] modo incremental exige --base-manifest.")
    if base is not None and not escolhidos:
        raise SystemExit("[gerar] com base, informe os apps escolhidos (--escolhidos).")
    if base is None:
        escolhidos = list(APPS)

    apps: dict[str, dict] = {}
    erros: list[str] = []
    for chave, app in APPS.items():
        exe = bundle / app.exe
        if not exe.is_file():
            erros.append(f"{app.exe} ausente do bundle")
            continue
        exe_sha = sha256_arquivo(exe)
        if chave not in escolhidos:
            b = base["apps"][chave]  # type: ignore[index]
            if modo == "incremental":
                if exe_sha != b["exe_sha256"]:
                    erros.append(
                        f"{chave}: {app.exe} deveria vir identico da {base_tag} "
                        f"({b['exe_sha256'][:12]}) e saiu {exe_sha[:12]}"
                    )
                entrada = {
                    "commit": b["commit"],
                    "compilado_em": b["compilado_em"],
                    "origem": base_tag,
                }
            else:
                entrada = {
                    "commit": b["commit"],
                    "compilado_em": versao,
                    "origem": f"recompilado no commit da {base_tag}",
                }
        else:
            commit = build_sha if app.repo is None else _git(raiz / app.pasta, "rev-parse", "HEAD")
            entrada = {"commit": commit, "compilado_em": versao, "origem": "recompilado"}
        apps[chave] = {"exe": app.exe, "exe_sha256": exe_sha, **entrada}

    if erros:
        raise SystemExit("[gerar] manifesto reprovado:\n  - " + "\n  - ".join(erros))

    return {
        "schema": SCHEMA,
        "versao_instalador": versao,
        "gerado_em": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "run_id": run_id,
        "build_sha": build_sha,
        "modo": modo,
        "base": base_tag or None,
        "escolhidos": escolhidos,
        "deps_hash": deps,
        "instalador": {
            "nome": instalador.name,
            "sha256": sha256_arquivo(instalador),
            "bytes": instalador.stat().st_size,
        },
        "apps": apps,
    }


# ---------------------------------------------------------------------------
# conferir-modulos
# ---------------------------------------------------------------------------
def modulos_do_exe(exe: Path) -> set[str]:
    """Nomes dos modulos Python dentro do PYZ de um .exe do PyInstaller."""
    try:
        from PyInstaller.archive.readers import CArchiveReader, ZlibArchiveReader
    except ImportError as exc:  # pragma: no cover - ambiente sem PyInstaller
        raise SystemExit(
            f"[conferir-modulos] PyInstaller indisponivel ({exc}); a conferencia "
            "nao pode rodar e o build nao deve ser publicado sem ela."
        ) from exc
    ar = CArchiveReader(str(exe))
    inicio = getattr(ar, "_start_offset", 0)
    nomes: set[str] = set()
    for nome, (off, _dlen, _ulen, _flag, tipo) in ar.toc.items():
        if tipo == "z" or nome.endswith(".pyz"):
            nomes |= set(ZlibArchiveReader(str(exe), start_offset=inicio + off).toc.keys())
    return nomes


def raizes_do_app(pasta: Path) -> set[str]:
    """Pacotes/modulos de primeira parte: o que fica na raiz do clone do app."""
    if not pasta.is_dir():
        return set()
    return {p.stem if p.is_file() else p.name for p in pasta.iterdir()
            if p.is_dir() or p.suffix == ".py"}


def modulos_perdidos(base: set[str], novo: set[str], primeira_parte: set[str]) -> list[str]:
    """Modulos que a base tinha e o novo nao, exceto os do proprio app.

    Codigo do app que saiu do repo e' mudanca legitima. Biblioteca de terceiros
    ou da biblioteca padrao que sumiu NAO e': foi o caso do Coplan 1.7.0, que
    saiu com 293 modulos a menos porque o build incremental so' instalou os
    requirements dele (19/11/2026).
    """
    return sorted(m for m in base - novo if m.split(".")[0] not in primeira_parte)


def conferir_modulos(bundle: Path, base: Path, chaves: list[str], raiz: Path) -> list[str]:
    erros: list[str] = []
    for chave in chaves:
        app = APPS[chave]
        exe_novo, exe_base = bundle / app.exe, base / app.exe
        if not exe_novo.is_file() or not exe_base.is_file():
            erros.append(f"{chave}: .exe ausente (novo={exe_novo.is_file()}, base={exe_base.is_file()})")
            continue
        mb, mn = modulos_do_exe(exe_base), modulos_do_exe(exe_novo)
        perdidos = modulos_perdidos(mb, mn, raizes_do_app(raiz / app.pasta))
        print(f"[conferir-modulos] {chave}: base {len(mb)} modulos, novo {len(mn)}, "
              f"perdidos de terceiros/stdlib {len(perdidos)}")
        if perdidos:
            raizes = sorted({m.split(".")[0] for m in perdidos})
            erros.append(
                f"{chave}: o .exe perdeu {len(perdidos)} modulo(s) em relacao a base "
                f"({', '.join(raizes[:15])}{'...' if len(raizes) > 15 else ''}). "
                "O ambiente do build nao tem as bibliotecas que a base tinha."
            )
    return erros


def imprimir_resumo(m: dict) -> None:
    print(f"[manifesto] instalador {m['versao_instalador']} | modo {m['modo']} | base {m['base'] or '-'}")
    for chave, e in m["apps"].items():
        print(f"  {chave:<11} {e['commit'][:7]}  compilado na {e['compilado_em']:<8} {e['origem']}")


# ---------------------------------------------------------------------------
# pendentes (local)
# ---------------------------------------------------------------------------
def _baixar_manifesto(repo: str, tag: str, destino: Path) -> Path:
    r = subprocess.run(
        ["gh", "release", "download", tag, "--repo", repo, "-p", "manifest.json", "-D", str(destino), "--clobber"],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        raise SystemExit(f"[pendentes] nao consegui baixar o manifest.json da {tag}: {r.stderr.strip()}")
    return destino / "manifest.json"


def _tags_de_release(repo: str) -> list[str]:
    r = subprocess.run(
        ["gh", "release", "list", "--repo", repo, "--limit", "200", "--json", "tagName", "--jq", ".[].tagName"],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        raise SystemExit(f"[bundle_manifest] gh release list falhou: {r.stderr.strip()}")
    return [t for t in r.stdout.split() if t]


def pendentes(base: dict, workspace: Path, buscar: bool) -> int:
    print(f"Base publicada: instalador {base['versao_instalador']} (run {base.get('run_id')})")
    print("Commits no origin/main de cada app que NAO estao na base:\n")
    build_repo = workspace / "ferramentas-planejamento-build"
    for chave, app in APPS.items():
        e = base["apps"].get(chave)
        if not e:
            print(f"{chave}: fora da base -- tem de ser recompilado.\n")
            continue
        repo = workspace / app.repo if app.repo else build_repo
        caminho = [] if app.repo else ["--", app.pasta]
        if buscar:
            _git(repo, "fetch", "-q", "origin")
        if not _git(repo, "cat-file", "-t", e["commit"], checar=False):
            print(f"{chave}: commit da base {e['commit'][:7]} nao existe em {repo.name}; faca fetch.\n")
            continue
        log = _git(repo, "log", "--oneline", f"{e['commit']}..origin/main", *caminho)
        reqs = [
            linha for linha in _git(repo, "diff", "--name-only", e["commit"], "origin/main", *caminho).splitlines()
            if Path(linha).name.lower().startswith("requirements") and linha.lower().endswith(".txt")
        ]
        if not log:
            print(f"{chave}: igual a base ({e['commit'][:7]})\n")
            continue
        linhas = log.splitlines()
        print(f"{chave}: {len(linhas)} commit(s) nao publicados desde {e['commit'][:7]}")
        for linha in linhas[:15]:
            print(f"    {linha}")
        if len(linhas) > 15:
            print(f"    ... e mais {len(linhas) - 15}")
        if reqs:
            print(f"    ATENCAO: requirements mudou ({', '.join(reqs)}) -> se entrar, o build recompila tudo")
        print()
    deps_mudados = _git(
        build_repo, "diff", "--name-only", base["build_sha"], "origin/main", "--",
        *DEPS_ARQUIVOS, *DEPS_PASTAS,
    )
    if deps_mudados:
        print("ATENCAO: dependencias do build mudaram desde a base -> o proximo build recompila tudo:")
        for linha in deps_mudados.splitlines():
            print(f"    {linha}")
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("deps-hash")
    p.add_argument("--root", type=Path, default=Path("."))

    p = sub.add_parser("normalizar")
    p.add_argument("apps")

    p = sub.add_parser("ultima-base")
    p.add_argument("--repo", default=REPO_PADRAO)

    p = sub.add_parser("fixar")
    p.add_argument("--base-manifest", type=Path, required=True)
    p.add_argument("--escolhidos", required=True)
    p.add_argument("--root", type=Path, default=Path("."))

    p = sub.add_parser("gerar")
    p.add_argument("--bundle", type=Path, required=True)
    p.add_argument("--root", type=Path, default=Path("."))
    p.add_argument("--versao", required=True)
    p.add_argument("--modo", required=True)
    p.add_argument("--escolhidos", default="")
    p.add_argument("--deps-hash", required=True)
    p.add_argument("--instalador", type=Path, required=True)
    p.add_argument("--build-sha", required=True)
    p.add_argument("--run-id", default="")
    p.add_argument("--base-manifest", type=Path)
    p.add_argument("--base-tag", default="")
    p.add_argument("--saida", type=Path, required=True)

    p = sub.add_parser("conferir-modulos")
    p.add_argument("--bundle", type=Path, required=True)
    p.add_argument("--base", type=Path, required=True)
    p.add_argument("--apps", required=True)
    p.add_argument("--root", type=Path, default=Path("."))

    p = sub.add_parser("pendentes")
    p.add_argument("--manifest", type=Path, help="manifest.json local; sem isto baixa o da ultima base")
    p.add_argument("--repo", default=REPO_PADRAO)
    p.add_argument("--workspace", type=Path, default=Path(__file__).resolve().parents[2])
    p.add_argument("--fetch", action="store_true", help="git fetch em cada repo antes de comparar")

    a = ap.parse_args(argv)

    if a.cmd == "deps-hash":
        print(deps_hash(a.root.resolve()))
    elif a.cmd == "normalizar":
        print(",".join(normalizar(a.apps)))
    elif a.cmd == "ultima-base":
        print(escolher_ultima_base(_tags_de_release(a.repo)))
    elif a.cmd == "fixar":
        fixar(carregar_manifesto(a.base_manifest), normalizar(a.escolhidos), a.root.resolve())
    elif a.cmd == "gerar":
        base = carregar_manifesto(a.base_manifest) if a.base_manifest else None
        m = gerar(
            bundle=a.bundle, raiz=a.root.resolve(), versao=a.versao, modo=a.modo,
            escolhidos=normalizar(a.escolhidos), deps=a.deps_hash, instalador=a.instalador,
            build_sha=a.build_sha, run_id=a.run_id, base=base, base_tag=a.base_tag,
        )
        a.saida.write_text(json.dumps(m, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        imprimir_resumo(m)
    elif a.cmd == "conferir-modulos":
        erros = conferir_modulos(a.bundle, a.base, normalizar(a.apps), a.root.resolve())
        if erros:
            raise SystemExit("[conferir-modulos] REPROVADO:\n  - " + "\n  - ".join(erros))
        print("[conferir-modulos] OK: nenhum .exe perdeu modulos em relacao a base.")
    elif a.cmd == "pendentes":
        if a.manifest:
            base = carregar_manifesto(a.manifest)
        else:
            tag = escolher_ultima_base(_tags_de_release(a.repo))
            if not tag:
                raise SystemExit("[pendentes] nenhuma release base-* publicada.")
            with tempfile.TemporaryDirectory() as tmp:
                base = carregar_manifesto(_baixar_manifesto(a.repo, tag, Path(tmp)))
        return pendentes(base, a.workspace.resolve(), a.fetch)
    return 0


if __name__ == "__main__":
    sys.exit(main())
