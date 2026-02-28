"""Projektový soubor — formát JSON s příponou ``.apcraft``

Struktura
---------
```json
{
  "version": "0.2.0",
  "settings": { "units": "mm", "scale": "1:100", "paper": "A4", ... },
  "scene": [ { "name": "Zeď-1", "type": "WALL", "params": {...}, "transform": {...}, "children": [...] } ],
}
```

Pokročilé funkce:
- Snapshoty (versioning) — uložit stav projektu s časovým razítkem
- Crash report + log
- Export balíčku (zip se všemi soubory)
"""

from __future__ import annotations

import json
import logging
import shutil
import time
import traceback
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from archpapercraft.scene_graph.node import NodeType, SceneNode
from archpapercraft.scene_graph.scene import Scene
from archpapercraft.scene_graph.transform import Transform


FILE_EXTENSION = ".apcraft"
AUTOSAVE_SUFFIX = ".autosave"
SNAPSHOT_DIR = ".snapshots"

# Logging pro crash report
_LOG_DIR = Path.home() / ".archpapercraft" / "logs"
_log = logging.getLogger("archpapercraft.project")


def _ensure_log_dir() -> Path:
    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    return _LOG_DIR


@dataclass
class ProjectSettings:
    """Globální nastavení projektu."""

    units: str = "mm"  # mm | cm | m
    scale: str = "1:100"
    paper: str = "A4"
    paper_margin_mm: float = 10.0
    paper_bleed_mm: float = 0.0
    paper_grammage: int = 160
    name: str = "Bez názvu"

    def to_dict(self) -> dict[str, Any]:
        return {
            "units": self.units,
            "scale": self.scale,
            "paper": self.paper,
            "paper_margin_mm": self.paper_margin_mm,
            "paper_bleed_mm": self.paper_bleed_mm,
            "paper_grammage": self.paper_grammage,
            "name": self.name,
        }

    @classmethod
    def from_dict(cls, d: dict) -> ProjectSettings:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})

    @property
    def scale_factor(self) -> float:
        """Return numeric scale (e.g. '1:100' → 0.01)."""
        parts = self.scale.split(":")
        if len(parts) == 2:
            return float(parts[0]) / float(parts[1])
        return 1.0


@dataclass
class Project:
    """Kombinuje nastavení + scénu pro serializaci."""

    settings: ProjectSettings = field(default_factory=ProjectSettings)
    scene: Scene = field(default_factory=Scene)
    file_path: Path | None = None
    _last_save_time: float = 0.0

    # ── serializace ────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": "0.2.0",
            "settings": self.settings.to_dict(),
            "scene": [_node_to_dict(c) for c in self.scene.root.children],
        }

    @classmethod
    def from_dict(cls, data: dict, file_path: Path | None = None) -> Project:
        settings = ProjectSettings.from_dict(data.get("settings", {}))
        proj = cls(settings=settings, file_path=file_path)
        for node_data in data.get("scene", []):
            node = _node_from_dict(node_data)
            proj.scene.root.add_child(node)
        return proj

    # ── save / load ────────────────────────────────────────────────────

    def save(self, path: str | Path | None = None) -> Path:
        p = Path(path) if path else self.file_path
        if p is None:
            raise ValueError("No file path specified for save.")
        p = p.with_suffix(FILE_EXTENSION)
        p.write_text(json.dumps(self.to_dict(), indent=2, default=_json_default), encoding="utf-8")
        self.file_path = p
        self._last_save_time = time.time()
        return p

    @classmethod
    def load(cls, path: str | Path) -> Project:
        p = Path(path)
        data = json.loads(p.read_text(encoding="utf-8"))
        return cls.from_dict(data, file_path=p)

    # ── autosave ───────────────────────────────────────────────────────

    def autosave(self) -> Path | None:
        if self.file_path is None:
            return None
        auto_path = self.file_path.with_suffix(FILE_EXTENSION + AUTOSAVE_SUFFIX)
        auto_path.write_text(
            json.dumps(self.to_dict(), indent=2, default=_json_default), encoding="utf-8"
        )
        return auto_path

    @classmethod
    def recover(cls, path: str | Path) -> Project | None:
        """Pokus o načtení z autosave vedle *path*."""
        p = Path(path)
        auto = p.with_suffix(FILE_EXTENSION + AUTOSAVE_SUFFIX)
        if auto.exists():
            return cls.load(auto)
        return None

    # ── snapshoty (verzování) ──────────────────────────────────────────

    def create_snapshot(self, label: str = "") -> Path | None:
        """Uloží snapshot (kopii) aktuálního stavu projektu.

        Snímky se ukládají do složky ``.snapshots/`` vedle projektového souboru.
        Název obsahuje časové razítko a volitelný popisek.
        """
        if self.file_path is None:
            return None

        snap_dir = self.file_path.parent / SNAPSHOT_DIR
        snap_dir.mkdir(exist_ok=True)

        timestamp = time.strftime("%Y%m%d_%H%M%S")
        suffix = f"_{label}" if label else ""
        snap_name = f"{self.file_path.stem}_{timestamp}{suffix}{FILE_EXTENSION}"
        snap_path = snap_dir / snap_name

        snap_path.write_text(
            json.dumps(self.to_dict(), indent=2, default=_json_default),
            encoding="utf-8",
        )
        _log.info("Snapshot vytvořen: %s", snap_path)
        return snap_path

    def list_snapshots(self) -> list[Path]:
        """Vrátí seznam všech snapshotů (seřazený od nejnovějšího)."""
        if self.file_path is None:
            return []
        snap_dir = self.file_path.parent / SNAPSHOT_DIR
        if not snap_dir.exists():
            return []
        snaps = sorted(snap_dir.glob(f"*{FILE_EXTENSION}"), reverse=True)
        return snaps

    @classmethod
    def load_snapshot(cls, snapshot_path: str | Path) -> "Project":
        """Načte projekt ze snapshotu."""
        return cls.load(snapshot_path)

    # ── export balíčku (zip) ───────────────────────────────────────────

    def export_bundle(self, output_path: str | Path | None = None) -> Path:
        """Zabalí projekt + snapshoty do ZIP archívu.

        Pokud *output_path* není zadán, uloží vedle projektového souboru.
        """
        if self.file_path is None:
            raise ValueError("Projekt musí být nejprve uložen.")

        if output_path is None:
            output_path = self.file_path.with_suffix(".zip")
        else:
            output_path = Path(output_path)

        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
            # Hlavní projektový soubor
            zf.writestr(
                self.file_path.name,
                json.dumps(self.to_dict(), indent=2, default=_json_default),
            )
            # Snapshoty
            snap_dir = self.file_path.parent / SNAPSHOT_DIR
            if snap_dir.exists():
                for snap in snap_dir.glob(f"*{FILE_EXTENSION}"):
                    zf.write(snap, f"{SNAPSHOT_DIR}/{snap.name}")

        _log.info("Bundle exportován: %s", output_path)
        return output_path

    # ── crash report ───────────────────────────────────────────────────

    @staticmethod
    def write_crash_report(exc: BaseException) -> Path:
        """Zapíše crash report do logovacího adresáře.

        Vrací cestu k souboru s reportem.
        """
        log_dir = _ensure_log_dir()
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        report_path = log_dir / f"crash_{timestamp}.log"

        lines = [
            f"ArchPapercraft Studio — Crash Report",
            f"Čas: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"",
            f"Výjimka: {type(exc).__name__}: {exc}",
            f"",
            "Traceback:",
            traceback.format_exc(),
        ]
        report_path.write_text("\n".join(lines), encoding="utf-8")
        _log.error("Crash report zapsán: %s", report_path)
        return report_path

    @staticmethod
    def list_crash_reports() -> list[Path]:
        """Vrátí seznam crash reportů."""
        log_dir = _ensure_log_dir()
        return sorted(log_dir.glob("crash_*.log"), reverse=True)


# ── internal conversion helpers ────────────────────────────────────────


def _json_default(obj: Any) -> Any:
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def _node_to_dict(node: SceneNode) -> dict[str, Any]:
    return {
        "name": node.name,
        "type": node.node_type.name,
        "id": node.node_id,
        "transform": {
            "position": node.transform.position.tolist(),
            "rotation": node.transform.rotation.tolist(),
            "scale": node.transform.scale.tolist(),
        },
        "parameters": node.parameters,
        "children": [_node_to_dict(c) for c in node.children],
    }


def _node_from_dict(data: dict) -> SceneNode:
    t_data = data.get("transform", {})
    transform = Transform(
        position=np.array(t_data.get("position", [0, 0, 0]), dtype=np.float64),
        rotation=np.array(t_data.get("rotation", [0, 0, 0]), dtype=np.float64),
        scale=np.array(t_data.get("scale", [1, 1, 1]), dtype=np.float64),
    )

    node = SceneNode(
        name=data.get("name", "Node"),
        node_type=NodeType[data.get("type", "GROUP")],
        node_id=data.get("id", ""),
        transform=transform,
        parameters=data.get("parameters", {}),
    )

    for child_data in data.get("children", []):
        child = _node_from_dict(child_data)
        node.add_child(child)

    return node
