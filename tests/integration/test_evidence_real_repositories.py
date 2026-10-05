"""
DevLensX Integration Test Suite (D5): Evidence Resolution Against REAL Repositories

Per D5 acceptance rules, this test requires REAL repository execution:
  1. Parse spring-petclinic through the polyglot pipeline.
  2. Register a snapshot and resolve a citation taken from an ACTUAL parsed symbol
     (OwnerController) — asserting the real source text comes back.
  3. Cross-repo isolation: a Repo-A citation must NEVER resolve against Repo B's
     snapshot (identity tuple enforcement).
  4. Stale commit detection: hash mismatch is rejected honestly.
"""

import sys
import os

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from devlensx.parser import parse_repo
from devlensx.evidence import (
    EvidenceRef,
    ResolutionStatus,
    get_snapshot_registry,
    register_snapshot,
)


def _find_class(classes, name):
    for c in classes:
        if c.get("name") == name:
            return c
    return None


def test_evidence_real_repo_resolution_and_isolation():
    print("Executing Integration Test (D5): Real-Repo Evidence + Isolation...")

    registry = get_snapshot_registry()

    # ---------- 1. Real parse: spring-petclinic ----------
    pet_model = parse_repo("eval_repos/spring-petclinic")
    pet_classes = pet_model.get("classes", [])
    owner_ctrl = _find_class(pet_classes, "OwnerController")
    assert owner_ctrl is not None, "OwnerController not found in real spring-petclinic parse"

    pet_run = "run_d5_petclinic"
    register_snapshot(
        repository_id=pet_model["repo"],
        analysis_run_id=pet_run,
        repo_path="eval_repos/spring-petclinic",
        commit_hash=None,
    )
    snap = registry.get(pet_run)
    assert snap is not None

    # Build ref from the ACTUAL parsed symbol (never hand-written)
    from devlensx.evidence.resolver import EvidenceResolver
    resolver = EvidenceResolver(registry)
    ref = EvidenceResolver.ref_from_brain_symbol(snap, owner_ctrl)
    assert ref.repository_id == "spring-petclinic"
    assert ref.analysis_run_id == pet_run
    print(f"  🟢 Ref built from real symbol: {ref.citation_str()}")

    result = resolver.resolve(ref)
    assert result.resolved, f"Real citation failed to resolve: {result.message}"
    assert result.total_lines > 0
    assert any(l.in_range for l in result.lines)

    # Assert REAL source content came back — the class declaration line must appear
    in_range_text = "\n".join(l.content for l in result.lines if l.in_range)
    assert "class OwnerController" in in_range_text, (
        f"Resolved content did not contain the real class declaration:\n{in_range_text[:300]}"
    )
    print("  🟢 Real source resolved; 'class OwnerController' present in cited range")

    # ---------- 2. Cross-repo isolation: battleship snapshot ----------
    bs_model = parse_repo("eval_repos/battleship-python")
    bs_classes = bs_model.get("classes", [])
    ai_player = _find_class(bs_classes, "AIPlayer")
    assert ai_player is not None

    bs_run = "run_d5_battleship"
    register_snapshot(
        repository_id=bs_model["repo"],
        analysis_run_id=bs_run,
        repo_path="eval_repos/battleship-python",
        commit_hash=None,
    )

    # Take the PETCLINIC citation but try to resolve it under the BATTLESHIP run:
    # identity mismatch (repository_id vs snapshot repository_id) must be blocked...
    hijacked = EvidenceRef(
        repository_id="battleship-python",
        analysis_run_id=bs_run,
        file_path=owner_ctrl["file"].replace("\\", "/"),
        line_start=int(owner_ctrl["line_start"]),
        line_end=int(owner_ctrl["line_end"]),
    )
    hijack_res = resolver.resolve(hijacked)
    assert not hijack_res.resolved
    assert hijack_res.status in (
        ResolutionStatus.PATH_VIOLATION,
        ResolutionStatus.FILE_NOT_FOUND,
    ), hijack_res.status
    print(f"  🟢 Isolation: petclinic path refused under battleship snapshot ({hijack_res.status.value})")

    # ...and the same file path under the CORRECT snapshot still resolves fine
    correct = resolver.resolve(ref)
    assert correct.resolved
    print("  🟢 Correct-snapshot resolution unaffected")

    # Also verify repository_id mismatch against wrong snapshot id
    wrong_run_ref = EvidenceRef(
        repository_id="spring-petclinic",
        analysis_run_id=bs_run,
        file_path=owner_ctrl["file"].replace("\\", "/"),
        line_start=int(owner_ctrl["line_start"]),
        line_end=int(owner_ctrl["line_end"]),
    )
    wrong_res = resolver.resolve(wrong_run_ref)
    assert not wrong_res.resolved
    assert wrong_res.status == ResolutionStatus.PATH_VIOLATION
    print("  🟢 Repo A citation blocked from resolving inside Repo B snapshot")

    # ---------- 3. Unknown snapshot -> honest state ----------
    ghost = EvidenceRef(
        repository_id="spring-petclinic",
        analysis_run_id="run_never_analyzed",
        file_path=owner_ctrl["file"].replace("\\", "/"),
        line_start=int(owner_ctrl["line_start"]),
        line_end=int(owner_ctrl["line_end"]),
    )
    ghost_res = resolver.resolve(ghost)
    assert not ghost_res.resolved
    assert ghost_res.status == ResolutionStatus.UNKNOWN_SNAPSHOT
    print("  🟢 Unknown snapshot honest rejection")

    # ---------- 4. Staleness: commit mismatch rejected ----------
    stale_ref = EvidenceRef(
        repository_id="spring-petclinic",
        analysis_run_id=pet_run,
        file_path=owner_ctrl["file"].replace("\\", "/"),
        line_start=int(owner_ctrl["line_start"]),
        line_end=int(owner_ctrl["line_end"]),
        commit_hash="deadbeef0000",
    )
    # Overwrite registered commit so hashes differ deterministically
    reg = get_snapshot_registry()
    rec = reg.get(pet_run)
    saved = rec.commit_hash
    rec.commit_hash = "cafebabe1234"
    try:
        stale_res = resolver.resolve(stale_ref)
        assert not stale_res.resolved
        assert stale_res.status == ResolutionStatus.STALE_COMMIT
        print("  🟢 Stale commit citation rejected with explicit status")
    finally:
        rec.commit_hash = saved

    # Cleanup registrations from this test process
    reg.remove(pet_run)
    reg.remove(bs_run)

    print("\nIntegration Test D5 Evidence+Isolation Complete: 100% Passed\n")


if __name__ == "__main__":
    test_evidence_real_repo_resolution_and_isolation()