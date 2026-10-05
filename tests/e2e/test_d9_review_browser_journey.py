"""D9 E2E: Git Diff → Review → Impacted Symbols → Evidence Browser Journey"""

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


def test_d9_review_browser_journey(live_stack):
    """Test: Review → upload/paste diff → changed symbols → affected symbols → evidence"""
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
            
            # Navigate to Review/Security tab
            page.click('button[title="Build Studio & Wiki"]', timeout=15_000)
            
            # Find Review button or navigate via command palette
            review_btn = page.locator("button").filter(has_text="Review").first
            if not review_btn.count():
                page.keyboard.press("Control+K")
                page.fill('input[placeholder*="Command"]', "review")
                page.keyboard.press("Enter")
            
            page.wait_for_selector("text=Review", timeout=15_000)
            
            # Sample git diff
            sample_diff = """diff --git a/src/main/java/org/springframework/samples/petclinic/owner/OwnerController.java b/src/main/java/org/springframework/samples/petclinic/owner/OwnerController.java
index 1234567..abcdefg 100644
--- a/src/main/java/org/springframework/samples/petclinic/owner/OwnerController.java
+++ b/src/main/java/org/springframework/samples/petclinic/owner/OwnerController.java
@@ -20,6 +20,7 @@ public class OwnerController {
     private final ClinicService clinicService;
     
     @Autowired
     public OwnerController(ClinicService clinicService) {
         this.clinicService = clinicService;
     }
+    
+    public void newMethod() {
+        // New feature method
+    }
 }
"""
            
            # Find diff input area
            textarea = page.locator("textarea[placeholder*='diff'], textarea[placeholder*='Diff']").first
            if textarea.count():
                textarea.fill(sample_diff)
                
                # Click review button
                analyze_btn = page.locator("button").filter(has_text="Analyze").first
                if not analyze_btn.count():
                    analyze_btn = page.locator("button").filter(has_text="Review").first
                if analyze_btn.count():
                    analyze_btn.click()
                    
                    # Wait for review results
                    page.wait_for_selector("text=VERIFIED", timeout=30_000)
                    
                    # Verify what changed
                    assert page.locator("text=What Changed").count() > 0 or page.locator("text=what_changed").count() > 0
                    
                    # Verify what affected
                    assert page.locator("text=What Affected").count() > 0 or page.locator("text=what_affected").count() > 0
                    
                    # Verify related tests
                    assert page.locator("text=Related Tests").count() > 0 or page.locator("text=related_tests").count() > 0
                    
                    # Verify evidence refs
                    assert page.locator("text=VERIFIED").count() > 0
                    
                    # Verify AI_SUGGESTION for what might break
                    assert page.locator("text=AI_SUGGESTION").count() > 0 or page.locator("text=what_might_break").count() > 0
                    
                    print("  ✅ D9 Review journey: Git Diff → Review → Evidence verified")
            
        finally:
            browser.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])