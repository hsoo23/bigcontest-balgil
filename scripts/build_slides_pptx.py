"""발표자료 16장을 PPTX 한 벌로 만든다 → reports/발길_발표자료.pptx.

**왜 필요한가.** 발표 도구를 구글 슬라이드로 정했는데(#40 ②), 원고(`발표자료_슬라이드.md`)와
그림(`reports/figures/*.png`)이 다 있어도 **16장을 손으로 옮기는 일**이 남아 있었다. 손으로 옮기면
제목·글머리를 다시 타이핑하다 숫자가 틀리고, 수치표를 고쳤을 때 슬라이드가 따라오지 않는다.
구글 슬라이드는 PPTX 를 그대로 읽으므로(파일 → 슬라이드 가져오기), **원고에서 PPTX 를 만들어
가져온 뒤 꾸미기만** 하면 된다. 숫자를 고치면 다시 돌려 가져오면 된다.

**원고를 고치지 않는다.** 슬라이드 문서가 사람이 읽는 원본이고 이 스크립트는 그것을 옮길 뿐이다.

한 장에 들어가는 것
  머리말   「1 · 문제」 — `## ` 줄
  제목     `### ` 줄. 이 장의 주장 한 줄이다
  글머리   `- ` 줄. `**굵게**`는 굵은 글씨로 살린다
  그림     `` `[그림]` `` 줄이 가리키는 PNG. 없으면 자리만 비운다(11장 캡처)
  발표 노트  `> ` 인용. **「그림 명세」는 뺀다** — 그림을 만드는 사람에게 남긴 말이라
            발표자가 읽을 글이 아니다. 그림은 이미 만들어져 있다

입력: docs/draft/발표자료_슬라이드.md · reports/figures/*.png
출력: reports/발길_발표자료.pptx (16:9, 13.333 × 7.5 인치)
실행: python scripts/build_slides_pptx.py
의존: python-pptx (캡처·그림과 같이 제출물을 만드는 쪽이라 requirements 에 넣지 않는다)

PPTX 는 바이트로 재현되지 않는다(만든 시각이 들어간다). 그림과 같은 규칙으로 **한 사람이
만들어 커밋한다**(#72).
"""
from __future__ import annotations

import re
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.util import Emu, Inches, Pt

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "docs" / "draft" / "발표자료_슬라이드.md"
OUT = ROOT / "reports" / "발길_발표자료.pptx"

INK, BLUE, MUTED = RGBColor(0x0B, 0x0B, 0x0B), RGBColor(0x2A, 0x78, 0xD6), RGBColor(0x89, 0x87, 0x81)
SURFACE = RGBColor(0xFC, 0xFC, 0xFB)
FONT = "맑은 고딕"

W, H = Inches(13.333), Inches(7.5)
MARGIN = Inches(0.62)

FIG = re.compile(r"`\[그림\]`.*?`(reports/figures/[\w./-]+\.png)`")
BOLD = re.compile(r"\*\*(.+?)\*\*")


def clean(s: str) -> str:
    """마크다운 표시를 걷는다. `\\~`(이스케이프)와 인라인 코드 백틱."""
    s = s.replace("\\~", "~").replace("\\|", "|")
    s = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", s)      # 링크는 글자만
    return s.replace("`", "").strip()


def put(frame, text: str, size: float, color=INK, bold_all=False, space_after=6) -> None:
    """`**굵게**`를 굵은 글씨로 살려 한 문단을 넣는다."""
    p = frame.paragraphs[0] if not frame.text and len(frame.paragraphs) == 1 else frame.add_paragraph()
    p.space_after = Pt(space_after)
    for i, part in enumerate(BOLD.split(clean(text))):
        if not part:
            continue
        r = p.add_run()
        r.text = part
        r.font.size, r.font.name, r.font.color.rgb = Pt(size), FONT, color
        r.font.bold = bold_all or bool(i % 2)           # split 의 홀수 조각이 ** 안쪽이다


def parse(md: str) -> list[dict]:
    slides, cur = [], None
    for ln in md.splitlines():
        if ln.startswith("## ") and "·" in ln:
            cur = {"eyebrow": ln[3:].strip(), "head": "", "bullets": [], "notes": [], "fig": None}
            slides.append(cur)
            continue
        if cur is None:
            continue
        if ln.startswith("### "):
            cur["head"] = ln[4:].strip()
        elif ln.startswith("- "):
            cur["bullets"].append(ln[2:].strip())
        elif ln.startswith(">"):
            t = ln.lstrip("> ").strip()
            if t and "그림 명세" not in t:
                cur["notes"].append(clean(t))
        elif ln.startswith("`[그림]`"):
            m = FIG.search(ln)
            if m and (ROOT / m.group(1)).exists():
                cur["fig"] = ROOT / m.group(1)
    return slides


def add_picture(slide, path: Path, left: Emu, top: Emu, max_w: Emu, max_h: Emu) -> None:
    from PIL import Image                                   # matplotlib 과 같이 들어 있다
    iw, ih = Image.open(path).size
    scale = min(max_w / iw, max_h / ih)
    w, h = int(iw * scale), int(ih * scale)
    slide.shapes.add_picture(str(path), int(left + (max_w - w) / 2), int(top + (max_h - h) / 2), w, h)


def build(slides: list[dict]) -> Presentation:
    prs = Presentation()
    prs.slide_width, prs.slide_height = W, H
    blank = prs.slide_layouts[6]
    for i, s in enumerate(slides):
        sl = prs.slides.add_slide(blank)
        sl.background.fill.solid()
        sl.background.fill.fore_color.rgb = SURFACE

        if i == 0:                                          # 표지 — 그림 위, 글 아래
            if s["fig"]:
                add_picture(sl, s["fig"], MARGIN, Inches(0.5), W - 2 * MARGIN, Inches(3.2))
            box = sl.shapes.add_textbox(MARGIN, Inches(3.9), W - 2 * MARGIN, Inches(3.0))
            put(box.text_frame, s["head"], 36, INK, bold_all=True, space_after=16)
            for b in s["bullets"]:
                put(box.text_frame, b, 16, MUTED, space_after=8)
        else:
            eb = sl.shapes.add_textbox(MARGIN, Inches(0.42), Inches(6), Inches(0.4))
            put(eb.text_frame, s["eyebrow"], 13, BLUE, bold_all=True)
            hb = sl.shapes.add_textbox(MARGIN, Inches(0.82), W - 2 * MARGIN, Inches(1.0))
            put(hb.text_frame, s["head"], 27, INK, bold_all=True)

            top, body_h = Inches(2.0), Inches(5.0)
            # 글이 많은 장은 글자를 줄인다 — 한 칸에 들어가야 읽힌다(6·10·15장이 그렇다)
            dense = sum(len(b) for b in s["bullets"])
            fs, gap = (13.5, 10) if dense <= 450 else (12, 8) if dense <= 650 else (11, 6)
            if s["bullets"] and s["fig"]:
                col = Inches(5.3)
                tb = sl.shapes.add_textbox(MARGIN, top, col, body_h)
                tb.text_frame.word_wrap = True
                for b in s["bullets"]:
                    put(tb.text_frame, "· " + b, fs, INK, space_after=gap)
                add_picture(sl, s["fig"], MARGIN + col + Inches(0.25), top,
                            W - 2 * MARGIN - col - Inches(0.25), body_h)
            elif s["fig"]:
                add_picture(sl, s["fig"], MARGIN, top, W - 2 * MARGIN, body_h)
            else:
                tb = sl.shapes.add_textbox(MARGIN, top, W - 2 * MARGIN, body_h)
                tb.text_frame.word_wrap = True
                for b in s["bullets"]:
                    put(tb.text_frame, "· " + b, min(15, fs + 1.5), INK, space_after=gap + 2)

        if s["notes"]:
            sl.notes_slide.notes_text_frame.text = "\n\n".join(s["notes"])
    return prs


def main() -> None:
    slides = parse(SRC.read_text(encoding="utf-8"))
    prs = build(slides)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    prs.save(OUT)
    no_fig = [s["eyebrow"] for s in slides if not s["fig"]]
    print(f"저장: {OUT.relative_to(ROOT)}  —  {len(slides)}장 · "
          f"그림 {sum(1 for s in slides if s['fig'])}장 · 발표 노트 {sum(1 for s in slides if s['notes'])}장")
    print("그림이 아직 없는 장: " + (" · ".join(no_fig) if no_fig else "없음"))
    print("구글 슬라이드에서 [파일 → 슬라이드 가져오기]로 읽습니다. 꾸미기는 거기서 합니다.")


if __name__ == "__main__":
    main()
