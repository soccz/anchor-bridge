#!/usr/bin/env python3
"""직접 작성한 합성 예시와 문서 소스에서 공개 자료만 생성한다."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from analysis.synthetic import records, studies


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", action="store_true", help="WeasyPrint로 공개 PDF도 생성")
    args = parser.parse_args()
    target = ROOT / "site"
    for folder in (target, target / "demo", target / "documents", target / "assets"):
        folder.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / "web/styles.css", target / "styles.css")
    payload = json.dumps(studies(), ensure_ascii=False)
    landing = (ROOT / "web/index.html").read_text().replace("__STUDIES__", payload)
    (target / "index.html").write_text(landing)
    css = (ROOT / "web/styles.css").read_text()
    template = (ROOT / "web/demo.template.html").read_text()
    demo = (template.replace("__CSS__", css).replace("__DATA__", json.dumps(records(), ensure_ascii=False))
            .replace("__STUDIES__", payload).replace("__APP__", (ROOT / "web/app.js").read_text()))
    (target / "demo/index.html").write_text(demo)
    if args.pdf:
        if not (target / "assets/demo-preview.png").is_file():
            raise RuntimeError("먼저 scripts/check_browser.py로 실제 시연 화면을 캡처하세요")
        for source, dest in (("brief", "AnchorBridge_Public_Brief"), ("methods", "AnchorBridge_Public_Methods")):
            subprocess.run(["weasyprint", str(ROOT / f"documents/{source}.html"),
                            str(target / f"documents/{dest}.pdf")], check=True)
    print("Built public site:", target)


if __name__ == "__main__":
    main()
