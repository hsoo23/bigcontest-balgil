"""발표 11장 그림 — 화면 캡처 넷을 한 장에 모은다 → reports/figures/fig_screens_grid.png.

11장은 「화면 넷」이 주장인데 캡처가 넉 장으로 따로 있어, 슬라이드에 넣을 그림이 없었다.
손으로 네 장을 올리면 장마다 크기·여백이 달라지므로 여기서 한 번에 맞춘다.

예전 화면 ①은 세로로 아주 길어(2880 × 6588) 위쪽만 잘랐다. 대시보드 틀(#126)로 바꾼 뒤에는
넷 모두 1:1 언저리(화면 ① 2880 × 3320)라 **자르지 않고 그대로 줄인다.** 세로로 긴 화면이 다시 생기면
PANEL 셋째 칸에 비율(가로 대비 세로)을 넣으면 위쪽만 잘린다.

캡처는 현수가 찍어 커밋한 것을 읽기만 한다(`capture_screens.py`, #118). 이 스크립트는 자르고
붙이기만 하므로 돌릴 때마다 같은 그림이 나온다 — 글자는 번호와 이름뿐이다.

입력: reports/screens/screen1.png ~ screen4.png
출력: reports/figures/fig_screens_grid.png
실행: python scripts/fig_screens_grid.py
"""
from __future__ import annotations

import sys

# 한글 윈도우 콘솔은 기본이 cp949 라 「—」 같은 글자에서 print 가 죽는다.
# 결과 파일은 이미 만들어진 뒤라 멀쩡한데 Traceback 만 보고 실패로 읽히므로, 출력만 UTF-8 로 돌린다.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "reports" / "screens"
OUT = ROOT / "reports" / "figures" / "fig_screens_grid.png"

PANEL = [("screen1.png", "① 주간 브리핑 — 이번 주 누구를 먼저 확인할까", None),
         ("screen2.png", "② 발길 상세 — 왜 이 집단인가", None),
         ("screen3.png", "③ 터전 지도 — 어느 동에 닿을 곳이 없나", None),
         ("screen4.png", "④ 보정 전·후 — 헛알림을 얼마나 지웠나", None)]

CELL_W, GAP, LABEL_H, PAD = 1180, 44, 58, 36
SURFACE, INK, MUTED, EDGE = (252, 252, 251), (11, 11, 11), (137, 135, 129), (222, 222, 220)


def font(size: int) -> ImageFont.FreeTypeFont:
    for name in ("malgun.ttf", "AppleGothic.ttf", "NanumGothic.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def panel(name: str, crop_ratio: float | None) -> Image.Image:
    im = Image.open(SRC / name).convert("RGB")
    if crop_ratio:                                   # 세로로 긴 화면은 위쪽만
        im = im.crop((0, 0, im.width, int(im.width * crop_ratio)))
    h = int(im.height * CELL_W / im.width)
    return im.resize((CELL_W, h), Image.LANCZOS)


def main() -> None:
    missing = [n for n, _, _ in PANEL if not (SRC / n).exists()]
    if missing:
        raise SystemExit(f"캡처가 없습니다: {' · '.join(missing)} — 먼저 python scripts/capture_screens.py")

    imgs = [panel(n, c) for n, _, c in PANEL]
    row_h = [max(imgs[0].height, imgs[1].height), max(imgs[2].height, imgs[3].height)]
    W = PAD * 2 + CELL_W * 2 + GAP
    H = PAD * 2 + sum(row_h) + (LABEL_H + 10) * 2 + GAP

    canvas = Image.new("RGB", (W, H), SURFACE)
    d = ImageDraw.Draw(canvas)
    f_label, f_sub = font(34), font(26)

    for i, (im, (_, title, _)) in enumerate(zip(imgs, PANEL)):
        col, row = i % 2, i // 2
        x = PAD + col * (CELL_W + GAP)
        y = PAD + sum(row_h[:row]) + (LABEL_H + 10) * row + GAP * row
        d.text((x, y + 6), title, font=f_label, fill=INK)
        top = y + LABEL_H
        canvas.paste(im, (x, top))
        d.rectangle([x, top, x + CELL_W - 1, top + im.height - 1], outline=EDGE, width=2)

    d.text((PAD, H - PAD + 2), "캡처: python scripts/capture_screens.py (1440px × 2배). "
                               "네 화면 모두 자르지 않고 줄였습니다 — 크게 보려면 보고서 그림 8-1~8-4.",
           font=f_sub, fill=MUTED)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(OUT, optimize=True)
    print(f"저장: {OUT.relative_to(ROOT)}  —  {W} × {H} · {OUT.stat().st_size / 1048576:.2f} MB")


if __name__ == "__main__":
    main()
