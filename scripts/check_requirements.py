# -*- coding: utf-8 -*-
"""Confere se o que o codigo IMPORTA esta declarado nos requirements.

Motivo (regra do usuario, 22/09/2026): *"nao tenho costume de atualizar os
requirements dos repositorios quando mexo nos codigos e incluo mais alguma
biblioteca que deve ser empacotada tambem"*. Import novo que nao entra no
requirements roda na maquina do desenvolvedor — onde a lib ja esta instalada —
e so quebra no bundle, depois do build, na maquina do usuario.

Regra escrita nao pega isso. Este script pega: le os imports de verdade com
``ast`` e compara com os requirements declarados.

Uso:
    python scripts/check_requirements.py                 # todos os repos
    python scripts/check_requirements.py coplanweb       # so um
    python scripts/check_requirements.py --raiz D:/Codigos   # outra raiz

Sai com codigo 1 se achar import nao declarado, para poder virar guarda de CI.
"""

from __future__ import annotations

import argparse
import ast
import pathlib
import sys

# Import que NAO se chama como o pacote no PyPI. Sem isto o script acusaria
# falta de "PIL" quando o requirements diz "pillow", que e' a mesma coisa.
APELIDOS = {
    "pil": "pillow",
    "yaml": "pyyaml",
    "win32com": "pywin32",
    "win32gui": "pywin32",
    "win32con": "pywin32",
    "win32api": "pywin32",
    "win32clipboard": "pywin32",
    "pythoncom": "pywin32",
    "pywintypes": "pywin32",
    "fitz": "pymupdf",
    "cv2": "opencv-python",
    "sklearn": "scikit-learn",
    "dateutil": "python-dateutil",
    "pptx": "python-pptx",
    "docx": "python-docx",
    "snowflake": "snowflake-connector-python",
    "dotenv": "python-dotenv",
    "serial": "pyserial",
    "OpenSSL": "pyopenssl",
    "Cryptodome": "pycryptodomex",
    "Crypto": "pycryptodome",
    "bs4": "beautifulsoup4",
    "extract_msg": "extract-msg",
    "huggingface_hub": "huggingface-hub",
    "pyqtgraph": "pyqtgraph",
    "PySide6": "pyside6",
    "fastexcel": "fastexcel",
    "webview": "pywebview",
    "clr": "pythonnet",
}

# Pacotes que entram por dependencia de outro e nao precisam estar no
# requirements do app; declara-los seria ruido.
TRANSITIVOS = {"pkg_resources", "setuptools", "pip", "_distutils_hack"}

#: repo -> requirements que valem para ele. O primeiro que existir vale;
#: varios arquivos somam (um app pode ter web + desktop).
REPOS = {
    "coplanweb": ["requirements-web.txt", "scripts/build/requirements-build.txt"],
    "elexplan": ["requirements.txt", "requirements-dev.txt"],
    "sistemadecadastro": ["main_web/requirements-web.txt",
                          "requirements-desktop.txt", "requirements-dev.txt"],
    "diagnostico_atual": ["requirements.txt"],
    "Ferramenta_plan": ["requirements.txt", "requirements-dev.txt"],
    "extracaopim": ["requirements.txt"],
}

IGNORAR_PASTAS = {
    ".git", "__pycache__", "node_modules", "build", "dist", "apps",
    ".venv", "venv", ".build_venv", "legado-status-medicao", "Output",
}

#: Pastas que EXISTEM no repo mas nao vao para o bundle: frontend aposentado e
#: ferramenta de build. O import delas nao precisa estar no requirements do
#: app, e cobrar isso so ensinaria a ignorar o verificador.
NAO_EMPACOTADO = {
    # O distribuido e' a app web; o Qt segue no repo, empacotavel a parte, e o
    # proprio requirements-web.txt diz que PySide6 nao e' mais necessario.
    "coplanweb": ("legacy_desktop",),
    # codigo9_cadastro e' o Qt legado; installer/ e' quem GERA o instalador.
    "sistemadecadastro": ("codigo9_cadastro", "installer"),
}

#: Excecoes por ARQUIVO, com motivo. Ficam a vista de proposito: excecao
#: silenciosa vira lixo que ninguem revisa. Formato: repo -> {arquivo: motivo}.
EXCECOES = {
    # Os cinco importam PySide6 no topo, sem guarda, e sao os caminhos Qt que
    # so rodam no DESKTOP — os "dialogos" e o "worker em QThread" que o proprio
    # requirements-web.txt cita ao explicar por que PySide6 saiu da app web.
    # Moram em `runtime/` junto com modulos que a web usa, mas a web nao os
    # importa, entao o PyInstaller nao os puxa para o bundle.
    #
    # Declarar PySide6 no requirements-web para calar o verificador incharia o
    # bundle da app web com o Qt inteiro, contra a decisao ja registrada. A
    # excecao fica escrita, e nao silenciosa, porque a arrumacao de verdade e'
    # separar esses arquivos do resto de `runtime/`.
    "coplanweb": {
        arquivo: "caminho Qt so do desktop; a app web nao importa"
        for arquivo in (
            "runtime/cli.py", "runtime/dialogs.py", "runtime/qss.py",
            "runtime/widgets.py", "runtime/workers.py",
        )
    },
}


def normalizar(nome: str) -> str:
    return nome.strip().lower().replace("_", "-")


def _pega_import_error(no: ast.Try) -> bool:
    """O `try` trata ImportError/ModuleNotFoundError?"""
    for handler in no.handlers:
        alvo = handler.type
        if alvo is None:  # `except:` cru tambem engole ImportError
            return True
        nomes = alvo.elts if isinstance(alvo, ast.Tuple) else [alvo]
        for item in nomes:
            if isinstance(item, ast.Name) and item.id in (
                    "ImportError", "ModuleNotFoundError"):
                return True
    return False


def imports_do_arquivo(caminho: pathlib.Path) -> set[str]:
    """Imports de terceiros do arquivo, SEM os declaradamente opcionais.

    Import dentro de ``try/except ImportError`` e' o idioma de dependencia
    opcional: o autor ja disse, no codigo, que o programa funciona sem ela.
    Cobrar declaracao disso so ensinaria a ignorar o verificador. Exemplo real:
    ``coplanweb/runtime/calc.py`` importa PySide6 assim, porque a app web roda
    headless e nao instala Qt.
    """
    try:
        arvore = ast.parse(caminho.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        # Arquivo de outra versao de Python ou template; nao e' trabalho deste
        # script julgar sintaxe.
        return set()

    opcionais: set[ast.AST] = set()
    for no in ast.walk(arvore):
        if isinstance(no, ast.Try) and _pega_import_error(no):
            for corpo in no.body:
                for dentro in ast.walk(corpo):
                    opcionais.add(dentro)

    achados: set[str] = set()
    for no in ast.walk(arvore):
        if no in opcionais:
            continue
        if isinstance(no, ast.Import):
            for alias in no.names:
                achados.add(alias.name.split(".")[0])
        elif isinstance(no, ast.ImportFrom):
            # `from . import x` e `from .mod import y` sao locais.
            if no.level == 0 and no.module:
                achados.add(no.module.split(".")[0])
    return achados


def modulos_locais(raiz: pathlib.Path) -> set[str]:
    """Nomes que resolvem dentro do proprio repo, e portanto nao sao deps.

    Varre o repo INTEIRO, nao so a raiz: `main_web/api_demandas.py` faz
    `import mw_db`, e `mw_db.py` e' irmao dele dentro de `main_web/`. Olhando
    so a raiz, o script acusaria `mw-db` como pacote faltando no PyPI — foi o
    que aconteceu na primeira versao, com 70 falsos positivos.
    """
    locais: set[str] = set()
    for item in raiz.rglob("*"):
        if any(parte in IGNORAR_PASTAS for parte in item.parts):
            continue
        if item.is_dir():
            locais.add(item.name)
        elif item.suffix == ".py":
            locais.add(item.stem)
    return locais


def declarados(raiz: pathlib.Path, arquivos: list[str]) -> tuple[set[str], list[str]]:
    nomes: set[str] = set()
    existentes: list[str] = []
    for rel in arquivos:
        caminho = raiz / rel
        if not caminho.exists():
            continue
        existentes.append(rel)
        for linha in caminho.read_text(encoding="utf-8-sig").splitlines():
            linha = linha.split("#", 1)[0].strip()
            if not linha or linha.startswith("-"):
                continue
            for sep in (">=", "<=", "==", "~=", "!=", ">", "<", ";", "["):
                if sep in linha:
                    linha = linha.split(sep, 1)[0]
            if linha.strip():
                nomes.add(normalizar(linha))
    return nomes, existentes


def conferir(raiz: pathlib.Path, arquivos: list[str],
             fora: tuple[str, ...] = (),
             excecoes: dict[str, str] | None = None) -> list[tuple[str, str]]:
    """Devolve [(pacote, exemplo de arquivo que importa)] nao declarados."""
    locais = modulos_locais(raiz)
    declarado, _ = declarados(raiz, arquivos)
    faltando: dict[str, str] = {}
    for py in raiz.rglob("*.py"):
        if any(parte in IGNORAR_PASTAS for parte in py.parts):
            continue
        if any(parte in fora for parte in py.parts):
            continue
        rel_posix = py.relative_to(raiz).as_posix()
        if excecoes and rel_posix in excecoes:
            continue
        # Teste importa coisa que o runtime nao empacota (pytest, playwright de
        # teste). O que vai para o bundle e' o codigo de producao.
        if "tests" in py.parts or py.name.startswith("test_"):
            continue
        for mod in imports_do_arquivo(py):
            if mod in locais or mod in TRANSITIVOS:
                continue
            if mod in sys.stdlib_module_names:
                continue
            # Todo o pywin32 entra por prefixo: sao dezenas de submodulos
            # (win32process, win32ui, ...) e listar um a um envelhece mal.
            if mod.startswith(("win32", "pywin", "pythonwin")):
                pacote = "pywin32"
            else:
                pacote = normalizar(
                    APELIDOS.get(mod, APELIDOS.get(mod.lower(), mod)))
            if pacote in declarado:
                continue
            faltando.setdefault(pacote, str(py.relative_to(raiz)))
    return sorted(faltando.items())


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("repos", nargs="*", help="repos a conferir; vazio = todos")
    ap.add_argument("--raiz", default=None,
                    help="raiz do workspace Codigos (default: pasta irma)")
    args = ap.parse_args()

    raiz = (pathlib.Path(args.raiz) if args.raiz
            else pathlib.Path(__file__).resolve().parents[2])
    alvos = args.repos or list(REPOS)

    problemas = 0
    for nome in alvos:
        if nome not in REPOS:
            print(f"[{nome}] repo desconhecido; adicione em REPOS")
            problemas += 1
            continue
        caminho = raiz / nome
        if not caminho.is_dir():
            print(f"[{nome}] nao encontrado em {raiz}")
            continue
        _, usados = declarados(caminho, REPOS[nome])
        excecoes = EXCECOES.get(nome, {})
        faltando = conferir(caminho, REPOS[nome],
                            NAO_EMPACOTADO.get(nome, ()), excecoes)
        alvo_txt = ", ".join(usados) or "NENHUM requirements encontrado"
        if faltando:
            problemas += len(faltando)
            print(f"[{nome}] {len(faltando)} import(s) fora de {alvo_txt}:")
            for pacote, exemplo in faltando:
                print(f"    {pacote:<28} importado em {exemplo}")
        else:
            print(f"[{nome}] ok ({alvo_txt})")
        for arquivo, motivo in sorted(excecoes.items()):
            print(f"    excecao: {arquivo} - {motivo}")

    print()
    if problemas:
        print(f"{problemas} pendencia(s). Import que nao esta no requirements "
              f"nao e' instalado no build e quebra no bundle do usuario.")
        return 1
    print("Todos os imports de producao estao declarados.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
