"""Test the isolated E2E infrastructure works correctly."""

import pytest


def test_isolated_environment_creation(isolated_env):
    """Test that isolated environment starts and responds to health checks."""
    # Backend health
    import requests
    resp = requests.get(f"{isolated_env.base_url}/api/health", timeout=5)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"

    # Frontend serves content
    resp = requests.get(isolated_env.frontend_url, timeout=5)
    assert resp.status_code == 200
    # Built frontend is a React SPA with title "web"
    assert "web" in resp.text or "root" in resp.text

    # Environment has unique ports
    assert isolated_env.backend_port != isolated_env.frontend_port
    assert isolated_env.backend_port > 0
    assert isolated_env.frontend_port > 0

    # Kuzu directory exists and is unique
    from pathlib import Path
    assert isolated_env.kuzu_dir.exists()
    assert isolated_env.kuzu_dir.is_dir()


def test_petclinic_analysis_in_isolated_env(isolated_env, petclinic_analysis):
    """Test PetClinic analysis works in isolated environment."""
    assert "analysis_run_id" in petclinic_analysis
    assert petclinic_analysis["repository"] == "spring-petclinic"
    assert "knowledge_graph" in petclinic_analysis
    assert len(petclinic_analysis["knowledge_graph"]["nodes"]) > 0


def test_battleship_analysis_in_isolated_env(isolated_env, battleship_analysis):
    """Test Battleship analysis works in isolated environment."""
    assert "analysis_run_id" in battleship_analysis
    assert battleship_analysis["repository"] == "battleship-python"
    assert "knowledge_graph" in battleship_analysis
    assert len(battleship_analysis["knowledge_graph"]["nodes"]) > 0


def test_cross_repo_isolation_in_same_env(isolated_env):
    """Test that two repositories analyzed in same env don't leak (separate runs)."""
    # Analyze PetClinic
    pet_result = isolated_env.analyze_repo("eval_repos/spring-petclinic")
    pet_run = pet_result["analysis_run_id"]

    # Analyze Battleship
    bs_result = isolated_env.analyze_repo("eval_repos/battleship-python")
    bs_run = bs_result["analysis_run_id"]

    # Different runs
    assert pet_run != bs_run

    # Verify PetClinic symbols in PetClinic run
    pet_symbols = {n["name"] for n in pet_result["knowledge_graph"]["nodes"]}
    # Check for at least one known PetClinic symbol
    assert "OwnerController" in pet_symbols

    # Verify Battleship symbols in Battleship run
    bs_symbols = {n["name"] for n in bs_result["knowledge_graph"]["nodes"]}
    assert len(bs_symbols) > 0

    # No cross-contamination in knowledge graphs
    assert "OwnerController" not in bs_symbols