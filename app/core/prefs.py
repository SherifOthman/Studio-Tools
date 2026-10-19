"""
prefs.py  –  Persistent user preferences (JSON file next to the executable).
Usage:  from app.core.prefs import prefs
        prefs["lang"] = "ar"
        prefs.save()
"""

import json
import os
import sys

_DEFAULTS = {
    "theme":        "blue",
    "appearance":   "dark",
    "fmt":          "jpg",
    "dpi":          300,
    "jpg_quality":  95,
    "bg":           "transparent",
    "all_pages":    False,
    "suffix":       "",
    "out_mode":     "beside",
    "last_out_dir": "",
}


def _path() -> str:
    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
    else:
        # When running from source, save next to main.py
        base = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    return os.path.join(base, "prefs.json")


class Prefs:
    def __init__(self):
        self._d = dict(_DEFAULTS)
        self._file = _path()
        self._load()

    def _load(self):
        try:
            with open(self._file, encoding="utf-8") as f:
                saved = json.load(f)
            for k, v in saved.items():
                if k in _DEFAULTS:
                    self._d[k] = v
        except Exception:
            pass

    def save(self):
        try:
            with open(self._file, "w", encoding="utf-8") as f:
                json.dump(self._d, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def __getitem__(self, key):
        return self._d.get(key, _DEFAULTS.get(key))

    def __setitem__(self, key, value):
        self._d[key] = value

    def get(self, key, default=None):
        return self._d.get(key, default if default is not None else _DEFAULTS.get(key))


prefs = Prefs()
