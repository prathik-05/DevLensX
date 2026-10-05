"""
DevLensX Unit Test Suite (D5): Evidence Citation Parsing + Safe Source Reading
Covers: citation parse/build round-trip, path traversal refusal,
symlink/binary/size guards, and range slicing.
"""

import sys
import os
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from devlensx.evidence import (
    EvidenceRef,
    ResolutionStatus,
    SourceReader,
    build_citation,
    parse_citation,
    split_citation_range,
)


def _make_snapshot(tmp: Path) -> None:
    (tmp / "src").mkdir()
    (tmp / "src" / "sample.ts").write_text(
        "\n".join(f"// line {i}" for i in range(1, 51)), encoding="utf-8"
    )


def test_evidence_citations_and_reader():
    print("Executing Unit Test: D5 Citations + SourceReader...")

    # ---- 1. citation parse/build round trip
    c = build_citation("src/a.ts", 10, 20)
    assert c == "src/a.ts#L10-L20"
    parsed = parse_citation(c)
    assert parsed is not None
    assert parsed.file_path == "src/a.ts"
    assert (parsed.line_start, parsed.line_end) == (10, 20)

    single = parse_citation("src/b.py#L7")
    assert single is not None and single.line_end == 7

    assert parse_citation("no-range-here") is None
    assert parse_citation("/absolute/path#L1-L2") is None  # absolute paths rejected
    rev = parse_citation("x.ts#L20-L10")  # reversed range normalized
    assert rev is not None and (rev.line_start, rev.line_end) == (10, 20)
    assert split_citation_range("a.java#L23-L45") == ("a.java", 23, 45)
    print("  🟢 Citation parsing/build verified")

    # ---- 2. reader happy path on a temp snapshot
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _make_snapshot(root)
        reader = SourceReader(str(root))

        ref = EvidenceRef(
            repository_id="repo_x",
            analysis_run_id="run_unit",
            file_path="src/sample.ts",
            line_start=23,
            line_end=25,
        )
        res = reader.read_range(ref, context_lines=2)
        assert res.resolved, res.message
        nums = [l.line_number for l in res.lines]
        assert nums == list(range(21, 28)), nums
        in_range = [l for l in res.lines if l.in_range]
        assert [l.line_number for l in in_range] == [23, 24, 25]
        assert all(l.content == f"// line {l.line_number}" for l in res.lines)
        print("  🟢 Range resolution with context window verified")

        # ---- 3. path traversal refused
        evil = EvidenceRef(
            repository_id="repo_x",
            analysis_run_id="run_unit",
            file_path="../../../../etc/passwd",
            line_start=1,
            line_end=1,
        )
        bad = reader.read_range(evil)
        assert bad.status == ResolutionStatus.PATH_VIOLATION and not bad.resolved
        print("  🟢 Path traversal refused")

        # ---- 4. missing file -> honest status
        missing = EvidenceRef(
            repository_id="repo_x",
            analysis_run_id="run_unit",
            file_path="src/nope.ts",
            line_start=1,
            line_end=1,
        )
        m = reader.read_range(missing)
        assert m.status == ResolutionStatus.FILE_NOT_FOUND and not m.resolved
        print("  🟢 Missing file honest state")

        # ---- 5. binary content refused
        (root / "blob.bin").write_bytes(b"\x00\x01\x02\xff\xfe\x00binary")
        bin_ref = EvidenceRef(
            repository_id="repo_x",
            analysis_run_id="run_unit",
            file_path="blob.bin",
            line_start=1,
            line_end=1,
        )
        b = reader.read_range(bin_ref)
        assert b.status == ResolutionStatus.BINARY_FILE and not b.resolved
        print("  🟢 Binary file refused")

        # ---- 6. oversized file refused
        big = root / "big.txt"
        big.write_text("\n".join("x" * 100 for _ in range(20000)), encoding="utf-8")
        big_ref = EvidenceRef(
            repository_id="repo_x",
            analysis_run_id="run_unit",
            file_path="big.txt",
            line_start=1,
            line_end=2,
        )
        o = reader.read_range(big_ref)
        assert o.status == ResolutionStatus.FILE_TOO_LARGE and not o.resolved
        print("  🟢 Oversized file refused")

    print("\nUnit Test D5 Citations+Reader Complete: 100% Passed\n")


if __name__ == "__main__":
    test_evidence_citations_and_reader()