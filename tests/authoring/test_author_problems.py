"""The compact readiness bar preserves canonical issue navigation and evidence."""

import copy

from PySide6.QtCore import Qt
from PySide6.QtTest import QSignalSpy

from archpapercraft.authoring import AuthorProject
from archpapercraft.authoring.model import Issue
from archpapercraft.ui.author_problems import AuthorProblemsPanel


def four_parts():
    project = AuthorProject.new(scale=1)
    for index in range(4):
        profile = project.add_profile([[0, 0], [20, 0], [20, 10], [0, 10]])
        project.add_surface(profile, name=f"Wall {index+1}")
    project.recompute()
    return project


def test_four_unplaced_parts_have_one_summary_and_each_remains_reachable(qtbot):
    project = four_parts()
    issues = project.validate_layout()
    assert len(issues) == 4 and {issue.code for issue in issues} == {"UNPLACED"}
    before = copy.deepcopy(project.to_dict())
    panel = AuthorProblemsPanel()
    qtbot.addWidget(panel)
    panel.show()
    panel.set_issues(issues, project)
    assert panel.issues.count() == 1
    assert panel.summary.text() == "4 díly čekají na umístění"
    assert not panel.issues.isVisible()
    observed = []
    panel.issues.itemActivated.connect(
        lambda item: observed.append(item.data(Qt.ItemDataRole.UserRole)))
    qtbot.mouseClick(panel.primary, Qt.MouseButton.LeftButton)
    qtbot.mouseClick(panel.details, Qt.MouseButton.LeftButton)
    for _ in range(3):
        qtbot.mouseClick(panel.next_part, Qt.MouseButton.LeftButton)
    assert len(set(observed)) == 4 and set(observed) == {issue.id for issue in issues}
    assert project.to_dict() == before  # Navigation never silently packs or accepts anything.


def test_recompute_is_a_regular_action_request_after_selecting_its_actual_issue(qtbot):
    project = four_parts()
    pid = next(iter(project.parts))
    project.parts[pid].stale = True
    issues = project.validate_layout()
    panel = AuthorProblemsPanel()
    qtbot.addWidget(panel)
    panel.show()
    panel.set_issues(issues, project)
    actions = QSignalSpy(panel.action_requested)
    selected = []
    panel.issues.itemActivated.connect(
        lambda item: selected.append(item.data(Qt.ItemDataRole.UserRole)))
    qtbot.mouseClick(panel.primary, Qt.MouseButton.LeftButton)
    assert selected == [next(issue.id for issue in issues if issue.code == "STALE")]
    assert actions.count() == 1 and actions.at(0) == ["recompute"]
    assert project.parts[pid].stale  # The host must execute its normal guarded command.


def test_acknowledgement_does_not_hide_or_accept_another_group_member(qtbot):
    project = four_parts()
    first, second = list(project.parts)[:2]
    a = Issue("warning-a", "CONTACT", "warning", "Zkontrolujte lepení.", (first,),
              digest="first-proof", acknowledged=True)
    b = Issue("warning-b", "CONTACT", "warning", "Zkontrolujte lepení.", (second,),
              digest="second-proof")
    panel = AuthorProblemsPanel()
    qtbot.addWidget(panel)
    panel.show()
    panel.set_issues([a, b], project)
    assert panel.issues.count() == 2
    selected = []
    panel.issues.itemActivated.connect(
        lambda item: selected.append(item.data(Qt.ItemDataRole.UserRole)))
    qtbot.mouseClick(panel.primary, Qt.MouseButton.LeftButton)
    assert selected == [b.id]
    assert project.acknowledgements == {}
    assert a.digest == "first-proof" and b.digest == "second-proof"


def test_refresh_preserves_the_selected_member_when_another_problem_is_resolved(qtbot):
    project = four_parts()
    issues = project.validate_layout()
    panel = AuthorProblemsPanel()
    qtbot.addWidget(panel)
    panel.show()
    panel.set_issues(issues, project)
    panel.primary.click()
    panel.next_part.click()
    selected = panel.issues.currentItem().data(Qt.ItemDataRole.UserRole)
    removed = next(issue.id for issue in issues if issue.id != selected)
    panel.set_issues([issue for issue in issues if issue.id != removed], project)
    assert panel.issues.count() == 1
    assert panel.issues.currentItem().data(Qt.ItemDataRole.UserRole) == selected
    assert panel.summary.text() == "3 díly čekají na umístění"
