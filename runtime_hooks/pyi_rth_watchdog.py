# -*- coding: utf-8 -*-
"""Runtime hook (PyInstaller) dos apps pywebview (Cadastro/Coplan/Capex).

Dois guardas:

1. Anti-zumbi + exit-code limpo: quando webview.start() retorna (janelas
   fechadas), chama os._exit(0) IMEDIATAMENTE no proprio finally do wrapper
   -- antes de qualquer shutdown do Python/.NET/pythonnet. Sem isso, o
   cleanup do CLR (pythonnet) sobrescreve o exit code com 0xF060 (-4000),
   que o launcher exibe como "Erro ao executar: Codigo de saida: 61536".
   Threads nao-daemon do .NET tambem segurariam o processo como zumbi.

2. Watchdog anti-congelamento (thread daemon): usa IsHungAppWindow, o
   mesmo criterio do Gerenciador de Tarefas. Se TODAS as janelas visiveis
   ficarem "Nao respondendo" por ~30s, o processo se encerra (os._exit(86)).
   Sem isso, janela congelada ignora o "Finalizar tarefa" da aba Processos
   (WM_CLOSE educado, nunca processado pela UI travada).

Limitacao do watchdog: deadlock segurando o GIL nao e coberto -- so a
aba Detalhes > Finalizar arvore de processos resolve nesses casos.
O conserto definitivo do congelamento mora nos repos dos apps.

Diagnostico: eventos em %LOCALAPPDATA%\\FerramentasPlanejamento\\watchdog.log
Desativar (debug): FERRAMENTAS_DISABLE_WATCHDOG=1
"""

import os
import sys
import threading

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
    """Garante exit code 0 e evita processo zumbi apos fechar as janelas.

    Chama os._exit(0) no proprio finally do wrapper de webview.start(),
    antes que o Python entregue o controle ao shutdown do .NET/pythonnet.
    Esse shutdown sobrescreve o exit code com 0xF060 (61536), que o
    launcher exibe como "Erro ao executar: Codigo de saida: 61536".
    """
    try:
        import webview
    except Exception:
        return

    orig_start = webview.start

    def start(*args, **kwargs):
        try:
            return orig_start(*args, **kwargs)
        finally:
            # Janelas fechadas. os._exit() pula o shutdown Python/.NET e
            # garante exit code 0 -- sem essa chamada o CLR sobrescreve
            # com 0xF060/61536 durante a limpeza de threads nao-daemon.
            _log("anti-zumbi: janelas fechadas; os._exit(0)")
            os._exit(0)

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
