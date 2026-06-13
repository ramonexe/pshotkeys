"""
app.py — PSHotkeys v2 core.

Wires: ProfileStore → RemapEngine → PSActionRunner
       PhotoshopWatcher → enable/disable engine
"""

import sys
import logging
import threading
from pathlib import Path
from typing import Callable, List, Optional

from remap_engine import RemapEngine, parse_combo, inject_keys, inject_sequence
from profile_store import ProfileStore
from ps_actions import ps_runner
from ps_detector import PhotoshopWatcher, photoshop_running

_STARTUP_REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_STARTUP_REG_NAME = "PSHotkeys"


def _set_startup(enabled: bool) -> bool:
    """Registra ou remove PSHotkeys do startup do Windows via registry."""
    if sys.platform != "win32":
        return False
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            _STARTUP_REG_KEY,
            0,
            winreg.KEY_SET_VALUE | winreg.KEY_QUERY_VALUE,
        )
        if enabled:
            exe = sys.executable
            if "python" in Path(exe).name.lower():
                main_py = Path(__file__).parent / "main.py"
                cmd = f'"{exe}" "{main_py}"'
            else:
                cmd = f'"{exe}"'
            winreg.SetValueEx(key, _STARTUP_REG_NAME, 0, winreg.REG_SZ, cmd)
        else:
            try:
                winreg.DeleteValue(key, _STARTUP_REG_NAME)
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
        return True
    except Exception as e:
        logging.getLogger(__name__).error("Startup registry: %s", e)
        return False


def _check_startup() -> bool:
    """Retorna True se PSHotkeys estiver registrado no startup do Windows."""
    if sys.platform != "win32":
        return False
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            _STARTUP_REG_KEY,
            0,
            winreg.KEY_QUERY_VALUE,
        )
        winreg.QueryValueEx(key, _STARTUP_REG_NAME)
        winreg.CloseKey(key)
        return True
    except (FileNotFoundError, OSError):
        return False

logger = logging.getLogger(__name__)


def _build_callback(action: dict) -> Callable:
    """Constrói callable a partir de um descriptor de action."""
    atype = action.get("type")

    if atype == "remap":
        keys = action["keys"]
        return lambda: inject_keys(keys)

    elif atype == "sequence":
        steps = action["steps"]
        return lambda: inject_sequence(steps)

    elif atype == "ps_action":
        fn_name = action["fn"]
        args = action.get("args", {})
        fn = getattr(ps_runner, fn_name, None)
        if fn is None:
            logger.warning("ps_action desconhecida: %s", fn_name)
            return lambda: None
        return lambda: fn(**args)

    elif atype == "jsx":
        code = action["code"]
        return lambda: ps_runner.run_custom_jsx(code)

    else:
        logger.warning("Tipo de action desconhecido: %s", atype)
        return lambda: None


class PSHotkeysApp:
    def __init__(self):
        self.store = ProfileStore()
        self.engine = RemapEngine()
        self._status_callbacks: List[Callable] = []
        self._fired_callbacks: List[Callable[[str], None]] = []
        self._master_enabled = True  # Botão ON/OFF

        self.watcher = PhotoshopWatcher(
            on_focus_gained=self._ps_focused,
            on_focus_lost=self._ps_unfocused,
            poll_ms=250,
        )

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def start(self):
        self._reload_bindings()
        self.engine.start()
        self.watcher.start()
        logger.info("PSHotkeys v2 iniciado")

    def stop(self):
        self.watcher.stop()
        self.engine.stop()
        logger.info("PSHotkeys v2 parado")

    # ── ON/OFF ────────────────────────────────────────────────────────────────

    def set_master_enabled(self, enabled: bool):
        self._master_enabled = enabled
        self.store.set_setting("master_enabled", enabled)
        if enabled and self.watcher.is_running:
            self.engine.enable()
        else:
            self.engine.disable()
        self._notify_status()

    @property
    def master_enabled(self) -> bool:
        return self._master_enabled

    # ── Perfis ────────────────────────────────────────────────────────────────

    def switch_profile(self, name: str) -> bool:
        ok = self.store.set_active(name)
        if ok:
            self._reload_bindings()
        return ok

    def create_profile(self, name: str, description: str = "") -> dict:
        p = self.store.create_profile(name, description)
        return p

    def delete_profile(self, name: str) -> bool:
        result = self.store.delete_profile(name)
        if result:
            self._reload_bindings()
        return result

    # ── Bindings ──────────────────────────────────────────────────────────────

    def _reload_bindings(self):
        profile = self.store.active_profile()
        if not profile:
            self.engine.load_bindings({})
            return

        bindings = {}
        for b in profile.get("bindings", []):
            if not b.get("enabled", True):
                continue
            trigger = b["trigger"]
            action = b["action"]
            name = b["name"]
            combo = parse_combo(trigger)

            base_cb = _build_callback(action)

            def make_cb(_cb, _name):
                def cb():
                    _cb()
                    for fn in self._fired_callbacks:
                        try:
                            fn(_name)
                        except Exception:
                            pass
                return cb

            bindings[combo] = make_cb(base_cb, name)

        self.engine.load_bindings(bindings)
        logger.info("Perfil '%s' carregado: %d bindings ativos",
                    self.store.active_name(), len(bindings))

    def add_binding(self, name: str, trigger: str, action: dict, category: str = "Custom"):
        active = self.store.active_name()
        if not active:
            return None
        b = self.store.add_binding(active, name, trigger, action, category)
        self._reload_bindings()
        return b

    def update_binding(self, binding_id: str, **fields):
        active = self.store.active_name()
        if not active:
            return False
        result = self.store.update_binding(active, binding_id, **fields)
        self._reload_bindings()
        return result

    def delete_binding(self, binding_id: str):
        active = self.store.active_name()
        if not active:
            return False
        result = self.store.delete_binding(active, binding_id)
        self._reload_bindings()
        return result

    def toggle_binding(self, binding_id: str):
        active = self.store.active_name()
        if not active:
            return None
        result = self.store.toggle_binding(active, binding_id)
        self._reload_bindings()
        return result

    # ── Startup do Windows ────────────────────────────────────────────────────

    def set_run_at_startup(self, enabled: bool) -> bool:
        ok = _set_startup(enabled)
        if ok:
            self.store.set_setting("run_at_startup", enabled)
        return ok

    def is_run_at_startup(self) -> bool:
        return _check_startup()

    # ── PSWatcher ─────────────────────────────────────────────────────────────

    def _ps_focused(self):
        if self._master_enabled:
            self.engine.enable()
        self._notify_status()

    def _ps_unfocused(self):
        self.engine.disable()
        self._notify_status()

    # ── Status ────────────────────────────────────────────────────────────────

    @property
    def is_active(self) -> bool:
        return self.engine._enabled

    @property
    def ps_running(self) -> bool:
        return photoshop_running()

    def on_status_change(self, cb: Callable):
        self._status_callbacks.append(cb)

    def on_shortcut_fired(self, cb: Callable[[str], None]):
        self._fired_callbacks.append(cb)

    def _notify_status(self):
        for cb in self._status_callbacks:
            try:
                cb()
            except Exception:
                pass
