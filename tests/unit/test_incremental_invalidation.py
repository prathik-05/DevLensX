from devlensx.incremental.invalidation import InvalidationEngine
from devlensx.incremental.models import SymbolChange, ChangeType

def test_invalidation():
    changed = [SymbolChange(symbol_id="OwnerController", file_path="OwnerController.java", change_type=ChangeType.MODIFIED)]
    dep_map = {"DIRECT": ["OwnerController"], "DOWNSTREAM": ["OwnerService"], "TEST": ["OwnerControllerTest"], "CONFIG": []}
    classes = [{"name": "OwnerController", "file": "OwnerController.java"}, {"name": "OwnerService", "file": "OwnerService.java"}]
    inv = InvalidationEngine.compute_invalidated_artifacts(changed, dep_map, classes, diagrams=[{"type": "ARCHITECTURE", "nodes": [{"id": "OwnerController"}]}])
    assert "OwnerController.java" in inv.files
    assert "OwnerController" in inv.symbols
    assert "OwnerService" in inv.symbols
    assert "ARCHITECTURE" in inv.diagrams

def test_no_unnecessary_invalidation():
    changed = []
    dep_map = {"DIRECT": [], "DOWNSTREAM": [], "TEST": [], "CONFIG": []}
    inv = InvalidationEngine.compute_invalidated_artifacts(changed, dep_map, [])
    assert inv.files == []
    assert inv.diagrams == []
