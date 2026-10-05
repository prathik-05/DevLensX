"""
DevLensX Module 8: Standalone Intelligence Web Dashboard (Streamlit)

Features:
  - Repository Summary (Language, Framework, Component Counts)
  - Execution Stage Timing Metrics (Parse, Graph, Agents, Critic, Synthesis, Total)
  - Process Visual Pipeline
  - Repository Intelligence Scorecard & Sub-Score Formulas
  - Top 5 Engineering Recommendations Cards with Evidence Coverage Score
  - Critic Rejection Audit Feed (Demonstrating hallucinated finding rejection)
  - Interactive Natural Language Q&A (Hybrid Retrieval Engine)
  - Change Impact Simulator & Blast Radius Heatmap
  - GitHub Repository Clone & Analyze support
"""

import streamlit as st
import sys
import os
import time
import tempfile
from pathlib import Path
from git import Repo

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.resolve()))

from devlensx.repository_memory import RepositoryIntelligenceEngine
from devlensx.agents import ArchitectureAgent, SecurityAgent, ChangeImpactAgent
from devlensx.critic import CriticAgent
from devlensx.recommendation import RecommendationEngine

st.set_page_config(
    page_title="DevLensX Intelligence Dashboard",
    page_icon="🔍",
    layout="wide"
)

st.title("🔍 DevLensX Intelligence Dashboard")
st.caption("An Evidence-Verified Software Engineering Intelligence Platform")

# Sidebar Configuration
st.sidebar.header("Repository Analysis Input")
repo_input = st.sidebar.text_input("Local Path or GitHub URL", value="sample_repo")
inject_hallucination = st.sidebar.checkbox("Inject Synthetic Hallucinated Finding (Test Critic Rejection)", value=True)

if st.sidebar.button("Run Full Repository Analysis", type="primary"):
    with st.spinner("Processing repository & running intelligence pipeline..."):
        try:
            t_start = time.perf_counter()
            target_path = repo_input
            if repo_input.startswith("http://") or repo_input.startswith("https://"):
                temp_dir = tempfile.mkdtemp(prefix="devlensx_repo_")
                st.sidebar.info("Cloning GitHub repository...")
                Repo.clone_from(repo_input, temp_dir)
                target_path = temp_dir

            intelligence = RepositoryIntelligenceEngine().analyze(target_path)
            model = intelligence.model
            graph_store = intelligence.graph_store
            retriever = intelligence.retriever
            edge_stats = intelligence.graph_edge_stats
            t_parse = intelligence.timings_ms["parse_ast_ms"]
            t_graph = intelligence.timings_ms["graph_build_ms"]

            # Stage 4: Multi-Agent Scan
            t0 = time.perf_counter()

            arch_agent = ArchitectureAgent(graph_store)
            sec_agent = SecurityAgent()
            impact_agent = ChangeImpactAgent(graph_store)

            arch_res = arch_agent.analyze(model)
            sec_res = sec_agent.analyze(model, target_path)
            impact_res = impact_agent.analyze(model)

            raw_findings = arch_res["findings"] + sec_res["findings"] + impact_res["findings"]

            if inject_hallucination:
                raw_findings.append({
                    "agent": "ArchitectureAgent",
                    "category": "Coupling",
                    "title": "Hallucinated Bottleneck: NonExistentPaymentGateway",
                    "severity": "HIGH",
                    "class_name": "NonExistentPaymentGateway",
                    "file": "com/example/gateway/NonExistentPaymentGateway.java",
                    "claim": "NonExistentPaymentGateway has 45 incoming dependencies violating structural boundaries.",
                    "evidence": {}
                })

            t_agents = round((time.perf_counter() - t0) * 1000, 2)

            # Stage 4: Critic Grounding Verification
            t0 = time.perf_counter()
            critic = CriticAgent(graph_store)
            verified_findings = critic.verify_all(raw_findings, model)
            t_critic = round((time.perf_counter() - t0) * 1000, 2)

            # Stage 5: Synthesis
            t0 = time.perf_counter()
            rec_engine = RecommendationEngine()
            synthesis = rec_engine.synthesize(verified_findings, model)
            t_synthesis = round((time.perf_counter() - t0) * 1000, 2)

            t_total = round((time.perf_counter() - t_start) * 1000, 2)

            st.session_state["model"] = model
            st.session_state["graph_store"] = graph_store
            st.session_state["retriever"] = retriever
            st.session_state["synthesis"] = synthesis
            st.session_state["verified_findings"] = verified_findings
            st.session_state["arch_res"] = arch_res
            st.session_state["timing_metrics"] = {
                "parse_ast_ms": t_parse,
                "graph_build_ms": t_graph,
                "multi_agent_scan_ms": t_agents,
                "critic_grounding_verification_ms": t_critic,
                "recommendation_synthesis_ms": t_synthesis,
                "total_execution_ms": t_total
            }

            st.sidebar.success(f"Analysis Complete in {t_total} ms!")
        except Exception as e:
            st.sidebar.error(f"Analysis failed: {str(e)}")

# Main Content Dashboard
if "synthesis" in st.session_state:
    model = st.session_state["model"]
    synthesis = st.session_state["synthesis"]
    summary = model.get("repo_summary", {})
    score_data = synthesis["repository_intelligence_score"]
    timing = st.session_state.get("timing_metrics", {})

    # 1. Process Visual Pipeline Banner & Timing Metrics
    st.markdown("#### ⚙️ Execution Pipeline & Stage Timing Benchmarks")
    st.markdown("`[1. Parse AST]` ➔ `[2. Knowledge Graph]` ➔ `[3. Multi-Agent Scan]` ➔ `[4. Grounding Critic]` ➔ `[5. Recommendation Engine]`")
    
    t_cols = st.columns(6)
    t_cols[0].metric("1. Parse AST", f"{timing.get('parse_ast_ms', 0)} ms")
    t_cols[1].metric("2. Graph Build", f"{timing.get('graph_build_ms', 0)} ms")
    t_cols[2].metric("3. Multi-Agent", f"{timing.get('multi_agent_scan_ms', 0)} ms")
    t_cols[3].metric("4. Critic Verification", f"{timing.get('critic_grounding_verification_ms', 0)} ms")
    t_cols[4].metric("5. Synthesis", f"{timing.get('recommendation_synthesis_ms', 0)} ms")
    t_cols[5].metric("Total Time", f"{timing.get('total_execution_ms', 0)} ms")

    st.divider()

    # 2. Repository Summary View
    st.markdown("### 📊 Repository Summary")
    r1, r2, r3, r4, r5, r6, r7 = st.columns(7)
    r1.metric("Language", summary.get("language", "Java"))
    r2.metric("Framework", summary.get("framework", "Spring Boot"))
    r3.metric("Controllers", summary.get("controllers", 0))
    r4.metric("Services", summary.get("services", 0))
    r5.metric("Repositories", summary.get("repositories", 0))
    r6.metric("Entities", summary.get("entities", 0))
    r7.metric("REST APIs", summary.get("rest_apis", 0))

    st.divider()

    # 3. Repository Intelligence Score
    st.markdown("### 🏆 Repository Intelligence Score")
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    col1.metric("Overall Score", f"{score_data['overall']} / 100")
    col2.metric("Architecture", f"{score_data['sub_scores']['architecture']}%")
    col3.metric("Security", f"{score_data['sub_scores']['security']}%")
    col4.metric("Maintainability", f"{score_data['sub_scores']['maintainability']}%")
    col5.metric("Coupling", f"{score_data['sub_scores']['coupling']}%")
    col6.metric("Evidence Coverage", f"{score_data['sub_scores']['evidence_coverage']}%")

    with st.expander("Sub-Score Calculation Formulas & Explanations"):
        st.json(score_data["sub_score_explanations"])

    st.divider()

    # 4. Top Engineering Recommendations Cards
    st.markdown("### 🎯 Top 5 Engineering Recommendations (Grounding Verified)")
    recs = synthesis["top_engineering_recommendations"]
    if not recs:
        st.info("No high-risk structural issues found! Repository health is strong.")
    else:
        for rec in recs:
            with st.expander(f"#{rec['rank']} [{rec['priority']}] {rec['title']} (Evidence Coverage Score: {rec['evidence_coverage_score']}%)"):
                st.write(f"**Target Component:** `{rec['target_component']}` | **File:** `{rec['file']}`")
                st.write(f"**Reason / Claim:** {rec['reason']}")
                st.write(f"**Evidence Ratio:** `{rec['evidence_summary']}` (Evidence Sources Confirmed)")
                st.write(f"**Affected Components:** {rec['affected_components'] or ['None']}")
                st.write(f"**Estimated Effort:** {rec['estimated_effort']} | **Expected Benefit:** {rec['expected_benefit']}")
                st.markdown("**Critic Audit Log (Grounding Verification):**")
                st.json(rec["evidence_trail"])

    st.divider()

    # 5. Rejected Findings Section (Demonstrating Critic Rejection)
    st.markdown("### 🛡️ Critic Rejection Feed (Filtered Hallucinations & Ungrounded Claims)")
    rejected = synthesis.get("rejected_findings_sample", [])
    if not rejected:
        st.write("No findings were rejected by the Critic Agent in this run.")
    else:
        st.warning(f"Critic Agent detected and REJECTED {len(rejected)} ungrounded finding(s):")
        for rej in rejected:
            st.error(f"❌ [{rej['verdict']}] {rej['title']} (Coverage: {rej['evidence_coverage_score']}% | Ratio: {rej['evidence_ratio']})")

    st.divider()

    # 6. Interactive Natural Language Q&A (Hybrid Retrieval Engine)
    st.markdown("### 💡 Interactive Repository Intelligence Q&A (Hybrid Retrieval)")
    user_query = st.text_input("Ask a repository question (e.g. 'explain OwnerService', 'what breaks if I modify OwnerRepository?'):")
    if user_query and "retriever" in st.session_state:
        context = st.session_state["retriever"].retrieve_context(user_query)
        st.markdown("**Retrieved Hybrid Context (Graph Triples + FAISS Semantic Embeddings):**")
        st.json(context)

    st.divider()

    # 7. Change Impact Simulator
    st.markdown("### ⚡ Change Impact & Blast Radius Simulator")
    class_names = [c["name"] for c in model["classes"]]
    selected_class = st.selectbox("Select Class to Predict Blast Radius", options=class_names)
    
    if selected_class and "graph_store" in st.session_state:
        impact_agent = ChangeImpactAgent(st.session_state["graph_store"])
        impact = impact_agent.analyze_change_impact(selected_class)
        
        st.write(f"**Risk Level:** `{impact['risk_level']}` | **Total Downstream Affected:** `{impact['total_affected_count']}` classes")
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Affected Controllers:**")
            st.write([ctrl["class_name"] for ctrl in impact["affected_controllers"]] or "None")
        with c2:
            st.markdown("**Affected Tests:**")
            st.write([tst["class_name"] for tst in impact["affected_tests"]] or "None")

    st.divider()

    # 8. Architectural Layer Flows & Dependency Chains
    st.markdown("### 🏗️ Architectural Layer Flows & Dependency Chains")
    arch_res = st.session_state.get("arch_res", {})
    t1, t2 = st.tabs(["Dependency Chains (Controller ➔ Service ➔ Repository)", "Layer Connection Counts"])
    with t1:
        st.table(arch_res.get("dependency_chains", []))
    with t2:
        st.table(arch_res.get("layer_flows", []))

else:
    st.info("👈 Please enter a target Java repository path in the sidebar and click **Run Full Repository Analysis**.")
