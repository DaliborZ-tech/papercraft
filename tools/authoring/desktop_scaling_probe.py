"""Observe actual Qt input delivery during a pinned native authoring proof.

Sets only per-process Qt scaling and adds a non-consuming application event
filter. No model, camera, event or command result is injected. This is a
technical scaling diagnostic, not a novice test or an OS scaling certification.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scale", type=float, choices=[1, 1.5, 2], required=True)
    parser.add_argument("--expected-sha", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--fixture", default="C-cylinder")
    args = parser.parse_args()
    os.environ["QT_SCALE_FACTOR"] = str(args.scale)
    sys.path.insert(0, str(ROOT/"src"))
    from desktop_b_proof import run_windows
    from PySide6.QtCore import QEvent, QObject
    from PySide6.QtWidgets import QApplication

    from archpapercraft.ui.author_paper import AuthorPaperView

    records, screens, filters = [], [], []
    started = time.monotonic()

    class Observer(QObject):
        def __init__(self, paper):
            super().__init__(paper)
            self.paper = paper

        def eventFilter(self, watched, event):  # noqa: N802 -- Qt virtual method
            interesting = (QEvent.Type.Wheel, QEvent.Type.MouseButtonPress,
                           QEvent.Type.MouseButtonRelease, QEvent.Type.MouseMove)
            if event.type() in interesting and len(records) < 20000:
                try:
                    paper = self.paper
                    transform = paper.transform()
                    point = event.position()
                    center = paper.mapToScene(paper.viewport().rect().center())
                    record = dict(seconds=time.monotonic()-started, type=event.type().name,
                                  target_class=type(watched).__name__,
                                  target_name=watched.objectName(),
                                  local_point=[point.x(), point.y()],
                                  global_point=[event.globalPosition().x(),
                                                event.globalPosition().y()],
                                  modifiers=event.modifiers().value,
                                  paper_transform=[transform.m11(), transform.m12(),
                                                   transform.m21(), transform.m22(),
                                                   transform.dx(), transform.dy()],
                                  paper_center=[center.x(), center.y()],
                                  paper_viewport=[paper.viewport().width(),
                                                  paper.viewport().height()],
                                  paper_scroll=[paper.horizontalScrollBar().value(),
                                                paper.verticalScrollBar().value()])
                    if event.type() == QEvent.Type.Wheel:
                        record["angle_delta"] = [event.angleDelta().x(), event.angleDelta().y()]
                    else:
                        record["button"] = event.button().value
                    records.append(record)
                except Exception as exc:
                    records.append(dict(observation_error=type(exc).__name__+": "+str(exc)))
            return False

    original = AuthorPaperView.__init__

    def observed_init(paper, *values, **kwargs):
        original(paper, *values, **kwargs)
        app = QApplication.instance()
        for screen in app.screens():
            rect = screen.availableGeometry()
            screens.append(dict(name=screen.name(), device_pixel_ratio=screen.devicePixelRatio(),
                                logical_dpi=screen.logicalDotsPerInch(),
                                available_logical=[rect.x(), rect.y(),
                                                   rect.width(), rect.height()]))
        observer = Observer(paper)
        filters.append(observer)
        app.installEventFilter(observer)

    AuthorPaperView.__init__ = observed_init
    try:
        result = run_windows(args.output.resolve(), args.expected_sha, args.fixture)
    finally:
        AuthorPaperView.__init__ = original
        if args.output.is_dir():
            target = args.output/"scaling-observations.json"
            target.write_text(json.dumps(dict(
                requested_per_process_scale=args.scale, actual_screens=screens,
                evidence_kind="actual native input; non-consuming event filter",
                observed_new_users=0, os_scaling_certification="NOT_RUN",
                events=records), indent=2)+"\n", encoding="utf-8")
            print(json.dumps(dict(observation_file=str(target), events=len(records),
                                  sha256=hashlib.sha256(target.read_bytes()).hexdigest())))
    return result


if __name__ == "__main__":
    raise SystemExit(main())
