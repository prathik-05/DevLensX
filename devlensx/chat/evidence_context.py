"""Evidence consolidation with explicit trust levels and query-aware retrieval.
Deterministic evidence (URM/Kuzu/D5/D6) can prove claims; FAISS cannot.
"""

import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from devlensx.evidence.models import SnapshotRecord, EvidenceRef, EvidenceType
from devlensx.evidence.source_reader import SourceReader
from devlensx.chat.models import ChatEvidence, ChatContext
from devlensx.chat.context import build_context_query
from devlensx.chat.intent import classify_intent, ChatIntent
from devlensx.understanding.profiling.repository_profiler import RepositoryProfiler, is_test_file_or_symbol


def collect_evidence(
    snapshot: SnapshotRecord,
    model: Dict[str, Any],
    user_query: str,
    context: Optional[ChatContext] = None,
    top_k: int = 12,
) -> ChatEvidence:
    """Collects query-aware deterministic AST symbols, relationships, and source excerpts."""
    context_query = build_context_query(context, user_query)
    intent = classify_intent(context_query)

    repo_path = getattr(snapshot, "repo_path", None) or model.get("repo_path") or model.get("root_path") or "."
    classes = model.get("classes", [])
    relationships = model.get("relationships", [])

    # 1. Profile repository for archetype, production symbols, and entrypoints
    profile = RepositoryProfiler.profile_repository(str(repo_path), classes=classes, repo_model=model)
    archetype = profile.get("archetype", "MODULAR_APPLICATION")
    ranked_prod = profile.get("ranked_production_symbols", [])
    test_symbols = profile.get("test_symbols", [])
    entrypoints = profile.get("entrypoints", [])

    # 2. Extract query keywords
    q_lower = context_query.lower()
    stopwords = {
        "what", "how", "where", "which", "who", "when", "why", "does", "do", "did", "is", "are", "was",
        "were", "the", "a", "an", "this", "that", "these", "those", "in", "on", "at", "to", "for", "from",
        "with", "by", "about", "project", "repository", "codebase", "code", "application", "app", "system",
        "can", "could", "should", "would", "my", "your", "our", "work", "explain", "tell", "me"
    }
    raw_tokens = re.findall(r"\b[a-zA-Z0-9_]{3,}\b", q_lower)
    tokens = [t for t in raw_tokens if t not in stopwords]

    # 3. Check for specific absent capability inquiries
    tech_topics = {
        "authentication": ("auth", "login", "token", "jwt", "oauth", "password", "security"),
        "redis": ("redis",),
        "kafka": ("kafka",),
        "rabbitmq": ("rabbitmq",),
        "elasticsearch": ("elasticsearch",),
        "mongodb": ("mongodb",),
        "neo4j": ("neo4j",),
        "paymentservice": ("payment", "paymentservice", "stripe"),
        "fakecontroller": ("fakecontroller",),
        "database": ("database", "db", "datasource", "sql", "hibernate", "jpa", "jdbc", "persistence", "connection pool", "relational database"),
        "file_upload": ("upload", "multipart", "fileupload", "file upload", "attachment"),
    }
    missing_caps: List[str] = []
    for cap_name, keywords in tech_topics.items():
        if any(kw in q_lower for kw in keywords):
            found = False
            for c in classes:
                c_text = f"{c.get('name', '')} {c.get('file', '')} {c.get('docstring', '')} {c.get('stereotype', '')}".lower()
                if any(kw in c_text for kw in keywords):
                    found = True
                    break
            if not found:
                missing_caps.append(cap_name)

    # 4. Search and score symbols
    search_pool = test_symbols if intent == ChatIntent.TESTING else (ranked_prod or [c for c in classes if not is_test_file_or_symbol(c.get("file", ""), c.get("name", ""))])
    if not search_pool and classes:
        search_pool = classes

    scored = []
    for s in search_pool:
        name = str(s.get("name", ""))
        name_low = name.lower()
        file_p = str(s.get("file", "")).replace("\\", "/").lower()
        stereo = str(s.get("stereotype", ""))
        score = 0

        # Exact and partial token matching
        for t in tokens:
            if t == name_low:
                score += 60
            elif t in name_low:
                score += 30
            elif t in file_p:
                score += 15

        # Intent-driven weighting
        if intent == ChatIntent.SECURITY:
            if any(k in name_low or k in file_p for k in ("security", "auth", "token", "jwt", "login", "permission")):
                score += 40
        elif intent == ChatIntent.DATA_FLOW or any(k in q_lower for k in ("persistence", "database", "repository", "dao")):
            if stereo in ("Repository", "DAO", "Entity", "Model", "Schema") or any(k in name_low for k in ("repo", "entity", "model", "data", "table", "schema", "owner")):
                score += 45
        elif intent in (ChatIntent.OVERVIEW, ChatIntent.ARCHITECTURE):
            if any(s.get("name") == (e.get("symbol_name") or e.get("symbol")) for e in entrypoints):
                score += 50
            elif s.get("role") in ("ENTRYPOINT", "CORE_ALGORITHM", "DOMAIN_SERVICE"):
                score += 35
            elif stereo in ("Controller", "Component", "Service"):
                score += 30
        elif intent == ChatIntent.WHERE_TO_EDIT:
            for m in s.get("methods", []):
                m_name = m.get("name", "").lower() if isinstance(m, dict) else str(m).lower()
                if any(t in m_name for t in tokens):
                    score += 20

        # Topic-specific targeted boosts
        if "theme" in q_lower and ("theme" in name_low or "theme" in file_p):
            score += 50
        if "effect" in q_lower and ("effect" in name_low or "effect" in file_p or any(w in name_low for w in ("burst", "trail", "activeweb"))):
            score += 50
        if "state" in q_lower and any(w in name_low for w in ("provider", "context", "state")):
            score += 50
        if "player" in q_lower and "player" in name_low:
            score += 50
        if "game" in q_lower and "game" in name_low:
            score += 50
        if "entry point" in q_lower or "entrypoint" in q_lower:
            if any(s.get("name") == (e.get("symbol_name") or e.get("symbol")) for e in entrypoints) or name_low in ("game", "main", "app"):
                score += 60
        if "layer" in q_lower and stereo in ("Controller", "Repository", "Service"):
            score += 40

        if score > 0:
            scored.append((score, s))

    scored.sort(key=lambda x: x[0], reverse=True)
    matched_symbols = [x[1] for x in scored[:top_k]]

    # Contextual boost: if context selected symbol is present, put it first
    if context and context.selected_symbol:
        sel = context.selected_symbol
        sel_c = next((c for c in classes if c.get("name") == sel), None)
        if sel_c and not any(s.get("name") == sel for s in matched_symbols):
            matched_symbols.insert(0, sel_c)

    # Fallback to top production symbols or entrypoints when query produces no direct matches
    if not matched_symbols:
        matched_symbols = list(ranked_prod[:top_k]) if ranked_prod else list(classes[:top_k])

    # 5. Expand 1-hop relationships (callers and callees)
    matched_names = {s.get("name", "").lower() for s in matched_symbols if s.get("name")}
    matched_rels = []
    for r in relationships:
        src = str(r.get("source", "")).split(".")[-1].lower()
        tgt = str(r.get("target", "")).split(".")[-1].lower()
        if src in matched_names or tgt in matched_names:
            matched_rels.append(r)

    # 6. Fetch Grounded Source Excerpts from Snapshot Disk
    reader = None
    if snapshot and snapshot.repo_path:
        try:
            reader = SourceReader(snapshot.repo_path)
        except Exception:
            reader = None

    source_refs = []
    source_snippets = []
    seen_refs = set()
    for s in matched_symbols[:6]:
        fpath = (s.get("file") or "").replace("\\", "/")
        if not fpath:
            continue
        start = max(1, int(s.get("line_start") or 1))
        end = max(start, int(s.get("line_end") or (start + 25)))
        ref_key = (fpath, start, end)
        if ref_key in seen_refs:
            continue
        seen_refs.add(ref_key)

        ref = EvidenceRef(
            repository_id=getattr(snapshot, "repository_id", "repo"),
            analysis_run_id=getattr(snapshot, "analysis_run_id", "run"),
            commit_hash=getattr(snapshot, "commit_hash", None),
            file_path=fpath,
            line_start=start,
            line_end=end,
            symbol_name=s.get("name"),
            evidence_type=EvidenceType.AST,
        )
        snippet_text = ""
        if reader:
            try:
                res = reader.read_range(ref, context_lines=2)
                if res.resolved and res.lines:
                    snippet_text = "\n".join(l.content for l in res.lines)
            except Exception:
                pass

        ref_dict = ref.to_dict()
        if snippet_text:
            ref_dict["snippet"] = snippet_text
            source_snippets.append({
                "symbol": s.get("name"),
                "file": fpath,
                "lines": f"{start}-{end}",
                "code": snippet_text
            })
        source_refs.append(ref_dict)

    # Fallback raw model sample if tiny repo has no files
    if not source_refs and matched_symbols:
        for s in matched_symbols[:4]:
            source_refs.append({
                "repository_id": getattr(snapshot, "repository_id", "repo"),
                "analysis_run_id": getattr(snapshot, "analysis_run_id", "run"),
                "file_path": s.get("file", ""),
                "line_start": s.get("line_start", 1),
                "line_end": s.get("line_end", 20),
                "symbol_name": s.get("name"),
            })

    return ChatEvidence(
        deterministic_symbols=matched_symbols[:top_k],
        deterministic_relationships=matched_rels[:20],
        deterministic_source_refs=source_refs,
        semantic_chunks=[],
        diagrams=[{"id": f"{getattr(snapshot, 'analysis_run_id', 'run')}_architecture"}],
        total_symbols=len(matched_symbols),
        total_relationships=len(matched_rels),
        missing_capabilities=missing_caps,
        detected_intent=intent.value if hasattr(intent, "value") else str(intent),
        archetype=archetype,
        query_matched=bool(matched_symbols or not missing_caps),
        source_snippets=source_snippets,
    )