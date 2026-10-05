# DevLensX v1 — 3-Minute Product Demonstration Script

**Goal:** Concise, high-impact demonstration of DevLensX repository understanding, evidence grounding, and hallucination defense.

---

## ⏱️ Video / Demo Script Breakdown (180 Seconds)

### 0:00 – 0:30: Introduction & Grounding Problem
- *"Imagine joining a 200-class Java codebase today and needing to understand its architecture before making changes."*
- *"Traditional AI tools statelessly invent classes or methods. DevLensX separates fact extraction from AI reasoning."*
- **Screen:** Show DevLensX Dashboard and upload `spring-petclinic.zip`.

### 0:30 – 1:00: Understand & Ask Workspaces
- *"DevLensX parses Java AST nodes into a KuzuDB graph and constructs a versioned RepositoryBrain."*
- **Screen:** Show Understand Workspace plain-English summary and discovered `Owner Management` domain capabilities.
- **Screen:** Navigate to Ask Workspace and submit *"How does owner management work?"*. Highlight 🟢 **`VERIFIED`** badges on `OwnerController` and `OwnerRepository`.

### 1:00 – 1:45: Hallucination Defense (Core Moat)
- *"Watch what happens when we ask about a non-existent class."*
- **Screen:** Submit query *"Does PaymentController handle payment processing?"*.
- **Screen:** DevLensX returns 🔴 **`INSUFFICIENT EVIDENCE: PaymentController was not found in the analyzed repository.`**
- *"The LLM is strictly prohibited from turning an unsupported claim into a repository fact."*

### 1:45 – 2:30: Debug & Build Studio Workspaces
- **Screen:** Navigate to Debug Workspace and paste a Java stack trace (`NullPointerException` at `OwnerController.java:110`). Show 🟢 **`VERIFIED BY AST`** location and 🔵 **`AI SUGGESTION`** hypothesis.
- **Screen:** Navigate to Build Studio and query `OwnerController`. Show explainable blast-radius change impact breakdown (`OwnerController -> OwnerRepository -> Owner`).

### 2:30 – 3:00: Living DeepWiki & Architecture Conclusion
- **Screen:** Show Living DeepWiki workspace consuming the exact same `analysis_run_id` `RepositoryBrain` snapshot without re-analysis.
- **Conclusion:** *"DevLensX provides evidence-grounded engineering intelligence—verified facts, clear suggestions, zero unbacked claims."*
