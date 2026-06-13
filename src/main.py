"""
main.py — PSHotkeys v2 entry point
"""

import sys
import logging
import os
from pathlib import Path
from typing import Optional

# Log para arquivo em produção
_log_dir = Path.home() / "AppData" / "Roaming" / "PSHotkeys"
_log_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)-7s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.FileHandler(_log_dir / "app.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)

logger = logging.getLogger(__name__)

sys.path.insert(0, os.path.dirname(__file__))

from app import PSHotkeysApp
from gui import MainWindow
from tray import TrayIcon


def _ensure_icon() -> Optional[str]:
    """Gera assets/icon.ico com Pillow se não existir. Retorna o caminho ou None."""
    assets = Path(__file__).parent.parent / "assets"
    assets.mkdir(exist_ok=True)
    icon_path = assets / "icon.ico"
    if not icon_path.exists():
        try:
            from PIL import Image, ImageDraw, ImageFont
            size = 64
            img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            draw.rounded_rectangle(
                [0, 0, size - 1, size - 1], radius=14,
                fill=(13, 135, 245, 255),
            )
            # Texto "PS"
            font = None
            for font_path in [
                "C:/Windows/Fonts/segoeui.ttf",
                "C:/Windows/Fonts/arial.ttf",
            ]:
                try:
                    font = ImageFont.truetype(font_path, 28)
                    break
                except Exception:
                    continue
            if font is None:
                font = ImageFont.load_default()

            text = "PS"
            bbox = draw.textbbox((0, 0), text, font=font)
            x = (size - (bbox[2] - bbox[0])) // 2 - bbox[0]
            y = (size - (bbox[3] - bbox[1])) // 2 - bbox[1]
            draw.text((x, y), text, fill="white", font=font)

            # Salva com múltiplos tamanhos para melhor renderização no Windows
            imgs = [img.resize((s, s), Image.LANCZOS) for s in (16, 32, 48, 64)]
            imgs[0].save(
                str(icon_path), format="ICO",
                append_images=imgs[1:],
                sizes=[(s, s) for s in (16, 32, 48, 64)],
            )
            logger.info("Ícone gerado: %s", icon_path)
        except Exception as e:
            logger.debug("Falha ao gerar ícone: %s", e)

    return str(icon_path) if icon_path.exists() else None


def main():
    icon_path = _ensure_icon()

    core = PSHotkeysApp()
    core.start()

    window = MainWindow(core)

    tray = TrayIcon(
        app_core=core,
        show_cb=lambda: window.root.after(0, window.show),
        quit_cb=lambda: window.root.after(0, window.quit),
        icon_path=icon_path,
    )
    window.set_tray(tray)
    tray.start()

    window.run()


if __name__ == "__main__":
    main()
