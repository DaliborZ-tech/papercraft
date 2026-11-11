# C GUIDE fault-test encoding correction

Test-only source: `84117c484aee8049f339cc602ba19d70e1e3ccba`.
Production `src` tree remains bit-identical to runtime
`67c44aefabe45b12543367f7d38046e06a6efb4f`:
`591ca8f7336051a0cd503eb2b9a24c742b71bc77`.

Independent reviewer `geometry_analysis` found that the SVG mutator's
ElementTree `encoding='utf8'` produced XML that Expat rejected for the Unicode
metadata fixture before the intended GUIDE guard. Production already writes
`utf-8`; this finding is a test-harness false-positive mechanism, not a producer
failure. The earlier 203-test run and artifacts remain unchanged. Its six SVG
fault cases alone did not demonstrate the claimed role/geometry guard and are
superseded by this corrected targeted proof.

The test writes `utf-8`, explicitly reparses each completed mutant and checks
the SVG root before publication validation. It also checks the rejection's
actual guard reason: missing/cross-role identities, extra path coverage,
reversed/moved GUIDE metrics, or changed part-CTM manufacturing tab metrics.
Malformed XML cannot satisfy those assertions. Prior-bundle byte preservation
and staging cleanup assertions remain present; no negative case was removed.

The six valid-XML GUIDE fault cases plus the actual cone-first SVG/PDF case
passed: **7 tests, 33.24 seconds**. The coupled case retains CUT, GUIDE and TABS
tiny-reserve metrics and BODY_ONLY source area checks. Ruff and diff checks pass.
JUnit: [targeted](evidence/pc007b-guide-valid-xml-test-fix.xml).

No production code, tolerance, scope or actual output artifact was changed.
The independent reviewer must recheck this test-only correction. This addendum
does not grant independent approval, actual UI/editor, novice or physical proof.
