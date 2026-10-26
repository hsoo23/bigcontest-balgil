"""HTML 제출물을 PDF 로 뜬다 → reports/package/*.pdf (크롬 헤드리스).

**왜 크롬인가.** 이 PC 에 pandoc·wkhtmltopdf·LibreOffice 가 없다. 브라우저의 인쇄가
한글 글꼴과 표를 가장 잘 뽑는데, 「인쇄 → PDF로 저장」은 사람이 창을 눌러야 한다.
크롬은 `--headless --print-to-pdf` 로 **창 없이 같은 엔진**으로 뽑아 주므로, 제출일 아침에
사람이 네 번 누르지 않아도 된다. 쪽 나눔·표 쪼개짐은 build_report.py 가 넣은 CSS 가 잡는다.

**머리글·꼬리글은 끈다**(`--no-pdf-header-footer`). 켜 두면 쪽마다 `file:///C:/Users/...` 와
날짜가 박혀 제출물에 로컬 경로가 들어간다.

만드는 것
  발길_분석보고서.pdf              reports/발길_분석보고서.html (build_report.py --html)
  발길_E5_가상데이터생성설계자료.pdf   reports/package/*.html (build_package.py)
  발길_E6_LLM활용설계자료.pdf

**발표자료 PDF 는 여기서 못 만든다** — 원고는 PPTX 이고(build_slides_pptx.py), 구글
슬라이드로 가져와 꾸민 뒤 거기서 내려받는 것이 본 제출물이다. PPTX → PDF 변환기
(LibreOffice)가 이 PC 에 없기도 하다.

실행: python scripts/build_pdf.py          (먼저 build_report.py --html · build_package.py)
의존: 크롬. 아래 CHROME 목록에서 찾는다. 없으면 어디를 봤는지 적고 멈춘다.
"""
from __future__ import annotations

import sys

# 한글 윈도우 콘솔은 기본이 cp949 라 「—」 같은 글자에서 print 가 죽는다(#122).
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import subprocess
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "reports" / "package"

CHROME = [
    Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
    Path.home() / r"AppData\Local\Google\Chrome\Application\chrome.exe",
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
    Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
]

JOBS = [("발길_분석보고서", ROOT / "reports" / "발길_분석보고서.html"),
        ("발길_E5_가상데이터생성설계자료", PKG / "발길_E5_가상데이터생성설계자료.html"),
        ("발길_E6_LLM활용설계자료", PKG / "발길_E6_LLM활용설계자료.html")]


def chrome() -> Path:
    for p in CHROME:
        if p.exists():
            return p
    raise SystemExit("크롬을 찾지 못했습니다. 본 곳:\n  " + "\n  ".join(str(p) for p in CHROME))


def to_pdf(exe: Path, src: Path, out: Path) -> None:
    url = "file:///" + urllib.parse.quote(src.as_posix().lstrip("/"))
    subprocess.run([str(exe), "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                    f"--print-to-pdf={out}", url], check=True, capture_output=True, timeout=300)


def main() -> None:
    exe = chrome()
    PKG.mkdir(parents=True, exist_ok=True)
    print(f"크롬: {exe}")
    total, missing = 0, []
    for name, src in JOBS:
        if not src.exists():
            missing.append(f"{name} — {src.relative_to(ROOT)} 가 없습니다")
            continue
        out = PKG / f"{name}.pdf"
        to_pdf(exe, src, out)
        total += out.stat().st_size
        print(f"  {name + '.pdf':40s} {out.stat().st_size / 1048576:8.2f} MB")
    print(f"  {'PDF 셋 합계':40s} {total / 1048576:8.2f} MB")
    for m in missing:
        print("  ! " + m)
    print("\n발표자료 PDF 는 구글 슬라이드에서 내려받습니다 — 원고는 reports/발길_발표자료.pptx")


if __name__ == "__main__":
    main()
