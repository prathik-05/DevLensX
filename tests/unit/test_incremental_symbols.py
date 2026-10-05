from devlensx.incremental.symbol_analyzer import SymbolAnalyzer
from devlensx.incremental.models import FileChange, ChangeType

def test_map_files_to_symbols():
    classes = [
        {"name": "OwnerController", "file": "src/main/java/OwnerController.java", "is_test": False},
        {"name": "OwnerService", "file": "src/main/java/OwnerService.java", "is_test": False},
        {"name": "OwnerControllerTest", "file": "src/test/java/OwnerControllerTest.java", "is_test": True},
    ]
    fcs = [FileChange(path="src/main/java/OwnerController.java", change_type=ChangeType.MODIFIED)]
    syms = SymbolAnalyzer.map_files_to_symbols(fcs, classes)
    assert any(s.symbol_id == "OwnerController" for s in syms)
    assert not any(s.symbol_id == "OwnerService" for s in syms)

def test_added_deleted():
    old = [{"name": "A", "file": "A.java", "is_test": False}]
    new = [{"name": "A", "file": "A.java", "is_test": False}, {"name": "B", "file": "B.java", "is_test": False}]
    added = SymbolAnalyzer.detect_added_symbols(new, old)
    assert len(added) == 1 and added[0].symbol_id == "B"
    deleted = SymbolAnalyzer.detect_deleted_symbols(old, new)
    assert len(deleted) == 0
    deleted2 = SymbolAnalyzer.detect_deleted_symbols(new, old)
    assert len(deleted2) == 1

def test_no_guess():
    classes = [{"name": "Foo", "file": "Foo.java", "is_test": False}]
    fcs = [FileChange(path="Bar.java", change_type=ChangeType.MODIFIED)]
    syms = SymbolAnalyzer.map_files_to_symbols(fcs, classes)
    assert len(syms) == 0
