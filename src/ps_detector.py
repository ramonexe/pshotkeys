"""
ps_detector.py — Detecta quando o Photoshop está em foco.

Usa polling leve via GetForegroundWindow (win32) + psutil para obter
o nome do processo em primeiro plano, sem depender de hooks globais.
"""

import sys
import time
import threading
import logging
from typing import Callable, Optional

logger = logging.getLogger(__name__)
IS_WINDOWS = sys.platform == "win32"

if IS_WINDOWS:
    import ctypes
    import ctypes.wintypes
    import psutil


def photoshop_running() -> bool:
    """Retorna True se photoshop.exe estiver em execução."""
    if not IS_WINDOWS:
        return False
    try:
        for proc in psutil.process_iter(["name"]):
            name = proc.info.get("name") or ""
            if name.lower() == "photoshop.exe":
                return True
    except Exception:
        pass
    return False


def _foreground_process_name() -> Optional[str]:
    """Retorna nome (em lower) do processo com foco agora."""
    if not IS_WINDOWS:
        return None
    try:
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        if not hwnd:
            return None
        pid = ctypes.wintypes.DWORD(0)
        ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        proc = psutil.Process(pid.value)
        return proc.name().lower()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return None
    except Exception as e:
        logger.debug("_foreground_process_name falhou: %s", e)
        return None


class PhotoshopWatcher:
    """
    Monitora presença do Photoshop via polling.

    Dispara on_focus_gained quando photoshop.exe inicia/é detectado,
    e on_focus_lost quando o processo encerra.
    Não requer que a janela do PS esteja em primeiro plano.
    """

    def __init__(
        self,
        on_focus_gained: Callable,
        on_focus_lost: Callable,
        poll_ms: int = 250,
    ):
        self._on_gained = on_focus_gained
        self._on_lost = on_focus_lost
        self._poll_sec = poll_ms / 1000.0
        self._thread: Optional[threading.Thread] = None
        self._active = False
        self.is_running = False

    @property
    def is_focused(self) -> bool:
        return self.is_running

    def start(self):
        self._active = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        logger.info("PhotoshopWatcher iniciado (poll=%.0fms)", self._poll_sec * 1000)

    def stop(self):
        self._active = False

    def _loop(self):
        while self._active:
            try:
                running = photoshop_running()
                if running != self.is_running:
                    self.is_running = running
                    label = "iniciado" if running else "encerrado"
                    logger.info("Photoshop %s", label)
                    cb = self._on_gained if running else self._on_lost
                    try:
                        cb()
                    except Exception as e:
                        logger.error("Watcher callback falhou: %s", e)
            except Exception as e:
                logger.debug("Watcher loop erro: %s", e)
            time.sleep(self._poll_sec)
