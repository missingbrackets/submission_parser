# ============================================================
#  skills/__init__.py
#  Auto-discovering skill registry.
#
#  DROP a new skill file into the skills/ folder.
#  It will appear in the app automatically — no other
#  files need to be edited.
#
#  Each skill file must:
#    1. Import BaseSkill from skills.base
#    2. Define a class that inherits BaseSkill
#    3. Set META["code"] to a unique short string
# ============================================================

import os
import importlib
import inspect
from skills.base import BaseSkill

# ── AUTO-DISCOVERY ────────────────────────────────────────────
_REGISTRY: dict = {}   # { label: SkillClass }

def _discover_skills():
    """
    Scan the skills/ directory for .py files (excluding base and __init__).
    Import each, find classes that subclass BaseSkill, register them.
    """
    skills_dir = os.path.dirname(__file__)

    for fname in sorted(os.listdir(skills_dir)):
        if not fname.endswith(".py"):
            continue
        if fname.startswith("_") or fname == "base.py":
            continue

        module_name = f"skills.{fname[:-3]}"
        try:
            module = importlib.import_module(module_name)
        except Exception as e:
            print(f"[skills] Warning: could not import {module_name}: {e}")
            continue

        for name, obj in inspect.getmembers(module, inspect.isclass):
            if (
                issubclass(obj, BaseSkill)
                and obj is not BaseSkill
                and obj.META.get("code")          # must have a code set
            ):
                label = obj.label()
                _REGISTRY[label] = obj

_discover_skills()


# ── PUBLIC API ────────────────────────────────────────────────

def available_classes() -> list:
    """Return sorted list of skill labels for the UI dropdown."""
    return sorted(_REGISTRY.keys())


def get_skill_class(label: str) -> type:
    """Return the skill class for a given label."""
    if label not in _REGISTRY:
        raise KeyError(f"No skill registered for: '{label}'. Available: {available_classes()}")
    return _REGISTRY[label]


def get_skill(label: str) -> dict:
    """
    Return skill config dict, with any JSON sidecar overrides applied.
    Shape identical to before — all existing call sites work unchanged.
    Extra keys: 'config' (raw sidecar dict), 'has_overrides' (bool).
    """
    from skills.config_loader import load_config, apply_config
    cls    = get_skill_class(label)
    config = load_config(cls.code())
    return apply_config(cls, config)


def list_skills_doc() -> str:
    """Print schema documentation for all registered skills."""
    lines = []
    for label in available_classes():
        cls = get_skill_class(label)
        lines.append(cls.schema_doc())
        lines.append("\n" + "=" * 80 + "\n")
    return "\n".join(lines)