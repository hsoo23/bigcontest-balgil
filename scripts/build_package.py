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

**여기서 만들지 않는 것**도 같이 찍는다 — 빠진 자리를 숨기지 않는다.
  발표자료 PDF     구글 슬라이드에서 내려받는다(원고는 build_slides_pptx.py 로 만든 PPTX)
  보고서·설계자료 PDF  scripts/build_pdf.py 가 크롬 헤드리스로 뜬다
  상가 강원 CSV zip   원본이 현수 PC 에만 있다
  큰 외부 원본 2종    서울 CSV · SGIS shp 세트 437.1MB 라 메일로 못 보낸다(#40 ③, 메일 3번 문단)

실행: python scripts/build_package.py [--open]
"""
from __future__ import annotations

import sys

# 한글 윈도우 콘솔은 기본이 cp949 라 「—」 같은 글자에서 print 가 죽는다.
# 결과 파일은 이미 만들어진 뒤라 멀쩡한데 Traceback 만 보고 실패로 읽히므로, 출력만 UTF-8 로 돌린다.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import argparse
import hashlib
import subprocess
import zipfile
from pathlib import Path

from build_report import to_html

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "package"
MAIL_LIMIT = 25 * 1024 * 1024          # 「보내기 전 확인」 6번
GANGWON_ZIP = 13.3 * 1024 * 1024       # 상가 강원 CSV zip — #112 에서 첨부로 정했고 수경이 잰 값
# #121 에서 정한 두 길. 「링크」 안으로 가면 아래 둘은 메일 본문 링크로 나가므로
# 첨부 합계에서 빠진다. 어느 쪽으로 정해도 그날 다시 고치지 않도록 **두 값을 같이 찍는다**
LINKED = ("발길_화면캡처.zip", "발길_외부데이터원본_상가강원.zip")
# zip 항목의 시각을 이 값으로 고정한다 — 묶는 PC 가 달라도 해시가 같아야 메일에 적을 수 있다
ZIP_EPOCH = (2026, 10, 26, 0, 0, 0)
# 코드 zip 에서 뺄 것. 제출본·캡처는 따로 첨부로 나가고(두 번 보내지 않는다),
# 아래 셋은 심사위원에게 보낼 글이 아니다(옛 문서 · 노션 파생물 · 깃허브 설정)
CODE_SKIP = ("reports/screens/", "docs/archive/", "docs/notion/", ".github/")

DESIGN = [("발길_E5_가상데이터생성설계자료", ROOT / "docs" / "draft" / "E5_가상데이터설계자료.md"),
          ("발길_E6_LLM활용설계자료", ROOT / "docs" / "draft" / "E6_LLM활용설계자료.md")]

ELSEWHERE = [("발길_발표자료.pdf", "구글 슬라이드에서 내려받기 — 원고는 reports/발길_발표자료.pptx"),
             ("발길_분석보고서.pdf", "python scripts/build_pdf.py — 크롬 헤드리스로 뜹니다(요약판 약 15쪽 · 3MB)"),
             ("발길_E5_가상데이터생성설계자료.pdf", "python scripts/build_pdf.py (0.37MB · 9쪽)"),
             ("발길_E6_LLM활용설계자료.pdf", "python scripts/build_pdf.py (0.24MB · 5쪽)"),
             ("발길_외부데이터원본_상가강원.zip", "이 PC 에 원본이 없습니다. data/external/sbiz_store/ 에 강원 CSV 가 있는 PC(수경·현수)에서 돌리면 여기서 묶입니다"),
             ("(메일 3번) 큰 외부 원본 2종", "서울 CSV · SGIS shp 세트 437.1MB — 드라이브 폴더에 올리고 메일에는 링크와 SHA-256 만 (#124)")]


def tracked() -> list[Path]:
    """git 이 추적하는 파일. 머지 충돌 중에는 한 파일이 단계별로 여러 번 나오므로 겹치는 것을 지운다."""
    out = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True)
    names = dict.fromkeys(n for n in out.stdout.decode("utf-8").split(chr(0)) if n)
    return [ROOT / n for n in names]


def zip_files(name: str, files: list[Path], base: Path = ROOT) -> Path | None:
    """파일을 묶는다. **누가 묶어도 바이트가 같게** 파일 시각을 고정한다.

    zip 은 항목마다 원본의 수정 시각을 담으므로, 같은 CSV 를 묶어도 PC 마다 해시가 달라진다
    (수경 PC `1efe6fe1…` · 현수 Mac `49283bb9…`, 크기는 13,346,057바이트로 같음 — #123 현수 리뷰).
    큰 파일을 드라이브 링크로 내기로 했고(#121) 메일 본문에 **zip 의 SHA-256 을 적어** 마감 뒤에
    바뀌지 않았음을 보이기로 했으니, 묶는 사람이 바뀌면 해시가 달라지는 것은 곤란하다.
    """
    files = [f for f in files if f.is_file()]
    if not files:
        return None
    p = OUT / name
    with zipfile.ZipFile(p, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for f in sorted(files):
            info = zipfile.ZipInfo(f.relative_to(base).as_posix(), date_time=ZIP_EPOCH)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16          # 권한도 고정한다 — 윈도우와 맥이 다르다
            z.writestr(info, f.read_bytes(), compresslevel=9)
    return p


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


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
    # 단, 상세판 HTML(10/26)은 첨부로 나가지 않으므로 코드 zip 에 넣는다 — 요약판 보고서가 그 파일을 가리킨다
    out = [f for f in files if f.parent.name == "reports" and f.name.startswith("발길_") and "상세판.html" not in f.name]
    skip = set(ext) | set(out) | {f for f in files if any(s in f.as_posix() for s in CODE_SKIP)}
    code = [f for f in files if f not in skip]
    syn = sorted((ROOT / "data" / "synthetic").glob("*")) if (ROOT / "data" / "synthetic").exists() else []
    # 상가 강원 CSV 는 git 에 없지만(62.6MB) 원본이 있는 PC 에서는 여기서 묶는다 —
    # 그래야 25MB 판정이 「실제로 보낼 첨부」 기준이 된다(#117 수경·현수 리뷰)
    gw = sorted((ROOT / "data" / "external" / "sbiz_store").glob("*강원*.csv"))
    shots = sorted((ROOT / "reports" / "screens").glob("*.png")) if (ROOT / "reports" / "screens").exists() else []

    made, missing = [], []
    for name, group in [("발길_재현코드.zip", code), ("발길_외부데이터원본.zip", ext),
                        ("발길_가상데이터.zip", syn), ("발길_화면캡처.zip", shots),
                        ("발길_외부데이터원본_상가강원.zip", gw)]:
        p = zip_files(name, group)
        (made.append((name, p, len(group))) if p else missing.append(name))

    for name, src in DESIGN:
        if src.exists():
            p = OUT / f"{name}.html"
            p.write_text(to_html(src.read_text(encoding="utf-8")), encoding="utf-8")
            made.append((p.name, p, 1))

    for extra in ["발길_분석보고서.html", "발길_분석보고서_상세판.html", "발길_발표자료.pptx"]:
        p = ROOT / "reports" / extra
        if p.exists():
            made.append((extra + "  (reports/)", p, 1))

    print("■ 만든 것")
    total = linked = 0.0
    for name, p, n in made:
        sz = p.stat().st_size
        if name.endswith(".zip"):
            total += sz
            if name in LINKED:
                linked += sz
        print(f"  {name:40s} {n:4d}개  {mb(sz):>10s}")
    known = total if gw else total + GANGWON_ZIP       # 강원 zip 은 여기서 묶었거나, 크기만 아는 값
    if not gw:
        linked += GANGWON_ZIP                         # 묶이지 않았어도 링크로 갈 쪽에 든다
    print(f"  {'zip 합계':40s} {'':4s}  {mb(total):>10s}")
    if not gw:
        print(f"  {'+ 상가 강원 zip (이 PC 에 원본 없음, 잰 값)':40s} {'':4s}  {mb(GANGWON_ZIP):>10s}")
    print(f"  {'= 지금까지 아는 첨부':40s} {'':4s}  {mb(known):>10s}")
    print()

    # #121 — 두 길의 여유를 같이 찍는다. PDF 넷의 크기는 뜬 뒤에 알 수 있으므로
    # 「합계가 넘는가」가 아니라 「PDF 에 얼마가 남는가」로 말한다
    print("■ PDF 넷에 남는 자리 (#121)")
    for label, attach in [("전부 첨부 — 상가 강원 · 화면캡처까지 메일에", known),
                          ("큰 것은 링크 — 상가 강원 · 화면캡처를 본문 링크로", known - linked)]:
        room = MAIL_LIMIT - attach
        if room <= 0:
            print(f"  {label:48s} 첨부 {mb(attach):>10s}  ■ 이미 {mb(-room)} 초과 — PDF 를 넣을 자리가 없습니다")
        else:
            print(f"  {label:48s} 첨부 {mb(attach):>10s}  → PDF 넷을 더해 {mb(room)} 이하")
    print("   발표자료 PDF 가 그림 15장 + 캡처를 품어 가장 큽니다. 뜨는 대로 #121 에 크기를 적습니다")
    print("   한 통으로 안 되면 「1/2 · 2/2」로 나눕니다(제출요건 6-2 확인 6번)")

    # 링크로 나가는 zip 은 메일 본문 표에 크기와 해시를 적는다(제출요건 6-2 3번).
    # 묶을 때 시각을 고정했으므로 누가 묶어도 같은 값이 나온다 — 그대로 옮겨 적으면 된다.
    linked_made = [(name, p) for name, p, _ in made if name in LINKED]
    if linked_made:
        print("\n■ 드라이브로 가는 zip — 메일 6-2 3번 표에 그대로 옮깁니다")
        for name, p in linked_made:
            print(f"  {name:40s} {mb(p.stat().st_size):>10s}  {sha256(p)}")
        print("   시각을 고정해 묶으므로 다른 PC 에서 다시 묶어도 같은 해시가 나옵니다")

    if missing:
        print("\n■ 아직 못 만든 것")
        for name in missing:
            why = "python scripts/capture_screens.py 를 먼저 돌려야 합니다 (현수, 체크리스트 9번)" \
                if "화면캡처" in name else "원본이 없습니다"
            print(f"  {name:40s} {why}")

    print("\n■ 이 스크립트가 만들지 않는 것 — 다른 스크립트나 사람이 합니다")
    done = {name for name, _, _ in made}
    for name, how in ELSEWHERE:
        if name in done:
            continue      # 이 PC 에서 묶였으면 「원본이 없습니다」를 또 찍지 않는다(#123 현수 리뷰 1)
        print(f"  {name:40s} {how}")


if __name__ == "__main__":
    main()
