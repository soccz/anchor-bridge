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
                    js("window.scrollTo(0,0)")
                    size = call("Page.getLayoutMetrics")["cssContentSize"]
                    params["clip"] = {"x": 0, "y": 0, "width": size["width"], "height": size["height"], "scale": 1}
                else:
                    size = js("({width:window.innerWidth,height:window.innerHeight,y:window.scrollY})")
                    params["clip"] = {"x": 0, "y": size["y"], "width": size["width"], "height": size["height"], "scale": 1}
                path.write_bytes(base64.b64decode(call("Page.captureScreenshot", params)["data"]))

            call("Page.enable"); call("Runtime.enable"); call("Network.enable")
            call("Emulation.setEmulatedMedia", {"features": [{"name": "prefers-reduced-motion", "value": "reduce"}]})
            viewport(1440, 1000)
            navigate(file_base + "/demo/index.html", ".choice")
            check("guided choice before explorer", "document.querySelectorAll('.choice').length===2 && !document.querySelector('#explorer').open && document.querySelector('[data-step=\"1\"]').disabled")
            shot(ROOT / "site/assets/demo-preview.png")
            shot(output / "demo-start-desktop.png")
            viewport(390, 844)
            check("first choice visible on mobile", "document.querySelector('.choice').getBoundingClientRect().bottom < 844")
            shot(output / "demo-start-mobile.png")
            js("document.querySelector('[data-pick=\"gaon-snack\"]').click()")
            check("mobile click brings verdict into view", "document.querySelector('.selection-result').getBoundingClientRect().bottom<=window.innerHeight+2")
            check("snack shows reason before proceeding", "document.querySelector('.selection-result').textContent.includes('제외') && !document.querySelector('[data-step=\"1\"]').disabled")
            js("document.querySelector('[data-pick=\"gaon-meal\"]').click();document.querySelector('[data-next]').click()")
            check("raw denominator gives 0.88", "document.querySelector('#denominator-proof').textContent.includes('0.88')")
            js("document.querySelector('[data-basis=\"1\"]').click()")
            check("both denominators change", "document.querySelector('#denominator-proof').textContent.includes('1.32') && document.querySelector('#denominator-proof').textContent.includes('9,000')")
            shot(output / "demo-proof-mobile.png", full=True)
            viewport(1440)
            shot(output / "demo-proof-desktop.png")
            js("document.querySelector('[data-next]').click()")
            js("document.querySelector('[data-check=\"0\"]').click();document.querySelector('#field-note').value='현장 메모 <script>실행 금지</script> & 협의';document.querySelector('#field-note').dispatchEvent(new Event('input'));document.querySelector('#story-review').click()")
            check("review preserves safe memo and check", "document.querySelector('#review-body').textContent.includes('☑') && document.querySelector('.review-memo').textContent.includes('<script>') && !document.querySelector('#review-body script')")
            js("document.querySelector('#close-review').click()")
            check("focus returns to story review", "document.activeElement.id==='story-review'")
            viewport(390, 844)
            js("document.querySelector('[data-case=\"life\"]').click()")
            check("life exception begins excluded", "document.querySelector('#story').textContent.includes('검토 대상에서 제외')")
            js("document.querySelector('[data-life=\"1\"]').click();document.querySelector('[data-next]').click()")
            check("composition before reweighting", "document.querySelector('#composition-proof').textContent.includes('34')")
            js("document.querySelector('[data-common=\"1\"]').click()")
            check("common weights change gap to 18pp", "document.querySelector('#composition-proof').textContent.includes('18') && document.querySelector('#composition-proof').textContent.includes('36.0%')")
            check("exception retains partner exclusion", "document.querySelector('.compare-table').textContent.includes('0.92') && document.querySelector('.compare-table').textContent.includes('제외')")
            viewport(1440)
            shot(output / "demo-life-desktop.png")
            js("document.querySelector('[data-case=\"age\"]').click();document.querySelector('[data-age=\"1\"]').click()")
            check("age condition produces hold not approval", "document.querySelector('#story').textContent.includes('추가 확인') && document.querySelector('#story').textContent.includes('미확인')")
            js("document.querySelector('[data-next]').click()")
            check("age supply not copied from base partner", "(document.querySelector('#story').textContent.match(/미확인/g)||[]).length>=2 && document.querySelector('#story').textContent.includes('10곳')")
            shot(output / "demo-age-desktop.png")
            js("document.querySelector('[data-next]').click();document.querySelector('#story-review').click()")
            check("age review keeps distinct partner", "document.querySelector('#review-body').textContent.includes('제과점') && (document.querySelector('#review-body').textContent.match(/미확인/g)||[]).length>=2")
            call("Input.dispatchKeyEvent", {"type":"keyDown","key":"Escape","code":"Escape","windowsVirtualKeyCode":27})
            call("Input.dispatchKeyEvent", {"type":"keyUp","key":"Escape","code":"Escape","windowsVirtualKeyCode":27})
            check("Escape dismisses review", "!document.querySelector('#review').open")
            js("document.querySelector('#explorer').open=true")
            check("nine searchable records", "document.querySelectorAll('.record').length===9")
            for state, count in (("검토 후보",3),("추가 확인",2),("제외",4)):
                js(f"document.querySelector('#status').value={json.dumps(state)};document.querySelector('#status').dispatchEvent(new Event('change'))")
                check("filter " + state, f"document.querySelectorAll('.record').length==={count}")
            js("document.querySelector('#reset').click();document.querySelector('#search').value='없는지역';document.querySelector('#search').dispatchEvent(new Event('input'))")
            check("empty search clears detail", "document.querySelectorAll('.record').length===0 && !document.querySelector('#open-review')")
            js("document.querySelector('#reset').click()")
            ids=js("JSON.parse(document.querySelector('#synthetic-data').textContent).map(r=>r.id)")
            for rid in ids:
                js(f"document.querySelector('[data-id=\"{rid}\"]').click();document.querySelector('#open-review').click()")
                check("review " + rid, f"document.querySelector('#review').open && document.querySelector('#review-body').textContent.includes('{rid}')")
                js("document.body.classList.add('print-review')")
                printed=call("Page.printToPDF", {"printBackground":True,"preferCSSPageSize":True})
                payload=base64.b64decode(printed["data"])
                doc=fitz.open(stream=payload,filetype="pdf")
                assert len(doc)==1, (rid,len(doc))
                assert rid in doc[0].get_text() and "현장" in doc[0].get_text()
                if rid=='gaon-meal': (output/'review.pdf').write_bytes(payload)
                js("document.body.classList.remove('print-review');document.querySelector('#close-review').click()")
            check("focus returns to explorer", "document.activeElement.id==='open-review'")
            for width in (375,390,768,1440):
                viewport(width)
                check(f"demo width {width}", "document.documentElement.scrollWidth<=window.innerWidth+1")
                if width==390:
                    check("mobile explorer detail before records", "document.querySelector('#detail').getBoundingClientRect().top < document.querySelector('#records').getBoundingClientRect().top")
            # Exercise maximum memo length at print size.
            js("document.querySelector('#explorer').open=false;document.querySelector('[data-case=\"base\"]').click();document.querySelector('[data-pick=\"gaon-meal\"]').click();document.querySelector('[data-step=\"2\"]').click();document.querySelector('#field-note').value='현장 확인 메모입니다. '.repeat(18).slice(0,180);document.querySelector('#field-note').dispatchEvent(new Event('input'));document.querySelector('#story-review').click();document.body.classList.add('print-review')")
            printed=call("Page.printToPDF", {"printBackground":True,"preferCSSPageSize":True})
            assert len(fitz.open(stream=base64.b64decode(printed['data']),filetype='pdf'))==1
            js("document.body.classList.remove('print-review');document.querySelector('#close-review').click()")
            navigate(file_base+'/demo/index.html?case=age','.case-tab')
            check("deep link selects age case", "document.querySelector('[data-case=\"age\"]').getAttribute('aria-pressed')==='true'")
            alone=output/'standalone';alone.mkdir(exist_ok=True)
            shutil.copyfile(ROOT/'site/demo/index.html',alone/'demo.html')
            call('Network.setBlockedURLs',{'urls':['http://*','https://*']})
            before=len(requests)
            navigate((alone/'demo.html').as_uri(),'.choice')
            js("document.querySelector('[data-pick=\"gaon-meal\"]').click();document.querySelector('[data-step=\"2\"]').click();document.querySelector('#story-review').click()")
            check("standalone offline review", "document.querySelector('#review').open")
            assert not [u for u in requests[before:] if u.startswith(('http://','https://'))]
            call('Network.setBlockedURLs',{'urls':[]})
            viewport(1440)
            navigate(file_base+'/index.html','#hero-proof')
            js("document.querySelector('[data-choice=\"snack\"]').click()")
            check("landing comparison changes rationale", "document.querySelector('#hero-proof').textContent.includes('탐색적 제외')")
            js("document.querySelector('[data-choice=\"meal\"]').click()")
            js("Promise.all([...document.images].map(async i=>{i.loading='eager';await i.decode()})).then(()=>true)")
            check("landing all images loaded", "[...document.images].every(i=>i.complete&&i.naturalWidth>0)")
            check("PDF previews preserve page proportions", "[...document.querySelectorAll('.document img')].every(i=>Math.abs(i.clientWidth/i.clientHeight-i.naturalWidth/i.naturalHeight)<.02)")
            for width in (375,390,768,1440):
                viewport(width)
                check(f"landing width {width}", "document.documentElement.scrollWidth<=window.innerWidth+1")
                if width in (390,1440): shot(output/f'landing-{width}.png',full=True)
            viewport(1200,630);js('window.scrollTo(0,0)');shot(ROOT/'site/assets/og.png')
            if args.portfolio:
                call('Network.setBlockedURLs',{'urls':['http://*','https://*']})
                viewport(1440)
                navigate((args.portfolio.resolve()/'index.html').as_uri(),'.cat-card')
                js("showPage('blog');renderSidebar('project')")
                check("portfolio entry routes to project", "!!document.querySelector('.post-card[data-url=\"/projects/anchor-bridge/\"]')")
                shot(output/'portfolio-project.png')
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
