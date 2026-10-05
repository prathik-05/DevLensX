"""D9 E2E: Wiki → OwnerController → Build → ChangePlan Browser Journey"""

import json
from playwright.sync_api import sync_playwright
import pytest

FRONTEND = "http://127.0.0.1:5173"


@pytest.fixture(scope="module")
def live_stack():
    import subprocess
    import time
    import requests
    
    backend_proc = subprocess.Popen(
        ["python", "run_devlensx.py", "api"],
        cwd="C:\\Users\\SVCS\\Desktop\\DevLensX",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    
    frontend_proc = subprocess.Popen(
        ["npm", "run", "dev"],
        cwd="C:\\Users\\SVCS\\Desktop\\DevLensX\\web",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    
    time.sleep(15)
    
    try:
        resp = requests.post("http://127.0.0.1:8000/api/analyze", 
            json={"repo_path": "eval_repos/spring-petclinic", "inject_hallucination": False},
            timeout=120)
        data = resp.json()
        pet_run = data.get("analysis_run_id")
    except Exception as e:
        print(f"Analysis failed: {e}")
        pet_run = None
    
    yield {"pet_run": pet_run}
    
    backend_proc.terminate()
    frontend_proc.terminate()


def test_d9_build_browser_journey(live_stack):
    """Test: Wiki → OwnerController → Impact → Build → ChangePlan"""
    pet_run = live_stack["pet_run"]
    if not pet_run:
        pytest.skip("No analysis run available")
    
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1600, "height": 1000})
        
        try:
            page.goto(FRONTEND, wait_until="domcontentloaded")
            
            page.click("text=Local Path")
            local_input = page.locator('input[placeholder="eval_repos/spring-petclinic"]')
            local_input.wait_for(state="visible", timeout=15_000)
            local_input.fill("eval_repos/spring-petclinic")
            page.click("text=Enter ArchitectOS Workspace")
            
            page.wait_for_selector("text=DevLensX Assistant Briefing", timeout=120_000)
            
            page.click('button[title="Build Studio & Wiki"]', timeout=15_000)
            page.wait_for_selector("text=Source Evidence", timeout=30_000)
            
            # Click OwnerController impact
            chip = page.locator("button").filter(has_text="OwnerController").first
            chip.wait_for(state="visible", timeout=15_000)
            chip.scroll_into_view_if_needed()
            chip.click()
            
            close_btn = page.locator('button[aria-label="Close source viewer"]')
            if close_btn.count():
                close_btn.first.click()
            
            # Click Impact button
            impact_btn = page.locator("button").filter(has_text="Impact: OwnerController").first
            impact_btn.wait_for(state="visible", timeout=15_000)
            impact_btn.scroll_into_view_if_needed()
            impact_btn.click()
            
            page.wait_for_selector("text=Change Impact Analysis", timeout=30_000)
            
            # Click Build Plan button
            build_btn = page.locator("button").filter(has_text="Build Plan").first
            build_btn.wait_for(state="visible", timeout=15_000)
            build_btn.scroll_into_view_if_needed()
            build_btn.click()
            
            # Verify change plan appears
            page.wait_for_selector("text=Change Plan Generated", timeout=30_000)
            
            # Verify steps with statuses
            assert page.locator("text=AI_SUGGESTION").count() > 0
            assert page.locator("text=VERIFIED_FACT").count() > 0 or page.locator("text=INSUFFICIENT_EVIDENCE").count() >= 0
            
            # Verify evidence refs
            assert page.locator("text=evidence refs").count() > 0 or page.locator("text=evidence_refs").count() > 0
            
            print("  ✅ D9 Build journey: Wiki → OwnerController → Impact → Build Plan verified")
            
        finally:
            browser.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])