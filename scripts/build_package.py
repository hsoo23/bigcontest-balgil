"""제출 패키지를 묶고 첨부 용량을 센다 → reports/package/ (제출요건 6-2 첨부 목록).

**왜 스크립트인가.** 제출 메일 첨부가 여덟 개다. 손으로 묶으면 10/26 아침에 하나를 빠뜨리거나
용량이 넘는 것을 그때 안다. 「보내기 전 확인」 6번이 **첨부 합계 25MB 아래인가**인데, 재 보려면
먼저 묶여 있어야 한다. 그래서 묶는 것과 세는 것을 같이 한다.

만드는 것 (reports/package/)
  발길_재현코드.zip          git 이 추적하는 파일에서 data/external 과 reports/발길_* 를 뺀 것
                            (외부 원본과 제출본은 따로 나가므로 두 번 넣지 않는다 — PPTX 하나가 2.5MB 다)
  발길_외부데이터원본.zip     data/external/** — 10종 · 출처와 SHA-256 은 docs/external_data.md
  발길_가상데이터.zip         data/synthetic/** — 파일명과 「비고」 열에 「가상」이 붙어 있다
  발길_화면캡처.zip          reports/screens/*.png — **capture_screens.py 를 먼저 돌려야 한다**
  발길_E5…·E6….html         PDF 로 뜨기 위한 HTML (build_report.to_html 과 같은 서식)

**여기서 못 만드는 것**도 같이 찍는다 — 사람이 해야 하는 자리를 숨기지 않는다.
  발표자료 PDF     구글 슬라이드에서 내려받는다(원고는 build_slides_pptx.py 로 만든 PPTX)
  보고서·설계자료 PDF  브라우저에서 HTML 을 열어 「인쇄 → PDF로 저장」
  상가 강원 CSV zip   원본이 현수 PC 에만 있다
  큰 외부 원본 2종    합계 436.9MB 라 메일로 못 보낸다(#40 ③, 메일 3번 문단)

실행: python scripts/build_package.py [--open]
"""
from __future__ import annotations

import argparse
import subprocess
import zipfile
from pathlib import Path

from build_report import to_html

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "package"
MAIL_LIMIT = 25 * 1024 * 1024          # 「보내기 전 확인」 6번

DESIGN = [("발길_E5_가상데이터생성설계자료", ROOT / "docs" / "draft" / "E5_가상데이터설계자료.md"),
          ("발길_E6_LLM활용설계자료", ROOT / "docs" / "draft" / "E6_LLM활용설계자료.md")]

ELSEWHERE = [("발길_발표자료.pdf", "구글 슬라이드에서 내려받기 — 원고는 reports/발길_발표자료.pptx"),
             ("발길_분석보고서.pdf", "reports/발길_분석보고서.html 을 브라우저에서 [인쇄 → PDF로 저장]"),
             ("발길_E5_가상데이터생성설계자료.pdf", "아래에서 만든 HTML 을 같은 방법으로"),
             ("발길_E6_LLM활용설계자료.pdf", "아래에서 만든 HTML 을 같은 방법으로"),
             ("발길_외부데이터원본_상가강원.zip", "원본이 현수 PC 에만 있습니다 (62.6MB → zip 13.3MB)"),
             ("(메일 3번) 큰 외부 원본 2종", "합계 436.9MB 라 첨부하지 않고 본문에 적습니다 (#40 ③)")]


def tracked() -> list[Path]:
    out = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True)
    return [ROOT / f for f in out.stdout.decode("utf-8").split("\0") if f]


def zip_files(name: str, files: list[Path], base: Path = ROOT) -> Path | None:
    files = [f for f in files if f.is_file()]
    if not files:
        return None
    p = OUT / name
    with zipfile.ZipFile(p, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for f in sorted(files):
            z.write(f, f.relative_to(base).as_posix())
    return p


def mb(n: int) -> str:
    return f"{n / 1048576:.2f} MB"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    files = tracked()
    ext = [f for f in files if "data/external/" in f.as_posix()]
    # 따로 첨부로 나가는 제출본은 코드 zip 에 또 넣지 않는다 — PPTX 하나가 2.5MB 다.
    # 그림(reports/figures)은 남긴다. 보고서가 그 파일을 가리키고 다시 그릴 수 있어야 한다
    out = [f for f in files if f.parent.name == "reports" and f.name.startswith("발길_")]
    code = [f for f in files if f not in set(ext) | set(out)]
    syn = sorted((ROOT / "data" / "synthetic").glob("*")) if (ROOT / "data" / "synthetic").exists() else []
    shots = sorted((ROOT / "reports" / "screens").glob("*.png")) if (ROOT / "reports" / "screens").exists() else []

    made, missing = [], []
    for name, group in [("발길_재현코드.zip", code), ("발길_외부데이터원본.zip", ext),
                        ("발길_가상데이터.zip", syn), ("발길_화면캡처.zip", shots)]:
        p = zip_files(name, group)
        (made.append((name, p, len(group))) if p else missing.append(name))

    for name, src in DESIGN:
        if src.exists():
            p = OUT / f"{name}.html"
            p.write_text(to_html(src.read_text(encoding="utf-8")), encoding="utf-8")
            made.append((p.name, p, 1))

    for extra in ["발길_분석보고서.html", "발길_발표자료.pptx"]:
        p = ROOT / "reports" / extra
        if p.exists():
            made.append((extra + "  (reports/)", p, 1))

    print("■ 만든 것")
    total = 0
    for name, p, n in made:
        sz = p.stat().st_size
        if name.endswith(".zip"):
            total += sz
        print(f"  {name:40s} {n:4d}개  {mb(sz):>10s}")
    print(f"  {'zip 합계':40s} {'':4s}  {mb(total):>10s}   (메일 한도 25MB "
          f"{'아래 — 한 통으로 보냅니다' if total < MAIL_LIMIT else '초과 — 「1/2 · 2/2」로 나눕니다'})")

    if missing:
        print("\n■ 아직 못 만든 것")
        for name in missing:
            why = "python scripts/capture_screens.py 를 먼저 돌려야 합니다 (현수, 체크리스트 9번)" \
                if "화면캡처" in name else "원본이 없습니다"
            print(f"  {name:40s} {why}")

    print("\n■ 여기서 만들 수 없는 것 — 사람이 해야 합니다")
    for name, how in ELSEWHERE:
        print(f"  {name:40s} {how}")


if __name__ == "__main__":
    main()
