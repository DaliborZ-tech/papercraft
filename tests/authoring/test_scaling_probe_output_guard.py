"""Rejected native diagnostics must preserve existing evidence byte for byte."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2]/"tools/authoring/desktop_scaling_probe.py"


def test_existing_scaling_evidence_is_preserved_on_early_rejection(tmp_path):
    trace = tmp_path/"scaling-observations.json"
    original = b'{"older_actual_trace":true}\n'
    trace.write_bytes(original)
    result = subprocess.run([sys.executable, str(SCRIPT), "--scale", "1.5",
                             "--expected-sha", "wrong-sha", "--output", str(tmp_path)],
                            capture_output=True)
    assert result.returncode != 0 and b"fresh directory" in result.stderr
    assert trace.read_bytes() == original
    assert {p.name for p in tmp_path.iterdir()} == {trace.name}


@pytest.mark.skipif(os.name != "nt", reason="Actual native Windows proof source guard")
def test_wrong_source_cannot_create_a_scaling_output_or_trace(tmp_path):
    output = tmp_path/"not-owned"
    result = subprocess.run([sys.executable, str(SCRIPT), "--scale", "1.5",
                             "--expected-sha", "wrong-sha", "--output", str(output)],
                            capture_output=True)
    assert result.returncode != 0 and b"Expected reviewed source" in result.stderr
    assert not output.exists()
