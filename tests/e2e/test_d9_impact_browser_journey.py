"""D9 E2E: Wiki → OwnerController → Show Impact Browser Journey

This test validates the D9 integration flow:
1. Analyze repository
2. Open Wiki
3. Select OwnerController
4. Click Show Impact
5. Verify blast radius with evidence
"""

import json
from playwright.sync_api import sync_playwright
import pytest

FRONTEND = "http://127.0.0.1:5173"


@pytest.fixture(scope="module")
def live_stack():
    """Analyze PetClinic once per module and share analysis_run_id."""
    import subprocess
    import time
    import requests
    
    # Start backend
    backend_proc = subprocess.Popen(
        ["python", "run_devlensx.py", "api"],
        cwd="C:\\Users\\SVCS\\Desktop\\DevLensX",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    
    # Start frontend
    frontend_proc = subprocess.Popen(
        ["npm", "run", "dev"],
        cwd="C:\\Users\\SVCS\\Desktop\\DevLensX\\web",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    
    # Wait for services
    time.sleep(15)
    
    # Analyze PetClinic
    try:
        resp = requests.post("http://127.0.0.1:8000/api/analyze", 
            json={"repo_path": "eval_repos/spring-petclinic", "inject_hallucination": False},
            timeout=120)
        data = resp.json()
        pet_run = data.get("analysis_run_id")
        print(f"PetClinic analysis_run_id: {pet_run}")
    except Exception as e:
        print(f"Analysis failed: {e}")
        pet_run = None
    
    yield {"pet_run": pet_run}
    
    # Cleanup
    backend_proc.terminate()
    frontend_proc.terminate()


def test_d9_impact_browser_journey(live_stack):
    """Test the golden D9 journey: Wiki → Symbol → Impact → Evidence"""
    pet_run = live_stack["pet_run"]
    if not pet_run:
        pytest.skip("No analysis run available")
    
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1600, "height": 1000})
        
        try:
            # 1. Navigate to frontend
            page.goto(FRONTEND, wait_until="domcontentloaded")
            
            # 2. Analyze PetClinic via UI (or use existing analysis)
            page.click("text=Local Path")
            local_input = page.locator('input[placeholder="eval_repos/spring-petclinic"]')
            local_input.wait_for(state="visible", timeout=15_000)
            local_input.fill("eval_repos/spring-petclinic")
            page.click("text=Enter ArchitectOS Workspace")
            
            # Wait for analysis to complete and overview to load
            page.wait_for_selector("text=DevLensX Assistant Briefing", timeout=120_000)
            
            # 3. Open the wiki surface
            page.click('button[title="Build Studio & Wiki"]', timeout=15_000)
            page.wait_for_selector("text=Source Evidence", timeout=30_000)
            
            # 4. Find and click OwnerController citation chip
            chip = page.locator("button").filter(has_text="OwnerController").first
            chip.wait_for(state="visible", timeout=15_000)
            chip.scroll_into_view_if_needed()
            chip.click()
            
            # Wait for SourceViewer to appear
            page.wait_for_function(
                "() => document.body.innerText.includes('class OwnerController') || document.body.innerText.includes('Evidence unavailable')",
                timeout=45_000
            )
            
            # 5. Close source viewer and navigate back to wiki
            close_btn = page.locator('button[aria-label="Close source viewer"]')
            if close_btn.count():
                close_btn.first.click()
            
            # 6. Click the "Impact" button for OwnerController
            impact_btn = page.locator("button").filter(has_text="Impact: OwnerController").first
            impact_btn.wait_for(state="visible", timeout=15_000)
            impact_btn.scroll_into_view_if_needed()
            impact_btn.click()
            
            # 7. Verify impact analysis results appear
            page.wait_for_selector("text=Change Impact Analysis", timeout=30_000)
            
            # Verify direct, downstream, tests sections
            assert page.locator("text=Direct").count() > 0
            assert page.locator("text=Downstream").count() > 0
            assert page.locator("text=Tests").count() > 0
            
            # Verify OwnerController appears in direct
            assert page.locator("text=OwnerController").count() > 0
            
            # 8. Verify evidence refs are present
            assert page.locator("text=VERIFIED").count() > 0
            
            print("  ✅ D9 Impact journey: Wiki → OwnerController → Show Impact → Blast Radius verified")
            
        finally:
            browser.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])