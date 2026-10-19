"""보고서·발표자료가 공통 서식(용어·표기·문체)을 지키는지 본다 (10/21~23 통합 편집, E).

보고서_목차.md 3절이 "셋이 따로 써도 한 사람이 쓴 것처럼 보이게 하는 최소 규칙"인데,
통합 편집에서 손으로 걸러내려면 다시 쓰게 된다. 쓰는 사람이 미리 돌려 보도록 만든다.

보는 것 셋
  용어   목차 3절 「왼쪽만 씁니다」 표의 오른쪽(안 쓰는 말)이 있는가
  문체   체언 종결("~함"), 수동형("산출되었다") 이 섞였는가
  표기   본문 서술에 소수 셋째 자리 이하가 있는가 (--decimals 로만. 규칙은 첫째 자리까지)
         표 줄은 보지 않는다 — AUC·SHAP·상관·비율은 셋째 자리가 뜻을 가진다
  물결표 한 줄에 이스케이프 안 된 ~ 가 둘 이상인가 (취소선으로 그려진다)

물결표 검사는 역슬래시를 세는 코드라 셸을 거치며 다치면 조용히 통과한다 — check_numbers 가
같은 자리에서 한 번 그랬다(#85). 그래서 실행마다 SELFTEST 로 확인하고 틀리면 바로 멈춘다.

한계
  코드 블록·표 구분선·링크 주소는 건너뛴다. 용어는 인용 안에서도 걸린다 —
  "위험군"을 인용해 비판하는 문장은 일부러 쓴 것이므로 사람이 보고 넘긴다.
  그래서 결과는 "확인할 목록"이고 판정이 아니다.

실행: python scripts/check_terms.py [--files docs/draft/05_모델링.md ...]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# docs/draft 만 보면 제출에 같이 나가는 문서(기획안·분석결과·입력형식·목차)를 놓친다.
# archive 는 옛 기획안, notion 은 make_notion.py 가 만드는 파생물이라 뺀다
SKIP_DIRS = ("archive", "notion")
# 규칙을 적은 문서는 금지어를 **이름으로** 들어야 한다. 용어 표와 「쓰면 안 되는 문장」 표가 그렇다
SKIP_FILES = ("보고서_목차.md", "협업규칙.md", "실행계획.md")
DEFAULT = sorted(p for p in (ROOT / "docs").rglob("*.md")
                 if not any(d in p.relative_to(ROOT / "docs").parts for d in SKIP_DIRS)
                 and p.name not in SKIP_FILES)

# 보고서_목차.md 3절 「용어 — 왼쪽만 씁니다」의 오른쪽. 바꿀 말을 함께 적는다
BANNED = {
    "외출 지수": "발길", "이동량": "발길의 양", "활동성": "발길",
    "위험군": "좁아짐 / 끊김", "고위험": "끊김(빨강)", "은둔형": "발길이 좁고 익명에 쏠린 집단",
    "관계형": "체류", "필수 소비": "장보기·병원·약국",
    "세그먼트": "집단", "코호트": "집단",
    "권역": "동",
    "지목 가게": "본인 등록 단골", "단골집": "본인 등록 단골",
    "개입": "확인", "조치": "확인", "아웃리치": "확인",
}
# 한국어는 띄어쓰기로 낱말이 갈리지 않아 부분일치가 난다. 실제로 겪은 것들:
#   「개입」 ← "탭 네 개입니다" · 「대면」 ← "카드와 통신만 맞대면"
FALSE_HIT = {
    "개입": re.compile(r"개입(?=니|니다)"),
    "조치": re.compile(r"(?<=조)치(?=수)"),
}
# 「대면」은 업종 분류로 쓰면 안 되지만 끊김 종류 라벨은 그대로 쓴다 (목차 3절 예외)
KEEP_DAEMYEON = re.compile(r"(맞대면|대면(형|만|성|\s*최저|\s*발길)|대면(?=[/·]))")

STYLE = [
    (re.compile(r"[가-힣]함\s*[.。]"), "체언 종결 — 「~입니다」로"),
    (re.compile(r"(되었|됐)다[.\s]"), "수동형·평서 종결 — 「했습니다」로"),
    (re.compile(r"[가-힣]되었습니다"), "수동형 — 능동으로"),
]
# 소수 둘째 자리 이하. ρ·AUC·상관·p는 예외(목차 3절이 성능 수치를 따로 다룬다)
DECIMAL3 = re.compile(r"(?<![\d.])\d+\.\d{3,}(?![\d.])")
DECIMAL_OK_NEAR = re.compile(r"(ρ|AUC|상관|변동계수|÷|비율|시드|sha|SHA|버전|==|p\s*=)")

SKIP = re.compile(r"^\s*(?:```|\|\s*-{2,}|> \*\*담당)")

# 한 줄에 이스케이프 안 된 물결표가 둘 이상이면 GitHub·일부 변환기가 그 사이를 취소선으로 그린다.
# "0.51~0.64 … 0.73~0.82" 가 "51~0 … 0" 이 지워진 모양이 된다. 숫자 범위를 쓰는 우리 문서에서
# 자주 생기고, 보고서를 PDF 로 뽑을 때도 따라간다(#68).
BACKSLASH = chr(92)


def loose_tildes(line: str) -> int:
    """이스케이프되지 않은 물결표 수. 정규식으로 쓰면 역슬래시가 겹쳐 읽기 어렵다."""
    return sum(1 for i, ch in enumerate(line)
               if ch == "~" and (i == 0 or line[i - 1] != BACKSLASH))


# 일부러 쓴 취소선(~~…~~)만 지우고 센다. 줄을 통째로 건너뛰면 같은 줄에 있는 범위를 놓친다(수경 #70 리뷰).
# 취소선 안에 이스케이프한 물결표가 올 수 있어(~~① \~④ 재실행~~) 그 자리를 넘어가도록 받는다 —
# [^~]* 만 쓰면 취소선이 안 지워지고 남은 ~ 다섯 개가 경고로 뜬다
STRIKE = re.compile(r"~~(?:\\~|[^~])*~~")

# 이 파일도 역슬래시를 세는 코드다 — check_numbers 의 \b 가 백스페이스로 바뀌어 아무것도 못 잡던 사고(#85)와
# 같은 자리다. 셸을 거치며 역슬래시가 다치면 물결표 검사가 조용히 통과한다. 그래서 매번 확인한다.
SELFTEST = [
    ("0.51~0.64 와 0.73~0.82", 2),                 # 그냥 쓴 물결표 둘 → 잡아야 한다
    ("0.51\\~0.64 와 0.73\\~0.82", 0),           # 이스케이프했으면 넘긴다
    ("~~① \\~④ 재실행~~ 뒤 한 줄", 0),              # 취소선 안의 이스케이프 물결표
    ("~~끝난 일~~ 그리고 0.1~0.2 와 0.3~0.4", 2),     # 취소선은 지우고 바깥 범위는 잡는다
]


def selftest() -> None:
    """물결표 검사가 살아 있는지 본다. 틀리면 바로 멈춘다 — 「0건」이 「다 맞다」여야 한다."""
    for line, want in SELFTEST:
        got = loose_tildes(STRIKE.sub("", line))
        if got != want:
            sys.exit(f"물결표 검사가 고장났습니다 — {line!r} 에서 {want} 를 기대했는데 {got}")


def show(path: Path) -> str:
    """저장소 안이면 상대경로, 밖이면 그대로. --files 로 바깥 파일을 줄 수 있다."""
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def scan(path: Path, decimals: bool = False) -> list[str]:
    out: list[str] = []
    in_code = False
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code or SKIP.match(line):
            continue
        body = re.sub(r"\]\([^)]*\)", "]()", line)       # 링크 주소 제외
        body = re.sub(r"`[^`]*`", "``", body)             # 인라인 코드 제외
        # 큰따옴표 안은 **쓴 것이 아니라 가리킨 것**이다. 빼지 않으면 금지어를 인용한 줄이 걸린다.
        # 「」는 빼지 않는다 — draft 가 강조로 많이 쓰고, 그 안에 금지어를 그냥 쓰면 잡아야 한다(수경 #70 리뷰).
        # 규칙을 적은 문서 셋은 위에서 통째로 빼므로 「」를 봐도 시끄러워지지 않는다
        quoted = re.sub(r"[\"“”][^\"“”]*[\"“”]", "", body)
        if loose_tildes(STRIKE.sub("", body)) >= 2:
            out.append(f"  {i:>4}  물결표  ~ 가 둘 이상 — 취소선으로 그려집니다. `{BACKSLASH}~` 로 이스케이프")
        for bad, good in BANNED.items():
            if bad not in quoted:
                continue
            f = FALSE_HIT.get(bad)
            if f and all(f.search(quoted[m.start():]) for m in re.finditer(bad, quoted)):
                continue  # 모두 부분일치면 넘긴다
            out.append(f"  {i:>4}  용어  「{bad}」 → {good}")
        if "대면" in quoted and not KEEP_DAEMYEON.search(quoted):
            out.append(f"  {i:>4}  용어  「대면」 — 업종 분류면 「체류」로. 끊김 종류 라벨이면 그대로")
        for pat, why in STYLE:
            if pat.search(body):
                out.append(f"  {i:>4}  문체  {why}")
        # 「소수 첫째 자리까지」는 본문 서술 수치의 규칙이다(7.2%, 2.78배). 표 안에는 AUC·SHAP·
        # 상관·비율처럼 셋째 자리가 뜻을 가지는 값이 들어가므로(1.003 을 1.0 으로 적으면
        # "1을 겨우 넘는다"가 사라진다) 표 줄은 보지 않는다. 본문에서도 그 맥락이면 넘긴다
        in_table = body.lstrip().startswith("|")
        skip_dec = not decimals or in_table or DECIMAL_OK_NEAR.search(body)
        for m in ([] if skip_dec else DECIMAL3.finditer(body)):
            if True:
                out.append(f"  {i:>4}  표기  {m.group(0)} — 소수 첫째 자리까지")
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    selftest()
    ap.add_argument("--files", nargs="*", type=Path, default=None)
    ap.add_argument("--decimals", action="store_true",
                    help="본문 소수 셋째 자리도 본다. AUC·비율이 본문에 나와 시끄러울 수 있다")
    a = ap.parse_args()

    total = 0
    for f in a.files or DEFAULT:
        if not f.exists():
            continue
        hits = scan(f, a.decimals)
        if not hits:
            continue
        print(f"\n■ {show(f)}  ({len(hits)}건)")
        print("\n".join(hits))
        total += len(hits)
    print(f"\n확인할 것 {total}건. 일부러 쓴 인용은 넘기세요 (보고서_목차.md 3절).")


if __name__ == "__main__":
    main()
