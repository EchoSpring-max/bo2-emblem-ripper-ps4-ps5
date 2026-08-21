"""Captured emblem groups: one folder per target player under saved/,
each holding meta.json (userhash, capture time) and one slot_<N>.bin per
saved emblem slot that player's console requested.
"""
import json
import os
import re
import threading
import time
from datetime import datetime

from . import config

_capture_lock = threading.Lock()

_SLOT_RE = re.compile(r"^slot_(\d+)\.bin$")


def group_dir(name):
    return os.path.join(config.SAVED_DIR, name)


def slot_path(name, slot):
    return os.path.join(group_dir(name), f"slot_{slot}.bin")


def read_meta(name):
    path = os.path.join(group_dir(name), "meta.json")
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        return None


def write_meta(name, meta):
    os.makedirs(group_dir(name), exist_ok=True)
    with open(os.path.join(group_dir(name), "meta.json"), "w") as f:
        json.dump(meta, f)


def list_groups():
    """Real captured groups, excluding the reserved active-set pseudo-group."""
    os.makedirs(config.SAVED_DIR, exist_ok=True)
    names = [
        d for d in os.listdir(config.SAVED_DIR)
        if os.path.isdir(group_dir(d)) and d != config.ACTIVE_NAME
    ]

    def sort_key(n):
        return (0, int(n)) if n.isdigit() else (1, n)
    return sorted(names, key=sort_key)


def group_slots(name):
    d = group_dir(name)
    if not os.path.isdir(d):
        return []
    return sorted(
        int(m.group(1)) for f in os.listdir(d) if (m := _SLOT_RE.match(f))
    )


def next_group_index():
    nums = [int(n) for n in list_groups() if n.isdigit()]
    return (max(nums) + 1) if nums else 1


def get_or_create_capture_group(userhash):
    """Reuse an existing group for the same target player if present,
    otherwise start a new group."""
    with _capture_lock:
        for name in reversed(list_groups()):
            meta = read_meta(name)
            if meta and meta.get("userhash") == userhash:
                return name
        idx = next_group_index()
        name = f"{idx:03d}"
        write_meta(name, {
            "userhash": userhash,
            "first_captured": time.strftime("%Y-%m-%d %H:%M:%S"),
        })
        return name


def write_slot_bytes(group, slot, data):
    os.makedirs(group_dir(group), exist_ok=True)
    with open(slot_path(group, slot), "wb") as f:
        f.write(data)


def mark_group_profile(group, is_profile=True):
    meta = read_meta(group) or {}
    meta["is_profile"] = bool(is_profile)
    write_meta(group, meta)


def slot_captured_at(group, slot):
    try:
        ts = os.path.getmtime(slot_path(group, slot))
    except FileNotFoundError:
        return ""
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")


# ---------- per-emblem labels ----------
# Users think of each captured slot as one "emblem" - they never need to know
# it's technically a (group, slot) pair. Labels are keyed by slot number
# (as a string) inside the group's own meta.json.

def get_emblem_label(group, slot):
    meta = read_meta(group) or {}
    return meta.get("labels", {}).get(str(slot), "")


def set_emblem_label(group, slot, label):
    meta = read_meta(group) or {}
    labels = meta.setdefault("labels", {})
    if label:
        labels[str(slot)] = label
    else:
        labels.pop(str(slot), None)
    write_meta(group, meta)


def list_emblems():
    """Every captured emblem as a flat list, newest first - one entry per
    (group, slot), with no group/slot concepts exposed beyond an opaque id."""
    emblems = []
    for group in list_groups():
        meta = read_meta(group) or {}
        for slot in group_slots(group):
            is_profile = meta.get("is_profile")
            if is_profile is None:
                # Older captures have no profile marker. The classic UI grouped
                # local profile emblem slots in the 500+ range, so keep that
                # visual hint for legacy data.
                is_profile = slot >= 500
            emblems.append({
                "id": f"{group}:{slot}",
                "group": group,
                "slot": slot,
                "label": meta.get("labels", {}).get(str(slot), ""),
                "captured_at": slot_captured_at(group, slot) or meta.get("first_captured", ""),
                "is_profile": bool(is_profile),
            })
    emblems.sort(key=lambda e: e["captured_at"], reverse=True)
    return emblems
