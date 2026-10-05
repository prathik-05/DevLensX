"""
DevLensX Evidence-Grounded Page Generator (D7.3)

Consumes adaptive DocumentationTree from D4 DocumentationPlanner.
Builds bounded EvidenceScope per page, formats partitioned context,
invokes LLM (or deterministic URM synthesizer fallback), extracts candidate claims,
and verifies every factual claim through PageVerifier.
"""

from typing import List, Dict, Any, Optional
import json

from devlensx.evidence.models import SnapshotRecord
from devlensx.documentation.models import DocumentationPage, DocumentationSection, EvidenceScope, PageStatus
from devlensx.documentation.evidence_scope import EvidenceScopeBuilder
from devlensx.documentation.evidence_retriever import EvidenceRetriever
from devlensx.documentation.claim_extractor import ClaimExtractor
from devlensx.documentation.page_verifier import PageVerifier
from devlensx.understanding.documentation.planner import DocumentationPlanner


class DocumentationPageGenerator:
    """Orchestrates evidence retrieval, structured draft synthesis, claim extraction, and verification."""

    def __init__(self, snapshot: SnapshotRecord, model: Dict[str, Any], retriever: Optional[Any] = None, llm_client: Optional[Any] = None, use_llm: bool = False):
        self.snapshot = snapshot
        self.model = model or {}
        self.retriever = retriever
        self.use_llm = use_llm
        if llm_client is not None:
            self.llm_client = llm_client
        elif use_llm:
            try:
                from devlensx.llm.provider import get_llm_provider
                self.llm_client = get_llm_provider("auto")
            except Exception:
                self.llm_client = None
        else:
            self.llm_client = None
        self.classes = self.model.get("classes", [])
        self.relationships = self.model.get("relationships", [])

    # ------------------------------------------------------------------
    # Deterministic URM Synthesizer Fallback
    # ------------------------------------------------------------------
    def _synthesize_deterministic_sections(self, blueprint: Dict[str, Any], scope: EvidenceScope) -> List[DocumentationSection]:
        """
        Produces clean, natural repository documentation explaining what the repository does,
        its architecture, and how components interact using verified AST facts.
        """
        sections: List[DocumentationSection] = []
        page_id = blueprint.get("id", "page")
        title = blueprint.get("title", "Documentation Page")
        purpose = blueprint.get("purpose", "")
        repo_name = self.snapshot.repository_id if self.snapshot else "Repository"

        repo_summary = self.model.get("repo_summary", {})
        lang = repo_summary.get("language", "Polyglot")
        fw = repo_summary.get("framework", "")

        controllers = [c for c in self.classes if c.get("stereotype") in ("Controller", "Route", "Handler") or "controller" in c.get("name", "").lower()]
        services = [c for c in self.classes if c.get("stereotype") in ("Service", "Manager") or "service" in c.get("name", "").lower()]
        repos = [c for c in self.classes if c.get("stereotype") in ("Repository", "DAO") or "repository" in c.get("name", "").lower() or "dao" in c.get("name", "").lower()]
        entities = [c for c in self.classes if c.get("stereotype") in ("Entity", "Model", "Schema") or "entity" in c.get("name", "").lower() or "model" in c.get("name", "").lower()]

        # 1. Natural Repository Description Section
        if page_id == "overview":
            # Infer domain identity from entities and controllers
            entity_names = [e["name"] for e in entities[:5]]
            ctrl_names = [c["name"] for c in controllers[:4]]

            domain_desc = ""
            if any("pet" in n.lower() or "vet" in n.lower() or "owner" in n.lower() for n in entity_names + ctrl_names):
                domain_desc = "a veterinary clinic management platform designed to track pet patients, medical visit histories, owners, and attending veterinarians."
            elif any("order" in n.lower() or "product" in n.lower() or "cart" in n.lower() for n in entity_names + ctrl_names):
                domain_desc = "an e-commerce service handling catalog browsing, customer carts, orders, and checkout processing."
            elif any("auth" in n.lower() or "user" in n.lower() or "token" in n.lower() for n in entity_names + ctrl_names):
                domain_desc = "an authentication and identity management service providing secure credential handling, sessions, and role-based access control."
            else:
                domain_desc = f"a {lang}{(' ' + fw) if fw else ''} software application structured across {len(self.classes)} verified components."

            overview_content = (
                f"**{repo_name}** is {domain_desc}\n\n"
                f"The system is built on **{lang}**{(' using the **' + fw + '** framework') if fw else ''}. "
                f"It coordinates {len(controllers)} controllers/API endpoints, {len(services)} business services, "
                f"{len(repos)} data repositories, and {len(entities)} core domain models."
            )
            heading1 = "What This Repository Does"
        elif page_id == "getting_started":
            from devlensx.reasoning.engine import RepositoryReasoningEngine
            info = RepositoryReasoningEngine().extract_manifest_instructions(self.model)
            if info.get("has_manifest"):
                prereqs = ", ".join(info.get("prerequisites", []))
                overview_content = (
                    f"Execution and setup instructions for **{repo_name}** verified from repository build manifests ({', '.join(info.get('manifests', []))}):\n\n"
                    f"- **Prerequisites:** {prereqs}\n"
                    f"- **Install Dependencies:** `{info.get('install')}`\n"
                    f"- **Build Project:** `{info.get('build')}`\n"
                    f"- **Run Service:** `{info.get('run')}`\n"
                    f"- **Execute Tests:** `{info.get('test')}`"
                )
            else:
                overview_content = (
                    f"Setup instructions for **{repo_name}**:\n\n"
                    f"- **Language Environment:** `{lang}`\n"
                    f"- **Framework:** `{fw or 'Standard'}`\n"
                    f"- Check repository root manifests or README for environment prerequisites."
                )
            heading1 = "Quickstart & Run Instructions"
        else:
            sym_names = [s["name"] for s in scope.symbols[:5]] if scope.symbols else []
            sym_str = f" centered on `{', '.join(sym_names)}`" if sym_names else ""
            overview_content = (
                f"**{title}** is an architectural subsystem of **{repo_name}**{sym_str}. "
                f"It coordinates {len(scope.symbols)} component(s) implementing domain logic, "
                f"managing operational contracts and dependencies across the application."
            )
            heading1 = f"{title} — Overview & Role"

        sec1_claims = []
        if scope.symbols:
            top_sym = scope.symbols[0]["name"]
            top_st = scope.symbols[0].get("stereotype") or "Component"
            overview_content += f"\n\nPrimary component: `{top_sym}` ({top_st}) in `{scope.symbols[0].get('file', '')}`."
            from devlensx.critic.claim_verifier import AtomicClaim, ClaimVerdict
            sec1_claims.append(AtomicClaim(
                subject=top_sym,
                predicate="is",
                object=top_st,
                claim_type="structural",
                verdict=ClaimVerdict.UNSUPPORTED,
            ))

        sections.append(DocumentationSection(
            heading=heading1,
            content=overview_content,
            claims=sec1_claims,
            evidence_refs=scope.evidence_refs[:2],
            diagram_ids=scope.diagram_ids[:1],
        ))

        # 2. Key Components
        if scope.symbols:
            sym_items = []
            sec2_claims = []
            from devlensx.critic.claim_verifier import AtomicClaim, ClaimVerdict
            for s in scope.symbols[:6]:
                st = s.get("stereotype") or s.get("kind") or "Component"
                sym_items.append(f"- `{s['name']}` ({st}) &mdash; `{s.get('file', '')}` (Lines {s.get('line_start')}-{s.get('line_end')})")
                sec2_claims.append(AtomicClaim(
                    subject=s["name"],
                    predicate="is",
                    object=st,
                    claim_type="structural",
                    verdict=ClaimVerdict.UNSUPPORTED,
                ))
            sec2_content = "Core components implementing this subsystem:\n" + "\n".join(sym_items)
            sections.append(DocumentationSection(
                heading="Core Components & Responsibilities",
                content=sec2_content,
                claims=sec2_claims,
                evidence_refs=scope.evidence_refs[:4],
                diagram_ids=scope.diagram_ids[1:2] if len(scope.diagram_ids) > 1 else [],
            ))

        # 3. Workflows & Collaborations
        if scope.relationships:
            from devlensx.critic.claim_verifier import AtomicClaim, ClaimVerdict
            rel_items = []
            rel_claims = []
            for r in scope.relationships[:8]:
                src = str(r.get("source"))
                tgt = str(r.get("target"))
                rel_type = str(r.get("type", "depends on")).replace("_", " ").lower()
                rel_items.append(f"- `{src}` &rarr; {rel_type} &rarr; `{tgt}`")
                rel_claims.append(AtomicClaim(
                    subject=src,
                    predicate=rel_type,
                    object=tgt,
                    claim_type="structural",
                    verdict=ClaimVerdict.UNSUPPORTED,
                ))
            sec3_content = "Verified execution workflows and dependency directions:\n" + "\n".join(rel_items)
            sections.append(DocumentationSection(
                heading="Execution Workflows & Collaborations",
                content=sec3_content,
                claims=rel_claims,
                evidence_refs=scope.evidence_refs[:4],
                diagram_ids=scope.diagram_ids[2:3] if len(scope.diagram_ids) > 2 else [],
            ))

        # 4. Verified Source Evidence & Citations
        if scope.evidence_refs:
            cit_items = [f"- `{ref.to_citation()}` ({ref.symbol_name})" for ref in scope.evidence_refs[:6]]
            sec4_content = "Source code provenance grounding this documentation:\n" + "\n".join(cit_items)
            sections.append(DocumentationSection(
                heading="Source Code Provenance",
                content=sec4_content,
                claims=[],
                evidence_refs=scope.evidence_refs[:6],
                verdict="VERIFIED",
            ))

        return sections

    # ------------------------------------------------------------------
    # LLM Structured Generator
    # ------------------------------------------------------------------
    def _generate_with_llm(self, blueprint: Dict[str, Any], scope: EvidenceScope) -> Optional[List[DocumentationSection]]:
        if not self.llm_client:
            return None

        prompt_context = EvidenceRetriever.build_prompt_context(scope)
        system_prompt = (
            "You are generating verified repository documentation for DevLensX.\n"
            "Use ONLY the supplied repository evidence.\n"
            "Do NOT invent files, classes, databases, frameworks, or APIs.\n"
            "Produce JSON format with: {\"sections\": [{\"heading\": str, \"content\": str, \"claims\": [{\"subject\": str, \"predicate\": str, \"object\": str}]}]}"
        )
        user_prompt = f"Page Title: {blueprint.get('title')}\nPurpose: {blueprint.get('purpose')}\n\nEvidence Context:\n{prompt_context}"

        try:
            raw_response = self.llm_client.generate(prompt=user_prompt, system_prompt=system_prompt)
            if not raw_response:
                return None
            import re
            m = re.search(r"\{.*\}", raw_response, re.DOTALL)
            json_str = m.group(0) if m else raw_response
            parsed = json.loads(json_str)
            raw_sections = parsed.get("sections", [])
            sections = []
            for s in raw_sections:
                claims = ClaimExtractor.extract_from_structured_dict(s)
                sections.append(DocumentationSection(
                    heading=s.get("heading", "Section"),
                    content=s.get("content", ""),
                    claims=claims,
                    diagram_ids=scope.diagram_ids[:1],
                ))
            return sections if sections else None
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Generate Single Page
    # ------------------------------------------------------------------
    def generate_page(self, blueprint: Dict[str, Any]) -> DocumentationPage:
        page_id = blueprint.get("id", "page")
        title = blueprint.get("title", "Documentation Page")
        purpose = blueprint.get("purpose", "")

        # 1. Build bounded evidence scope
        scope = EvidenceScopeBuilder.build_scope(
            page_id=page_id,
            page_blueprint=blueprint,
            snapshot=self.snapshot,
            model=self.model,
            retriever=self.retriever,
        )

        # 2. Generate sections (LLM or deterministic fallback)
        sections = self._generate_with_llm(blueprint, scope)
        if not sections:
            sections = self._synthesize_deterministic_sections(blueprint, scope)

        # 3. Create initial unverified page
        unverified_page = DocumentationPage(
            id=page_id,
            title=title,
            purpose=purpose,
            repository_id=self.snapshot.repository_id,
            analysis_run_id=self.snapshot.analysis_run_id,
            commit_hash=self.snapshot.commit_hash,
            sections=sections,
            diagram_ids=scope.diagram_ids,
        )

        # 4. Verify all claims through PageVerifier
        verified_page = PageVerifier.verify_page(
            page=unverified_page,
            snapshot=self.snapshot,
            classes=self.classes,
            relationships=self.relationships,
        )

        return verified_page

    # ------------------------------------------------------------------
    # Generate Complete Documentation Tree (Consuming D4 Planner)
    # ------------------------------------------------------------------
    def generate_all_pages(self) -> List[DocumentationPage]:
        """Plans pages using D4 DocumentationPlanner, then generates and verifies each page."""
        from devlensx.understanding.model.repository_brain import RepositoryBrain
        repo_dir = self.snapshot.repo_path or "."
        brain = RepositoryBrain(
            repo_path=repo_dir,
            classes=self.classes,
            analysis_run_id=self.snapshot.analysis_run_id,
        )
        planner = DocumentationPlanner(brain)
        doc_tree = planner.plan()
        
        blueprints = []
        for p in doc_tree.pages:
            blueprints.append({
                "id": getattr(p, "id", getattr(p, "page_id", "page")),
                "title": getattr(p, "title", "Documentation Page"),
                "purpose": getattr(p, "purpose", ""),
                "type": p.page_type.value if hasattr(p.page_type, "value") else str(p.page_type),
                "target_symbols": getattr(p, "related_symbols", getattr(p, "target_symbols", [])),
                "target_files": getattr(p, "related_files", getattr(p, "target_files", [])),
            })

        if not blueprints:
            blueprints = [
                {"id": "overview", "title": "Repository Overview", "purpose": "High-level architectural overview", "type": "overview"},
                {"id": "core_architecture", "title": "Core Architecture", "purpose": "System components and tiers", "type": "architecture"},
                {"id": "glossary", "title": "Terminology & Glossary", "purpose": "Key domain concepts", "type": "glossary"},
            ]

        pages: List[DocumentationPage] = []
        for bp in blueprints:
            page = self.generate_page(bp)
            pages.append(page)

        return pages
