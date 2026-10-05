from typing import List, Dict, Any
from devlensx.incremental.models import FileChange, SymbolChange, ChangeType
from pathlib import Path

class SymbolAnalyzer:
    @staticmethod
    def map_files_to_symbols(file_changes: List[FileChange], urm_classes: List[Dict[str, Any]]) -> List[SymbolChange]:
        """Map changed files to URM symbols deterministically."""
        # Build file -> symbols map
        file_to_symbols: Dict[str, List[Dict[str, Any]]] = {}
        for c in urm_classes:
            f = (c.get("file") or "").replace("\\", "/")
            file_to_symbols.setdefault(f, []).append(c)
            # Also try without prefix
            file_to_symbols.setdefault(Path(f).name, []).append(c)

        result: List[SymbolChange] = []
        seen = set()
        for fc in file_changes:
            # Try exact match, then suffix match
            candidates = file_to_symbols.get(fc.path, [])
            if not candidates:
                # suffix match: changed file "src/main/java/Foo.java" may match "Foo.java"
                for key, syms in file_to_symbols.items():
                    if fc.path.endswith(key) or key.endswith(fc.path):
                        candidates.extend(syms)
                        break
                # Also check normalized
                if not candidates:
                    normalized = fc.path.replace("\\", "/")
                    for key in list(file_to_symbols.keys()):
                        if normalized == key or normalized.endswith("/" + key) or key.endswith("/" + normalized):
                            candidates.extend(file_to_symbols[key])
            # Deduplicate candidates
            uniq = {c["name"]: c for c in candidates}.values()
            for sym in uniq:
                sid = sym.get("name")
                if sid in seen:
                    continue
                seen.add(sid)
                result.append(SymbolChange(
                    symbol_id=sid,
                    file_path=fc.path,
                    change_type=fc.change_type,
                    symbol_name=sid,
                    is_test=bool(sym.get("is_test"))
                ))
            # If file had no symbols but was ADDED/MODIFIED, we still note as file-level change
            # but no symbol entry needed - caller will use file_changes for vector invalidation
        return result

    @staticmethod
    def detect_added_symbols(new_classes: List[Dict[str, Any]], old_classes: List[Dict[str, Any]]) -> List[SymbolChange]:
        old_names = {c["name"] for c in old_classes}
        added = []
        for c in new_classes:
            if c["name"] not in old_names:
                added.append(SymbolChange(symbol_id=c["name"], file_path=c.get("file",""), change_type=ChangeType.ADDED, symbol_name=c["name"], is_test=bool(c.get("is_test"))))
        return added

    @staticmethod
    def detect_deleted_symbols(old_classes: List[Dict[str, Any]], new_classes: List[Dict[str, Any]]) -> List[SymbolChange]:
        new_names = {c["name"] for c in new_classes}
        deleted = []
        for c in old_classes:
            if c["name"] not in new_names:
                deleted.append(SymbolChange(symbol_id=c["name"], file_path=c.get("file",""), change_type=ChangeType.DELETED, symbol_name=c["name"], is_test=bool(c.get("is_test"))))
        return deleted
