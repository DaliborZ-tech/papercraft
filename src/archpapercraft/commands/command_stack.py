"""Undo/Redo systém — Command pattern s hlubokým zásobníkem.

Každá uživatelská akce je zapouzdřena do příkazu (Command), který umí:
- ``execute()`` — provést akci
- ``undo()`` — vrátit akci zpět

CommandStack udržuje historii a umožňuje libovolně hluboké Undo/Redo.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable

import numpy as np

from archpapercraft.scene_graph.node import NodeType, SceneNode
from archpapercraft.scene_graph.scene import Scene
from archpapercraft.scene_graph.transform import Transform


# ── Abstraktní příkaz ──────────────────────────────────────────────────


class Command(ABC):
    """Základní třída pro všechny příkazy (Undo/Redo)."""

    @abstractmethod
    def execute(self) -> None:
        """Provede příkaz."""

    @abstractmethod
    def undo(self) -> None:
        """Vrátí příkaz zpět."""

    def description(self) -> str:
        """Lidsky čitelný popis příkazu pro zobrazení v menu."""
        return self.__class__.__name__


# ── Zásobník příkazů ───────────────────────────────────────────────────


class CommandStack:
    """Zásobník Undo/Redo příkazů.

    Parametry
    ---------
    max_depth : int
        Maximální hloubka zásobníku (výchozí 200).
    on_change : Callable | None
        Callback volaný po každé změně zásobníku (pro aktualizaci UI).
    """

    def __init__(
        self,
        max_depth: int = 200,
        on_change: Callable[[], None] | None = None,
    ) -> None:
        self._undo_stack: list[Command] = []
        self._redo_stack: list[Command] = []
        self._max_depth = max_depth
        self._on_change = on_change

    # ── veřejné API ───────────────────────────────────────────────────

    def execute(self, command: Command) -> None:
        """Provede příkaz a přidá ho na undo zásobník."""
        command.execute()
        self._undo_stack.append(command)
        self._redo_stack.clear()
        # Oříznutí zásobníku
        if len(self._undo_stack) > self._max_depth:
            self._undo_stack = self._undo_stack[-self._max_depth :]
        self._notify()

    def undo(self) -> bool:
        """Vrátí poslední příkaz. Vrací True pokud se podařilo."""
        if not self._undo_stack:
            return False
        cmd = self._undo_stack.pop()
        cmd.undo()
        self._redo_stack.append(cmd)
        self._notify()
        return True

    def redo(self) -> bool:
        """Znovu provede poslední vrácený příkaz. Vrací True pokud se podařilo."""
        if not self._redo_stack:
            return False
        cmd = self._redo_stack.pop()
        cmd.execute()
        self._undo_stack.append(cmd)
        self._notify()
        return True

    def clear(self) -> None:
        """Vymaže oba zásobníky."""
        self._undo_stack.clear()
        self._redo_stack.clear()
        self._notify()

    @property
    def can_undo(self) -> bool:
        return len(self._undo_stack) > 0

    @property
    def can_redo(self) -> bool:
        return len(self._redo_stack) > 0

    @property
    def undo_description(self) -> str:
        """Popis příkazu, který bude vrácen."""
        if self._undo_stack:
            return self._undo_stack[-1].description()
        return ""

    @property
    def redo_description(self) -> str:
        """Popis příkazu, který bude znovu proveden."""
        if self._redo_stack:
            return self._redo_stack[-1].description()
        return ""

    @property
    def undo_count(self) -> int:
        return len(self._undo_stack)

    @property
    def redo_count(self) -> int:
        return len(self._redo_stack)

    def _notify(self) -> None:
        if self._on_change:
            self._on_change()


# ── Konkrétní příkazy ─────────────────────────────────────────────────


class AddNodeCommand(Command):
    """Přidání uzlu do scény."""

    def __init__(
        self,
        scene: Scene,
        name: str,
        node_type: NodeType,
        parent: SceneNode | None = None,
        **params: Any,
    ) -> None:
        self._scene = scene
        self._name = name
        self._node_type = node_type
        self._parent = parent
        self._params = params
        self._node: SceneNode | None = None

    def execute(self) -> None:
        self._node = self._scene.add_node(
            self._name, self._node_type, self._parent, **self._params
        )
        self._scene.rebuild_meshes()

    def undo(self) -> None:
        if self._node:
            self._scene.remove_node(self._node)

    def description(self) -> str:
        return f"Přidat {self._name}"


class RemoveNodeCommand(Command):
    """Odebrání uzlu ze scény."""

    def __init__(self, scene: Scene, node: SceneNode) -> None:
        self._scene = scene
        self._node = node
        self._parent: SceneNode | None = None
        self._index: int = -1

    def execute(self) -> None:
        self._parent = self._node.parent
        if self._parent:
            self._index = self._parent.children.index(self._node)
        self._scene.remove_node(self._node)

    def undo(self) -> None:
        if self._parent:
            self._parent.children.insert(self._index, self._node)
            self._node.parent = self._parent
        else:
            self._scene.root.add_child(self._node)
        self._scene.rebuild_meshes()

    def description(self) -> str:
        return f"Odebrat {self._node.name}"


class SetTransformCommand(Command):
    """Změna transformace uzlu."""

    def __init__(self, node: SceneNode, new_transform: Transform) -> None:
        self._node = node
        self._new = Transform(
            position=new_transform.position.copy(),
            rotation=new_transform.rotation.copy(),
            scale=new_transform.scale.copy(),
        )
        self._old = Transform(
            position=node.transform.position.copy(),
            rotation=node.transform.rotation.copy(),
            scale=node.transform.scale.copy(),
        )

    def execute(self) -> None:
        self._node.transform = Transform(
            position=self._new.position.copy(),
            rotation=self._new.rotation.copy(),
            scale=self._new.scale.copy(),
        )
        self._node.mark_dirty()

    def undo(self) -> None:
        self._node.transform = Transform(
            position=self._old.position.copy(),
            rotation=self._old.rotation.copy(),
            scale=self._old.scale.copy(),
        )
        self._node.mark_dirty()

    def description(self) -> str:
        return f"Transformace {self._node.name}"


class SetParameterCommand(Command):
    """Změna parametru uzlu."""

    def __init__(self, node: SceneNode, key: str, new_value: Any) -> None:
        self._node = node
        self._key = key
        self._new_value = new_value
        self._old_value = node.parameters.get(key)

    def execute(self) -> None:
        self._node.set_param(self._key, self._new_value)

    def undo(self) -> None:
        if self._old_value is None:
            self._node.parameters.pop(self._key, None)
        else:
            self._node.set_param(self._key, self._old_value)

    def description(self) -> str:
        return f"Změnit {self._key} — {self._node.name}"


class RenameNodeCommand(Command):
    """Přejmenování uzlu."""

    def __init__(self, node: SceneNode, new_name: str) -> None:
        self._node = node
        self._new_name = new_name
        self._old_name = node.name

    def execute(self) -> None:
        self._node.name = self._new_name

    def undo(self) -> None:
        self._node.name = self._old_name

    def description(self) -> str:
        return f"Přejmenovat na {self._new_name}"


class MoveNodeCommand(Command):
    """Přesun uzlu na jiného rodiče."""

    def __init__(
        self,
        node: SceneNode,
        new_parent: SceneNode,
        index: int = -1,
    ) -> None:
        self._node = node
        self._new_parent = new_parent
        self._new_index = index
        self._old_parent: SceneNode | None = node.parent
        self._old_index: int = -1

    def execute(self) -> None:
        if self._old_parent:
            self._old_index = self._old_parent.children.index(self._node)
            self._old_parent.remove_child(self._node)
        if self._new_index >= 0:
            self._new_parent.children.insert(self._new_index, self._node)
            self._node.parent = self._new_parent
        else:
            self._new_parent.add_child(self._node)

    def undo(self) -> None:
        self._new_parent.remove_child(self._node)
        if self._old_parent:
            self._old_parent.children.insert(self._old_index, self._node)
            self._node.parent = self._old_parent

    def description(self) -> str:
        return f"Přesunout {self._node.name}"


class BatchCommand(Command):
    """Skupinový příkaz — seskupí více příkazů do jedné Undo operace."""

    def __init__(self, commands: list[Command], desc: str = "Hromadná změna") -> None:
        self._commands = commands
        self._desc = desc

    def execute(self) -> None:
        for cmd in self._commands:
            cmd.execute()

    def undo(self) -> None:
        for cmd in reversed(self._commands):
            cmd.undo()

    def description(self) -> str:
        return self._desc
