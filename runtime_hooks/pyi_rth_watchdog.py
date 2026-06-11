# -*- coding: utf-8 -*-
"""Runtime hook (PyInstaller) dos apps pywebview (Cadastro/Coplan/Capex).

Dois guardas, ambos em threads daemon:

1. Anti-zumbi: quando webview.start() retorna (todas as janelas fecharam),
   agenda os._exit(0) apos um periodo de graca. Threads nao-daemon do
   pythonnet/.NET costumam segurar o processo vivo sem janela ("zumbi"),
   o que impede reabrir o app e polui o Gerenciador de Tarefas.

2. Watchdog anti-congelamento: usa a MESMA checagem do Gerenciador de
   Tarefas (user32.IsHungAppWindow). Se TODAS as janelas visiveis do
   processo ficarem "Nao respondendo" por ~30s seguidos, o processo se
   encerra sozinho (os._exit(86)). Sem isso, janela congelada ignora o
   "Finalizar tarefa" da aba Processos (que e' um WM_CLOSE educado) e so
   morre via aba Detalhes > Finalizar arvore de processos.

Limitacao conhecida: se o congelamento for um deadlock segurando o GIL
(ex.: chamada nativa pythonnet travada), a thread do watchdog tambem
para de rodar e nao ha kill — nesse caso so a aba Detalhes resolve.
O conserto definitivo do congelamento e' nos repos dos proprios apps.

Diagnostico: eventos sao registrados em
%LOCALAPPDATA%\\FerramentasPlanejamento\\watchdog.log.
Para desativar (debug): defina FERRAMENTAS_DISABLE_WATCHDOG=1.
"""

import os
import sys
import threading

_GRACE_EXIT_S = 10.0   # apos fechar as janelas, prazo p/ cleanup legitimo
_HANG_POLL_S = 5.0     # intervalo entre checagens do watchdog
_HANG_STRIKES = 6      # 6 x 5s => ~30s congelado => kill


def _log(msg):
    try:
        import datetime
        base = os.path.join(
            os.environ.get("LOCALAPPDATA", ""), "FerramentasPlanejamento")
        os.makedirs(base, exist_ok=True)
        exe = os.path.basename(getattr(sys, "executable", "") or "app")
        with open(os.path.join(base, "watchdog.log"), "a",
                  encoding="utf-8") as fh:
            fh.write("%s | %s | %s\n" % (
                datetime.datetime.now().isoformat(timespec="seconds"),
                exe, msg))
    except Exception:
        pass


def _arm_anti_zombie():
    """Forca a morte do processo depois que todas as janelas fecharem."""
    try:
        import webview
    except Exception:
        return

    orig_start = webview.start

    def start(*args, **kwargs):
        try:
            return orig_start(*args, **kwargs)
        finally:
            # start() retornou => todas as janelas fecharam. Da um prazo
            # para cleanup e mata o processo: threads .NET nao-daemon
            # seguram um zumbi sem janela indefinidamente.
            def _die():
                _log("anti-zumbi: janelas fechadas ha %.0fs; os._exit(0)"
                     % _GRACE_EXIT_S)
                os._exit(0)

            t = threading.Timer(_GRACE_EXIT_S, _die)
            t.daemon = True
            t.start()

    webview.start = start


def _watchdog_loop():
    import ctypes
    import time
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    WNDENUMPROC = ctypes.WINFUNCTYPE(
        wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    pid = os.getpid()

    def all_visible_windows_hung():
        """True se o processo tem >=1 janela visivel e TODAS estao
        'Nao respondendo' (mesmo criterio do Gerenciador de Tarefas)."""
        wins = []

        def _cb(hwnd, _lparam):
            wpid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(wpid))
            if wpid.value == pid and user32.IsWindowVisible(hwnd):
                wins.append(hwnd)
            return True

        user32.EnumWindows(WNDENUMPROC(_cb), 0)
        if not wins:
            return False
        return all(user32.IsHungAppWindow(h) for h in wins)

    strikes = 0
    while True:
        time.sleep(_HANG_POLL_S)
        try:
            hung = all_visible_windows_hung()
        except Exception:
            hung = False
        strikes = strikes + 1 if hung else 0
        if strikes == 1:
            _log("watchdog: janela 'Nao respondendo' detectada")
        if strikes >= _HANG_STRIKES:
            _log("watchdog: congelado ha ~%.0fs; os._exit(86)"
                 % (_HANG_POLL_S * _HANG_STRIKES))
            os._exit(86)


def _main():
    if sys.platform != "win32":
        return
    if os.environ.get("FERRAMENTAS_DISABLE_WATCHDOG") == "1":
        return
    _arm_anti_zombie()
    threading.Thread(
        target=_watchdog_loop, name="hang-watchdog", daemon=True).start()


_main()
