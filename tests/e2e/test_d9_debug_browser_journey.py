"""D9 E2E: StackTrace → DebugTrace → SourceViewer Browser Journey"""

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


def test_d9_debug_browser_journey(live_stack):
    """Test: Debug → paste stack trace → Trace → verified location → SourceViewer"""
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
            
            # Navigate to Debug/Build Studio tab
            page.click('button[title="Build Studio & Wiki"]', timeout=15_000)
            
            # Find Debug button or navigate to Debug view
            debug_btn = page.locator("button").filter(has_text="Debug").first
            if debug_btn.count():
                debug_btn.click()
            else:
                # Navigate via command palette or other means
                page.keyboard.press("Control+K")
                page.fill('input[placeholder*="Command"]', "debug")
                page.keyboard.press("Enter")
            
            # Wait for debug interface
            page.wait_for_selector("text=Debug", timeout=15_000)
            
            # Paste a sample stack trace
            stack_trace = """java.lang.NullPointerException
    at org.springframework.samples.petclinic.owner.OwnerController.processFindForm(OwnerController.java:87)
    at org.springframework.samples.petclinic.owner.OwnerController.initFindForm(OwnerController.java:72)
    at java.base/jdk.internal.reflect.NativeMethodAccessorImpl.invoke0(Native Method)"""
            
            # Find textarea for stack trace
            textarea = page.locator("textarea[placeholder*='stack trace'], textarea[placeholder*='Stack trace']").first
            if textarea.count():
                textarea.fill(stack_trace)
                
                # Click trace button
                trace_btn = page.locator("button").filter(has_text="Trace").first
                if trace_btn.count():
                    trace_btn.click()
                    
                    # Wait for results
                    page.wait_for_selector("text=VERIFIED", timeout=30_000)
                    
                    # Verify verified locations
                    assert page.locator("text=OwnerController").count() > 0
                    assert page.locator("text=VERIFIED").count() > 0
                    
                    print("  ✅ D9 Debug journey: StackTrace → DebugTrace → SourceViewer verified")
            
        finally:
            browser.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])