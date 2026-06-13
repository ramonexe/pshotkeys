"""
tray.py — Ícone de bandeja (system tray) para PSHotkeys.

Usa pystray + pillow. Se não estiver instalado, falha silenciosamente
e o app continua funcionando sem tray.
"""

import logging
import threading
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class TrayIcon:
    """
    Ícone na bandeja do sistema Windows.

    show_cb  : chamado para mostrar a janela principal (deve ser thread-safe,
               ex: root.after(0, show))
    quit_cb  : chamado para encerrar o app completamente
    icon_path: caminho para .ico; gera ícone padrão via Pillow se None/ausente
    """

    def __init__(
        self,
        app_core,
        show_cb: Callable,
        quit_cb: Callable,
        icon_path: Optional[str] = None,
    ):
        self._app = app_core
        self._show_cb = show_cb
        self._quit_cb = quit_cb
        self._icon_path = icon_path
        self._icon = None
        self._available = False

    @property
    def available(self) -> bool:
        return self._available

    def start(self):
        t = threading.Thread(target=self._run, daemon=True)
        t.start()

    def stop(self):
        if self._icon:
            try:
                self._icon.stop()
            except Exception:
                pass
        self._available = False

    def notify(self, title: str, message: str):
        if self._icon:
            try:
                self._icon.notify(message, title)
            except Exception:
                pass

    # ── Internals ─────────────────────────────────────────────────────────────

    def _load_image(self):
        from PIL import Image
        if self._icon_path:
            p = Path(self._icon_path)
            if p.exists():
                try:
                    return Image.open(str(p)).convert("RGBA")
                except Exception:
                    pass
        return self._make_default_image()

    @staticmethod
    def _make_default_image():
        from PIL import Image, ImageDraw
        size = 64
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        # Círculo azul com "PS" em branco
        draw.ellipse([2, 2, size - 2, size - 2], fill=(13, 135, 245, 255))
        # Quadrado interno para simular letras
        m = size // 4
        draw.rectangle([m, m + 4, size - m - 2, size - m - 2],
                       fill=(255, 255, 255, 200))
        draw.rectangle([m + 4, m + 8, size - m - 6, size - m - 6],
                       fill=(13, 135, 245, 255))
        return img

    def _run(self):
        try:
            import pystray

            img = self._load_image()

            menu = pystray.Menu(
                pystray.MenuItem("Mostrar", self._on_show, default=True),
                pystray.MenuItem(
                    "Ativo",
                    self._on_toggle,
                    checked=lambda item: self._app.master_enabled,
                ),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Sair", self._on_quit),
            )

            self._icon = pystray.Icon("PSHotkeys", img, "PSHotkeys", menu)
            self._available = True
            logger.info("Tray icon iniciado")
            self._icon.run()
        except ImportError:
            logger.warning("pystray/pillow não instalado — tray icon indisponível")
        except Exception as e:
            logger.error("Tray icon falhou: %s", e)

    def _on_show(self, icon=None, item=None):
        try:
            self._show_cb()
        except Exception as e:
            logger.error("Tray show_cb: %s", e)

    def _on_toggle(self, icon=None, item=None):
        try:
            self._app.set_master_enabled(not self._app.master_enabled)
        except Exception as e:
            logger.error("Tray toggle: %s", e)

    def _on_quit(self, icon=None, item=None):
        self.stop()
        try:
            self._quit_cb()
        except Exception as e:
            logger.error("Tray quit_cb: %s", e)
