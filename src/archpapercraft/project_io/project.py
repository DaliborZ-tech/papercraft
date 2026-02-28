"""Project file handling — JSON-based project format.

File extension: ``.apcraft``

Structure
---------
```json
{
  "version": "0.1.0",
  "settings": { "units": "mm", "scale": "1:100", "paper": "A4", ... },
  "scene": [ { "name": "Wall-1", "type": "WALL", "params": {...}, "transform": {...}, "children": [...] } ],
}
```
"""

from __future__ import annotations

import json
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from archpapercraft.scene_graph.node import NodeType, SceneNode
from archpapercraft.scene_graph.scene import Scene
from archpapercraft.scene_graph.transform import Transform


FILE_EXTENSION = ".apcraft"
AUTOSAVE_SUFFIX = ".autosave"


@dataclass
class ProjectSettings:
    """Global project settings."""

    units: str = "mm"  # mm | cm | m
    scale: str = "1:100"
    paper: str = "A4"
    paper_margin_mm: float = 10.0
    paper_bleed_mm: float = 0.0
    paper_grammage: int = 160
    name: str = "Untitled"

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
    """Combines settings + scene for serialisation."""

    settings: ProjectSettings = field(default_factory=ProjectSettings)
    scene: Scene = field(default_factory=Scene)
    file_path: Path | None = None
    _last_save_time: float = 0.0

    # ── serialise ──────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": "0.1.0",
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
        """Try to load from autosave next to *path*."""
        p = Path(path)
        auto = p.with_suffix(FILE_EXTENSION + AUTOSAVE_SUFFIX)
        if auto.exists():
            return cls.load(auto)
        return None


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
