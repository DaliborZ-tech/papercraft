"""Správce scény — vlastní kořenový uzel a koordinuje generování meshí."""

from __future__ import annotations

from archpapercraft.core_geometry.primitives import (
    MeshData,
    make_box_mesh,
    make_cone_mesh,
    make_cylinder_mesh,
    make_sphere_mesh,
    make_torus_mesh,
)
from archpapercraft.scene_graph.node import NodeType, SceneNode


class Scene:
    """Kontejner scény nejvyšší úrovně."""

    def __init__(self) -> None:
        self.root = SceneNode(name="Scene", node_type=NodeType.GROUP)

    # ── node creation convenience ──────────────────────────────────────

    def add_node(
        self, name: str, node_type: NodeType, parent: SceneNode | None = None, **params
    ) -> SceneNode:
        node = SceneNode(name=name, node_type=node_type, parameters=dict(params))
        target = parent if parent is not None else self.root
        target.add_child(node)
        return node

    def remove_node(self, node: SceneNode) -> None:
        if node.parent:
            node.parent.remove_child(node)

    def find_node(self, node_id: str) -> SceneNode | None:
        return self.root.find_by_id(node_id)

    # ── mesh regeneration ──────────────────────────────────────────────

    def rebuild_meshes(self) -> None:
        """Walk the tree and regenerate meshes for dirty nodes."""
        for node in self.root.all_nodes():
            if node.is_dirty:
                self._generate_mesh(node)

    def _generate_mesh(self, node: SceneNode) -> None:
        """Generate (or regenerate) mesh from the node's type + parameters."""
        p = node.parameters

        if node.node_type == NodeType.PRIMITIVE_BOX:
            p.setdefault("dx", 1.0)
            p.setdefault("dy", 1.0)
            p.setdefault("dz", 1.0)
            node.mesh = make_box_mesh(p["dx"], p["dy"], p["dz"])

        elif node.node_type == NodeType.PRIMITIVE_CYLINDER:
            p.setdefault("radius", 0.5)
            p.setdefault("height", 1.0)
            p.setdefault("segments", 32)
            node.mesh = make_cylinder_mesh(p["radius"], p["height"], p["segments"])

        elif node.node_type == NodeType.PRIMITIVE_CONE:
            p.setdefault("radius_bottom", 0.5)
            p.setdefault("radius_top", 0.0)
            p.setdefault("height", 1.0)
            p.setdefault("segments", 32)
            node.mesh = make_cone_mesh(
                p["radius_bottom"], p["radius_top"], p["height"], p["segments"],
            )

        elif node.node_type == NodeType.PRIMITIVE_SPHERE:
            p.setdefault("radius", 0.5)
            p.setdefault("segments", 32)
            p.setdefault("rings", 16)
            node.mesh = make_sphere_mesh(p["radius"], p["segments"], p["rings"])

        elif node.node_type == NodeType.PRIMITIVE_TORUS:
            p.setdefault("major_radius", 1.0)
            p.setdefault("minor_radius", 0.3)
            p.setdefault("major_segments", 32)
            p.setdefault("minor_segments", 16)
            node.mesh = make_torus_mesh(
                p["major_radius"], p["minor_radius"],
                p["major_segments"], p["minor_segments"],
            )

        elif node.node_type in (
            NodeType.WALL,
            NodeType.OPENING,
            NodeType.ROOF,
            NodeType.GOTHIC_WINDOW,
            NodeType.ONION_DOME,
            NodeType.FLOOR_SLAB,
            NodeType.TOWER,
            NodeType.BUTTRESS,
        ):
            # Delegated to arch_presets module (lazy import to avoid circular)
            from archpapercraft.arch_presets import generate_preset_mesh

            node.mesh = generate_preset_mesh(node)

        elif node.node_type == NodeType.GROUP:
            pass  # groups have no own mesh

    # ── query ──────────────────────────────────────────────────────────

    def all_mesh_nodes(self) -> list[SceneNode]:
        """Return every node that has a non-None mesh."""
        return [n for n in self.root.all_nodes() if n.mesh is not None]

    def collect_meshes(self) -> list[MeshData]:
        """Return a flat list of all meshes (for export / analysis)."""
        return [n.mesh for n in self.all_mesh_nodes()]

    def collect_visible_meshes(self, world_space: bool = False) -> list[MeshData]:
        """Return meshes only from visible nodes.

        Parameters
        ----------
        world_space : bool
            If True, apply node transforms to vertices so meshes are
            in world coordinates (needed for export pipeline).
        """
        result: list[MeshData] = []
        for n in self.all_mesh_nodes():
            if not n.visible:
                continue
            if world_space:
                mat = n.transform.to_matrix()
                verts = n.mesh.vertices @ mat[:3, :3].T + mat[:3, 3]
                result.append(MeshData(vertices=verts, faces=n.mesh.faces.copy()))
            else:
                result.append(n.mesh)
        return result
