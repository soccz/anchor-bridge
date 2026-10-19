#!/usr/bin/env python3
"""공개 시연을 실제 Chrome에서 점검하고 문서용 화면을 캡처한다."""
import base64
import argparse
from functools import partial
import http.server
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import time
import urllib.request

import fitz
import websocket

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--portfolio", type=Path, help="선택: 포트폴리오 루트 index.html의 연결도 검사")
    args = parser.parse_args()
    output = ROOT / ".cache/browser"
    output.mkdir(parents=True, exist_ok=True)
    browser = shutil.which("google-chrome") or shutil.which("chromium")
    if not browser:
        raise RuntimeError("Chrome/Chromium이 필요합니다")

    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), partial(Handler, directory=str(ROOT / "site")))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_port}"
    file_base = (ROOT / "site").as_uri()
    checks, errors, requests = [], [], []
    with tempfile.TemporaryDirectory(prefix="profile-", dir=output) as temp:
        log = (output / "chrome.log").open("w")
        process = subprocess.Popen([browser, "--headless", "--no-sandbox", "--disable-gpu", "--no-first-run", "--no-proxy-server", "--disable-dev-shm-usage",
                                    "--no-default-browser-check", "--disable-background-networking", "--remote-debugging-port=0",
                                    "--user-data-dir=" + temp, "about:blank"], stdout=log, stderr=log)
        conn = None
        try:
            active = Path(temp) / "DevToolsActivePort"
            deadline = time.monotonic() + 35
            while not active.exists():
                if process.poll() is not None or time.monotonic() > deadline:
                    raise RuntimeError((output / "chrome.log").read_text()[-1800:])
                time.sleep(.1)
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            with opener.open(base + "/demo/", timeout=5) as response:
                assert response.status == 200
            print("PASS local HTTP preview", flush=True)
            port = active.read_text().splitlines()[0]
            targets = json.load(opener.open(f"http://127.0.0.1:{port}/json/list"))
            target = next(x for x in targets if x["type"] == "page")
            conn = websocket.create_connection(target["webSocketDebuggerUrl"], timeout=30, suppress_origin=True)
            serial = 0

            def call(method, params=None):
                nonlocal serial
                serial += 1
                conn.send(json.dumps({"id": serial, "method": method, "params": params or {}}))
                while True:
                    item = json.loads(conn.recv())
                    if item.get("method") == "Runtime.exceptionThrown":
                        errors.append(item["params"])
                    if item.get("method") == "Network.requestWillBeSent":
                        requests.append(item["params"]["request"]["url"])
                    if item.get("id") == serial:
                        if "error" in item:
                            raise RuntimeError(item["error"])
                        return item.get("result", {})

            def js(source):
                result = call("Runtime.evaluate", {"expression": source, "returnByValue": True, "awaitPromise": True})
                if "exceptionDetails" in result:
                    raise RuntimeError(result["exceptionDetails"])
                return result["result"].get("value")

            def check(name, source):
                if js(source) is not True:
                    state = js("JSON.stringify({status:document.querySelector('#status')?.value,records:document.querySelectorAll('.record').length,body:document.body.innerText.slice(0,600)})")
                    raise AssertionError(f"{name}: {state}; errors={errors}")
                checks.append(name)
                print("PASS", name, flush=True)

            def navigate(url, selector):
                print("OPEN", url, flush=True)
                call("Page.navigate", {"url": url})
                deadline = time.monotonic() + 15
                while time.monotonic() < deadline:
                    if js(f"document.readyState==='complete' && !!document.querySelector({json.dumps(selector)})"):
                        js("document.fonts.ready.then(()=>true)")
                        return
                    time.sleep(.1)
                raise AssertionError("Load failed: " + url)

            def viewport(width, height=1000):
                call("Emulation.setDeviceMetricsOverride", {"width": width, "height": height, "deviceScaleFactor": 1, "mobile": False})

            def shot(path, full=False):
                params = {"format": "png", "captureBeyondViewport": True}
                if full:
                    size = call("Page.getLayoutMetrics")["cssContentSize"]
                    params["clip"] = {"x": 0, "y": 0, "width": size["width"], "height": size["height"], "scale": 1}
                else:
                    size = js("({width:window.innerWidth,height:window.innerHeight})")
                    params["clip"] = {"x": 0, "y": 0, "width": size["width"], "height": size["height"], "scale": 1}
                path.write_bytes(base64.b64decode(call("Page.captureScreenshot", params)["data"]))

            call("Page.enable"); call("Runtime.enable"); call("Network.enable")
            call("Emulation.setEmulatedMedia", {"features": [{"name": "prefers-reduced-motion", "value": "reduce"}]})
            viewport(1440)
            navigate(file_base + "/demo/index.html", ".record")
            check("initial nine synthetic records", "document.querySelectorAll('.record').length===9 && document.body.textContent.includes('합성')")
            shot(ROOT / "site/assets/demo-preview.png")
            for state, count in (("검토 후보", 3), ("추가 확인", 2), ("제외", 4)):
                js(f"document.querySelector('#status').value={json.dumps(state)};document.querySelector('#status').dispatchEvent(new Event('change'))")
                check("filter " + state, f"document.querySelectorAll('.record').length==={count}")
            js("document.querySelector('#reset').click();document.querySelector('#search').value='없는지역';document.querySelector('#search').dispatchEvent(new Event('input'))")
            check("empty search removes stale candidate", "document.querySelectorAll('.record').length===0 && !document.querySelector('#open-review')")
            js("document.querySelector('#reset').click()")
            for case, count in (("가온시", 3), ("누리군", 2), ("다온시", 2)):
                js(f"document.querySelector('[data-case=\"{case}\"]').click()")
                check("case " + case, f"document.querySelectorAll('.record').length==={count}")
            js("document.querySelector('[data-id=\"daon-bakery\"]').click()")
            check("age candidate retains missing supply", "document.querySelector('#detail').textContent.includes('연령 실험') && (document.querySelector('#detail').textContent.match(/미확인/g)||[]).length>=2")
            js("document.querySelector('#reset').click()")
            ids = js("JSON.parse(document.querySelector('#synthetic-data').textContent).map(r=>r.id)")
            for rid in ids:
                js(f"document.querySelector('[data-id=\"{rid}\"]').click();document.querySelector('#open-review').click()")
                check("review contains " + rid, f"document.querySelector('#review').open && document.querySelector('#review-body').textContent.includes('{rid}')")
                js("document.body.classList.add('print-review')")
                printed = call("Page.printToPDF", {"printBackground": True, "preferCSSPageSize": True})
                payload = base64.b64decode(printed["data"])
                doc = fitz.open(stream=payload, filetype="pdf")
                assert len(doc) == 1, (rid, "review page count", len(doc))
                text = doc[0].get_text()
                assert rid in text and "합성" in text and "현장 확인" in text
                if rid == "gaon-meal":
                    (output / "review.pdf").write_bytes(payload)
                js("document.body.classList.remove('print-review');document.querySelector('#close-review').click()")
            check("focus returns after closing review", "document.activeElement.id==='open-review'")
            js("document.querySelector('#open-review').click()")
            call("Input.dispatchKeyEvent", {"type": "keyDown", "key": "Escape", "code": "Escape", "windowsVirtualKeyCode": 27})
            call("Input.dispatchKeyEvent", {"type": "keyUp", "key": "Escape", "code": "Escape", "windowsVirtualKeyCode": 27})
            check("Escape closes modal", "!document.querySelector('#review').open")
            for width in (375, 390, 768, 1440):
                viewport(width)
                check(f"demo no horizontal overflow {width}", "document.documentElement.scrollWidth<=window.innerWidth+1")
                if width == 390:
                    shot(output / "demo-mobile.png", full=True)
            navigate(file_base + "/demo/index.html?case=" + urllib.parse.quote("누리군"), ".record")
            check("deep link opens requested case", "document.querySelectorAll('.record').length===2 && document.querySelector('[data-case=\"누리군\"]').getAttribute('aria-pressed')==='true'")
            # Isolated single-file check: no HTTP and no neighbouring files.
            alone = output / "standalone"
            alone.mkdir(exist_ok=True)
            shutil.copyfile(ROOT / "site/demo/index.html", alone / "demo.html")
            call("Network.setBlockedURLs", {"urls": ["http://*", "https://*"]})
            before = len(requests)
            navigate((alone / "demo.html").as_uri(), ".record")
            check("offline single-file demo", "document.querySelectorAll('.record').length===9")
            js("document.querySelector('#open-review').click()")
            check("offline review works", "document.querySelector('#review').open")
            assert not [url for url in requests[before:] if url.startswith(("http://", "https://"))]
            call("Network.setBlockedURLs", {"urls": []})
            viewport(1440)
            navigate(file_base + "/index.html", "#case-panel h3")
            js("document.querySelector('[data-choice=\"snack\"]').click()")
            check("hero choice changes explanation", "document.querySelector('#hero-decision').textContent.includes('역행')")
            js("document.querySelector('[data-choice=\"meal\"]').click()")
            for key, expected in (("base", "가온시"), ("life", "누리군"), ("age", "다온시")):
                js(f"document.querySelector('[data-perspective=\"{key}\"]').click()")
                check("perspective " + key, f"document.querySelector('#case-panel').textContent.includes('{expected}')")
            js("document.querySelector('[data-perspective=\"base\"]').click()")
            js("Promise.all([...document.images].map(async image=>{image.loading='eager';await image.decode()})).then(()=>true)")
            check("all landing images loaded", "[...document.images].every(image=>image.complete&&image.naturalWidth>0)")
            for width in (375, 390, 768, 1440):
                viewport(width)
                check(f"landing no horizontal overflow {width}", "document.documentElement.scrollWidth<=window.innerWidth+1")
                if width in (390, 1440):
                    shot(output / f"landing-{width}.png", full=True)
            viewport(1200, 630)
            js("window.scrollTo(0,0)")
            shot(ROOT / "site/assets/og.png")
            if args.portfolio:
                call("Network.setBlockedURLs", {"urls": ["http://*", "https://*"]})
                viewport(1440)
                navigate((args.portfolio.resolve() / "index.html").as_uri(), ".cat-card")
                js("showPage('blog');renderSidebar('project')")
                check("portfolio card routes to case study", "!!document.querySelector('.post-card[data-url=\"/projects/anchor-bridge/\"]')")
                check("portfolio card shows Korean project title", "document.querySelector('.post-card[data-url=\"/projects/anchor-bridge/\"]').textContent.includes('빵집 다음엔 어디로?')")
                check("project remains discoverable without GitHub API", "allRepos.some(r=>r.name==='anchor-bridge') && getCat('anchor-bridge')==='project'")
                # API result takes precedence over static fallback: presentation must still match.
                js("allRepos=mergeStaticProjects([{name:'anchor-bridge',description:null,language:'Python',pushed_at:'2026-10-19T09:00:00Z'}]);renderSidebar('project')")
                check("live repository metadata keeps title and description", "document.querySelector('.post-card[data-url=\"/projects/anchor-bridge/\"]').textContent.includes('공개용 PDF') && document.querySelector('.post-card[data-url=\"/projects/anchor-bridge/\"]').textContent.includes('빵집 다음엔 어디로?')")
                shot(output / "portfolio-project.png")
                viewport(390)
                check("portfolio mobile no horizontal overflow", "document.documentElement.scrollWidth<=window.innerWidth+1")
            assert not errors, errors
            (output / "results.json").write_text(json.dumps({"checks": checks, "printed_candidates": ids, "runtime_errors": errors}, ensure_ascii=False, indent=2))
            print(f"PASS {len(checks)} browser assertions and {len(ids)} one-page reviews")
        finally:
            if conn:
                conn.close()
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill(); process.wait()
            log.close()
            server.shutdown(); server.server_close()


if __name__ == "__main__":
    main()
