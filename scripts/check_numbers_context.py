"""check_numbers.py 가 「있음」이라고 한 숫자가 수치표의 **같은 뜻** 줄에 걸렸는지 나란히 보여 준다.

왜 따로 있나
  check_numbers.py 는 글자만 맞으면 통과시킨다. 06의 개포1동 「7~8곳」이 수치표의 「춘천 7~8곳」에
  걸려 통과한 것(#100), 끊김 「3배」가 창구 배수 「3배」에 걸린 것(#109)이 그렇게 남았다.
  이 스크립트는 숫자마다 「문서 앞뒤 글 ↔ 수치표에서 걸린 줄의 앞뒤 글」을 찍어서,
  사람이 같은 뜻인지 읽게 한다. 체크리스트 12번(10/19 #4 교차 대조)에 쓴 것을 정리했다.

무엇을 숫자로 보고 무엇을 「걸렸다」로 보는가
  check_numbers.py 의 numbers · in_table · SKIP_LINE · ALLOW 를 그대로 부른다. 규칙을 고치면 여기도 같이 바뀐다.
  다른 점은 수치표 전체가 아니라 **줄마다** in_table 을 불러서 어느 줄에 걸렸는지 남기는 것뿐이다.

--suspect
  문서 글과 걸린 수치표 줄이 낱말을 하나 이하만 나누는 숫자만 보여 준다. 다른 뜻 줄에 걸렸을 가능성이
  큰 것부터 보려는 거름망이다. 같은 뜻인데 낱말이 달라 뜨는 것도 많고, 낱말이 겹쳐도 뜻이 다를 수 있으니
  판정이 아니라 읽을 순서다.

실행: python scripts/check_numbers_context.py docs/draft/06_터전.md docs/draft/08_시나리오화면.md
      python scripts/check_numbers_context.py docs/draft/발표자료_슬라이드.md --slides 5,11 --suspect
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_numbers as cn  # noqa: E402

# 낱말 겹침을 셀 때 뜻 없이 어디에나 나오는 말
STOP = {"있습니다", "입니다", "합니다", "없습니다", "그래서", "기준", "같은", "이상"}


def doc_lines(path: Path, slides: set[str] | None) -> list[tuple[int, str]]:
    """문서의 (줄 번호, 줄). 발표자료는 --slides 로 「## 5 · 」 같은 장만 고를 수 있다."""
    lines = path.read_text(encoding="utf-8").splitlines()
    if not slides:
        return list(enumerate(lines, 1))
    out, ch = [], None
    for i, line in enumerate(lines, 1):
        m = re.match(r"^## (\d+) ·", line)
        if m:
            ch = m.group(1)
        elif line.startswith("## "):
            ch = None
        if ch in slides:
            out.append((i, line))
    return out


def snip(line: str, tok: str, w: int) -> str:
    """tok 앞뒤 w 글자. 표의 | 는 출력이 헷갈려서 ¦ 로 바꾼다."""
    j = line.find(tok)
    if j < 0:
        j = line.find(cn.loose(tok))
    j = max(j, 0)
    return line[max(0, j - w): j + len(tok) + w].replace("|", "¦").strip()


def words(s: str) -> set[str]:
    return {w for w in re.findall(r"[가-힣A-Za-z_]{2,}", s) if w not in STOP}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+", type=Path)
    ap.add_argument("--slides", default="", help="발표자료에서 볼 장 번호, 쉼표로 (예: 5,11)")
    ap.add_argument("--suspect", action="store_true", help="낱말이 거의 안 겹치는 숫자만 보여 준다")
    ap.add_argument("--hits", type=int, default=4, help="숫자마다 보여 줄 수치표 줄 수")
    a = ap.parse_args()

    if cn.numbers(cn.SELFTEST) != cn.SELFTEST_WANT:
        sys.exit("check_numbers.py 의 숫자 찾기가 고장났습니다 — 그쪽을 먼저 돌려 보세요")
    table = cn.TABLE.read_text(encoding="utf-8").splitlines()
    table_loose = [cn.loose(t) for t in table]
    slides = {s.strip() for s in a.slides.split(",") if s.strip()} or None

    for f in a.files:
        if f.resolve() == cn.TABLE.resolve():
            continue
        print(f"\n■ {cn.show(f.resolve())}")
        in_code = False
        for i, line in doc_lines(f, slides):
            if line.strip().startswith("```"):
                in_code = not in_code
                continue
            if in_code or cn.SKIP_LINE.match(line):
                continue
            for tok in sorted(cn.numbers(line)):
                hits = [(k, t) for k, (t, tl) in enumerate(zip(table, table_loose), 1)
                        if cn.in_table(tok, t, tl)]
                ctx = snip(line, tok, 45)
                if a.suspect:
                    best = max((len(words(ctx) & words(t)) for _, t in hits), default=0)
                    if best > 1:
                        continue
                print(f"[{i}] {tok}  ←  {ctx}")
                for k, t in hits[:a.hits]:
                    print(f"      수치표 {k}: {snip(t, tok, 38)}")
                if len(hits) > a.hits:
                    print(f"      … 수치표에서 {len(hits)}줄")
                if not hits:
                    print("      (수치표에 없음)")


if __name__ == "__main__":
    main()
