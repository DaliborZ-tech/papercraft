"""Testy pro commands/command_stack.py — Undo/Redo systém."""

import pytest

from archpapercraft.commands.command_stack import (
    Command,
    CommandStack,
    AddNodeCommand,
    RemoveNodeCommand,
    SetTransformCommand,
    SetParameterCommand,
    RenameNodeCommand,
    BatchCommand,
)
from archpapercraft.scene_graph.node import SceneNode, NodeType
from archpapercraft.scene_graph.scene import Scene
from archpapercraft.scene_graph.transform import Transform

import numpy as np


class TestCommandStack:
    def test_empty_stack(self):
        cs = CommandStack()
        assert not cs.can_undo
        assert not cs.can_redo
        assert cs.undo_count == 0

    def test_execute_and_undo(self):
        scene = Scene()
        node = SceneNode(name="Test", node_type=NodeType.PRIMITIVE_BOX)
        cmd = AddNodeCommand(scene, scene.root, node)
        cs = CommandStack()
        cs.execute(cmd)
        assert len(scene.root.children) == 1
        assert cs.can_undo
        cs.undo()
        assert len(scene.root.children) == 0
        assert not cs.can_undo

    def test_redo(self):
        scene = Scene()
        node = SceneNode(name="Test", node_type=NodeType.PRIMITIVE_BOX)
        cmd = AddNodeCommand(scene, scene.root, node)
        cs = CommandStack()
        cs.execute(cmd)
        cs.undo()
        assert cs.can_redo
        cs.redo()
        assert len(scene.root.children) == 1

    def test_max_depth(self):
        cs = CommandStack(max_depth=3)
        scene = Scene()
        for i in range(5):
            node = SceneNode(name=f"N{i}", node_type=NodeType.PRIMITIVE_BOX)
            cs.execute(AddNodeCommand(scene, scene.root, node))
        assert cs.undo_count == 3

    def test_clear(self):
        cs = CommandStack()
        scene = Scene()
        node = SceneNode(name="X", node_type=NodeType.PRIMITIVE_BOX)
        cs.execute(AddNodeCommand(scene, scene.root, node))
        cs.clear()
        assert not cs.can_undo
        assert not cs.can_redo

    def test_on_change_callback(self):
        calls = []
        cs = CommandStack(on_change=lambda: calls.append(1))
        scene = Scene()
        node = SceneNode(name="X", node_type=NodeType.PRIMITIVE_BOX)
        cs.execute(AddNodeCommand(scene, scene.root, node))
        assert len(calls) == 1
        cs.undo()
        assert len(calls) == 2


class TestRenameCommand:
    def test_rename_undo(self):
        node = SceneNode(name="Old", node_type=NodeType.PRIMITIVE_BOX)
        cmd = RenameNodeCommand(node, "New")
        cmd.execute()
        assert node.name == "New"
        cmd.undo()
        assert node.name == "Old"


class TestSetParameterCommand:
    def test_set_param(self):
        node = SceneNode(name="Box", node_type=NodeType.PRIMITIVE_BOX,
                         parameters={"dx": 1.0})
        cmd = SetParameterCommand(node, "dx", 5.0)
        cmd.execute()
        assert node.parameters["dx"] == 5.0
        cmd.undo()
        assert node.parameters["dx"] == 1.0


class TestBatchCommand:
    def test_batch(self):
        scene = Scene()
        n1 = SceneNode(name="A", node_type=NodeType.PRIMITIVE_BOX)
        n2 = SceneNode(name="B", node_type=NodeType.PRIMITIVE_BOX)
        cmds = [
            AddNodeCommand(scene, scene.root, n1),
            AddNodeCommand(scene, scene.root, n2),
        ]
        batch = BatchCommand(cmds, "Add two")
        batch.execute()
        assert len(scene.root.children) == 2
        batch.undo()
        assert len(scene.root.children) == 0
