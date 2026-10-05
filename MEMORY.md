# DevLensX — Project Memory & Architecture Fact Base

> **Product Identity:** DevLensX — Understand, Debug, Build, and Review Any Codebase with Evidence.
> **Current Version:** Phase P3 — CodeTurtle Review Intelligence (Completed & Verified)
> **Last Verification:** 2026-09-20 — 53 Review/OCR Tests, 69 Unit Tests, 20 Wiki Tests, 0 Build Errors.

---

## 1. Core Trust Model & Non-Negotiable Invariants

1. **Defensible Grounding Principle:**
   DevLensX prevents unsupported repository claims from being classified as `VERIFIED`; ungrounded or ambiguous claims fail closed as `AI_SUGGESTION` or `INSUFFICIENT_EVIDENCE`.
2. **Snapshot Isolation:**
   Every operation binds strictly to exact `(repository_id, analysis_run_id, commit_hash)`. No process-global fallback, no synthetic AST, missing snapshots fail closed (`SNAPSHOT_NOT_FOUND`).
3. **Evidence-First Pipeline:**
   $$\text{Diff} \longrightarrow \text{RuleSniffer} \longrightarrow \text{Snapshot Context} \longrightarrow \text{LLM Reasoning} \longrightarrow \text{Pre-Filter} \longrightarrow \text{Relocator} \longrightarrow \text{ClaimVerifier} \longrightarrow \text{SuggestDiff} \longrightarrow \text{UI}$$
4. **Separation of Concerns:**
   - **Rule Engine / Pre-Filter (`evaluate_negative_constraints`):** Review intelligence (suppresses obviously irrelevant candidate findings before verification).
   - **ClaimVerifier (`ClaimVerifierEngine`):** Sole evidence-based truth boundary (requires real AST symbol and changed-file matches).
   - **SuggestDiff Engine (`compute_line_diff`):** Myers-style shortest edit script diff generator. Produces 1-click committable patches requiring explicit user action (`committable: true`, `verified: false`, `requires_user_action: true`).
5. **Read-Only / Explicit-Action:**
   No automatic code writing. All suggested fixes require explicit human review and application.

---

## 2. Completed Milestones

- **Phase P0 — Platform Foundation:** AST → KùzuDB → FAISS → Brain → Critic → Security → Docker → Staging.
- **Phase P1 — Polyglot Expansion:** Tree-sitter Universal Repository Model (URM) with adapters for 21 languages.
- **Phase P2 — Repository-First Architecture:** DeepWiki (11 grounded sections) → Component Inspector → Change Impact cascade → Debug Center → 11-workspace layout.
- **Phase P3 — CodeTurtle Review Intelligence:**
  - `devlensx/review/rules/system_rules.py` & `rule_catalog.py`: Path sniffer and negative review constraints (Java, Python, TypeScript/JavaScript, Go, Build/XML).
  - `devlensx/review/relocation.py`: Hunk-based sliding-window line matching and cross-file relocation. Ambiguous matches fail closed as `INSUFFICIENT_EVIDENCE`.
  - `devlensx/review/suggestdiff.py`: Myers line-diff engine producing structured `diff_snippet` (`header`, `deleted`, `added`) and committable patches.
  - `devlensx/review/codeturtle.py`: Unified pipeline integrating RuleSniffer → Pre-Filter → Relocation → ClaimVerifier → SuggestDiff.
  - `web/src/components/CodeTurtleView.tsx`: Live code review execution via `reviewCodeTurtle(analysisRunId, diff)` with live Myers diff snippet rendering.

---

## 3. Test Baseline (Zero Regressions)

- **Combined Review & OCR Suites:** 53 / 53 passed
- **DevLensX Unit Test Baseline:** 69 / 69 passed
- **Reasoning & Wiki Suites:** 20 / 20 passed
- **Frontend Build (`npm run build`):** 0 errors / 22.73s
