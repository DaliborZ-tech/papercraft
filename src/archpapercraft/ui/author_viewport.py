"""OpenGL author surfaces and depth-correct picking of the same trimmed mesh."""
# ruff: noqa: N802 -- Qt event overrides use the framework's method names.

from __future__ import annotations

import math

import numpy as np
from OpenGL import GL
from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QSurfaceFormat
from PySide6.QtOpenGLWidgets import QOpenGLWidget


class AuthorViewport(QOpenGLWidget):
    surface_selected = Signal(str)
    edge_selected = Signal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        fmt = QSurfaceFormat()
        fmt.setVersion(2, 1)
        fmt.setProfile(QSurfaceFormat.OpenGLContextProfile.CompatibilityProfile)
        fmt.setDepthBufferSize(24)
        self.setFormat(fmt)
        self.project = None
        self.meshes = {}
        self.selected_surfaces = set()
        self.selected_edge = None
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
        if frame:
            self.focus_selection(all_surfaces=True)
        self.update()

    def select(self, surfaces=(), edge=None):
        self.selected_surfaces = set(surfaces)
        self.selected_edge = edge
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
                *(0.97, 0.72, 0.30) if sid in self.selected_surfaces else (0.69, 0.83, 0.77)
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
        if self.selected_edge:
            sid, eid = self.selected_edge
            edge = next(
                (e for e in self.meshes.get(sid, {}).get("boundary", []) if e["id"] == eid), None
            )
            if edge:
                GL.glDisable(GL.GL_DEPTH_TEST)
                GL.glColor3f(0.98, 0.29, 0.08)
                GL.glLineWidth(4)
                GL.glBegin(GL.GL_LINES)
                GL.glVertex3dv(edge["start"])
                GL.glVertex3dv(edge["end"])
                GL.glEnd()
        painter = QPainter(self)
        painter.setPen(QColor("#254e45"))
        painter.drawText(12, 22, "Prostor · vybraný díl se zvýrazní také na papíře")
        if not self.meshes:
            painter.drawText(12, 52, "Začněte kreslením vlastního obrysu vlevo.")
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
