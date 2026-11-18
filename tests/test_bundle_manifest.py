# -*- coding: utf-8 -*-
"""Testes de scripts/bundle_manifest.py (base publicada, WS-20261118-base-publicada).

    python -m unittest discover -s tests -v
"""

from __future__ import annotations

import hashlib
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "bundle_manifest.py"
_spec = importlib.util.spec_from_file_location("bundle_manifest", _SCRIPT)
bm = importlib.util.module_from_spec(_spec)
sys.modules["bundle_manifest"] = bm
_spec.loader.exec_module(bm)


def _sha(dados: bytes) -> str:
    return hashlib.sha256(dados).hexdigest()


class NormalizarTest(unittest.TestCase):
    def test_aliases_e_duplicados(self):
        self.assertEqual(bm.normalizar("coplan, Capex;elexplan status"), ["coplan_web", "elexplan"])

    def test_all_e_vazio(self):
        self.assertEqual(bm.normalizar("all"), list(bm.APPS))
        self.assertEqual(bm.normalizar("  "), [])

    def test_desconhecido_derruba(self):
        with self.assertRaises(SystemExit):
            bm.normalizar("coplan,interplan")


class UltimaBaseTest(unittest.TestCase):
    def test_semver_e_nao_ordem_alfabetica(self):
        tags = ["latest", "base-1.3.9", "base-1.3.11", "base-1.3.10", "base-x", "v1.4.0"]
        self.assertEqual(bm.escolher_ultima_base(tags), "base-1.3.11")
        self.assertEqual(bm.escolher_ultima_base(tags + ["base-1.4.0"]), "base-1.4.0")

    def test_sem_base(self):
        self.assertEqual(bm.escolher_ultima_base(["latest"]), "")


class DepsHashTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.raiz = Path(self._tmp.name)
        (self.raiz / "runtime_hooks").mkdir()
        (self.raiz / "apps" / "coplan" / "backend").mkdir(parents=True)
        (self.raiz / "requirements.lock.txt").write_bytes(b"numpy==2.4.6\n")
        (self.raiz / "multi_apps.spec").write_bytes(b"# spec\n")
        (self.raiz / "runtime_hooks" / "rh.py").write_bytes(b"x = 1\n")
        (self.raiz / "apps" / "coplan" / "requirements-web.txt").write_bytes(b"pandas\n")
        (self.raiz / "apps" / "coplan" / "backend" / "api.py").write_bytes(b"print(1)\n")

    def tearDown(self):
        self._tmp.cleanup()

    def test_codigo_do_app_nao_entra(self):
        antes = bm.deps_hash(self.raiz)
        (self.raiz / "apps" / "coplan" / "backend" / "api.py").write_bytes(b"print(2)\n")
        self.assertEqual(bm.deps_hash(self.raiz), antes)

    def test_requirements_do_app_entra(self):
        antes = bm.deps_hash(self.raiz)
        (self.raiz / "apps" / "coplan" / "requirements-web.txt").write_bytes(b"pandas\npolars\n")
        self.assertNotEqual(bm.deps_hash(self.raiz), antes)

    def test_fim_de_linha_nao_muda(self):
        antes = bm.deps_hash(self.raiz)
        (self.raiz / "requirements.lock.txt").write_bytes(b"numpy==2.4.6\r\n")
        self.assertEqual(bm.deps_hash(self.raiz), antes)

    def test_pycache_ignorado(self):
        antes = bm.deps_hash(self.raiz)
        (self.raiz / "runtime_hooks" / "__pycache__").mkdir()
        (self.raiz / "runtime_hooks" / "__pycache__" / "rh.cpython-312.pyc").write_bytes(b"\0")
        self.assertEqual(bm.deps_hash(self.raiz), antes)


class _ComBundle(unittest.TestCase):
    """Bundle falso com os cinco .exe e um instalador."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        t = Path(self._tmp.name)
        self.bundle = t / "bundle"
        self.bundle.mkdir()
        self.conteudo = {}
        for chave, app in bm.APPS.items():
            dados = f"exe {chave} novo".encode()
            (self.bundle / app.exe).write_bytes(dados)
            self.conteudo[chave] = dados
        self.instalador = t / "FerramentasCompartilhadas-Setup-1.3.12.exe"
        self.instalador.write_bytes(b"instalador")
        self.raiz = t
        self.git = mock.patch.object(bm, "_git", side_effect=self._git_falso)
        self.chamadas = []
        self.git.start()

    def tearDown(self):
        self.git.stop()
        self._tmp.cleanup()

    def _git_falso(self, pasta, *args, checar=True):
        self.chamadas.append((Path(pasta), args))
        if args[:1] == ("rev-parse",):
            return "f" * 40
        return ""

    def _base(self, **troca_sha):
        apps = {}
        for chave, app in bm.APPS.items():
            apps[chave] = {
                "exe": app.exe,
                "exe_sha256": troca_sha.get(chave, _sha(self.conteudo[chave])),
                "commit": f"{chave[:1]}" * 40,
                "compilado_em": "1.3.11",
                "origem": "recompilado",
            }
        return {"schema": 1, "versao_instalador": "1.3.11", "build_sha": "b" * 40, "apps": apps}

    def _gerar(self, **kw):
        padrao = dict(
            bundle=self.bundle, raiz=self.raiz, versao="1.3.12", modo="full", escolhidos=[],
            deps="d" * 64, instalador=self.instalador, build_sha="a" * 40, run_id="1",
            base=None, base_tag="",
        )
        padrao.update(kw)
        return bm.gerar(**padrao)


class GerarTest(_ComBundle):
    def test_completo_sem_base(self):
        m = self._gerar()
        self.assertEqual(m["modo"], "full")
        self.assertIsNone(m["base"])
        self.assertEqual(set(m["apps"]), set(bm.APPS))
        for chave, e in m["apps"].items():
            self.assertEqual(e["origem"], "recompilado")
            self.assertEqual(e["compilado_em"], "1.3.12")
        # O Unificador vive no repo de build: o commit e' o do build.
        self.assertEqual(m["apps"]["unif"]["commit"], "a" * 40)
        self.assertEqual(m["instalador"]["sha256"], _sha(b"instalador"))

    def test_incremental_reaproveita_identico(self):
        m = self._gerar(modo="incremental", escolhidos=["coplan_web"], base=self._base(), base_tag="base-1.3.11")
        self.assertEqual(m["apps"]["coplan_web"]["origem"], "recompilado")
        self.assertEqual(m["apps"]["coplan_web"]["compilado_em"], "1.3.12")
        self.assertEqual(m["apps"]["elexplan"]["origem"], "base-1.3.11")
        self.assertEqual(m["apps"]["elexplan"]["compilado_em"], "1.3.11")
        self.assertEqual(m["apps"]["elexplan"]["commit"], "e" * 40)

    def test_incremental_exe_diferente_da_base_reprova(self):
        base = self._base(elexplan="0" * 64)
        with self.assertRaises(SystemExit) as ctx:
            self._gerar(modo="incremental", escolhidos=["coplan_web"], base=base, base_tag="base-1.3.11")
        self.assertIn("elexplan", str(ctx.exception))

    def test_completo_com_base_mantem_commit_publicado(self):
        # Dependencias mudaram: tudo recompilado, mas os nao escolhidos
        # registram o commit da base, nao o main.
        base = self._base(elexplan="0" * 64)
        m = self._gerar(modo="full", escolhidos=["coplan_web"], base=base, base_tag="base-1.3.11")
        self.assertEqual(m["apps"]["elexplan"]["commit"], "e" * 40)
        self.assertEqual(m["apps"]["elexplan"]["compilado_em"], "1.3.12")
        self.assertIn("base-1.3.11", m["apps"]["elexplan"]["origem"])

    def test_exe_ausente_reprova(self):
        (self.bundle / "Elexplan.exe").unlink()
        with self.assertRaises(SystemExit):
            self._gerar()

    def test_incremental_sem_base_reprova(self):
        with self.assertRaises(SystemExit):
            self._gerar(modo="incremental", escolhidos=["coplan_web"])


class FixarTest(_ComBundle):
    def test_fixa_so_os_nao_escolhidos(self):
        feitos = bm.fixar(self._base(), ["coplan_web"], self.raiz)
        self.assertEqual({c for c, _ in feitos}, set(bm.APPS) - {"coplan_web"})
        pastas = {p for p, _ in self.chamadas}
        self.assertNotIn(self.raiz / "apps/coplan", pastas)
        self.assertIn(self.raiz / "apps/elexplan", pastas)

    def test_unificador_restaura_so_a_pasta(self):
        bm.fixar(self._base(), ["coplan_web"], self.raiz)
        checkouts = [a for p, a in self.chamadas if p == self.raiz and a[:1] == ("checkout",)]
        self.assertEqual(checkouts, [("checkout", "u" * 40, "--", "apps/unificador")])

    def test_app_fora_da_base_derruba(self):
        base = self._base()
        del base["apps"]["cadastro"]
        with self.assertRaises(SystemExit):
            bm.fixar(base, ["coplan_web"], self.raiz)


if __name__ == "__main__":
    unittest.main()
