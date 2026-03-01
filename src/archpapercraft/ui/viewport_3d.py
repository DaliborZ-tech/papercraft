"""3D viewport widget — vykresluje scénu pomocí Qt OpenGL.

Pro MVP používá jednoduchý drátový / plošně stínovaný renderer
na QOpenGLWidget. Pokročilejší renderer (např. PBR) může nahradit později.

Funkce:
- Orbita / posuv / zoom
- Předvolby pohledu (shora, zepředu, z boku, perspektiva)
- Přepínání drátového modelu / mřížky
"""

from __future__ import annotations

import math

import numpy as np
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QMouseEvent, QWheelEvent
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtWidgets import QWidget

from archpapercraft.scene_graph.scene import Scene

try:
    from OpenGL import GL
    _GL_AVAILABLE = True
except ImportError:
    _GL_AVAILABLE = False


class Viewport3D(QOpenGLWidget):
    """Interaktivní 3D viewport s orbitou / posuvem / zoomem."""

    def __init__(self, scene: Scene | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._scene = scene or Scene()
        self._selected_node = None

        # Stav kamery (orbitální kamera)
        self._orbit_yaw = 30.0
        self._orbit_pitch = 25.0
        self._orbit_distance = 50.0
        self._target = np.array([0.0, 0.0, 0.0])
        self._pan_offset = np.array([0.0, 0.0])

        # Přepínače zobrazení
        self._show_wireframe = True
        self._show_grid = True

        # Nastavení z preferences (výchozí hodnoty)
        self._bg_color = (0.18, 0.20, 0.22)
        self._grid_step = 1.0
        self._orbit_sensitivity = 0.5
        self._pan_sensitivity = 0.05
        self._zoom_factor_in = 0.9
        self._zoom_factor_out = 1.1

        # Sledování myši
        self._last_mouse: QPoint = QPoint()
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def apply_preferences(self, vp_settings) -> None:
        """Aplikuje ViewportSettings z nastavení."""
        r, g, b = vp_settings.background_color
        self._bg_color = (r / 255.0, g / 255.0, b / 255.0)
        self._grid_step = max(0.1, vp_settings.grid_size)
        self._orbit_sensitivity = max(0.01, vp_settings.orbit_sensitivity * 0.5)
        self._pan_sensitivity = max(0.001, vp_settings.pan_sensitivity * 0.05)
        # Aktualizovat GL stav pokud je inicializováno
        if _GL_AVAILABLE and self.isValid():
            self.makeCurrent()
            GL.glClearColor(self._bg_color[0], self._bg_color[1], self._bg_color[2], 1.0)
            self.doneCurrent()
        self.update()

    def set_scene(self, scene: Scene) -> None:
        self._scene = scene
        self.update()

    def set_selected_node(self, node) -> None:
        """Nastav vybraný uzel pro zvýraznění."""
        self._selected_node = node
        self.update()

    # ── OpenGL callbacks ───────────────────────────────────────────────

    def initializeGL(self) -> None:
        if not _GL_AVAILABLE:
            return
        GL.glClearColor(self._bg_color[0], self._bg_color[1], self._bg_color[2], 1.0)
        GL.glEnable(GL.GL_DEPTH_TEST)
        GL.glEnable(GL.GL_LINE_SMOOTH)
        GL.glLineWidth(1.0)

        # Face-normal lighting
        GL.glEnable(GL.GL_LIGHTING)
        GL.glEnable(GL.GL_LIGHT0)
        GL.glEnable(GL.GL_COLOR_MATERIAL)
        GL.glColorMaterial(GL.GL_FRONT_AND_BACK, GL.GL_AMBIENT_AND_DIFFUSE)
        GL.glLightfv(GL.GL_LIGHT0, GL.GL_POSITION, [0.3, 1.0, 0.5, 0.0])
        GL.glLightfv(GL.GL_LIGHT0, GL.GL_DIFFUSE, [0.9, 0.9, 0.9, 1.0])
        GL.glLightfv(GL.GL_LIGHT0, GL.GL_AMBIENT, [0.25, 0.25, 0.28, 1.0])

    def resizeGL(self, w: int, h: int) -> None:
        if not _GL_AVAILABLE:
            return
        GL.glViewport(0, 0, w, h)
        GL.glMatrixMode(GL.GL_PROJECTION)
        GL.glLoadIdentity()

        aspect = w / max(h, 1)
        fov = 45.0
        near, far = 0.1, 5000.0
        top = near * math.tan(math.radians(fov / 2))
        right = top * aspect
        GL.glFrustum(-right, right, -top, top, near, far)

        GL.glMatrixMode(GL.GL_MODELVIEW)

    def paintGL(self) -> None:
        if not _GL_AVAILABLE:
            return
        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
        GL.glLoadIdentity()

        # Camera transform
        GL.glTranslatef(self._pan_offset[0], self._pan_offset[1], -self._orbit_distance)
        GL.glRotatef(self._orbit_pitch, 1, 0, 0)
        GL.glRotatef(self._orbit_yaw, 0, 1, 0)
        GL.glTranslatef(-self._target[0], -self._target[1], -self._target[2])

        # Kresli mřížku
        if self._show_grid:
            self._draw_grid()

        # Kresli meshe
        self._draw_meshes()

    def _draw_grid(self, size: int = 20, step: float | None = None) -> None:
        if step is None:
            step = self._grid_step
        GL.glDisable(GL.GL_LIGHTING)
        GL.glColor3f(0.35, 0.35, 0.35)
        GL.glBegin(GL.GL_LINES)
        for i in range(-size, size + 1):
            GL.glVertex3f(i * step, 0, -size * step)
            GL.glVertex3f(i * step, 0, size * step)
            GL.glVertex3f(-size * step, 0, i * step)
            GL.glVertex3f(size * step, 0, i * step)
        GL.glEnd()

        # Axes
        GL.glLineWidth(2.0)
        GL.glBegin(GL.GL_LINES)
        GL.glColor3f(1, 0, 0); GL.glVertex3f(0, 0, 0); GL.glVertex3f(3, 0, 0)
        GL.glColor3f(0, 1, 0); GL.glVertex3f(0, 0, 0); GL.glVertex3f(0, 3, 0)
        GL.glColor3f(0, 0, 1); GL.glVertex3f(0, 0, 0); GL.glVertex3f(0, 0, 3)
        GL.glEnd()
        GL.glLineWidth(1.0)
        GL.glEnable(GL.GL_LIGHTING)

    def _draw_meshes(self) -> None:
        for node in self._scene.all_mesh_nodes():
            mesh = node.mesh
            if mesh is None:
                continue

            # Přeskočit neviditelné uzly
            if hasattr(node, "visible") and not node.visible:
                continue

            is_selected = (self._selected_node is not None
                           and node.node_id == self._selected_node.node_id)

            mat = node.transform.to_matrix()
            GL.glPushMatrix()
            GL.glMultMatrixf(mat.T.astype(np.float32).flatten())

            if self._show_wireframe:
                # Drátový model — bez osvětlení
                GL.glDisable(GL.GL_LIGHTING)
                if is_selected:
                    GL.glColor3f(1.0, 0.65, 0.0)   # oranžová (výběr)
                    GL.glLineWidth(2.0)
                else:
                    GL.glColor3f(0.8, 0.85, 0.9)
                    GL.glLineWidth(1.0)
                GL.glPolygonMode(GL.GL_FRONT_AND_BACK, GL.GL_LINE)
                GL.glBegin(GL.GL_TRIANGLES)
                for face in mesh.faces:
                    for vi in face:
                        v = mesh.vertices[vi]
                        GL.glVertex3f(float(v[0]), float(v[1]), float(v[2]))
                GL.glEnd()
                GL.glLineWidth(1.0)
                GL.glEnable(GL.GL_LIGHTING)

            # Plošné stínování s normálami
            GL.glEnable(GL.GL_BLEND)
            GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)
            if is_selected:
                GL.glColor4f(1.0, 0.65, 0.0, 0.35)  # oranžový nádech
            else:
                GL.glColor4f(0.4, 0.55, 0.7, 0.45)
            GL.glPolygonMode(GL.GL_FRONT_AND_BACK, GL.GL_FILL)
            GL.glBegin(GL.GL_TRIANGLES)
            for face in mesh.faces:
                # Compute face normal for lighting
                v0 = mesh.vertices[face[0]]
                v1 = mesh.vertices[face[1]]
                v2 = mesh.vertices[face[2]]
                edge1 = v1 - v0
                edge2 = v2 - v0
                normal = np.cross(edge1, edge2)
                length = np.linalg.norm(normal)
                if length > 1e-12:
                    normal /= length
                GL.glNormal3f(float(normal[0]), float(normal[1]), float(normal[2]))
                for vi in face:
                    v = mesh.vertices[vi]
                    GL.glVertex3f(float(v[0]), float(v[1]), float(v[2]))
            GL.glEnd()
            GL.glDisable(GL.GL_BLEND)

            GL.glPopMatrix()

    # ── předvolby pohledu ──────────────────────────────────────────────

    def set_view_preset(self, preset: str) -> None:
        """Nastaví předdefinovaný pohled kamery."""
        self._pan_offset = np.array([0.0, 0.0])
        if preset == "TOP":
            self._orbit_yaw = 0.0
            self._orbit_pitch = 89.9
        elif preset == "FRONT":
            self._orbit_yaw = 0.0
            self._orbit_pitch = 0.0
        elif preset == "SIDE":
            self._orbit_yaw = 90.0
            self._orbit_pitch = 0.0
        elif preset == "PERSPECTIVE":
            self._orbit_yaw = 30.0
            self._orbit_pitch = 25.0
        self.update()

    def toggle_wireframe(self) -> None:
        """Přepne drátový režim."""
        self._show_wireframe = not self._show_wireframe
        self.update()

    def toggle_grid(self) -> None:
        """Přepne zobrazení mřížky."""
        self._show_grid = not self._show_grid
        self.update()

    # ── interakce myší ─────────────────────────────────────────────────

    def mousePressEvent(self, event: QMouseEvent) -> None:
        self._last_mouse = event.position().toPoint()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        pos = event.position().toPoint()
        dx = pos.x() - self._last_mouse.x()
        dy = pos.y() - self._last_mouse.y()

        if event.buttons() & Qt.MouseButton.MiddleButton:
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                # Pan
                self._pan_offset[0] += dx * self._pan_sensitivity
                self._pan_offset[1] -= dy * self._pan_sensitivity
            else:
                # Orbit
                self._orbit_yaw += dx * self._orbit_sensitivity
                self._orbit_pitch += dy * self._orbit_sensitivity
                self._orbit_pitch = max(-90, min(90, self._orbit_pitch))
        elif event.buttons() & Qt.MouseButton.RightButton:
            # Pan (alternative)
            self._pan_offset[0] += dx * self._pan_sensitivity
            self._pan_offset[1] -= dy * self._pan_sensitivity

        self._last_mouse = pos
        self.update()

    def wheelEvent(self, event: QWheelEvent) -> None:
        delta = event.angleDelta().y()
        factor = 0.9 if delta > 0 else 1.1
        self._orbit_distance *= factor
        self._orbit_distance = max(1.0, min(2000.0, self._orbit_distance))
        self.update()
