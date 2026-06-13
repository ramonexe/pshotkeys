"""
ps_actions.py — Ações especiais que não existem nativamente no Photoshop.

Comunicação via ExtendScript (.jsx) executado pelo PS.
O PS escuta scripts via:  File > Scripts > Script Events Manager  OU
via linha de comando:  photoshop.exe -r script.jsx

Método usado aqui: escreve um .jsx temporário e chama via COM (win32com)
que é o método mais confiável — funciona com CC 2015 até 2025+.

Setup único necessário pelo usuário (feito no wizard de primeiro uso):
  Preferences > General > "Allow Scripts to Access Network" → ON
  (algumas versões pedem isso, outras não)
"""

import sys
import os
import tempfile
import logging
import subprocess
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)
IS_WINDOWS = sys.platform == "win32"

if IS_WINDOWS:
    try:
        import win32com.client
        _HAS_COM = True
    except ImportError:
        _HAS_COM = False
        logger.warning("pywin32 não instalado — ações via COM indisponíveis")
else:
    _HAS_COM = False


# ── ExtendScript templates ────────────────────────────────────────────────────

def _jsx_rotate_canvas(angle_deg: float) -> str:
    return f"""
var doc = app.activeDocument;
var action = new ActionDescriptor();
action.putUnitDouble(charIDToTypeID("Angl"), charIDToTypeID("#Ang"), {angle_deg});
executeAction(charIDToTypeID("Rtte"), action, DialogModes.NO);
"""

def _jsx_rotate_canvas_reset() -> str:
    return """
var doc = app.activeDocument;
var action = new ActionDescriptor();
action.putUnitDouble(charIDToTypeID("Angl"), charIDToTypeID("#Ang"), 0);
executeAction(charIDToTypeID("Rtte"), action, DialogModes.NO);
"""

def _jsx_zoom(percent: int) -> str:
    return f"""
var idslct = charIDToTypeID("slct");
var desc = new ActionDescriptor();
desc.putUnitDouble(charIDToTypeID("Scl "), charIDToTypeID("#Prc"), {percent});
executeAction(charIDToTypeID("setd"), desc, DialogModes.NO);
"""

def _jsx_toggle_layer_visibility() -> str:
    return """
var doc = app.activeDocument;
var layer = doc.activeLayer;
layer.visible = !layer.visible;
"""

def _jsx_merge_visible_stamp() -> str:
    return """
function stampVisible() {
    var desc = new ActionDescriptor();
    var ref = new ActionReference();
    ref.putClass(charIDToTypeID("Lyr "));
    desc.putReference(charIDToTypeID("null"), ref);
    desc.putBoolean(charIDToTypeID("Dplc"), true);
    desc.putBoolean(stringIDToTypeID("mergeAll"), true);
    executeAction(charIDToTypeID("Mrge"), desc, DialogModes.NO);
}
stampVisible();
"""

def _jsx_flatten_to_new_layer() -> str:
    return """
var doc = app.activeDocument;
doc.selection.selectAll();
doc.selection.copy(true); // merged
doc.paste();
doc.selection.deselect();
"""


# ── Executor ─────────────────────────────────────────────────────────────────

class PSActionRunner:
    """
    Executa scripts ExtendScript no Photoshop ativo.
    
    Método primário: win32com (COM automation) — instantâneo, sem processo filho.
    Fallback: escreve .jsx em temp e abre via subprocess (compatível com mais versões).
    """

    def __init__(self):
        self._app = None  # COM handle cacheado

    def _get_com_app(self):
        if not _HAS_COM:
            return None
        try:
            if self._app is None:
                self._app = win32com.client.GetActiveObject("Photoshop.Application")
            return self._app
        except Exception as e:
            logger.warning("COM falhou: %s", e)
            self._app = None
            return None

    def run_jsx(self, jsx_code: str) -> bool:
        """Executa JSX no PS. Retorna True se bem-sucedido."""
        # Tentativa via COM (preferida)
        app = self._get_com_app()
        if app:
            try:
                app.DoJavaScript(jsx_code)
                return True
            except Exception as e:
                logger.warning("COM DoJavaScript falhou: %s — tentando fallback", e)
                self._app = None

        # Fallback: arquivo temporário
        return self._run_via_file(jsx_code)

    def _run_via_file(self, jsx_code: str) -> bool:
        try:
            tmp = tempfile.NamedTemporaryFile(suffix=".jsx", delete=False,
                                              mode="w", encoding="utf-8")
            tmp.write(jsx_code)
            tmp.close()

            # Encontrar executável do PS no registro
            ps_exe = self._find_ps_exe()
            if not ps_exe:
                logger.error("Photoshop.exe não encontrado para fallback")
                return False

            subprocess.Popen([ps_exe, "-r", tmp.name])
            return True
        except Exception as e:
            logger.error("Fallback JSX falhou: %s", e)
            return False
        finally:
            try:
                os.unlink(tmp.name)
            except Exception:
                pass

    def _find_ps_exe(self) -> Optional[str]:
        if not IS_WINDOWS:
            return None
        import winreg
        try:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Adobe\Photoshop")
            # Itera subkeys (versões)
            i = 0
            while True:
                try:
                    ver = winreg.EnumKey(key, i)
                    sub = winreg.OpenKey(key, ver)
                    path, _ = winreg.QueryValueEx(sub, "ApplicationPath")
                    exe = Path(path) / "Photoshop.exe"
                    if exe.exists():
                        return str(exe)
                    i += 1
                except OSError:
                    break
        except Exception:
            pass
        return None

    # ── Ações de alto nível ───────────────────────────────────────────────────

    def rotate_canvas_left(self, step: float = 15.0):
        self.run_jsx(_jsx_rotate_canvas(-step))

    def rotate_canvas_right(self, step: float = 15.0):
        self.run_jsx(_jsx_rotate_canvas(step))

    def rotate_canvas_reset(self):
        self.run_jsx(_jsx_rotate_canvas_reset())

    def stamp_visible(self):
        self.run_jsx(_jsx_merge_visible_stamp())

    def toggle_layer_visibility(self):
        self.run_jsx(_jsx_toggle_layer_visibility())

    def flatten_to_new_layer(self):
        self.run_jsx(_jsx_flatten_to_new_layer())

    def run_custom_jsx(self, jsx_code: str):
        self.run_jsx(jsx_code)


# Singleton global
ps_runner = PSActionRunner()
