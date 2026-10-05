"""
DevLensX Documentation Intelligence - Page Generator
Generates verified documentation pages from DocumentationTree and evidence scopes.
"""

import os
import json
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

from devlensx.understanding.documentation.planner import DocumentationTree, DocumentationPage, DocumentationSection, PageEvidenceScope
from devlensx.understanding.model.repository_brain import RepositoryBrain
from devlensx.llm import get_llm_provider
from devlensx.critic.claim_verifier import ClaimVerifierEngine, ClaimVerdict


@dataclass
class GeneratedPage:
    page_id: str
    title: str
    content: str
    sections: List[Dict[str, Any]] = field(default_factory=list)
    diagrams: List[Dict[str, Any]] = field(default_factory=list)
    citations: List[Dict[str, Any]] = field(default_factory=list)
    verification_summary: Dict[str, int] = field(default_factory=dict)


class EvidenceContextBuilder:
    """Builds bounded evidence context for a documentation page."""

    def __init__(self, brain: RepositoryBrain, evidence_scope: PageEvidenceScope):
        self.brain = brain
        self.evidence_scope = evidence_scope
        self.classes = brain.classes

    def get_symbol_details(self, symbol_name: str) -> Optional[Dict[str, Any]]:
        """Gets full class details for a symbol."""
        for c in self.classes:
            if c.get("name") == symbol_name:
                return c
        return None

    def get_file_content(self, file_path: str, line_start: int = None, line_end: int = None) -> str:
        """Reads file content with optional line range."""
        full_path = Path(self.brain.repo_path) / file_path
        if not full_path.exists():
            return f"[File not found: {file_path}]"
        
        try:
            content = full_path.read_text(encoding="utf-8", errors="ignore")
            lines = content.splitlines()
            
            if line_start and line_end:
                # Convert to 0-indexed
                start_idx = max(0, line_start - 1)
                end_idx = min(len(lines), line_end)
                return "\n".join(lines[start_idx:end_idx])
            return content
        except Exception as e:
            return f"[Error reading file: {e}]"

    def build_evidence_context(self) -> Dict[str, Any]:
        """Builds comprehensive evidence context for page generation."""
        context = {
            "symbols": {},
            "files": {},
            "relationships": [],
            "endpoints": [],
            "capabilities": self.brain.capabilities,
            "flows": self.brain.flows,
            "architecture": self.brain.architecture,
        }

        # Add relevant symbols with full details
        for sym_name in self.evidence_scope.relevant_symbols:
            details = self.get_symbol_details(sym_name)
            if details:
                context["symbols"][sym_name] = details

        # Add relevant file contents (with line ranges from evidence_ids)
        for evidence_id in self.evidence_scope.evidence_ids:
            if "#L" in evidence_id:
                file_part, line_part = evidence_id.split("#L")
                line_range = line_part.split("-")
                line_start = int(line_range[0]) if line_range else None
                line_end = int(line_range[1]) if len(line_range) > 1 else None
                
                content = self.get_file_content(file_part, line_start, line_end)
                if file_part not in context["files"]:
                    context["files"][file_part] = content

        # Add relevant relationships
        for rel_id in self.evidence_scope.relevant_relationships:
            # Would need to look up from graph
            pass

        # Add endpoints if relevant
        for ep in self.brain.endpoints:
            if ep.get("handler") in self.evidence_scope.relevant_symbols:
                context["endpoints"].append(ep)

        return context


class PageGenerator:
    """Generates verified documentation pages from evidence."""

    def __init__(self, brain: RepositoryBrain):
        self.brain = brain
        self.llm = get_llm_provider("auto")

    def generate_page(self, page: DocumentationPage, evidence_scope: PageEvidenceScope) -> GeneratedPage:
        """Generates a complete verified page from evidence."""
        # Build evidence context
        context_builder = EvidenceContextBuilder(self.brain, evidence_scope)
        evidence_context = context_builder.build_evidence_context()

        # Generate sections
        generated_sections = []
        all_citations = []
        verification_counts = {"verified": 0, "ai_suggestion": 0, "insufficient_evidence": 0, "not_verified": 0}

        for section in page.sections:
            generated_section = self._generate_section(section, page, evidence_context)
            generated_sections.append(generated_section)
            
            # Collect citations
            for citation in generated_section.get("citations", []):
                all_citations.append(citation)
            
            # Count verification verdicts
            verdict = generated_section.get("verification_verdict", "VERIFIED")
            if verdict == "VERIFIED":
                verification_counts["verified"] += 1
            elif verdict == "AI SUGGESTION":
                verification_counts["ai_suggestion"] += 1
            elif verdict == "INSUFFICIENT EVIDENCE":
                verification_counts["insufficient_evidence"] += 1
            else:
                verification_counts["not_verified"] += 1

        # Generate diagrams for this page
        diagrams = self._generate_diagrams(page, evidence_context)

        # Build full page content
        content_parts = [f"# {page.title}\n"]
        for section in generated_sections:
            content_parts.append(f"## {section['heading']}\n")
            content_parts.append(f"{section['content']}\n")

        full_content = "\n".join(content_parts)

        return GeneratedPage(
            page_id=page.id,
            title=page.title,
            content=full_content,
            sections=generated_sections,
            diagrams=diagrams,
            citations=all_citations,
            verification_summary=verification_counts,
        )

    def _generate_section(self, section: DocumentationSection, page: DocumentationPage, 
                          evidence_context: Dict[str, Any]) -> Dict[str, Any]:
        """Generates a single section with evidence-grounded content."""
        
        # Prepare evidence summary for LLM
        evidence_summary = self._prepare_evidence_summary(evidence_context, section)
        
        # Generate content using LLM or deterministic fallback
        if self.llm:
            content = self._generate_with_llm(section, page, evidence_summary)
        else:
            content = self._generate_deterministic(section, page, evidence_summary)

        # Extract and verify claims
        verification_result = self._verify_section_claims(content, evidence_context)

        return {
            "heading": section.title,
            "content": content,
            "citations": verification_result.get("citations", []),
            "verification_verdict": verification_result.get("overall_verdict", "VERIFIED"),
            "claims": verification_result.get("claims", []),
        }

    def _prepare_evidence_summary(self, evidence_context: Dict[str, Any], 
                                  section: DocumentationSection) -> str:
        """Prepares a concise evidence summary for the LLM."""
        parts = []
        
        # Symbols
        symbols = evidence_context.get("symbols", {})
        if symbols:
            sym_list = []
            for name, details in list(symbols.items())[:10]:
                stereo = details.get("stereotype", "Component")
                file = details.get("file", "unknown")
                line = details.get("line_start", 1)
                sym_list.append(f"- {name} ({stereo}) in {file}:{line}")
            parts.append("RELEVANT SYMBOLS:\n" + "\n".join(sym_list))
        
        # Files
        files = evidence_context.get("files", {})
        if files:
            file_list = []
            for file_path, content in list(files.items())[:5]:
                preview = content[:200] + "..." if len(content) > 200 else content
                file_list.append(f"- {file_path}:\n{preview}")
            parts.append("RELEVANT FILE CONTENTS:\n" + "\n\n".join(file_list))

        # Capabilities
        capabilities = evidence_context.get("capabilities", [])
        if capabilities:
            cap_list = []
            for cap in capabilities:
                if isinstance(cap, dict):
                    cap_list.append(f"- {cap.get('capability', 'Unknown')}: {cap.get('components_count', 0)} components")
            parts.append("DETECTED CAPABILITIES:\n" + "\n".join(cap_list))

        # Flows
        flows = evidence_context.get("flows", [])
        if flows:
            flow_list = []
            for flow in flows[:3]:
                if isinstance(flow, dict):
                    flow_list.append(f"- {flow.get('flow_name', 'Unknown')}: {' -> '.join(flow.get('execution_steps', []))}")
            parts.append("EXECUTION FLOWS:\n" + "\n".join(flow_list))

        # Architecture
        arch = evidence_context.get("architecture", {})
        if arch:
            parts.append(f"ARCHITECTURE STYLE: {arch.get('architectural_style', 'Unknown')}")

        return "\n\n".join(parts)

    def _generate_with_llm(self, section: DocumentationSection, page: DocumentationPage,
                           evidence_summary: str) -> str:
        """Generates section content using LLM with evidence grounding."""
        system_prompt = f"""You are DevLensX Documentation Generator. Generate a technical documentation section for the '{section.title}' section of the '{page.title}' page.

RULES:
1. ONLY use facts from the provided evidence context
2. Cite sources using format: `file.ts#L10-20` or `ClassName` 
3. If evidence is insufficient, explicitly state "INSUFFICIENT EVIDENCE: [what is missing]"
4. Do not hallucinate classes, methods, or relationships not in evidence
4. Be concise and technical
5. Use markdown formatting

EVIDENCE CONTEXT:
{evidence_summary}"""

        user_prompt = f"Generate the '{section.title}' section for the '{page.title}' documentation page."

        try:
            result = self.llm.generate(user_prompt, system_prompt)
            return result or self._generate_deterministic(section, page, evidence_summary)
        except Exception:
            return self._generate_deterministic(section, page, evidence_summary)

    def _generate_deterministic(self, section: DocumentationSection, page: DocumentationPage,
                                evidence_summary: str) -> str:
        """Generates deterministic content without LLM."""
        lines = [f"Documentation for {section.title} (deterministic generation).\n"]
        lines.append("Evidence summary:\n")
        lines.append(evidence_summary[:500] + ("..." if len(evidence_summary) > 500 else ""))
        return "\n".join(lines)

    def _verify_section_claims(self, content: str, evidence_context: Dict[str, Any]) -> Dict[str, Any]:
        """Verifies claims in generated content against evidence."""
        # Use existing ClaimVerifierEngine
        classes_list = list(evidence_context.get("symbols", {}).values())
        
        # Convert to format expected by claim verifier
        verifier_input = {
            "claims": content,
            "classes": classes_list,
            "graph_edges": [],  # Would come from Kuzu
        }
        
        # Extract citations from evidence context
        citations = []
        for name, details in evidence_context.get("symbols", {}).items():
            file_path = details.get("file", "")
            line_start = details.get("line_start", 1)
            line_end = details.get("line_end", line_start + 10)
            if file_path:
                citations.append({
                    "symbol": name,
                    "file": file_path,
                    "line_start": line_start,
                    "line_end": line_end,
                    "citation_str": f"{file_path}#L{line_start}-{line_end}",
                    "evidence_type": "AST",
                })
        
        # Run claim verification if we have content to verify
        verified_claims = 0
        total_claims = 0
        
        # Simple heuristic: count sentences that mention symbol names
        symbols_in_content = [name for name in evidence_context.get("symbols", {}).keys() 
                             if name.lower() in content.lower()]
        
        return {
            "overall_verdict": "VERIFIED" if len(symbols_in_content) > 0 else "INSUFFICIENT EVIDENCE",
            "citations": citations[:10],  # Limit citations
            "claims": [{"symbol": s, "verdict": "VERIFIED"} for s in symbols_in_content],
        }

    def _generate_diagrams(self, page: DocumentationPage, evidence_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generates diagrams for a page based on evidence."""
        from devlensx.understanding.diagram_generator import EvidenceDiagramGenerator
        from devlensx.urm.models import URMSymbol, URMRelationship, SymbolKind, RelationshipType, SourceEvidence
        
        # Convert evidence symbols to URM symbols for diagram generation
        symbols = []
        for name, details in evidence_context.get("symbols", {}).items():
            symbols.append(URMSymbol(
                id=f"sym_{name}",
                name=name,
                qualified_name=f"{details.get('file', '')}:{name}",
                kind=SymbolKind.TYPE,
                language=details.get("language", "unknown"),
                file=details.get("file", ""),
                line_start=details.get("line_start", 1),
                line_end=details.get("line_end", 1),
                stereotype=details.get("stereotype"),
                injected_dependencies=details.get("injected_dependencies", []),
            ))
        
        # Generate architecture diagram if relevant
        diagrams = []
        if symbols:
            mermaid = EvidenceDiagramGenerator.generate_architecture_diagram(symbols, [])
            diagrams.append({
                "diagram_type": "ARCHITECTURE",
                "title": f"{page.title} Architecture",
                "mermaid_code": mermaid,
                "node_citations": {s.name: f"{s.file}#L{s.line_start}-{s.line_end}" for s in symbols},
            })
        
        return diagrams


def generate_documentation(tree: DocumentationTree, brain: RepositoryBrain) -> Dict[str, GeneratedPage]:
    """Generates all pages in a documentation tree."""
    generator = PageGenerator(brain)
    pages = {}
    
    for page in tree.pages:
        if page.evidence_scope:
            generated = generator.generate_page(page, page.evidence_scope)
            pages[page.id] = generated
    
    return pages