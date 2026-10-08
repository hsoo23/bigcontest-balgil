"""카드 업종 분류표 대조 (A1 사전작업).

팀 안에 돌고 있는 분류표 네 개를 업종 단위로 나란히 놓고, 확정안과 다른 업종만 뽑는다.
카드 원본이 있으면 실제 업종명과 맞는지, 바뀌는 업종이 매출·건수에서 얼마나 되는지도 본다.

    python scripts/compare_categories.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from balgil.features import ALONE_MCT, ESSENTIAL_MCT, SOCIAL_MCT  # noqa: E402

# 1) 통합본 코드 (src/balgil/features.py)
CODE = {"사회적": SOCIAL_MCT, "혼자형": ALONE_MCT, "필수": ESSENTIAL_MCT}

# 2) docs/기획안_발길.md 부록 — 대면/익명
PLAN = {
    "대면": ["한식", "중식", "일식", "양식", "기타요식", "커피전문점", "제과점", "미용실", "미용서비스",
             "싸우나/목욕탕", "안마/마사지", "노래방", "유흥업소", "스포츠시설", "헬스장",
             "실내/실외골프장", "학원/학습지"],
    "익명": ["편의점", "할인점/슈퍼마켓/양판점", "기타식품", "농수산물", "정육점", "주류판매", "패스트푸드"],
}

# 3) docs/분석결과.md 1.4절·부록 — 3분할 (scripts/explore_quality.py 기준)
ANALYSIS = {
    "체류": ["커피전문점", "미용실", "미용서비스", "싸우나/목욕탕", "안마/마사지", "노래방", "유흥업소",
             "스포츠시설", "헬스장", "실내/실외골프장", "학원/학습지"],
    "식사": ["한식", "중식", "일식", "양식", "기타요식", "패스트푸드", "제과점"],
    "장보기": ["편의점", "할인점/슈퍼마켓/양판점", "기타식품", "농수산물", "정육점", "주류판매"],
}

# 4) docs/실행계획.md 2절 — 발길 4분류 확정안 (= 윤지 재분석 코드 b0_common.py, 10/10 승인 대상)
FINAL = {
    "체류": ["커피전문점", "미용실", "미용서비스", "싸우나/목욕탕", "안마/마사지", "노래방", "유흥업소",
             "스포츠시설", "헬스장", "실내/실외골프장", "학원/학습지"],
    "식사": ["한식", "중식", "일식", "양식", "기타요식"],
    "익명": ["편의점", "할인점/슈퍼마켓/양판점", "기타식품", "농수산물", "정육점", "주류판매", "패스트푸드"],
    "병원·약국": ["약국", "일반병원", "종합병원", "한의원", "치과병원", "기타의료", "보건소"],
    "제외": ["제과점"],
}

TABLES = {"코드": CODE, "기획안": PLAN, "분석결과": ANALYSIS, "확정안": FINAL}


def lookup(table: dict[str, list[str]], name: str) -> str:
    hits = [k for k, v in table.items() if name in v]
    return "+".join(hits) if hits else "-"


def main() -> None:
    names = list(dict.fromkeys(n for t in TABLES.values() for v in t.values() for n in v))

    # 한 표 안에서 두 분류에 들어간 업종 (주류판매 같은 중복)
    for tname, t in TABLES.items():
        for n in names:
            if len([k for k, v in t.items() if n in v]) > 1:
                print(f"[중복] {tname}: {n} → {lookup(t, n)}")

    rows = [(n, *(lookup(t, n) for t in TABLES.values())) for n in names]
    # 네 표가 모두 같은 '사회적/대면/체류/체류' 식의 대응이면 안 바뀐 것으로 본다
    same = {("사회적", "대면", "체류", "체류"), ("사회적", "대면", "식사", "식사"),
            ("혼자형", "익명", "장보기", "익명")}
    diff = [r for r in rows if tuple(r[1:]) not in same]

    print(f"\n업종 {len(names)}개 중 확정안과 어긋나는 업종 {len(diff)}개\n")
    print("| 업종 | " + " | ".join(TABLES) + " |")
    print("|---|" + "---|" * len(TABLES))
    for r in diff:
        print("| " + " | ".join(r) + " |")

    check_raw(names)


def check_raw(names: list[str]) -> None:
    """카드 원본이 있으면 업종명 실재 여부와 바뀌는 업종의 비중을 본다."""
    from balgil.data import CARD_FILES, RAW_DIR, load_card

    path = RAW_DIR / "card" / CARD_FILES["card_resid"]
    if not path.exists():
        print("\n카드 원본 없음: 업종명 실재 여부는 data/raw/card/ 배치 후 다시 실행해서 확인")
        return

    card = load_card("card_resid")
    by = card.groupby("MCT_RY_CD")[["TS_AT", "USE_CNT"]].sum()
    share = (by / by.sum() * 100).round(2)

    missing = [n for n in names if n not in by.index]
    unlisted = [n for n in by.index if n not in names]
    print(f"\n원본 업종 {len(by)}개")
    print(f"표에는 있는데 원본에 없는 업종: {missing or '없음'}")
    print("원본에는 있는데 어느 표에도 없는 업종 (매출 %, 건수 %):")
    for n in unlisted:
        print(f"  {n}: {share.loc[n, 'TS_AT']}%, {share.loc[n, 'USE_CNT']}%")
    print("\n업종별 비중 (매출 %, 건수 %):")
    for n in names:
        if n in share.index:
            print(f"  {n}: {share.loc[n, 'TS_AT']}%, {share.loc[n, 'USE_CNT']}%")


if __name__ == "__main__":
    main()
