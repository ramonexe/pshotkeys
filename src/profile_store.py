"""
profile_store.py — Gerencia perfis de remapeamento.

Cada perfil é um conjunto de bindings:
  trigger (combo original) → action (o que executar)

Tipos de action:
  "remap"   → substitui por outro combo de teclado
  "ps_action" → executa uma ação especial do PS (via ExtendScript)
  "sequence"  → sequência de combos com delays
  "jsx"       → código JSX customizado

Perfis ficam em: %APPDATA%/PSHotkeys/profiles/<nome>.json
Export/import: qualquer caminho .json
"""

import json
import uuid
import shutil
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


def _get_profiles_dir() -> Path:
    try:
        base = Path.home() / "AppData" / "Roaming" / "PSHotkeys" / "profiles"
    except Exception:
        base = Path.home() / ".pshotkeys" / "profiles"
    base.mkdir(parents=True, exist_ok=True)
    return base


def _get_settings_path() -> Path:
    return _get_profiles_dir().parent / "settings.json"


# ── Perfis padrão ─────────────────────────────────────────────────────────────

DEFAULT_PROFILES = {
    "Padrão": {
        "id": "builtin-default",
        "name": "Padrão",
        "description": "Perfil padrão",
        "bindings": [],
    },
}


class ProfileStore:
    def __init__(self):
        self._dir = _get_profiles_dir()
        self._settings_path = _get_settings_path()
        self._profiles: Dict[str, dict] = {}
        self._active_profile: Optional[str] = None
        self._load_all()

    # ── Carregamento ──────────────────────────────────────────────────────────

    def _load_all(self):
        loaded = False
        for f in self._dir.glob("*.json"):
            try:
                with open(f, encoding="utf-8") as fp:
                    data = json.load(fp)
                name = data.get("name", f.stem)
                self._profiles[name] = data
                loaded = True
                logger.info("Perfil carregado: %s (%d bindings)",
                            name, len(data.get("bindings", [])))
            except Exception as e:
                logger.warning("Erro ao carregar %s: %s", f, e)

        if not loaded:
            self._seed_defaults()

        # Carregar perfil ativo das settings
        active = self._load_settings().get("active_profile")
        if active and active in self._profiles:
            self._active_profile = active
        elif self._profiles:
            self._active_profile = next(iter(self._profiles))

    def _seed_defaults(self):
        for name, data in DEFAULT_PROFILES.items():
            self._profiles[name] = data
            self._save_profile(name)
        logger.info("Perfis padrão criados")

    def _save_profile(self, name: str):
        path = self._dir / f"{name}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self._profiles[name], f, indent=2, ensure_ascii=False)

    def _load_settings(self) -> dict:
        if self._settings_path.exists():
            try:
                with open(self._settings_path, encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_settings(self, data: dict):
        with open(self._settings_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    # ── API pública ───────────────────────────────────────────────────────────

    def profile_names(self) -> List[str]:
        return list(self._profiles.keys())

    def get_profile(self, name: str) -> Optional[dict]:
        return self._profiles.get(name)

    def active_name(self) -> Optional[str]:
        return self._active_profile

    def active_profile(self) -> Optional[dict]:
        if self._active_profile:
            return self._profiles.get(self._active_profile)
        return None

    def set_active(self, name: str) -> bool:
        if name not in self._profiles:
            return False
        self._active_profile = name
        settings = self._load_settings()
        settings["active_profile"] = name
        self._save_settings(settings)
        logger.info("Perfil ativo: %s", name)
        return True

    def create_profile(self, name: str, description: str = "") -> dict:
        profile = {
            "id": str(uuid.uuid4()),
            "name": name,
            "description": description,
            "bindings": [],
        }
        self._profiles[name] = profile
        self._save_profile(name)
        return profile

    def delete_profile(self, name: str) -> bool:
        if name not in self._profiles or len(self._profiles) <= 1:
            return False
        del self._profiles[name]
        path = self._dir / f"{name}.json"
        if path.exists():
            path.unlink()
        if self._active_profile == name:
            self._active_profile = next(iter(self._profiles))
        return True

    def rename_profile(self, old: str, new: str) -> bool:
        if old not in self._profiles or new in self._profiles:
            return False
        data = self._profiles.pop(old)
        data["name"] = new
        self._profiles[new] = data
        old_path = self._dir / f"{old}.json"
        if old_path.exists():
            old_path.unlink()
        self._save_profile(new)
        if self._active_profile == old:
            self._active_profile = new
        return True

    # ── Bindings ──────────────────────────────────────────────────────────────

    def add_binding(self, profile_name: str, name: str, trigger: str,
                    action: dict, category: str = "Custom") -> Optional[dict]:
        profile = self._profiles.get(profile_name)
        if not profile:
            return None
        binding = {
            "id": str(uuid.uuid4()),
            "name": name,
            "trigger": trigger.lower().strip(),
            "action": action,
            "enabled": True,
            "category": category,
        }
        profile.setdefault("bindings", []).append(binding)
        self._save_profile(profile_name)
        return binding

    def update_binding(self, profile_name: str, binding_id: str, **fields) -> bool:
        profile = self._profiles.get(profile_name)
        if not profile:
            return False
        for b in profile.get("bindings", []):
            if b["id"] == binding_id:
                b.update(fields)
                self._save_profile(profile_name)
                return True
        return False

    def delete_binding(self, profile_name: str, binding_id: str) -> bool:
        profile = self._profiles.get(profile_name)
        if not profile:
            return False
        before = len(profile.get("bindings", []))
        profile["bindings"] = [b for b in profile.get("bindings", [])
                                if b["id"] != binding_id]
        if len(profile["bindings"]) < before:
            self._save_profile(profile_name)
            return True
        return False

    def toggle_binding(self, profile_name: str, binding_id: str) -> Optional[bool]:
        profile = self._profiles.get(profile_name)
        if not profile:
            return None
        for b in profile.get("bindings", []):
            if b["id"] == binding_id:
                b["enabled"] = not b.get("enabled", True)
                self._save_profile(profile_name)
                return b["enabled"]
        return None

    # ── Import / Export ───────────────────────────────────────────────────────

    def export_profile(self, name: str, dest_path: str) -> bool:
        profile = self._profiles.get(name)
        if not profile:
            return False
        try:
            with open(dest_path, "w", encoding="utf-8") as f:
                json.dump(profile, f, indent=2, ensure_ascii=False)
            logger.info("Perfil exportado: %s → %s", name, dest_path)
            return True
        except Exception as e:
            logger.error("Export falhou: %s", e)
            return False

    def import_profile(self, src_path: str) -> Optional[str]:
        try:
            with open(src_path, encoding="utf-8") as f:
                data = json.load(f)
            name = data.get("name", Path(src_path).stem)
            # Evitar sobrescrever sem avisar
            if name in self._profiles:
                name = f"{name} (importado)"
            data["name"] = name
            self._profiles[name] = data
            self._save_profile(name)
            logger.info("Perfil importado: %s", name)
            return name
        except Exception as e:
            logger.error("Import falhou: %s", e)
            return None

    # ── Settings gerais ───────────────────────────────────────────────────────

    def get_setting(self, key: str, default=None):
        return self._load_settings().get(key, default)

    def set_setting(self, key: str, value: Any):
        settings = self._load_settings()
        settings[key] = value
        self._save_settings(settings)
