"""
DevLensX Documentation Evidence Scope Builder (D7.1)

Constructs the bounded evidence package provided to a documentation page generator.
Ensures the generator operates strictly within evidenced repository bounds.
"""

from typing import List, Dict, Any, Optional
from pathlib import Path

from devlensx.evidence.models import EvidenceRef, EvidenceType, SnapshotRecord
from devlensx.documentation.models import EvidenceScope


class EvidenceScopeBuilder:
    """Builds a bounded, immutable EvidenceScope for a specific page."""

    @staticmethod
    def build_scope(
        page_id: str,
        page_blueprint: Dict[str, Any],
        snapshot: SnapshotRecord,
        model: Dict[str, Any],
        retriever: Optional[Any] = None,
    ) -> EvidenceScope:
        repo_id = snapshot.repository_id
        run_id = snapshot.analysis_run_id
        commit_hash = snapshot.commit_hash

        all_classes = model.get("classes", [])
        all_relationships = model.get("relationships", [])
        all_endpoints = model.get("endpoints", [])
        all_configurations = model.get("configurations", [])

        target_files = page_blueprint.get("target_files", [])
        target_symbols = page_blueprint.get("target_symbols", [])

        # 1. Filter Symbols
        matched_symbols: List[Dict[str, Any]] = []
        if target_files:
            norm_targets = [f.replace("\\", "/").lower() for f in target_files]
            for c in all_classes:
                c_file = (c.get("file") or "").replace("\\", "/").lower()
                if any(t in c_file or c_file.endswith(t) for t in norm_targets):
                    matched_symbols.append(c)
        elif target_symbols:
            matched_symbols = [c for c in all_classes if c.get("name") in target_symbols]
        else:
            # Domain / Overview fallback
            matched_symbols = all_classes[:25]

        # 2. Filter Relationships
        symbol_names = set(c["name"] for c in matched_symbols)
        matched_relationships: List[Dict[str, Any]] = []
        for r in all_relationships:
            src = str(r.get("source", ""))
            tgt = str(r.get("target", ""))
            if any(s in src or s in tgt for s in symbol_names):
                matched_relationships.append(r)

        # 3. Filter Endpoints
        matched_endpoints: List[Dict[str, Any]] = []
        for ep in all_endpoints:
            if ep.get("handler") in symbol_names or not symbol_names:
                matched_endpoints.append(ep)

        # 4. Filter Configurations
        matched_configurations = all_configurations[:10]

        # 5. Build D5 EvidenceRefs
        evidence_refs: List[EvidenceRef] = []
        for sym in matched_symbols[:20]:
            file_path = (sym.get("file") or "").replace("\\", "/")
            if file_path:
                start = int(sym.get("line_start") or 1)
                end = int(sym.get("line_end") or (start + 20))
                evidence_refs.append(EvidenceRef(
                    repository_id=repo_id,
                    analysis_run_id=run_id,
                    commit_hash=commit_hash,
                    file_path=file_path,
                    line_start=start,
                    line_end=end,
                    symbol_name=sym.get("name"),
                    evidence_type=EvidenceType.AST,
                ))

        # 6. Retrieve Semantic Chunks (FAISS Context - marked as semantic, NOT proof)
        semantic_chunks: List[Dict[str, Any]] = []
        if retriever:
            try:
                query = f"{page_blueprint.get('title', '')} {' '.join(target_symbols[:3])}"
                results = retriever.retrieve(query, top_k=4)
                for r in results:
                    semantic_chunks.append({
                        "file": r.get("file", ""),
                        "snippet": r.get("snippet", ""),
                        "score": r.get("relevance_score", 0.0),
                    })
            except Exception:
                pass

        # 7. Map D6 Diagram IDs
        diagram_ids: List[str] = []
        page_type = page_blueprint.get("type", "").lower()
        if "architecture" in page_id or "architecture" in page_type:
            diagram_ids = ["ARCHITECTURE", "DEPENDENCY", "COMPONENT"]
        elif "api" in page_id or "route" in page_type:
            diagram_ids = ["DATA_FLOW", "SEQUENCE"]
        elif "component" in page_id or "module" in page_type:
            diagram_ids = ["COMPONENT", "CALL_GRAPH"]
        else:
            diagram_ids = ["DEPENDENCY"]

        return EvidenceScope(
            repository_id=repo_id,
            analysis_run_id=run_id,
            commit_hash=commit_hash,
            page_id=page_id,
            target_files=target_files,
            symbols=matched_symbols,
            relationships=matched_relationships,
            endpoints=matched_endpoints,
            configurations=matched_configurations,
            semantic_chunks=semantic_chunks,
            evidence_refs=evidence_refs,
            diagram_ids=diagram_ids,
        )
