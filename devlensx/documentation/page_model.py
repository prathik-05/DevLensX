"""
DevLensX Repository Knowledge Compiler - Documentation Data Models
Defines first-class data models for Wiki pages, evidence packages, diagrams, citations, and glossary entries.
"""

from typing import List, Dict, Any, Optional


class PageCitation:
    def __init__(self, file: str, line_start: int, line_end: int, symbol_id: Optional[str] = None):
        self.file = file
        self.line_start = line_start
        self.line_end = line_end
        self.symbol_id = symbol_id
        self.citation_str = f"{file}#L{line_start}-{line_end}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file": self.file,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "symbol_id": self.symbol_id,
            "citation_str": self.citation_str
        }


class PageDiagram:
    def __init__(self, diagram_type: str, title: str, mermaid_code: str, node_citations: Dict[str, str]):
        self.diagram_type = diagram_type  # ARCHITECTURE, SEQUENCE, DEPENDENCY, STATE, DATA_FLOW
        self.title = title
        self.mermaid_code = mermaid_code
        self.node_citations = node_citations  # node_id -> "file.ts#L10-20"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "diagram_type": self.diagram_type,
            "title": self.title,
            "mermaid_code": self.mermaid_code,
            "node_citations": self.node_citations
        }


class PageSection:
    def __init__(self, heading: str, content: str, citations: List[PageCitation], verification_verdict: str = "VERIFIED"):
        self.heading = heading
        self.content = content
        self.citations = citations
        self.verification_verdict = verification_verdict

    def to_dict(self) -> Dict[str, Any]:
        return {
            "heading": self.heading,
            "content": self.content,
            "citations": [c.to_dict() for c in self.citations],
            "verification_verdict": self.verification_verdict
        }


class WikiPage:
    def __init__(self, page_id: str, title: str, order: int, sections: List[PageSection], diagrams: List[PageDiagram]):
        self.page_id = page_id
        self.title = title
        self.order = order
        self.sections = sections
        self.diagrams = diagrams

    def to_dict(self) -> Dict[str, Any]:
        return {
            "page_id": self.page_id,
            "title": self.title,
            "order": self.order,
            "sections": [s.to_dict() for s in self.sections],
            "diagrams": [d.to_dict() for d in self.diagrams]
        }


class GlossaryEntry:
    def __init__(self, term: str, definition: str, category: str, citation: PageCitation):
        self.term = term
        self.definition = definition
        self.category = category
        self.citation = citation

    def to_dict(self) -> Dict[str, Any]:
        return {
            "term": self.term,
            "definition": self.definition,
            "category": self.category,
            "citation": self.citation.to_dict()
        }
