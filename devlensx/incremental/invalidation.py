from typing import List, Dict, Any
from devlensx.incremental.models import InvalidationSet, SymbolChange, FileChange

class InvalidationEngine:
    @staticmethod
    def compute_invalidated_artifacts(changed_symbols: List[SymbolChange], dependency_map: Dict[str, List[str]], urm_classes: List[Dict[str, Any]], diagrams: List[Dict[str, Any]] = None, wiki_pages: List[Any] = None) -> InvalidationSet:
        inv = InvalidationSet()
        # Files
        inv.files = list({s.file_path for s in changed_symbols if s.file_path})
        # Symbols
        inv.symbols = [s.symbol_id for s in changed_symbols]
        # Add downstream
        downstream = dependency_map.get("DOWNSTREAM", [])
        inv.symbols.extend(downstream)
        inv.relationships = downstream.copy()
        # Diagrams that contain changed symbols
        if diagrams:
            for d in diagrams:
                nodes = d.get("nodes") or []
                for n in nodes:
                    nid = n.get("id") or n.get("label")
                    if nid in inv.symbols:
                        inv.diagrams.append(d.get("type") or d.get("id") or "DIAGRAM")
                        break
        else:
            # Fallback: invalidate core diagrams if any symbol changed
            if inv.symbols:
                inv.diagrams = ["ARCHITECTURE", "DEPENDENCY", "CALL_GRAPH"]
        # Wiki pages
        if wiki_pages:
            for p in wiki_pages:
                # page scope check: if page symbols intersect
                scope_syms = getattr(p, "evidence_scope", None)
                if scope_syms:
                    relevant = getattr(scope_syms, "relevant_symbols", []) or []
                    if any(s in relevant for s in inv.symbols):
                        inv.wiki_pages.append(getattr(p, "id", str(p)))
                else:
                    # Fallback: if page title matches symbol
                    title = getattr(p, "title", "") or (p.get("title") if isinstance(p, dict) else "")
                    if any(s == title for s in inv.symbols):
                        inv.wiki_pages.append(title)
            if inv.symbols and not inv.wiki_pages:
                inv.wiki_pages = ["OVERVIEW", "CORE_ARCHITECTURE"]
        else:
            if inv.symbols:
                inv.wiki_pages = ["OVERVIEW", "CORE_ARCHITECTURE"]
        # Evidence & vectors
        inv.evidence = inv.symbols.copy()
        inv.vectors = inv.files.copy()
        # Deduplicate
        inv.files = sorted(set(inv.files))
        inv.symbols = sorted(set(inv.symbols))
        inv.relationships = sorted(set(inv.relationships))
        inv.diagrams = sorted(set(inv.diagrams))
        inv.wiki_pages = sorted(set(inv.wiki_pages))
        inv.evidence = sorted(set(inv.evidence))
        inv.vectors = sorted(set(inv.vectors))
        return inv
