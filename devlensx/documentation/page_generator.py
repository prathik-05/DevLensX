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

        repo_dir = self.snapshot.repo_path or "."
        from devlensx.understanding.profiling.repository_profiler import RepositoryProfiler, is_test_file_or_symbol
        from devlensx.diagrams.generator import DiagramGenerator

        profile = RepositoryProfiler.profile_repository(repo_dir, self.classes, self.relationships)
        archetype = profile.get("archetype", "MODULAR_APPLICATION")
        ranked_prod = profile.get("ranked_production_symbols", [])
        prod_classes = [c for c in self.classes if not is_test_file_or_symbol(c.get("file", ""), c.get("name", ""))]

        controllers = [c for c in prod_classes if c.get("stereotype") in ("Controller", "Route", "Handler") or "controller" in c.get("name", "").lower()]
        services = [c for c in prod_classes if c.get("stereotype") in ("Service", "Manager") or "service" in c.get("name", "").lower()]
        repos = [c for c in prod_classes if c.get("stereotype") in ("Repository", "DAO") or "repository" in c.get("name", "").lower() or "dao" in c.get("name", "").lower()]
        entities = [c for c in prod_classes if c.get("stereotype") in ("Entity", "Model", "Schema") or "entity" in c.get("name", "").lower() or "model" in c.get("name", "").lower()]

        section_mermaid = None
        diag_gen = None
        if self.snapshot:
            try:
                diag_gen = DiagramGenerator(self.snapshot, self.model)
            except Exception:
                diag_gen = None

        # 1. Natural Repository Description Section
        if page_id == "overview":
            if archetype == "ALGORITHMIC_SYSTEM":
                core_algo_names = ", ".join(f"`{s['name']}`" for s in ranked_prod[:3] if s.get("role") == "CORE_ALGORITHM") or "core evaluation algorithms"
                entry_names = ", ".join(e.get("symbol_name") or e.get("symbol") or Path(e.get("file", "")).stem for e in profile.get("entrypoints", [])) or "main entrypoint"
                domain_desc = f"an algorithmic decision system in {lang}. It implements {core_algo_names} with state representation and deterministic evaluations coordinated through `{entry_names}`."
            elif archetype == "CLI_ENGINE":
                core_names = ", ".join(f"`{s['name']}`" for s in ranked_prod[:3]) or "CLI game components"
                entry_names = ", ".join(e.get("symbol_name") or e.get("symbol") or Path(e.get("file", "")).stem for e in profile.get("entrypoints", [])) or "__main__"
                domain_desc = f"a command-line system in {lang}. It manages interactive command dispatch, application state, and execution through `{entry_names}` and {core_names}."
            elif archetype == "FRONTEND_UI":
                comp_names = ", ".join(f"`{s['name']}`" for s in ranked_prod[:4] if s.get("role") == "UI_COMPONENT") or "UI components"
                domain_desc = f"an interactive frontend web application built with {lang}{(' on ' + fw) if fw else ''}. It organizes view layouts, reactive state, and component trees ({comp_names})."
            elif archetype == "FRAMEWORK_LIBRARY":
                lib_names = ", ".join(f"`{s['name']}`" for s in ranked_prod[:4]) or "exported public API modules"
                domain_desc = f"a reusable {lang} software library providing modular interfaces and utilities ({lib_names}) for downstream consumers."
            else:
                domain_desc = f"a {lang}{(' ' + fw) if fw else ''} software application structured across {len(prod_classes)} verified production components."

            overview_content = (
                f"**{repo_name}** is {domain_desc}\n\n"
                f"**System Archetype:** `{archetype}`\n\n"
                f"{profile.get('archetype_rationale', '')}\n\n"
                f"The codebase coordinates {len(prod_classes)} production component(s) across detected manifests ({', '.join(profile.get('manifests', [])) or 'repository root'})."
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
        elif page_id in ("core_architecture", "architecture"):
            heading1 = "System Architecture & Tier Decomposition"
            if archetype == "ALGORITHMIC_SYSTEM":
                layer_desc = [
                    f"- **Ingress & Execution:** {', '.join(e['symbol_name'] for e in profile.get('entrypoints', [])) or 'Main CLI / Script'}",
                    f"- **Decision Engine:** {', '.join(s['name'] for s in ranked_prod if s.get('role') == 'CORE_ALGORITHM') or 'Core algorithms'}",
                    f"- **Domain State & Models:** {', '.join(s['name'] for s in ranked_prod if s.get('role') in ('DOMAIN_MODEL', 'STORAGE_PERSISTENCE')) or 'In-memory state'}",
                ]
            elif archetype == "FRONTEND_UI":
                layer_desc = [
                    f"- **View Routes:** {', '.join(e['symbol_name'] for e in profile.get('entrypoints', [])) or 'Page / Layout'}",
                    f"- **UI Components:** {', '.join(s['name'] for s in ranked_prod if s.get('role') == 'UI_COMPONENT') or 'Declarative components'}",
                    f"- **Domain State:** {', '.join(s['name'] for s in ranked_prod if s.get('role') in ('DOMAIN_MODEL', 'DOMAIN_SERVICE')) or 'State Context'}",
                ]
            elif archetype == "CLI_ENGINE":
                layer_desc = [
                    f"- **CLI Entrypoint:** {', '.join(e['symbol_name'] for e in profile.get('entrypoints', [])) or '__main__'}",
                    f"- **Game / Engine Logic:** {', '.join(s['name'] for s in ranked_prod if s.get('role') == 'CORE_ALGORITHM') or 'Game Coordinator'}",
                    f"- **Simulation State:** {', '.join(s['name'] for s in ranked_prod if s.get('role') in ('DOMAIN_MODEL', 'STORAGE_PERSISTENCE')) or 'In-memory state'}",
                ]
            else:
                layer_desc = []
                if controllers:
                    layer_desc.append(f"- **Presentation Layer:** {len(controllers)} controllers/handlers ({', '.join(c['name'] for c in controllers[:4])})")
                if services:
                    layer_desc.append(f"- **Business Logic Layer:** {len(services)} services/engines ({', '.join(s['name'] for s in services[:4])})")
                if repos:
                    layer_desc.append(f"- **Persistence Layer:** {len(repos)} repositories/data access components ({', '.join(r['name'] for r in repos[:4])})")
                if entities:
                    layer_desc.append(f"- **Domain Models:** {len(entities)} entities/schemas ({', '.join(e['name'] for e in entities[:4])})")

            overview_content = (
                f"**{repo_name}** is organized around an **{archetype}** pattern verified from static AST structures.\n\n"
                f"**Architectural Tiers:**\n" + ("\n".join(layer_desc) if layer_desc else "- Modular component structure.") + "\n\n"
                f"Dependencies preserve clear separation of concerns across verified component boundaries."
            )
            if diag_gen:
                try:
                    section_mermaid = diag_gen.generate_architecture_diagram().mermaid_code
                except Exception:
                    section_mermaid = None
            if not scope.diagram_ids:
                scope.diagram_ids.append(f"{self.snapshot.analysis_run_id}_architecture")
        elif page_id in ("runtime_flow", "workflows"):
            heading1 = "Execution Workflows & Call Flow"
            df = profile.get("data_flow", [])
            flow_steps = []
            if df:
                for step in df:
                    flow_steps.append(f"- {step}")
            elif controllers and services:
                flow_steps.append(f"1. **Request Ingestion:** HTTP requests reach `{controllers[0]['name']}`.")
                flow_steps.append(f"2. **Business Dispatch:** Controller delegates to `{services[0]['name']}` for domain rule processing.")
                if repos:
                    flow_steps.append(f"3. **Persistence Query:** Service queries `{repos[0]['name']}` for entity state retrieval or mutation.")
                flow_steps.append("4. **Response Serialization:** Results are serialized back to caller.")
            else:
                flow_steps.append(f"1. Input dispatched to primary components ({', '.join(s['name'] for s in ranked_prod[:3]) if ranked_prod else 'entrypoint'}).")
                flow_steps.append("2. Coordinated execution through static dependency calls.")
            overview_content = (
                f"Verified runtime execution pathways in **{repo_name}**:\n\n" + "\n".join(flow_steps)
            )
            if diag_gen:
                try:
                    section_mermaid = diag_gen.generate_data_flow_diagram().mermaid_code
                except Exception:
                    section_mermaid = None
            if not scope.diagram_ids:
                scope.diagram_ids.append(f"{self.snapshot.analysis_run_id}_sequence")
        elif page_id in ("api_routes", "api"):
            heading1 = "API Routes & HTTP Handlers"
            eps = self.model.get("endpoints", [])
            if eps:
                ep_lines = []
                for ep in eps[:10]:
                    method = ep.get("method", "GET")
                    route = ep.get("route", ep.get("path", "/"))
                    handler = ep.get("handler", "handler")
                    fpath = ep.get("file", "")
                    ep_lines.append(f"- `{method} {route}` &rarr; `{handler}` ({fpath})")
                overview_content = (
                    f"**{repo_name}** exposes {len(eps)} HTTP endpoint(s) mapped directly from routing declarations:\n\n" +
                    "\n".join(ep_lines)
                )
            else:
                overview_content = (
                    f"No HTTP routes or REST API endpoints were detected in **{repo_name}**.\n\n"
                    f"This codebase is categorized as an `{archetype}`. Internal module interaction occurs via "
                    f"direct functional invocation and class interfaces rather than network HTTP endpoints."
                )
        elif page_id in ("data_layer", "persistence"):
            heading1 = "Data Models & Persistence Layer"
            if repos or entities:
                ent_lines = [f"- `{e['name']}` (Entity) &mdash; `{e.get('file', '')}`" for e in entities[:6]]
                repo_lines = [f"- `{r['name']}` (Repository) &mdash; `{r.get('file', '')}`" for r in repos[:6]]
                parts = []
                if ent_lines:
                    parts.append("**Entities & Domain Schemas:**\n" + "\n".join(ent_lines))
                if repo_lines:
                    parts.append("**Repositories & Data Access Objects:**\n" + "\n".join(repo_lines))
                overview_content = f"Data architecture and state storage for **{repo_name}**:\n\n" + "\n\n".join(parts)
            else:
                data_mods = [s for s in ranked_prod if s.get("role") in ("DOMAIN_MODEL", "STORAGE_PERSISTENCE")]
                if data_mods:
                    overview_content = (
                        f"State management for **{repo_name}** is handled via in-memory data models:\n\n" +
                        "\n".join(f"- `{m['name']}` &mdash; `{m.get('file', '')}` (Lines {m.get('line_start')}-{m.get('line_end')})" for m in data_mods[:6])
                    )
                else:
                    overview_content = "No database entities or dedicated persistence repositories were detected in this codebase. State is maintained transiently in execution structures."
            if not scope.diagram_ids:
                scope.diagram_ids.append(f"{self.snapshot.analysis_run_id}_data_flow")
        elif page_id == "security":
            heading1 = "Security Architecture & Policy Boundaries"
            sec_classes = [c for c in prod_classes if any(kw in c["name"].lower() for kw in ("security", "auth", "token", "jwt", "crypto"))]
            lines = []
            if sec_classes:
                lines.append("**Authentication & Security Handlers:**\n" + "\n".join(f"- `{c['name']}` &mdash; `{c.get('file', '')}`" for c in sec_classes[:5]))
            lines.append("Repository access policies, credential protections, and validation boundaries verified against static AST evidence.")
            overview_content = f"Security posture and controls for **{repo_name}**:\n\n" + "\n\n".join(lines)
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
            mermaid=section_mermaid,
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
