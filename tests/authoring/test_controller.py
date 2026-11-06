"""Command observers must see a complete, atomic history transition."""

import pytest

from archpapercraft.application.author_controller import AuthorController
from archpapercraft.authoring import ValidationError


def test_history_callback_sees_available_inverse_command_and_save_point(tmp_path):
    controller = AuthorController()
    states = []
    controller.on_change = lambda: states.append(
        (controller.can_undo, controller.can_redo, controller.dirty)
    )
    controller.new()
    controller.execute("Draw profile", lambda p: p.add_profile([[0, 0], [100, 0]], closed=False))
    controller.save(tmp_path / "own.apcraft")
    assert states[-1] == (True, False, False)
    controller.undo()
    assert states[-1] == (False, True, True)
    assert not controller.project.profiles
    controller.redo()
    assert states[-1] == (True, False, False)
    assert len(controller.project.profiles) == 1


def test_failed_command_keeps_geometry_history_and_redo():
    controller = AuthorController()
    controller.new()
    controller.execute("Profile", lambda p: p.add_profile([[0, 0], [100, 0]], closed=False))
    controller.undo()
    before = controller.project.to_dict()

    def operation(project):
        project.name = "This must roll back"
        project.add_profile([[0, 0], [0, 0]], closed=False)

    with pytest.raises(ValidationError):
        controller.execute("Invalid experiment", operation)
    assert controller.project.to_dict() == before
    assert controller.can_redo and not controller.can_undo
    controller.redo()
    assert len(controller.project.profiles) == 1
