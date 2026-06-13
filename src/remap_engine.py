"""
remap_engine.py — Intercepta teclas e substitui por outras em tempo real.

Arquitetura: suppress=False + event_filter para supressão seletiva.

Por que NÃO usar suppress=True com re-injeção:
  pynput com suppress=True suprime TODOS os eventos, inclusive os
  sintéticos injetados via Controller._kb.press(). Isso cria um loop
  infinito: real → suppressed → inject → pynput captura injetado →
  suppresses → inject novamente → … resultando em todos os atalhos
  do PS pararem de funcionar.

Arquitetura correta:
  suppress=False → teclas não-mapeadas passam pelo hook naturalmente,
  sem necessidade de re-injeção.
  event_filter → chamado sincronamente no callback do hook Win32. Para
  combos mapeados: levanta SuppressException (suprime o original) e
  dispara a ação. Para eventos injetados (flag LLKHF_INJECTED): retorna
  True para passar adiante — sem loop.
"""

import sys
import time
import threading
import logging
from typing import Callable, Dict, Optional, Set
from pynput import keyboard
from pynput.keyboard import Key, Controller

logger = logging.getLogger(__name__)
IS_WINDOWS = sys.platform == "win32"

_kb = Controller()

# ── Mapeamento VK code → string canônica (para event_filter) ──────────────────

_MODS_VK: Dict[int, str] = {
    0x11: "ctrl", 0xA2: "ctrl", 0xA3: "ctrl",   # CONTROL / LCONTROL / RCONTROL
    0x12: "alt",  0xA4: "alt",  0xA5: "alt",    # MENU / LMENU / RMENU
    0x10: "shift", 0xA0: "shift", 0xA1: "shift", # SHIFT / LSHIFT / RSHIFT
    0x5B: "win",  0x5C: "win",                   # LWIN / RWIN
}

_SPECIAL_VK: Dict[int, str] = {
    0x20: "space", 0x0D: "enter", 0x09: "tab",
    0x08: "backspace", 0x2E: "delete", 0x1B: "escape",
    0x24: "home",  0x23: "end",
    0x21: "pageup", 0x22: "pagedown",
    0x26: "up", 0x28: "down", 0x25: "left", 0x27: "right",
    **{0x70 + i: f"f{i + 1}" for i in range(12)},  # F1–F12
}


def _vk_to_str(vk: int) -> Optional[str]:
    """Converte VK code → string canônica (mesma usada em parse_combo)."""
    if vk in _MODS_VK:
        return _MODS_VK[vk]
    if vk in _SPECIAL_VK:
        return _SPECIAL_VK[vk]
    if 0x41 <= vk <= 0x5A:
        return chr(vk).lower()   # A–Z → a–z
    if 0x30 <= vk <= 0x39:
        return chr(vk)           # 0–9
    return None


# ── Helpers para injeção (mantidos para compatibilidade com app.py) ────────────

_MOD_CANONICAL = {
    Key.ctrl_l: "ctrl", Key.ctrl_r: "ctrl", Key.ctrl: "ctrl",
    Key.alt_l:  "alt",  Key.alt_r:  "alt",  Key.alt:  "alt",
    Key.shift_l: "shift", Key.shift_r: "shift", Key.shift: "shift",
    Key.cmd_l:  "win",  Key.cmd_r:  "win",  Key.cmd:  "win",
}

_SPECIAL = {
    Key.space: "space", Key.enter: "enter", Key.tab: "tab",
    Key.backspace: "backspace", Key.delete: "delete", Key.esc: "escape",
    Key.home: "home", Key.end: "end", Key.page_up: "pageup",
    Key.page_down: "pagedown", Key.up: "up", Key.down: "down",
    Key.left: "left", Key.right: "right",
    Key.f1: "f1", Key.f2: "f2", Key.f3: "f3", Key.f4: "f4",
    Key.f5: "f5", Key.f6: "f6", Key.f7: "f7", Key.f8: "f8",
    Key.f9: "f9", Key.f10: "f10", Key.f11: "f11", Key.f12: "f12",
}


def key_to_str(key) -> Optional[str]:
    """Converte qualquer tecla pynput → string canônica."""
    if key in _MOD_CANONICAL:
        return _MOD_CANONICAL[key]
    if key in _SPECIAL:
        return _SPECIAL[key]
    try:
        if key.char:
            return key.char.lower()
    except AttributeError:
        pass
    try:
        return key.name.lower()
    except AttributeError:
        return None


def str_to_pynput(token: str):
    """Converte string canônica → objeto pynput para injeção."""
    _map = {
        "ctrl": Key.ctrl, "alt": Key.alt, "shift": Key.shift, "win": Key.cmd,
        "enter": Key.enter, "space": Key.space, "tab": Key.tab,
        "backspace": Key.backspace, "delete": Key.delete, "escape": Key.esc,
        "home": Key.home, "end": Key.end, "pageup": Key.page_up,
        "pagedown": Key.page_down, "up": Key.up, "down": Key.down,
        "left": Key.left, "right": Key.right,
        **{f"f{i}": getattr(Key, f"f{i}") for i in range(1, 13)},
    }
    if token in _map:
        return _map[token]
    return token


def parse_combo(combo_str: str) -> frozenset:
    """'ctrl+alt+e' → frozenset({'ctrl','alt','e'})"""
    return frozenset(t.strip().lower() for t in combo_str.split("+") if t.strip())


def inject_keys(keys: list):
    """Injeta uma combinação de teclas simuladas."""
    pynput_keys = [str_to_pynput(k) for k in keys]
    for k in pynput_keys[:-1]:
        _kb.press(k)
    _kb.press(pynput_keys[-1])
    _kb.release(pynput_keys[-1])
    for k in reversed(pynput_keys[:-1]):
        _kb.release(k)


def inject_sequence(steps: list):
    """Injeta uma sequência de combos com delays."""
    for step in steps:
        inject_keys(step["keys"])
        time.sleep(step.get("delay", 0.05))


# ── RemapEngine ────────────────────────────────────────────────────────────────

# Importa SuppressException do pynput interno uma única vez.
try:
    from pynput._util.win32 import SystemHook as _SystemHook
    _SuppressException = _SystemHook.SuppressException
except Exception:
    _SuppressException = None

_WM_KEYDOWN   = 0x0100
_WM_KEYUP     = 0x0101
_WM_SYSKEYDOWN = 0x0104
_WM_SYSKEYUP  = 0x0105
_LLKHF_INJECTED       = 0x10
_LLKHF_LOWER_IL_INJECTED = 0x02


class RemapEngine:
    """
    Motor de remapeamento.

    Usa suppress=False + event_filter para supressão seletiva:
    - Teclas não-mapeadas: passam pelo hook sem intervenção (sem re-injeção).
    - Combos mapeados: suprimir original via SuppressException + disparar ação.
    - Eventos injetados (LLKHF_INJECTED): passam sempre (sem loop).
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._bindings: Dict[frozenset, Callable] = {}
        self._held_vk: Set[int] = set()  # VK codes pressionados (no event_filter)
        self._enabled = False
        self._listener: Optional[keyboard.Listener] = None
        self._debounce: Dict[frozenset, float] = {}
        self._debounce_sec = 0.18

    def enable(self):
        self._enabled = True
        self._held_vk.clear()

    def disable(self):
        self._enabled = False
        self._held_vk.clear()

    def load_bindings(self, bindings: Dict[frozenset, Callable]):
        with self._lock:
            self._bindings = dict(bindings)
        logger.info("Bindings carregados: %d atalhos", len(bindings))

    # ── Hook filter ───────────────────────────────────────────────────────────

    def _event_filter(self, msg, data):
        """
        Chamado sincronamente no thread do hook Win32, antes de qualquer
        callback Python. Decide se o evento deve ser suprimido.

        Retorna True para passar adiante; levanta SuppressException para suprimir.
        """
        # Eventos injetados (LLKHF_INJECTED): são nossas teclas de substituição.
        # Sempre passam adiante para chegar ao PS — sem loop.
        if data.flags & (_LLKHF_INJECTED | _LLKHF_LOWER_IL_INJECTED):
            return True

        is_press   = msg in (_WM_KEYDOWN, _WM_SYSKEYDOWN)
        is_release = msg in (_WM_KEYUP,   _WM_SYSKEYUP)
        vk = data.vkCode

        if is_press:
            self._held_vk.add(vk)
        elif is_release:
            self._held_vk.discard(vk)
            return True  # Releases nunca são suprimidos

        if not is_press or not self._enabled:
            return True

        # Monta combo a partir dos VKs pressionados
        combo_strs = {s for v in self._held_vk if (s := _vk_to_str(v))}
        combo = frozenset(combo_strs)

        with self._lock:
            action = self._bindings.get(combo)

        if action:
            if _SuppressException is None:
                logger.warning("SuppressException não disponível — supressão desativada")
                return True
            now = time.monotonic()
            last = self._debounce.get(combo, 0)
            if now - last > self._debounce_sec:
                self._debounce[combo] = now
                logger.debug("Suprimindo combo %s → disparando ação", combo)
                threading.Thread(target=action, daemon=True).start()
            else:
                logger.debug("Combo %s em debounce — suprimindo sem disparar", combo)
            raise _SuppressException()  # Suprime o original

        return True

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def start(self):
        if self._listener and self._listener.is_alive():
            return
        self._listener = keyboard.Listener(
            suppress=False,
            win32_event_filter=self._event_filter,
        )
        self._listener.daemon = True
        self._listener.start()
        logger.info("RemapEngine iniciado (suppress=False, event_filter ativo)")

    def stop(self):
        if self._listener:
            self._listener.stop()
            try:
                self._listener.join(timeout=1.0)
            except Exception:
                pass
        self._held_vk.clear()
        self._listener = None
        logger.info("RemapEngine parado")
