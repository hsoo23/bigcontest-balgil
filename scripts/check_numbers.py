"""보고서·발표자료의 숫자가 최종 수치표에 있는지 대조한다 (10/22 전수 대조, E).

협업규칙: 숫자는 10/17 최종 수치표에서만 가져온다. 그런데 문서가 열하나에 발표자료까지
있어서 손으로 훑으면 반드시 빠뜨린다. 이 스크립트는 "수치표에 없는 숫자"를 찾아 준다.

무엇을 숫자로 보는가
  단위가 붙은 값만 본다 — %, 배, 건, 명, 일, 개, 곳, 칸, 동, ρ, 소수점 숫자, N/M 꼴.
  절 번호(4.3), 날짜(2025-10-12), 이슈 번호(#49), 연도는 센다고 뜻이 없으므로 뺀다.

무엇을 "있다"로 보는가
  수치표에 같은 문자열이 나오면 있다고 본다. 반올림 표기가 다르면(0.79 ↔ -0.79) 못 찾으므로
  부호와 천 단위 쉼표를 지운 꼴로도 한 번 더 찾는다.

한계
  글자가 같아도 뜻이 다를 수 있다(다른 표의 44). 그래서 결과는 "확인할 목록"이고
  판정이 아니다. 사람이 한 줄씩 보는 것을 전제로 만든 도구다.
  그리고 수치표가 값을 표 칸으로 쪼개 적으면(| 19 | 0 |) 본문의 "0 / 19"를 못 찾는다.
  그 꼴은 뜨더라도 수치표 표를 눈으로 확인하면 된다.

ALLOW 에 적힌 값은 수치표가 아니라 다른 문서가 단일 출처인 것들이다(가상 명부 41명 → E5 등).
늘어나면 거기에 이유와 함께 적는다. 빈 목록으로 두면 매번 같은 줄을 다시 보게 된다.

실행: python scripts/check_numbers.py [--files docs/draft/05_모델링.md ...] [--show-ok] [--decimals]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TABLE = ROOT / "docs" / "최종수치표.md"
DEFAULT = sorted((ROOT / "docs" / "draft").glob("*.md"))

UNIT = r"%|배|건|명|일|개|곳|칸|동|회|주|쪽"
NUM = r"−?-?\d+(?:,\d{3})*(?:\.\d+)?"
PATTERNS = [
    re.compile(rf"{NUM}\s*(?:{UNIT})"),        # 44건, 1.80배, 58.7%
    re.compile(rf"{NUM}\s+/\s+{NUM}"),           # 12 / 12
    re.compile(rf"\d{{2,}}\s*/\s*\d{{2,}}"),  # 18/31, 47/47 (날짜와 겹치지 않는 꼴)
    re.compile(rf"ρ\s*=?\s*{NUM}"),              # ρ -0.79
]
DECIMALS = re.compile(rf"(?<![.\d]){NUM}\.\d+(?![.\d])")  # --decimals 로만 켠다

# 세는 뜻이 없는 것 — 날짜·이슈 번호·연도·커밋 해시·절 번호
DROP_IN_LINE = [
    re.compile(r"\d{4}-\d{2}(?:-\d{2})?"),   # 2025-10-12
    re.compile(r"\d{1,2}/\d{1,2}(?!\s*\d)"),  # 10/17 같은 날짜
    re.compile(r"#\d+"),                            # #49
    re.compile(r"\d{4}년"),
    re.compile(r"[0-9a-f]{7,40}"),              # 커밋 해시
    re.compile(r"\d+(?:\.\d+)+\s*(?:절|장|항)"),  # 9.1절, 4.3절
    re.compile(r"(?:절|장|항)\s*\d+(?:\.\d+)+"),
]
SKIP_LINE = re.compile(r"^\s*(?:#|>?\s*\*\*담당|\|\s*---|```|-\s*\*\*담당)")

# 수치표가 받는 값이 아닌 것 — 다른 문서가 단일 출처다. 이유를 함께 남긴다
ALLOW = {
    "41명": "가상 명부 규모 — E5 설계자료",
    "827곳": "가상 장소 표 규모 — E5",
    "273곳": "가상 가게 수 — E5",
    "591곳": "시설 표 — 수치표 6-2 들어오면 지운다",
    "37곳": "도서관 수 — 외부 데이터(fac_library)",
    "11개": "도구 개수 — 기획안 5절",
    "47개": "행정동 수 — dong_code.csv",
    "36칸": "지표 패널 칸 수 — 정의",
    "32칸": "모델 패널 칸 수 — 정의",
    "12칸": "60대 이상 칸 수 — 정의",
    "100MB": "GitHub 한도 — 규정 밖 사실",
    "47 / 47": "행안부 코드 연결 커버리지 — 03절·external_data.md",
}


def numbers(text: str, decimals: bool = False) -> set[str]:
    out: set[str] = set()
    pats = PATTERNS + ([DECIMALS] if decimals else [])
    for line in text.splitlines():
        if SKIP_LINE.match(line):
            continue
        clean = line
        for d in DROP_IN_LINE:
            clean = d.sub(" ", clean)
        for p in pats:
            out.update(re.sub(r"\s+", " ", m.group(0)).strip() for m in p.finditer(clean))
    return {t for t in out if t not in ALLOW}


def loose(tok: str) -> str:
    """부호·쉼표·공백·ρ= 를 지운 꼴. 0.79 와 −0.79, "ρ = −0.79" 와 "−0.79" 를 같게 본다."""
    return re.sub(r"[−\-,\sρ=]", "", tok)


def show(path: Path) -> str:
    """저장소 안이면 상대경로, 밖이면 그대로. --files 로 바깥 파일을 줄 수 있다."""
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def in_table(tok: str, text: str, text_loose: str) -> bool:
    """수치표에 그 값이 있는가. 앞뒤가 숫자·소수점이면 더 긴 수의 일부이므로 안 센다.

    경계를 안 보면 `shap==0.48.0` 이 "ρ 0.48" 을 찾았다고 말한다 — 실제로 한 번 겪었다."""
    if tok in text:
        return True
    lt = loose(tok)
    return bool(lt) and re.search(rf"(?<![\d.]){re.escape(lt)}(?![\d.])", text_loose) is not None


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--files", nargs="*", type=Path, default=None)
    ap.add_argument("--show-ok", action="store_true", help="수치표에서 찾은 것도 함께 보여 준다")
    ap.add_argument("--decimals", action="store_true", help="단위 없는 소수(0.347 등)도 본다. 절 번호가 섞여 시끄럽다")
    a = ap.parse_args()

    if not TABLE.exists():
        sys.exit(f"수치표가 없습니다: {TABLE}")
    table_text = TABLE.read_text(encoding="utf-8")
    table_loose = loose(table_text)

    files = a.files or DEFAULT
    missing_total = 0
    for f in files:
        if not f.exists() or f.resolve() == TABLE.resolve():
            continue
        found = sorted(numbers(f.read_text(encoding="utf-8"), a.decimals))
        missing = [t for t in found if not in_table(t, table_text, table_loose)]
        if not missing and not a.show_ok:
            continue
        print(f"\n■ {show(f)}  (숫자 {len(found)}개 · 수치표에 없음 {len(missing)}개)")
        for t in missing:
            print(f"    없음  {t}")
        if a.show_ok:
            for t in found:
                if t not in missing:
                    print(f"    있음  {t}")
        missing_total += len(missing)

    print(f"\n수치표에 없는 숫자 {missing_total}개."
          " 글자가 같아도 뜻이 다를 수 있으니 한 줄씩 확인하세요.")


if __name__ == "__main__":
    main()
