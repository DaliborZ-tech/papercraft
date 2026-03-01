"""Abstrakce geometrického backendu — rozhraní pro modelovací operace.

Dva backendy:
- **MeshBackend** (výchozí) — čistě numpy, vždy dostupný, booleany omezené.
- **OCCBackend** — přes pythonocc-core, plné CSG (boolean union/difference/intersect).

Aplikace vybere backend automaticky podle dostupnosti, nebo jej lze vynutit.

Použití::

    from archpapercraft.core_geometry.backend import get_backend

    be = get_backend()          # automatický výběr
    be = get_backend("occ")     # explicitně OCC (vyhodí pokud chybí)
    be = get_backend("mesh")    # explicitně mesh
"""

from __future__ import annotations

import abc
import logging
from typing import Literal

import numpy as np

from archpapercraft.core_geometry.primitives import MeshData, OCC_AVAILABLE

_log = logging.getLogger(__name__)

BackendName = Literal["auto", "mesh", "occ"]


# ======================================================================
#  Abstraktní rozhraní
# ======================================================================


class GeometryBackend(abc.ABC):
    """Společné rozhraní pro geometrické operace."""

    name: str

    # ── CSG ────────────────────────────────────────────────────────────

    @abc.abstractmethod
    def boolean_union(self, a: MeshData, b: MeshData) -> MeshData: ...

    @abc.abstractmethod
    def boolean_difference(self, a: MeshData, b: MeshData) -> MeshData: ...

    @abc.abstractmethod
    def boolean_intersect(self, a: MeshData, b: MeshData) -> MeshData: ...

    @property
    @abc.abstractmethod
    def supports_csg(self) -> bool:
        """True pokud backend podporuje skutečné CSG (ne placeholder)."""
        ...


# ======================================================================
#  Mesh backend (numpy — vždy dostupný)
# ======================================================================


class MeshBackend(GeometryBackend):
    """Odlehčený backend založený na numpy meshích.

    Boolean operace: union = slepení meshů, difference/intersect jsou
    *placeholdery* (vrací ``a`` beze změny). Pro plné CSG je třeba OCC.
    """

    name = "mesh"

    @property
    def supports_csg(self) -> bool:
        return False

    def boolean_union(self, a: MeshData, b: MeshData) -> MeshData:
        offset = a.num_vertices
        verts = np.vstack([a.vertices, b.vertices])
        faces = np.vstack([a.faces, b.faces + offset])
        return MeshData(vertices=verts, faces=faces)

    def boolean_difference(self, a: MeshData, b: MeshData) -> MeshData:
        _log.warning(
            "MeshBackend: boolean_difference je placeholder — "
            "pro reálné CSG nainstalujte pythonocc-core."
        )
        return a

    def boolean_intersect(self, a: MeshData, b: MeshData) -> MeshData:
        _log.warning(
            "MeshBackend: boolean_intersect je placeholder — "
            "pro reálné CSG nainstalujte pythonocc-core."
        )
        return a


# ======================================================================
#  OCC backend (plné CSG — vyžaduje pythonocc-core)
# ======================================================================


class OCCBackend(GeometryBackend):
    """Backend s plným CSG přes OpenCascade (pythonocc-core)."""

    name = "occ"

    def __init__(self) -> None:
        if not OCC_AVAILABLE:
            raise RuntimeError(
                "OCCBackend vyžaduje pythonocc-core.  "
                "Nainstalujte: pip install archpapercraft-studio[occ]"
            )
        from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut, BRepAlgoAPI_Fuse, BRepAlgoAPI_Common
        self._Fuse = BRepAlgoAPI_Fuse
        self._Cut = BRepAlgoAPI_Cut
        self._Common = BRepAlgoAPI_Common

    @property
    def supports_csg(self) -> bool:
        return True

    def boolean_union(self, a: MeshData, b: MeshData) -> MeshData:
        shape_a = _mesh_to_occ(a)
        shape_b = _mesh_to_occ(b)
        result = self._Fuse(shape_a, shape_b).Shape()
        return _occ_to_mesh(result)

    def boolean_difference(self, a: MeshData, b: MeshData) -> MeshData:
        shape_a = _mesh_to_occ(a)
        shape_b = _mesh_to_occ(b)
        result = self._Cut(shape_a, shape_b).Shape()
        return _occ_to_mesh(result)

    def boolean_intersect(self, a: MeshData, b: MeshData) -> MeshData:
        shape_a = _mesh_to_occ(a)
        shape_b = _mesh_to_occ(b)
        result = self._Common(shape_a, shape_b).Shape()
        return _occ_to_mesh(result)


# ── OCC ↔ mesh konverze (stub — plná implementace vyžaduje tesselator) ─


def _mesh_to_occ(mesh: MeshData):  # -> TopoDS_Shape
    """Převede MeshData na OCC TopoDS_Shape (přes BRepBuilderAPI).

    POZN.: Toto je zjednodušená verze. Plná konverze by měla stavět
    BRep z trojúhelníkové sítě přes BRepBuilderAPI_Sewing.
    """
    from OCP.BRepBuilderAPI import BRepBuilderAPI_Sewing
    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakePolygon, BRepBuilderAPI_MakeFace
    from OCP.gp import gp_Pnt

    sewing = BRepBuilderAPI_Sewing(1e-6)
    for fi in range(mesh.num_faces):
        tri = mesh.faces[fi]
        pts = [gp_Pnt(*mesh.vertices[tri[j]].tolist()) for j in range(3)]
        wire_builder = BRepBuilderAPI_MakePolygon()
        for pt in pts:
            wire_builder.Add(pt)
        wire_builder.Close()
        face = BRepBuilderAPI_MakeFace(wire_builder.Wire())
        sewing.Add(face.Face())
    sewing.Perform()
    return sewing.SewedShape()


def _occ_to_mesh(shape) -> MeshData:  # shape: TopoDS_Shape
    """Převede OCC TopoDS_Shape na MeshData (triangulace)."""
    from OCP.BRepMesh import BRepMesh_IncrementalMesh
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopAbs import TopAbs_FACE
    from OCP.TopLoc import TopLoc_Location
    from OCP.BRep import BRep_Tool

    BRepMesh_IncrementalMesh(shape, 0.5)  # tesselace

    all_verts: list[list[float]] = []
    all_faces: list[list[int]] = []
    offset = 0

    explorer = TopExp_Explorer(shape, TopAbs_FACE)
    while explorer.More():
        face = explorer.Current()
        loc = TopLoc_Location()
        tri = BRep_Tool.Triangulation_s(face, loc)
        if tri is not None:
            for i in range(1, tri.NbNodes() + 1):
                pt = tri.Node(i)
                all_verts.append([pt.X(), pt.Y(), pt.Z()])
            for i in range(1, tri.NbTriangles() + 1):
                t = tri.Triangle(i)
                n1, n2, n3 = t.Get()
                all_faces.append([offset + n1 - 1, offset + n2 - 1, offset + n3 - 1])
            offset += tri.NbNodes()
        explorer.Next()

    if not all_verts:
        return MeshData(
            vertices=np.empty((0, 3), dtype=np.float64),
            faces=np.empty((0, 3), dtype=np.int32),
        )

    return MeshData(
        vertices=np.array(all_verts, dtype=np.float64),
        faces=np.array(all_faces, dtype=np.int32),
    )


# ======================================================================
#  Factory — výběr backendu
# ======================================================================

_active_backend: GeometryBackend | None = None


def get_backend(name: BackendName = "auto") -> GeometryBackend:
    """Vrátí instanci geometrického backendu.

    Parametry
    ---------
    name : ``"auto"`` | ``"mesh"`` | ``"occ"``
        ``"auto"`` → OCC pokud je dostupný, jinak mesh.
        ``"occ"``  → vyhodí RuntimeError pokud OCC chybí.
        ``"mesh"`` → vždy mesh (i když OCC je k dispozici).
    """
    global _active_backend

    if _active_backend is not None and name == "auto":
        return _active_backend

    if name == "occ":
        _active_backend = OCCBackend()
    elif name == "mesh":
        _active_backend = MeshBackend()
    else:  # auto
        if OCC_AVAILABLE:
            _active_backend = OCCBackend()
            _log.info("Geometrický backend: OCC (plné CSG)")
        else:
            _active_backend = MeshBackend()
            _log.info(
                "Geometrický backend: Mesh (bez plného CSG). "
                "Pro boolean operace doporučujeme nainstalovat pythonocc-core."
            )

    return _active_backend
