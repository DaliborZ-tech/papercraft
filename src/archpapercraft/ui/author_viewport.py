"""OpenGL author surfaces and depth-correct picking of the same trimmed mesh."""
# ruff: noqa: N802 -- Qt event overrides use the framework's method names.

from __future__ import annotations

import math

import numpy as np
from OpenGL import GL
from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QSurfaceFormat
from PySide6.QtOpenGLWidgets import QOpenGLWidget

from archpapercraft.authoring import ValidationError


class AuthorViewport(QOpenGLWidget):
    surface_selected = Signal(str)
    edge_selected = Signal(str, str)
    profile_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        fmt = QSurfaceFormat()
        fmt.setVersion(2, 1)
        fmt.setProfile(QSurfaceFormat.OpenGLContextProfile.CompatibilityProfile)
        fmt.setDepthBufferSize(24)
        self.setFormat(fmt)
        self.project = None
        self.meshes = {}
        self.profile_paths = {}
        self.profile_problems = {}
        self.selected_profile = None
        self.selected_surfaces = set()
        self.selected_edge = None
        self.relation = None
        self.relation_paths = []
        self.relation_status = ""
        self.related_surfaces = set()
        self.yaw, self.pitch, self.span = 30.0, 55.0, 6000.0
        self.center, self.pan = np.zeros(3), np.zeros(2)
        self._last = QPointF()
        self.setMinimumSize(220, 200)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def set_project(self, project, *, frame=False):
        self.project = project
        self.meshes = (
            {sid: project.world_geometry(sid) for sid in project.surfaces} if project else {}
        )
        used = ({p for s in project.surfaces.values() for p in s.source_profile_ids()}
                if project else set())
        loft_sources = ({p for s in project.surfaces.values() if s.kind == "ruled_loft"
                         for p in s.source_profile_ids()} if project else set())
        self.profile_paths, self.profile_problems = {}, {}
        for pid, profile in project.profiles.items() if project else []:
            if pid not in used or pid in loft_sources:
                try:
                    points = project.profile_outline(pid)
                    self.profile_paths[pid] = profile.plane.world(points).tolist()
                except ValidationError as exc:
                    self.profile_problems[pid] = str(exc)
        if frame:
            self.focus_selection(all_surfaces=True)
        self.select_relation(self.relation)
        self.update()

    def select(self, surfaces=(), edge=None):
        self.selected_surfaces = set(surfaces)
        self.selected_edge = edge
        self.update()

    def select_profile(self, identity):
        self.selected_profile = identity
        self.update()

    def select_relation(self, relation):
        self.relation = relation
        self.relation_paths, self.relation_status = [], ""
        self.related_surfaces = set()
        if not self.project or not relation:
            self.update()
            return
        kind, identity = relation
        project = self.project
        try:
            if kind == "attachment":
                record = project.attachments[identity]
                self.related_surfaces = {record.source_surface_id, record.target_surface_id}
                geometry = project.attachment_geometry(identity)
                if not geometry["valid"]:
                    self.relation_status = "Připojení potřebuje opravu; vyberte problém dole."
                    self.update()
                    return
                source = geometry["source_world"]
                self.relation_paths.append((source, record.source_edge_id is None, "#bd5d00"))
                if record.target_region_uv:
                    world = project._surface_world_points(
                        record.target_surface_id, record.target_region_uv
                    ).tolist()
                    self.relation_paths.append((world, True, "#975ca8"))
                connector_id = record.connector_id
            elif kind == "joint":
                record = project.joints[identity]
                self.related_surfaces = {record.surface_a, record.surface_b}
                connector_id = record.connector_id
            else:
                self.relation = None
                self.update()
                return
            if connector_id:
                connector = project.connector_geometry(connector_id)
                for tab in connector["tabs"]:
                    world = tab.get("folded_world")
                    if world is None:
                        world = project._surface_world_points(
                            tab["receiver_surface_id"],
                            np.asarray(tab["footprint_uv_mm"]) / project.scale,
                        ).tolist()
                    self.relation_paths.append((world, True, "#a75800"))
            if self.relation_paths:
                self.relation_status = "Připojovací čára / lepicí oblast a ohnuté chlopně"
        except (ValidationError, KeyError):
            self.relation_paths = []
            self.relation_status = "Připojení potřebuje opravu; vyberte problém dole."
        self.update()

    def camera(self):
        yaw, pitch = np.radians([self.yaw, -self.pitch])
        c, s, a, b = math.cos(yaw), math.sin(yaw), math.cos(pitch), math.sin(pitch)
        rotation = np.array([[1, 0, 0], [0, a, -b], [0, b, a]]) @ np.array(
            [[c, -s, 0], [s, c, 0], [0, 0, 1]]
        )
        view = np.eye(4)
        view[:3, :3] = rotation
        view[:3, 3] = -rotation @ self.center
        view[:2, 3] += self.pan
        aspect = max(self.width() / max(self.height(), 1), 0.1)
        projection = np.diag([1 / (self.span * aspect), 1 / self.span, -1 / (10 * self.span), 1])
        return projection, view

    def project_points(self, points):
        points = np.asarray(points, dtype=float)
        projection, view = self.camera()
        hom = np.column_stack([points, np.ones(len(points))])
        ndc = (projection @ view @ hom.T).T
        return np.column_stack(
            [(ndc[:, 0] + 1) * self.width() / 2, (1 - ndc[:, 1]) * self.height() / 2, ndc[:, 2]]
        )

    def focus_selection(self, all_surfaces=False):
        ids = (
            list(self.meshes)
            if all_surfaces or not self.selected_surfaces
            else self.selected_surfaces
        )
        arrays = [self.meshes[sid]["vertices"] for sid in ids if sid in self.meshes]
        if self.selected_profile in self.profile_paths and not all_surfaces:
            arrays = [self.profile_paths[self.selected_profile]]
        elif all_surfaces or not arrays:
            arrays.extend(self.profile_paths.values())
        if arrays:
            points = np.vstack(arrays)
            self.center = (points.min(0) + points.max(0)) / 2
            self.pan[:] = 0
            _, view = self.camera()
            extents = np.ptp(points @ view[:3, :3].T, axis=0)
            aspect = max(self.width() / max(self.height(), 1), 0.1)
            self.span = max(float(extents[1]) / 2, float(extents[0]) / (2 * aspect), 1.0) * 1.25
        self.update()

    def initializeGL(self):
        GL.glEnable(GL.GL_DEPTH_TEST)

    def paintGL(self):
        GL.glClearColor(0.94, 0.97, 0.96, 1)
        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
        GL.glEnable(GL.GL_DEPTH_TEST)
        GL.glDisable(GL.GL_LIGHTING)
        projection, view = self.camera()
        GL.glMatrixMode(GL.GL_PROJECTION)
        GL.glLoadMatrixd(projection.T)
        GL.glMatrixMode(GL.GL_MODELVIEW)
        GL.glLoadMatrixd(view.T)
        GL.glEnable(GL.GL_POLYGON_OFFSET_FILL)
        GL.glPolygonOffset(1, 1)
        for sid, mesh in self.meshes.items():
            GL.glColor3f(
                *((0.97, 0.72, 0.30) if sid in self.selected_surfaces else
                  (0.52, 0.72, 0.83) if sid in self.related_surfaces else (0.69, 0.83, 0.77))
            )
            points = np.asarray(mesh["vertices"])
            GL.glBegin(GL.GL_TRIANGLES)
            for triangle in mesh["triangles"]:
                for index in triangle:
                    GL.glVertex3dv(points[index])
            GL.glEnd()
        GL.glDisable(GL.GL_POLYGON_OFFSET_FILL)
        GL.glColor3f(0.2, 0.35, 0.30)
        GL.glLineWidth(1.5)
        for mesh in self.meshes.values():
            GL.glBegin(GL.GL_LINES)
            for edge in mesh["boundary"]:
                GL.glVertex3dv(edge["start"])
                GL.glVertex3dv(edge["end"])
            GL.glEnd()
        if self.profile_paths:
            GL.glEnable(GL.GL_LINE_STIPPLE)
            GL.glLineStipple(1, 0x00FF)
            for pid, points in self.profile_paths.items():
                GL.glColor3f(*((0.98, 0.40, 0.10) if pid == self.selected_profile
                               else (0.25, 0.45, 0.75)))
                GL.glBegin(GL.GL_LINE_LOOP if self.project.profiles[pid].closed
                           else GL.GL_LINE_STRIP)
                for point in points:
                    GL.glVertex3dv(point)
                GL.glEnd()
            GL.glDisable(GL.GL_LINE_STIPPLE)
        if self.selected_edge:
            sid, eid = self.selected_edge
            edges = [e for e in self.meshes.get(sid, {}).get("boundary", []) if e["id"] == eid]
            if edges:
                GL.glDisable(GL.GL_DEPTH_TEST)
                GL.glColor3f(0.98, 0.29, 0.08)
                GL.glLineWidth(4)
                GL.glBegin(GL.GL_LINES)
                for edge in edges:
                    GL.glVertex3dv(edge["start"])
                    GL.glVertex3dv(edge["end"])
                GL.glEnd()
        if self.relation_paths:
            GL.glDisable(GL.GL_DEPTH_TEST)
            GL.glLineWidth(3)
            for points, closed, color in self.relation_paths:
                shade = QColor(color)
                GL.glColor3f(shade.redF(), shade.greenF(), shade.blueF())
                GL.glBegin(GL.GL_LINE_LOOP if closed else GL.GL_LINE_STRIP)
                for point in points:
                    GL.glVertex3dv(point)
                GL.glEnd()
        painter = QPainter(self)
        painter.setPen(QColor("#254e45"))
        painter.drawText(12, 22, "Prostor · vybraný díl se zvýrazní také na papíře")
        if self.selected_profile in self.profile_problems:
            painter.drawText(12, 42,
                             "Náhled profilu nelze ověřit. Upravte jeho křivku nebo rozměry.")
        elif self.profile_paths:
            painter.drawText(12, 42, "Čárkovaně: zdrojové profily, zatím nejsou papírovým dílem.")
        elif not self.meshes:
            painter.drawText(12, 52, "Začněte kreslením vlastního obrysu vlevo.")
        elif self.relation_status:
            painter.drawText(12, 42, self.relation_status)
        painter.drawText(
            12, self.height() - 14, "Prostřední: oběh · Shift: posun · kolečko: zoom · F: zaměřit"
        )
        painter.end()

    @staticmethod
    def _depth_at(point, triangle):
        first, second, third = triangle[:, :2]
        matrix = np.column_stack([second - first, third - first])
        if abs(float(np.linalg.det(matrix))) < 1e-10:
            return None
        u, v = np.linalg.solve(matrix, point - first)
        if u >= -1e-8 and v >= -1e-8 and u + v <= 1 + 1e-8:
            return float((1 - u - v) * triangle[0, 2] + u * triangle[1, 2] + v * triangle[2, 2])
        return None

    def surface_at(self, point):
        point = np.array([point.x(), point.y()])
        hits = []
        for sid, mesh in self.meshes.items():
            screen = self.project_points(mesh["vertices"])
            for triangle in mesh["triangles"]:
                depth = self._depth_at(point, screen[list(triangle)])
                if depth is not None:
                    hits.append((depth, sid))
        return min(hits)[1] if hits else None

    @staticmethod
    def segment_distance(point, first, second):
        direction = second - first
        t = np.clip(
            np.dot(point - first, direction) / max(np.dot(direction, direction), 1e-15), 0, 1
        )
        return float(np.linalg.norm(point - first - t * direction))

    def mousePressEvent(self, event):
        self._last = event.position()
        if event.button() != Qt.MouseButton.LeftButton or not self.project:
            return
        sid = self.surface_at(event.position())
        if sid:
            point = np.array([event.position().x(), event.position().y()])
            candidates = []
            for edge in self.meshes[sid]["boundary"]:
                endpoints = self.project_points([edge["start"], edge["end"]])[:, :2]
                candidates.append((self.segment_distance(point, *endpoints), edge["id"]))
            if candidates and min(candidates)[0] < 7:
                self.edge_selected.emit(sid, min(candidates)[1])
            else:
                self.surface_selected.emit(sid)
        else:
            point = np.array([event.position().x(), event.position().y()])
            candidates = []
            for pid, points in self.profile_paths.items():
                screen = self.project_points(points)[:, :2]
                if self.project.profiles[pid].closed:
                    screen = np.vstack([screen, screen[0]])
                candidates.extend((self.segment_distance(point, a, b), pid)
                                  for a, b in zip(screen, screen[1:]))
            if candidates and min(candidates)[0] < 8:
                self.profile_selected.emit(min(candidates)[1])
            else:
                self.surface_selected.emit("")

    def mouseMoveEvent(self, event):
        delta = event.position() - self._last
        if event.buttons() & Qt.MouseButton.MiddleButton:
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                self.pan += (
                    np.array([delta.x(), -delta.y()]) * 2 * self.span / max(self.height(), 1)
                )
            else:
                self.yaw += delta.x() * 0.5
                self.pitch = float(np.clip(self.pitch + delta.y() * 0.5, 5, 175))
        self._last = event.position()
        self.update()

    def wheelEvent(self, event):
        self.span = float(
            np.clip(self.span * (0.9 if event.angleDelta().y() > 0 else 1.1), 0.01, 1e10)
        )
        self.update()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_F:
            self.focus_selection()
        else:
            super().keyPressEvent(event)
