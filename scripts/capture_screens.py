"""담당자 화면 4개를 PNG로 캡처한다 → reports/screens/ (제출 체크리스트 9번, D3).

화면을 손으로 찍으면 창 크기·스크롤·지도 타일 로딩이 매번 달라 발표자료와 보고서의 그림이 어긋난다.
이 스크립트가 streamlit을 직접 띄우고 ?screen=1~4 로 한 화면씩 같은 창 크기에서 찍는다.

실행: python scripts/capture_screens.py [--screens 1 3] [--port 8766] [--width 1440] [--scale 2]
의존: 화면 라이브러리(app/requirements-app.txt) + playwright (캡처 전용이라 requirements에 넣지 않는다)
      pip install playwright==1.55.0 && python -m playwright install chromium
산출: reports/screens/screen{1..4}.png  (화면 ①은 시연 기준일 DEMO_AS_OF 주가 기본값으로 찍힌다)
주의: 화면 ③ 배경 지도(Esri 타일)는 인터넷이 있어야 그려진다. 없으면 동 경계·시설 점만 찍힌다.
"""
from __future__ import annotations

import argparse
import asyncio
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "screens"
NAMES = {"1": "주간 브리핑", "2": "발길 상세", "3": "터전 지도", "4": "보정 전·후"}


def wait_up(url: str, timeout: float = 90) -> None:
    end = time.time() + timeout
    while time.time() < end:
        try:
            with urllib.request.urlopen(f"{url}/_stcore/health", timeout=3) as r:
                if r.status == 200:
                    return
        except OSError:
            time.sleep(1)
    raise RuntimeError(f"streamlit이 {timeout:.0f}초 안에 뜨지 않았습니다 ({url})")


async def shoot(url: str, screens: list[str], width: int, scale: int) -> None:
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch(headless=True)
        except Exception:  # playwright 브라우저를 받지 않은 PC면 설치된 크롬으로 찍는다
            browser = await p.chromium.launch(channel="chrome", headless=True)
        page = await browser.new_page(viewport={"width": width, "height": 1000}, device_scale_factor=scale)
        for n in screens:
            await page.goto(f"{url}/?screen={n}")
            await page.wait_for_selector(".bg-h", timeout=90_000)  # 화면 제목(style.heading)이 그려질 때까지
            await page.wait_for_load_state("networkidle")
            await page.wait_for_timeout(6_000 if n == "3" else 3_000)  # 차트 애니메이션·지도 타일
            # streamlit은 페이지가 아니라 안쪽 영역이 스크롤돼 full_page가 첫 화면만 찍는다 → 창을 내용 높이로 늘린다
            h = await page.evaluate("() => document.querySelector('[data-testid=\"stMainBlockContainer\"]')"
                                    ".getBoundingClientRect().bottom + window.scrollY")
            await page.set_viewport_size({"width": width, "height": int(h) + 40})
            await page.wait_for_timeout(1_500)
            path = OUT / f"screen{n}.png"
            await page.screenshot(path=str(path), full_page=True)
            print(f"  화면 {n} {NAMES[n]} → {path.relative_to(ROOT)}")
        await browser.close()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--screens", nargs="+", default=list(NAMES), choices=list(NAMES))
    ap.add_argument("--port", type=int, default=8766)
    ap.add_argument("--width", type=int, default=1440, help="창 너비(px). 발표자료 16:9 한 장에 맞춘 값")
    ap.add_argument("--scale", type=int, default=2, help="픽셀 배율. 2면 슬라이드에서 글자가 흐려지지 않는다")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    url = f"http://localhost:{a.port}"
    with socket.socket() as s:  # 이미 떠 있는 다른 화면(다른 브랜치일 수 있다)을 찍지 않게 막는다
        if s.connect_ex(("localhost", a.port)) == 0:
            sys.exit(f"포트 {a.port}을 이미 다른 프로그램이 쓰고 있습니다. --port로 비어 있는 포트를 주세요.")
    proc = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", str(ROOT / "app" / "balgil_app.py"), "--server.headless", "true",
         "--server.port", str(a.port)], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        wait_up(url)
        print(f"캡처 {len(a.screens)}장 ({a.width}px × {a.scale}배)")
        asyncio.run(shoot(url, a.screens, a.width, a.scale))
    finally:
        proc.terminate()
        proc.wait(timeout=10)


if __name__ == "__main__":
    main()
