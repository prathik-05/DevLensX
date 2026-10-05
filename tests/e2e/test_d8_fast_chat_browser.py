"""
E2E: Fast chat browser journey — click through DocsPage ChatPanel in Fast mode.
"""
import sys, os, time, json, socket, threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
import pytest

BACKEND = "http://127.0.0.1:8000"
FRONTEND = "http://127.0.0.1:49232"

def _wait_port(port, timeout=30):
    end=time.time()+timeout
    while time.time()<end:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5): return True
        except: time.sleep(0.2)
    return False

@pytest.fixture(scope="module")
def live_stack2():
    import uvicorn, urllib.request
    cfg=uvicorn.Config("devlensx.api.main:app", host="127.0.0.1", port=8000, log_level="error", reload=False)
    server=uvicorn.Server(cfg)
    threading.Thread(target=server.run, daemon=True).start()
    assert _wait_port(8000)
    dist=os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")), "web", "dist")
    handler=partial(SimpleHTTPRequestHandler, directory=dist)
    httpd=ThreadingHTTPServer(("127.0.0.1",49232), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    assert _wait_port(49232)
    req=urllib.request.Request(f"{BACKEND}/api/analyze", data=json.dumps({"repo_path":"eval_repos/spring-petclinic"}).encode(), headers={"Content-Type":"application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=180) as r: pet=json.loads(r.read())
    assert pet.get("analysis_run_id")
    yield pet
    server.should_exit=True; httpd.shutdown()

def test_d8_fast_chat_browser(live_stack2):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b=p.chromium.launch(); pg=b.new_page(viewport={"width":1600,"height":1000})
        pg.goto(FRONTEND, wait_until="domcontentloaded")
        pg.click("text=Local Path")
        pg.locator('input[placeholder="eval_repos/spring-petclinic"]').wait_for(state="visible", timeout=15000)
        pg.fill('input[placeholder="eval_repos/spring-petclinic"]', "eval_repos/spring-petclinic")
        pg.click("text=Enter ArchitectOS Workspace")
        pg.wait_for_selector("text=DevLensX Assistant Briefing", timeout=120000)
        pg.click('button[title="Build Studio & Wiki"]', timeout=15000)
        # ChatPanel is in right sidebar — wait for mode buttons
        pg.wait_for_selector("text=Fast", timeout=30000)
        # Ensure Fast is active (default)
        pg.locator('input[placeholder*="Ask about"]').fill("Which repository does OwnerController depend on?")
        pg.keyboard.press("Enter")
        pg.wait_for_function("() => document.body.innerText.includes('OwnerRepository')", timeout=30000)
        assert "OwnerRepository" in pg.text_content("body")
        b.close()
