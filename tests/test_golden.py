"""Golden test: rebuild the bundle from sources/ (using committed transcripts/) and check it matches the committed okf-bundle/."""
import pytest

from build_okf import ROOT, build, compare, finalise


def test_build_has_no_errors():
    assert build(ROOT).errors == []


def test_bundle_matches_committed():
    bundle = ROOT / "okf-bundle"
    if not (bundle / "index.md").exists():
        pytest.skip("okf-bundle/ has not been built yet")
    result = build(ROOT)
    files = finalise(result.outputs, bundle, "2000-01-01T00:00:00Z")
    assert compare(files, bundle) == [], "run rh-build and review the changes in okf-bundle/"
