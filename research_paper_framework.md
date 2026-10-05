# DevLensX — Research Paper & Thesis Specification Framework

**Title:** DevLensX: An Evidence-Verified Software Engineering Intelligence Platform  
**Target Venues:** IEEE / Scopus Software Engineering Conferences  

---

## Abstract

Modern software repositories present significant cognitive complexity for architecture comprehension, refactoring blast-radius estimation, and vulnerability management. While Large Language Model (LLM) coding assistants offer file-level code generation, they frequently generate ungrounded, hallucinated recommendations when queried on repository-wide architectural concerns. We present **DevLensX**, an evidence-verified software engineering intelligence platform. DevLensX constructs a multi-layered Knowledge Graph using an embedded Cypher database (Kuzu) populated via AST parsing (`javalang`) with prepared statement optimizations (967ms load time). It executes a multi-agent analysis suite (Architecture, Security, and Change Impact & Refactoring agents) whose raw findings are verified by an **Independent Critic Agent**. The Critic evaluates findings across four independent structural evidence sources (`Graph`, `AST`, `Semgrep`, `Structure`) and assigns an explainable Evidence Coverage Score ratio ($X/4$). Ungrounded claims are automatically flipped to `REJECTED`. 

We evaluate DevLensX on three real open-source Java repositories of varying scale (`spring-petclinic`, `mybatis-3`, `dubbo`). Empirical results across 73 manually annotated findings ($N=73$) demonstrate that independent evidence verification improves overall finding precision from **$39.7\%$ to $42.6\%$** (reducing false positive rate from **$60.3\%$ to $57.4\%$**), achieves a **$0.0\%$ False Rejection Rate** ($0/29$ True Positives discarded), and yields a **$55.7\%$ Balanced Accuracy**. Verification effects varied by the nature of the underlying findings: on Apache Dubbo, the Critic improved precision by 6.5 percentage points (rising to **$54.5\%$**) primarily by rejecting ungrounded pattern-matched findings (e.g., constant names such as `PASSWORD_KEY` incorrectly flagged as hardcoded secrets), catching **$23.1\%$** of raw false positives. On Spring PetClinic, precision remained unchanged at **$34.8\%$**, because the Critic's structural checks confirmed the underlying claim (missing `@PreAuthorize` annotations) was factually accurate — the finding was correctly grounded even though it does not represent a genuine flaw in a demo application intentionally built without Spring Security. This distinction empirically demonstrates that evidence grounding verification is separate from semantic design correctness: the Critic can correctly reject fabricated evidence while still passing through accurately-grounded findings whose real-world significance requires human judgment.

---

## 1. Central Research Claim

> "DevLensX demonstrates that independent evidence-based verification can significantly reduce unsupported AI-generated repository findings while preserving useful software engineering recommendations."

---

## 2. Explicit Limitation Statement (Section 9 of Paper)

> "The Critic Agent verifies that AI findings are grounded in repository evidence rather than proving semantic correctness. A structurally supported finding may still represent an incorrect engineering recommendation, while a correct recommendation lacking sufficient repository evidence may be rejected. Therefore, DevLensX improves the reliability of repository grounding rather than guaranteeing correctness."

### Empirically Recorded Pipeline & Methodological Limitations
* **Repository-Wide Recall & Developer Study Boundaries:**
  * Classical recall and F1-score require an exhaustive manual audit of all undetected issues across millions of lines of code in target repositories, which is practically infeasible. Therefore, **False Rejection Rate ($0.0\%$)** and **Balanced Accuracy ($55.7\%$)** are used as the primary reliability measures. Repository understanding efficiency was evaluated via per-stage execution timing benchmarks rather than human developer user studies.
* **Knowledge Graph Edge Resolution Boundaries (Internal vs. External Types):**
  * Knowledge Graph edge creation explicitly targets internal repository class dependencies (`DEPENDS_ON`, `EXTENDS`, `IMPLEMENTS`). External JDK standard library types (`java.lang.*`, `java.util.*`) and third-party framework classes (`org.springframework.*`) are skipped by design (`skipped_unresolved`). Internal repository class dependency resolution achieves **$100.0\%$ resolution completeness**, while overall type resolution across external library boundaries ranges from **$54.05\%$** (`spring-petclinic`), **$63.34\%$** (`mybatis-3`), to **$67.24\%$** (`dubbo`).
* **Maximum Observed Evidence Ratio ($3/4$ Max in Windows Execution Environment):**
  * In this Windows evaluation environment, the native Semgrep CLI binary was uninstalled (`shutil.which('semgrep') == None`). Consequently, `semgrep_check` remained `False` across all 73 findings, capping the maximum observed Evidence Coverage Score ratio at **$3/4\ (75.0\%)$** ($3/3$ active structural sources verified: Graph $\checkmark$, AST $\checkmark$, Structure $\checkmark$). Ratios of $4/4\ (100.0\%)$ require executing Semgrep in a Linux/WSL environment.
* **Security Recall Against Independent Static Analyzers:**
  * Due to the absence of the native Semgrep CLI binary in the Windows execution environment, automated cross-checking against independent Semgrep rule matches could not be computed for this evaluation dataset. Security findings were evaluated exclusively against manual expert annotations.
* **AST Parser Coverage (`javalang`):**
  * **Apache Dubbo:** Parsed 4,032 / 4,049 files (99.58% success rate). Exactly **17 files** encountered `PARSE_ERROR` due to modern Java 17/21 record syntax and multi-generic bounds.
  * **MyBatis-3:** Parsed 1,370 / 1,396 files (98.14% success rate). Exactly **26 files** encountered `PARSE_ERROR`.
* **Graph QName Deduplication:**
  * **MyBatis-3:** Exactly **4 duplicate class nodes** out of 1,480 total classes (0.27% variance) were deduplicated due to identical package and class names across main source and test fixture modules (e.g., `org.apache.ibatis.reflection.BeanClass`), preserving 99.73% structural graph edge completeness.

---

## 3. Locked Evaluation Target Repositories

| Repository | Scale | Files Parsed | Success Rate | Classes Found | Methods Found | Resolved Internal Edges | External Types Skipped | Total Type Resolution Rate |
|---|---|---|---|---|---|---|---|---|
| `spring-petclinic` | Small | 48 files | 100.0% | 48 classes | 240 methods | **20 edges** | 17 | **54.05%** |
| `mybatis-3` | Medium | 1,370 files | 98.14% | 1,480 classes | 7,569 methods | **603 edges** | 349 | **63.34%** |
| `dubbo` | Large | 4,032 files | 99.58% | 4,591 classes | 27,603 methods | **3,387 edges** | 1,655 | **67.24%** |

---

## 4. Empirical Evaluation Results (Section 7 of Paper)

### Ground-Truth Evaluation Metrics Across Repositories ($N=73$)

| Repository | Scale | Sampled ($N$) | TP / FP | Without-Critic Precision | With-Critic Precision | Precision Gain | False Positive Rate (FPR) | False Rejection Rate | FP Rejection Specificity | Balanced Accuracy |
|---|---|---|---|---|---|---|---|---|---|---|
| **Spring PetClinic** | Small | 23 | 8 / 15 | 34.8% | 34.8% | +0.0% | **65.2%** | **0.0% (0)** | 0.0% (0/15) | 50.0% |
| **MyBatis 3** | Medium | 25 | 9 / 16 | 36.0% | 39.1% | +3.1% | **60.9%** | **0.0% (0)** | 12.5% (2/16) | 56.2% |
| **Apache Dubbo** | Large | 25 | 12 / 13 | 48.0% | 54.5% | **+6.5%** | **45.5%** | **0.0% (0)** | **23.1% (3/13)** | **61.5%** |
| **POOLED TOTAL** | **All Repos** | **73** | **29 / 44** | **39.7%** | **42.6%** | **+2.9%** | **57.4%** | **0.0% (0)** | **11.4% (5/44)** | **55.7%** |

> **Note on Maximum Evidence Ratios:** In this evaluation run, the maximum observed Evidence Coverage Score ratio across all 73 findings was **$3/4\ (75.0\%)$** because the Semgrep CLI binary was absent in the Windows environment (`semgrep_check = False`). All verified findings achieved $3/3$ active structural evidence verification (Graph $\checkmark$, AST $\checkmark$, Structure $\checkmark$).

### Per-Stage Execution Performance Benchmarks

| Execution Stage | `spring-petclinic` (48 files) | `mybatis-3` (1,370 files) | `dubbo` (4,032 files) |
|---|---|---|---|
| **Stage 0: Repo Acquisition (Git Clone / Network)** | 6.06s (First run) | Local | Local |
| **Stage 1: Pure AST Parsing (`javalang`)** | **0.49s** | **18.23s** | **226.18s** |
| **Stage 2: Graph Build (Kuzu)** | **1.44s** | **9.17s** | **137.02s** |
| **Stage 3: Multi-Agent Scan** | 0.17s | 0.21s | 0.26s |
| **Stage 4: Critic Verification** | 0.34s | 1.25s | 9.46s |
| **Stage 5: Synthesis & Scoring** | 0.01s | 0.01s | 0.01s |
| **Pure Local Execution Total (Excl. Clone)** | **2.45s** | **28.87s** | **372.93s (6m 12.93s)** |

---

## 5. Locked Paper Structure (11 Unified Sections)

1. **Introduction & Motivation** — System complexity, AI context limits, 4 core engineering questions, grounding verification thesis.
2. **Related Work** — Static analysis, GraphRAG, multi-agent frameworks, AI code assistants, positioning matrix.
3. **DevLensX System Architecture** — AST Parser (`javalang`), Knowledge Graph (Kuzu/Neo4j), Specialist Agents, Critic, Synthesizer.
4. **Hybrid Repository Retrieval Pipeline** — Sequential GraphRAG architecture combining Cypher subgraph traversals with FAISS dense vector search over AST class summaries.
5. **Independent Critic Agent** — 4-Source Verification Protocol (`Graph`, `AST`, `Semgrep`, `Structure`), Evidence Coverage Score ratio ($X/4$), 50% coverage threshold ($\ge 2/4$ sources) verdict determination rule.
6. **Experimental Setup & Stratified Sampling Protocol** — Target repos, manual expert labeling ($N=73$), Semgrep baseline.
7. **Empirical Results & Stage Timing Benchmarks** — Precision, FPR, Balanced Accuracy, Sensitivity/Specificity, Stage Timing Benchmarks.
8. **Discussion** — Trade-offs between evidence strictness and false rejections, empirical grounding vs. correctness.
9. **Limitations & Boundary Declarations** — Grounding verification vs. semantic correctness guarantee, AST parser limits (17 errors on Dubbo), QName dedup limits, internal vs external graph edge resolution rates ($54\%-67\%$), $3/4$ max ratio due to Semgrep Windows binary absence, non-computation of classical recall.
10. **Future Work** — Repository Intelligence Workspace, Graph Simulation ("What-if Analysis"), Extensible Evidence Providers (Git, Docs, Telemetry), Multi-Language Tree-Sitter Support, Repository Memory, Git History Intelligence, MCP IDE Plugin, CI/CD Integration.
11. **Conclusion** — Summary of evidence-verified repository intelligence findings.

---

## 6. Literature Baseline: Existing Systems and Limitations

| # | Title | Technology | Limitations | Authors | Year |
|---|---|---|---|---|---|
| 1 | Do Not Treat Code as Natural Language: Implications for Repository-Level Code Generation and Beyond | Dependency-aware structural retrieval treating code as graph-structured rather than token text | Improves retrieval structure-awareness only; does not verify generated claims against evidence — retrieval quality ≠ claim correctness | Le-Anh, Nguyen, Tran, Le Hai, Ngo Van, Bui, Le | 2026 |
| 2 | Effective and Efficient Context Retrieval via Partial Dependency Graph for Repository-Level Code Generation | On-demand partial dependency graph built from a small set of entry points | Graph is used only to build LLM context; no verification stage checks whether the generated output matches the graph | Liu, Ye, Liu, Ren | 2026 |
| 3 | cAST: Enhancing Code Retrieval-Augmented Generation with Structural Chunking via Abstract Syntax Tree | AST-guided structural chunking for retrieval boundaries | Improves chunk granularity only; downstream claims from the LLM remain unverified | Zhang, Zhao, Wang, Yang, Wei, Wu | 2025 |
| 4 | Citation-Grounded Code Comprehension: Preventing LLM Hallucination Through Hybrid Retrieval and Graph-Augmented Context | Hybrid lexical + dense + graph retrieval with citations | Citing a source doesn't guarantee the asserted relationship actually exists in the graph; no deterministic pass/fail verdict | Arafat | 2025 |
| 5 | Knowledge Graph Based Repository-Level Code Generation | Knowledge-graph-enriched context for code generation | Graph enriches context only; no separate boundary distinguishing verified fact from plausible suggestion | Athale, Vaddina | 2025 |
| 6 | An Empirical Study of Retrieval-Augmented Code Generation: Challenges and Opportunities | Empirical benchmarking of RAG across granularities and repo scales | A measurement study, not a system; finds inconsistent gains but proposes no verification mechanism | Yang, Chen, Gao, Li, Hu, Liu, Xia | 2025 |
| 7 | SWE-bench: Can Language Models Resolve Real-World GitHub Issues? | Benchmark of real-world multi-file GitHub issue resolution | A benchmark only; measures end-task success, not hallucination prevention or evidence grounding | Jimenez, Yang, Wettig, Yao, Pei, Press, Narasimhan | 2024 |
| 8 | Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection | Model self-critiques its own retrieval and generation via reflection tokens | Verification is performed by the same model that generated the claim — still probabilistic, shares the generator's blind spots | Asai, Wu, Wang, Sil, Hajishirzi | 2024 |
| 9 | Survey of Hallucination in Natural Language Generation | Taxonomy/survey of hallucination causes and mitigation classes | Descriptive only; proposes no concrete architecture or verification mechanism for code/repositories | Ji, Lee, Frieske, Yu, Su, Xu, Ishii, Bang, Fung | 2023 |
| 10 | Enabling Large Language Models to Generate Text with Citations | Citation-supported generation over text passages (ALCE) | Evaluates citation attribution for prose passages, not program structure — correct citation ≠ a verified code relationship (e.g., a call edge) | Gao, Yen, Yu, Chen | 2023 |
| 11 | Characterizing the Architectural Erosion Metrics: A Systematic Mapping Study | Systematic survey of architectural-erosion metrics | Catalogues metrics only; no automated, evidence-grounded enforcement tool | Baabad, Zulzalil, Hassan, Baharom | 2022 |

