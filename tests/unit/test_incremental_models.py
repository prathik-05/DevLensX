from devlensx.incremental.models import ChangeType, FileChange, SymbolChange, InvalidationSet, IncrementalResult

def test_change_type():
    assert ChangeType.ADDED.value == "ADDED"
    assert ChangeType.MODIFIED.value == "MODIFIED"

def test_file_change():
    fc = FileChange(path="a.java", change_type=ChangeType.ADDED)
    d = fc.to_dict()
    assert d["path"] == "a.java"

def test_symbol_change():
    sc = SymbolChange(symbol_id="Foo", file_path="Foo.java", change_type=ChangeType.MODIFIED)
    assert sc.symbol_id == "Foo"

def test_invalidation_set():
    inv = InvalidationSet(files=["a.java"], symbols=["Foo"])
    assert "a.java" in inv.files

def test_incremental_result():
    r = IncrementalResult(repository_id="r", previous_run_id="a", new_run_id="b", previous_commit="c1", new_commit="c2")
    d = r.to_dict()
    assert d["repository_id"] == "r"
    assert d["status"] == "COMPLETE"
