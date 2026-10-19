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

  한 자리·두 자리 수는 반대 방향으로도 샌다 — "8명"은 수치표 어딘가의 8에 우연히 맞는다.
  그래서 보고서가 인용하는 작은 수는 수치표에 **단위까지 붙여** 적는다(6-2 동별 표, 6-3 시연 표).
  단위 없이 칸에만 적으면 이 도구가 "있음"이라고 말해도 그 근거가 다른 표의 수일 수 있다.

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
# 「숫자는 수치표에서만」은 **보고서·발표자료**의 규칙이다(보고서_목차 3절). 기획안·분석결과·메모는
# 수치표가 생기기 전에 쓴 글이고 그 자체가 출처라 여기서 보지 않는다 — 넓히면 14건이 늘 뜬다.
# 용어 쪽은 반대로 모든 제출 문서에 걸리므로 check_terms.py 는 docs/ 전체를 본다
DEFAULT = sorted((ROOT / "docs" / "draft").glob("*.md"))

UNIT = r"%|배|건|명|일|개|곳|칸|동|회|주|쪽"
NUM = r"−?-?\d+(?:,\d{3})*(?:\.\d+)?"
# 경계는 \b 대신 앞뒤 글자를 직접 본다. 한글도 \w 라서 \b 를 쓰면 「14건의」「5.7건을」이 안 잡힌다.
# 앞은 「후평3동」「V030」 같은 이름 속 숫자를 막고, 뒤의 (?!월)은 「6개월」을 「6개」로 세지 않게 한다.
# 10/16에 만든 판은 \b 자리에 백스페이스 문자(\x08)가 들어가 단위 붙은 숫자를 하나도 못 잡았다 —
# 그래서 아래 SELFTEST 로 매번 확인한다
PATTERNS = [
    # 단위 앞 띄어쓰기는 받지 않는다 — 받으면 「17 / 17 일치」「1365 일감」이 「17 일」「1365 일」로 잡힌다
    re.compile(rf"(?<![\w.]){NUM}(?:{UNIT})(?!월)"),        # 44건, 1.80배, 58.7%
    re.compile(rf"{NUM}\s+/\s+{NUM}"),           # 12 / 12
    re.compile(rf"(?<![\w/.])\d{{2,}}\s*/\s*\d{{2,}}(?![\w/.])"),  # 18/31, 47/47 (날짜와 겹치지 않는 꼴)
    re.compile(rf"ρ\s*=?\s*{NUM}"),              # ρ -0.79
]
DECIMALS = re.compile(rf"(?<![.\d]){NUM}\.\d+(?![.\d])")  # --decimals 로만 켠다

# 세는 뜻이 없는 것 — 날짜·이슈 번호·연도·커밋 해시·절 번호
DROP_IN_LINE = [
    re.compile(r"(?<!\d)\d{4}-\d{2}(?:-\d{2})?(?!\d)"),   # 2025-10-12
    re.compile(r"(?<![\d/])(?:1[0-2]|0?[1-9])/(?:[12]\d|3[01]|0?[1-9])(?![\d/])(?!\s*\d)"),  # 10/17 같은 날짜
    re.compile(r"#\d+"),                            # #49
    re.compile(r"(?<!\d)\d{4}년"),
    re.compile(r"(?<![0-9A-Za-z])[0-9a-f]{7,40}(?![0-9A-Za-z])"),              # 커밋 해시
    re.compile(r"(?<![\d.])\d+(?:\.\d+)+\s*(?:절|장|항)"),  # 9.1절, 4.3절
    re.compile(r"(?:절|장|항)\s*\d+(?:\.\d+)+"),
]
# 절 끝의 「채우기 전 확인」·「남은 일」은 쓰는 사람에게 남긴 메모라 제출 본문이 아니다
SKIP_LINE = re.compile(r"^\s*(?:#|>?\s*\*\*담당|\|\s*---|```|-\s*\*\*담당|\*\*(?:채우기 전 확인|남은 일)\*\*)")

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
    "22개": "강남 행정동 수 — dong_code.csv",
    "25개": "춘천 행정동 수 — dong_code.csv",
    "24칸": "통신 시간대 표의 1시간 칸 수 — 원본 정의",
    "5건": "카드 원본에서 가장 작은 칸 — 03절 3.1, 원본 관찰",
    "3%": "판단값: 상대방 업종 최소 비중 — agent.py, #49",
    "3명": "명부 교차가 올리는 인원 — agent.py 정의",
    "4곳": "장소를 올리는 최대 수 — agent.py 정의",
    "1회": "루프 주기(주 1회 · 월 1회) — 07절 정의",

    # ── 정의·구조값. 세어서 나온 값이 아니라 정해 둔 것이라 수치표가 받지 않는다
    "376칸": "폐기한 설계 — 행정동 47 × 8칸. 01절이 「허위 해상도」 예로만 든다",
    "47동": "행정동 수 — dong_code.csv. 「47개」와 같은 수, 단위만 다르다",
    "11동": "강남 공급 부족 동 수 = 터전순위 하위 절반(22 → 11, 내림) — 수치표 6-2",
    "12동": "춘천 공급 부족 동 수 = 25 → 12(내림) — 수치표 6-2",
    "2곳": "지역 수(강남·춘천) — 정의",
    "25%": "분위 이름(상위·하위 25% 평균) — 값이 아니라 가름 기준",
    "15개": "다른 PC 재현 대조 17개 중 일치 수 — #5 코멘트, 2026-10-10 회차. 10/11 회차는 17/17",

    # ── 문서 메타. 슬롯·문서 개수를 말하는 수라 발표에 나가지 않는다
    "23개": "발표자료 치환 슬롯 수 — 치환표. 발표에 나가는 값이 아니다",
    "12개": "슬롯이 늘기 전 수 — 치환표 갱신 기록",
    "44건": "quality_checks.csv 「뺀 업종」 건수 — 치환표가 제과점 민감도와 다른 계열임을 밝히는 자리",

    # ── E5 가상 데이터 설계값. E5 가 규정 필수 설계자료이고 그 자체가 출처다
    "11칸": "41명을 나눌 칸 수(12칸 중 시연 칸 뺀 나머지) — E5 4.1",
    "33명": "시연 칸 8명을 뺀 인원 — E5 4.1",
    "36명": "기준일보다 늦은 접촉일을 뺀 이른 주의 칸 인원 — E5 4.6",
    "20명": "본인 등록 중 가게 등록 수 — E5 6절",
    "21명": "본인 등록 인원(41명의 50% 가정) — E5 4.5·6절. 가정값이라 성능 주장에 쓰지 않는다",
    "21개": "41명의 주소가 흩어진 동 수 — E5 4.3",
    "262곳": "지정 가게 수 — E5 5절",
    "150일": "접촉일 범위의 끝 — E5 4.4 (경과일 15~131일이 되게 둔 값)",
    "7%": "춘천 면 5곳이 그 칸 1인세대에서 차지하는 몫 — E5 4.3 뽑기 근거",
    "5%": "게이트키퍼 지정률 가정값 — E5 5절. 근거 자료가 없다",
    "50%": "본인 등록률 가정값 — E5 6절. 근거 자료가 없다",
    "47/47": "행안부 동 이름 연결 — E5 4.2·external_data.md. 「47 / 47」과 같은 수, 띄어쓰기만 다르다",
    "1곳": "지정 가게 최소 수 — E5 5절 규칙",
    "1명": "명부 파일 한 줄이 한 사람 — E5 3절 형식 설명",
    "4명": "칸당 최대 인원 — E5 4.1 (#20 「칸당 3~4명」)",
    "6명": "칸이 그보다 두꺼우면 시연 칸만 눈에 띈다는 기준 — E5 4.1",
    "7명": "퇴계동 인원(41명 중 최다 동) — E5 4.3",
}


# 「0개」가 「다 맞다」인지 「하나도 못 읽었다」인지 가르는 문장. 날짜·이름 속 숫자·「개월」은 빠져야 한다
SELFTEST = "2025-10-12 기준 14건의 끊김, 58.7%, 1.80배, 18/31, 12 / 12, ρ −0.79. 후평3동, 6개월, 10/17."
SELFTEST_WANT = {"14건", "58.7%", "1.80배", "18/31", "12 / 12", "ρ −0.79"}


def numbers(text: str, decimals: bool = False) -> set[str]:
    out: set[str] = set()
    pats = PATTERNS + ([DECIMALS] if decimals else [])
    in_code = False
    for line in text.splitlines():
        # 코드 블록은 명령 출력을 그대로 옮긴 것이다. 바로 위의 명령을 다시 돌려 대조하고, 여기서는 세지 않는다
        if line.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code or SKIP_LINE.match(line):
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

    경계를 안 보면 `shap==0.48.0` 이 "ρ 0.48" 을 찾았다고 말한다 — 실제로 한 번 겪었다.
    그대로 찾을 때도 같다 — 경계 없이 `tok in text` 로 보면 「5건」이 「175건」에서 찾아진다(#85 리뷰).
    앞의 쉼표는 「291개」가 「126,291개」에 걸리지 않게 한다."""
    if re.search(rf"(?<![\d.,]){re.escape(tok)}(?!\d|\.\d)", text):
        return True
    lt = loose(tok)
    if lt and re.search(rf"(?<![\d.]){re.escape(lt)}(?![\d.])", text_loose):
        return True
    # 수치표가 단위를 열 이름에 두고 칸에는 수만 적는 경우(「| 461 |」「1.53 \~ 1.81」).
    # 소수이거나 네 자리 이상이면 그 수만으로도 우연히 겹치기 어려워 단위를 떼고 한 번 더 찾는다.
    # 세 자리는 안 된다 — E5의 가상 접촉 「131일」이 3절 경보 수 「131」에 걸렸다
    bare = re.fullmatch(rf"({NUM})(?:{UNIT})", tok)
    if bare and ("." in bare[1] or len(re.sub(r"\D", "", bare[1])) >= 4):
        return re.search(rf"(?<![\d.,]){re.escape(bare[1])}(?!\d|\.\d)", text) is not None
    return False


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--files", nargs="*", type=Path, default=None)
    ap.add_argument("--show-ok", action="store_true", help="수치표에서 찾은 것도 함께 보여 준다")
    ap.add_argument("--decimals", action="store_true", help="단위 없는 소수(0.347 등)도 본다. 절 번호가 섞여 시끄럽다")
    a = ap.parse_args()

    got = numbers(SELFTEST)
    if got != SELFTEST_WANT:
        sys.exit(f"숫자 찾기가 고장났습니다 — {sorted(SELFTEST_WANT)} 를 기대했는데 {sorted(got)}")
    if in_table("5건", "175건", "175건") or not in_table("5건", "결제 5건.", "결제5건."):
        sys.exit("수치표 대조가 고장났습니다 — 「5건」을 「175건」에서 찾거나 「결제 5건」에서 못 찾습니다")
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
