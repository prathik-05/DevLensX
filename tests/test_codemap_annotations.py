"""Codemap two-pass annotation tests."""
from devlensx.codemap import annotate_stop, build_codemap_stops

MODEL = {
    "repo": "petclinic",
    "classes": [
        {"name": "OwnerController", "package": "org.example", "stereotype": "Controller", "kind": "class",
         "file": "OwnerController.java", "line_start": 10, "line_end": 60, "is_test": False,
         "methods": [{"name": "createOwner"}]},
        {"name": "OwnerService", "package": "org.example", "stereotype": "Service", "kind": "class",
         "file": "OwnerService.java", "line_start": 5, "line_end": 40, "is_test": False,
         "methods": [{"name": "save"}]},
    ],
    "relationships": [{"source": "OwnerController", "target": "OwnerService", "type": "DEPENDS_ON"}],
}


def test_two_pass_annotation_grounded():
    cls = MODEL["classes"][0]
    ann = annotate_stop("OwnerController", cls, 1, 5, MODEL, None, None)
    assert "OwnerController" in ann
    assert "#1" in ann  # rank preserved
    assert "incoming dependents" in ann


def test_stops_ordered_by_blast_radius():
    stops = build_codemap_stops(MODEL, None, "test-run", None)
    assert len(stops) >= 2
    assert stops[0]["class_name"] == "OwnerService"  # highest fan-in
    for s in stops:
        assert s["jump_link"] and "#L" in s["jump_link"]
        assert s["evidence_ref"]
