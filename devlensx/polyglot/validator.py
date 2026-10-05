import time, subprocess
from pathlib import Path
from typing import Dict, Any
from devlensx.polyglot.models import LanguageValidationRecord, LanguageStatus

LANGUAGE_CONFIG = {
    "Java": {"repo": "eval_repos/spring-petclinic", "parser": True, "adapter": True},
    "TypeScript": {"repo": "eval_repos/sp-portfolio", "parser": True, "adapter": True},
    "JavaScript": {"repo": None, "parser": True, "adapter": True},
    "Python": {"repo": "eval_repos/battleship-python", "parser": True, "adapter": True},
    "Go": {"repo": None, "parser": True, "adapter": False},
    "Rust": {"repo": None, "parser": True, "adapter": False},
    "C#": {"repo": None, "parser": True, "adapter": False},
    "C++": {"repo": None, "parser": True, "adapter": False},
}

class PolyglotValidator:
    @staticmethod
    def validate_language(language: str) -> LanguageValidationRecord:
        cfg = LANGUAGE_CONFIG.get(language, {"parser": False, "adapter": False, "repo": None})
        rec = LanguageValidationRecord(language=language, parser_available=cfg.get("parser", False), adapter_available=cfg.get("adapter", False))
        repo_path = cfg.get("repo")
        if not repo_path or not Path(repo_path).exists():
            rec.status = LanguageStatus.VALIDATION_PENDING
            return rec
        rec.real_repository = {"name": Path(repo_path).name, "path": repo_path}
        try:
            from devlensx.repository_memory import RepositoryIntelligenceEngine
            from devlensx.evidence.resolver import register_snapshot, get_snapshot_registry
            from devlensx.chat.orchestrator import store_model, ChatOrchestrator
            from devlensx.impact.analyzer import ImpactAnalyzer
            engine = RepositoryIntelligenceEngine()
            intel = engine.analyze(repo_path)
            model = intel.model
            rec.files_discovered = model.get("stats", {}).get("files_parsed", 0)
            rec.files_parsed = model.get("stats", {}).get("files_parsed", 0)
            rec.parse_failures = model.get("stats", {}).get("files_failed", 0)
            rec.symbols = len(model.get("classes", []))
            rec.relationships = intel.graph_edge_stats.get("DEPENDS_ON", 0) + intel.graph_edge_stats.get("EXTENDS", 0)
            # Evidence
            try:
                from devlensx.understanding.model.repository_brain import RepositoryBrain
                brain = RepositoryBrain(repo_path, model.get("classes", []))
                commit = None
                try:
                    r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo_path, capture_output=True, text=True, timeout=5)
                    if r.returncode==0: commit = r.stdout.strip()[:12]
                except: pass
                rec.commit_hash = commit
                snap = register_snapshot(model.get("repo", Path(repo_path).name), brain.analysis_run_id, repo_path, commit)
                store_model(brain.analysis_run_id, model)
                # Evidence resolution: create an EvidenceRef for first class
                if model.get("classes"):
                    from devlensx.evidence.resolver import EvidenceResolver
                    resolver = EvidenceResolver()
                    ref = EvidenceResolver.ref_from_brain_symbol(snap, model["classes"][0])
                    result = resolver.resolve(ref)
                    rec.evidence_resolution = result.resolved
                else:
                    rec.evidence_resolution = False
                # Wiki
                try:
                    from devlensx.documentation.page_generator import DocumentationPageGenerator
                    gen = DocumentationPageGenerator(snap, model, retriever=intel.retriever)
                    pages = gen.generate_all_pages()
                    rec.wiki_generation = len(pages) > 0
                except: rec.wiki_generation = False
                # Diagrams
                try:
                    from devlensx.diagrams.generator import generate_all_diagrams, get_diagram_store
                    generate_all_diagrams(snap, model)
                    diags = get_diagram_store().list_all(brain.analysis_run_id)
                    rec.diagram_generation = len(diags) > 0
                except: rec.diagram_generation = False
                # Chat: 3 classes
                try:
                    # Structural - lenient: answer should contain symbol and not be empty
                    sym = model['classes'][0]['name']
                    ans = ChatOrchestrator.chat(brain.analysis_run_id, f"Where is {sym}?", mode="FAST")
                    structural_ok = ans.answer and len(ans.answer) > 20 and (sym.lower() in ans.answer.lower() or any(c.verdict for c in ans.claims))
                    # Hallucination
                    ans2 = ChatOrchestrator.chat(brain.analysis_run_id, "Does this repository use Redis?", mode="FAST")
                    hall_ok = "insufficient" in ans2.answer.lower() or ans2.verification_summary.get("insufficient_evidence",0)>0 or any("INSUFFICIENT" in (c.verdict.upper()) for c in ans2.claims)
                    rec.chat_validation = bool(structural_ok and hall_ok)
                except Exception as e:
                    rec.chat_validation = False
                    rec.failure_stage = f"CHAT_EXCEPTION:{str(e)[:80]}"
                # Workspace
                try:
                    imp = ImpactAnalyzer.analyze(model["classes"][0]["name"], brain.analysis_run_id)
                    rec.workspace_validation = imp.repository_id == snap.repository_id
                except: rec.workspace_validation = False
                rec.validation_timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                # Final status
                if rec.files_parsed >0 and rec.symbols>0 and rec.evidence_resolution and rec.wiki_generation and rec.diagram_generation and rec.chat_validation and rec.workspace_validation:
                    rec.status = LanguageStatus.VALIDATED
                else:
                    rec.status = LanguageStatus.VALIDATION_FAILED
                    # Determine failure stage
                    if rec.parse_failures>0: rec.failure_stage = "PARSING"
                    elif not rec.evidence_resolution: rec.failure_stage = "EVIDENCE_RESOLUTION"
                    elif not rec.wiki_generation: rec.failure_stage = "WIKI_GENERATION"
                    elif not rec.diagram_generation: rec.failure_stage = "DIAGRAM_GENERATION"
                    elif not rec.chat_validation: rec.failure_stage = "CHAT_VALIDATION"
                    elif not rec.workspace_validation: rec.failure_stage = "WORKSPACE_VALIDATION"
            except Exception as e:
                rec.status = LanguageStatus.VALIDATION_FAILED
                rec.failure_stage = f"EXCEPTION:{str(e)[:100]}"
        except Exception as e:
            rec.status = LanguageStatus.VALIDATION_FAILED
            rec.failure_stage = str(e)[:100]
        return rec

    @staticmethod
    def validate_all() -> Dict[str, LanguageValidationRecord]:
        results = {}
        for lang in LANGUAGE_CONFIG:
            results[lang] = PolyglotValidator.validate_language(lang)
        return results
