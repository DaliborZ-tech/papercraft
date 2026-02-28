"""arch_presets — parametrické architektonické objekty.

Generátory meshí pro: Zeď, Otvor, Střechu, Gotické okno, Cibulovou báň,
Desku podlahy, Věž a Opěrný pilíř.
"""

from __future__ import annotations

from archpapercraft.core_geometry.primitives import MeshData
from archpapercraft.scene_graph.node import NodeType, SceneNode


def generate_preset_mesh(node: SceneNode) -> MeshData | None:
    """Dispečer generování meshí podle typu uzlu."""
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

    elif node.node_type == NodeType.FLOOR_SLAB:
        from archpapercraft.arch_presets.floor_slab import generate_floor_slab
        p = node.parameters
        return generate_floor_slab(
            p.get("length", 10.0),
            p.get("width", 8.0),
            p.get("thickness", 0.2),
        )

    elif node.node_type == NodeType.TOWER:
        from archpapercraft.arch_presets.tower import generate_tower
        p = node.parameters
        return generate_tower(
            shape=p.get("shape", "cylindrical"),
            radius=p.get("radius", 2.0),
            height=p.get("height", 10.0),
            sides=p.get("sides", 8),
            segments=p.get("segments", 32),
            floors=p.get("floors", 3),
            cornice_height=p.get("cornice_height", 0.3),
            cornice_overhang=p.get("cornice_overhang", 0.2),
        )

    elif node.node_type == NodeType.BUTTRESS:
        from archpapercraft.arch_presets.buttress import generate_buttress
        p = node.parameters
        return generate_buttress(
            width=p.get("width", 1.0),
            depth_bottom=p.get("depth_bottom", 2.0),
            depth_top=p.get("depth_top", 0.5),
            height=p.get("height", 5.0),
        )

    return None
