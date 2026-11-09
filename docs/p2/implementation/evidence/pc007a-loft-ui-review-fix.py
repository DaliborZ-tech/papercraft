"""Additional independent widget response-atomicity oracles after LUI01."""

import copy
from uuid import uuid4

import pytest

from archpapercraft.authoring import AuthorProject
from archpapercraft.ui.author_loft import LoftProfilesDialog

pytestmark = pytest.mark.ui


@pytest.mark.parametrize("bad_field", ["invalid_end", "collision_with_patch", "message"])
def test_entire_failed_response_is_read_only_for_draft_identity(qtbot, bad_field):
    p = AuthorProject.new()
    p.add_profile([[0, 0], [10, 0], [10, 10]], closed=False)
    p.add_profile([[0, 0], [10, 0], [10, 10]], closed=False)

    def callback(_clone, _a, _b, **params):
        params = copy.deepcopy(params)
        for row in params["correspondences"]:
            row["ruling_id"] = str(uuid4())
        params["end_ruling_id"] = str(uuid4())
        result = {"status": "EXACT", "params": params, "family": "TEST_ONLY"}
        if bad_field == "invalid_end":
            params["end_ruling_id"] = "broken"
        elif bad_field == "collision_with_patch":
            params["end_ruling_id"] = params["correspondences"][1]["id"]
        else:
            result["message"] = None
        return result

    d = LoftProfilesDialog(p, preview_function=callback)
    qtbot.addWidget(d)
    d.show()
    qtbot.waitExposed(d)
    before = p.to_dict(validate=False)
    expected = copy.deepcopy(d._parameters())
    d.confirm_pairs.setChecked(True)
    assert d.request_preview()
    qtbot.waitUntil(lambda: d._running_job is None)
    assert d.preview_result is None and not d.apply_button.isEnabled()
    assert d._parameters() == expected
    assert p.to_dict(validate=False) == before
