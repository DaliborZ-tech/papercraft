"""Globální nastavení aplikace — uložení / načtení, výchozí hodnoty.

Nastavení se ukládá do ``~/.archpapercraft/settings.json`` (Windows: ``%APPDATA%``).

Kategorie nastavení:
- Obecné (jazyk, jednotky, téma)
- Viewport (barvy, mřížka, citlivost myši)
- Snap (režimy, velikost mřížky, úhlový krok)
- Export (výchozí formát, gramáž, chlopně)
- Klávesové zkratky
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any


def _config_dir() -> Path:
    """Vrátí adresář pro konfigurační soubory."""
    import os
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home()))
    else:
        base = Path.home() / ".config"
    d = base / "archpapercraft"
    d.mkdir(parents=True, exist_ok=True)
    return d


@dataclass
class GeneralSettings:
    """Obecná nastavení."""
    language: str = "cs"              # cs / en
    default_units: str = "mm"         # mm / cm / m
    default_scale: str = "1:100"
    theme: str = "system"             # system / light / dark
    autosave_interval_sec: int = 120  # sekundy mezi autosave
    max_undo_depth: int = 200


@dataclass
class ViewportSettings:
    """Nastavení 3D viewportu."""
    background_color: tuple[int, int, int] = (45, 45, 48)
    grid_color: tuple[int, int, int] = (80, 80, 80)
    grid_size: float = 10.0           # mm
    grid_subdivisions: int = 5
    orbit_sensitivity: float = 1.0
    pan_sensitivity: float = 1.0
    zoom_sensitivity: float = 1.0
    show_grid: bool = True
    show_axes: bool = True
    wireframe_color: tuple[int, int, int] = (200, 200, 200)
    selection_color: tuple[int, int, int] = (255, 165, 0)
    seam_color: tuple[int, int, int] = (255, 0, 0)


@dataclass
class SnapPreferences:
    """Nastavení přichytávání."""
    enabled: bool = True
    snap_to_grid: bool = True
    snap_to_vertex: bool = False
    snap_to_edge: bool = False
    snap_to_axis: bool = True
    angle_snap: bool = True
    angle_step_deg: float = 15.0
    grid_size: float = 10.0
    vertex_radius: float = 5.0
    edge_radius: float = 5.0


@dataclass
class ExportSettings:
    """Výchozí nastavení exportu."""
    default_format: str = "pdf"       # pdf / svg / dxf / png
    default_paper: str = "A4"
    default_margin_mm: float = 10.0
    default_grammage: int = 160
    tab_shape: str = "tapered"        # straight / tapered / tooth
    include_build_guide: bool = True
    png_dpi: int = 150


@dataclass
class KeyboardShortcuts:
    """Klávesové zkratky (výchozí)."""
    new_project: str = "Ctrl+N"
    open_project: str = "Ctrl+O"
    save_project: str = "Ctrl+S"
    save_as: str = "Ctrl+Shift+S"
    undo: str = "Ctrl+Z"
    redo: str = "Ctrl+Y"
    delete: str = "Delete"
    duplicate: str = "Ctrl+D"
    select_all: str = "Ctrl+A"
    focus_selection: str = "Numpad ."
    toggle_grid: str = "G"
    toggle_snap: str = "S"
    view_top: str = "Numpad 7"
    view_front: str = "Numpad 1"
    view_side: str = "Numpad 3"
    view_perspective: str = "Numpad 0"
    export: str = "Ctrl+E"


@dataclass
class Preferences:
    """Hlavní kontejner všech nastavení aplikace."""

    general: GeneralSettings = field(default_factory=GeneralSettings)
    viewport: ViewportSettings = field(default_factory=ViewportSettings)
    snap: SnapPreferences = field(default_factory=SnapPreferences)
    export: ExportSettings = field(default_factory=ExportSettings)
    shortcuts: KeyboardShortcuts = field(default_factory=KeyboardShortcuts)

    # ── uložení / načtení ─────────────────────────────────────────────

    def save(self, path: Path | None = None) -> Path:
        """Uloží nastavení do JSON souboru."""
        if path is None:
            path = _config_dir() / "settings.json"
        data = {
            "general": asdict(self.general),
            "viewport": asdict(self.viewport),
            "snap": asdict(self.snap),
            "export": asdict(self.export),
            "shortcuts": asdict(self.shortcuts),
        }
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return path

    @classmethod
    def load(cls, path: Path | None = None) -> Preferences:
        """Načte nastavení ze souboru. Chybějící klíče = výchozí hodnoty."""
        if path is None:
            path = _config_dir() / "settings.json"
        if not path.exists():
            return cls()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return cls()

        prefs = cls()
        if "general" in data:
            prefs.general = _merge_dataclass(GeneralSettings, data["general"])
        if "viewport" in data:
            prefs.viewport = _merge_dataclass(ViewportSettings, data["viewport"])
        if "snap" in data:
            prefs.snap = _merge_dataclass(SnapPreferences, data["snap"])
        if "export" in data:
            prefs.export = _merge_dataclass(ExportSettings, data["export"])
        if "shortcuts" in data:
            prefs.shortcuts = _merge_dataclass(KeyboardShortcuts, data["shortcuts"])
        return prefs

    @classmethod
    def reset(cls) -> Preferences:
        """Vrátí výchozí nastavení."""
        return cls()


def _merge_dataclass(cls: type, data: dict[str, Any]) -> Any:
    """Vytvoří instanci dataclass z dict, ignoruje neznámé klíče."""
    valid = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
    # Převod tuple polí z JSON list
    for k, v in valid.items():
        f = cls.__dataclass_fields__[k]
        if f.type.startswith("tuple") and isinstance(v, list):
            valid[k] = tuple(v)
    return cls(**valid)
