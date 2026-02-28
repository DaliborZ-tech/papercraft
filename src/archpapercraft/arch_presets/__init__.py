"""arch_presets — parametric architectural objects.

Provides mesh generators for Wall, Opening, Roof, Gothic Window, and Onion Dome.
"""

from __future__ import annotations

from archpapercraft.core_geometry.primitives import MeshData
from archpapercraft.scene_graph.node import NodeType, SceneNode


def generate_preset_mesh(node: SceneNode) -> MeshData | None:
    """Dispatch mesh generation based on node type."""
    if node.node_type == NodeType.WALL:
        from archpapercraft.arch_presets.wall import generate_wall
        return generate_wall(node.parameters)

    elif node.node_type == NodeType.OPENING:
        from archpapercraft.arch_presets.opening import generate_opening
        return generate_opening(node.parameters)

    elif node.node_type == NodeType.ROOF:
        from archpapercraft.arch_presets.roof import generate_gabled_roof
        return generate_gabled_roof(node.parameters)

    elif node.node_type == NodeType.GOTHIC_WINDOW:
        from archpapercraft.arch_presets.gothic_window import generate_gothic_window
        return generate_gothic_window(node.parameters)

    elif node.node_type == NodeType.ONION_DOME:
        from archpapercraft.arch_presets.onion_dome import generate_onion_dome
        return generate_onion_dome(node.parameters)

    return None
