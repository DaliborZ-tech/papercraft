"""Testy pro rozšířenou node visibility/lock/isolate + layer."""

import numpy as np
import pytest

from archpapercraft.scene_graph.node import SceneNode, NodeType
from archpapercraft.scene_graph.scene import Scene


class TestVisibility:
    def test_default_visible(self):
        node = SceneNode(name="X", node_type=NodeType.PRIMITIVE_BOX)
        assert node.visible is True

    def test_set_visible(self):
        node = SceneNode(name="X", node_type=NodeType.PRIMITIVE_BOX)
        node.set_visible(False)
        assert node.visible is False

    def test_recursive_visibility(self):
        parent = SceneNode(name="P", node_type=NodeType.GROUP)
        child = SceneNode(name="C", node_type=NodeType.PRIMITIVE_BOX)
        parent.add_child(child)
        parent.set_visible(False, recursive=True)
        assert parent.visible is False
        assert child.visible is False


class TestLocked:
    def test_default_unlocked(self):
        node = SceneNode(name="X", node_type=NodeType.PRIMITIVE_BOX)
        assert node.locked is False

    def test_set_locked(self):
        node = SceneNode(name="X", node_type=NodeType.PRIMITIVE_BOX)
        node.set_locked(True)
        assert node.locked is True

    def test_recursive_lock(self):
        parent = SceneNode(name="P", node_type=NodeType.GROUP)
        child = SceneNode(name="C", node_type=NodeType.PRIMITIVE_BOX)
        parent.add_child(child)
        parent.set_locked(True, recursive=True)
        assert child.locked is True


class TestIsolate:
    def test_isolate(self):
        node = SceneNode(name="X", node_type=NodeType.PRIMITIVE_BOX)
        node.isolate()
        assert node.isolated is True

    def test_unisolate(self):
        node = SceneNode(name="X", node_type=NodeType.PRIMITIVE_BOX)
        node.isolate()
        node.unisolate()
        assert node.isolated is False


class TestLayer:
    def test_default_layer(self):
        node = SceneNode(name="X", node_type=NodeType.PRIMITIVE_BOX)
        assert node.layer == "default"


class TestVisibleNodes:
    def test_visible_nodes(self):
        scene = Scene()
        scene.add_node("A", NodeType.PRIMITIVE_BOX)
        scene.add_node("B", NodeType.PRIMITIVE_BOX)
        scene.root.children[1].set_visible(False)
        visible = scene.root.visible_nodes()
        names = [n.name for n in visible]
        assert "A" in names
        assert "B" not in names


class TestNewNodeTypes:
    def test_sphere_type(self):
        assert NodeType.PRIMITIVE_SPHERE is not None

    def test_torus_type(self):
        assert NodeType.PRIMITIVE_TORUS is not None

    def test_floor_slab_type(self):
        assert NodeType.FLOOR_SLAB is not None

    def test_tower_type(self):
        assert NodeType.TOWER is not None

    def test_buttress_type(self):
        assert NodeType.BUTTRESS is not None
