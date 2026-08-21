"""The single emblem currently selected to load into your own editor.

Exactly one captured emblem can be selected at a time. While in Show mode,
opening your own emblem editor on the PS5 triggers a request for one of your
saved emblem slots - the proxy answers with the selected emblem's data.
Optionally, that replacement can be limited to one specific slot so the
console's other emblem slots pass through untouched.
"""
import json
import os

from . import config
from .storage import group_dir


def _data_path():
    return os.path.join(group_dir(config.ACTIVE_NAME), "selected.bin")


def _meta_path():
    return os.path.join(group_dir(config.ACTIVE_NAME), "selected_meta.json")


def read_selection():
    """Selection metadata for the currently selected emblem, or None."""
    try:
        with open(_meta_path()) as f:
            return json.load(f)
    except FileNotFoundError:
        return None


def select_emblem(group, slot, target_slot=None):
    """Select one captured emblem to load into your own editor next."""
    os.makedirs(group_dir(config.ACTIVE_NAME), exist_ok=True)
    with open(os.path.join(group_dir(group), f"slot_{slot}.bin"), "rb") as f:
        data = f.read()
    with open(_data_path(), "wb") as f:
        f.write(data)
    with open(_meta_path(), "w") as f:
        json.dump({
            "group": group,
            "slot": slot,
            "target_slot": target_slot,
        }, f)


def set_target_slot(target_slot):
    """Update the optional injection target slot without changing selection."""
    meta = read_selection()
    if not meta:
        return False
    meta["target_slot"] = target_slot
    os.makedirs(group_dir(config.ACTIVE_NAME), exist_ok=True)
    with open(_meta_path(), "w") as f:
        json.dump(meta, f)
    return True


def clear_selection():
    for p in (_data_path(), _meta_path()):
        if os.path.exists(p):
            os.remove(p)


def read_selected_data():
    """Raw bytes (HTTP headers + body) of the selected emblem, or None."""
    try:
        with open(_data_path(), "rb") as f:
            return f.read()
    except FileNotFoundError:
        return None
