"""A5 민감도 — 제과점을 체류 / 식사에 넣어도 결론이 같은가.

확정안은 제과점을 어느 분류에도 넣지 않는다. 두 경우를 더 돌려 세 가지를 본다.
  1 월별 안정성  60·70·80대 체류 비중이 6개월 내내 같은 성 50대보다 낮은가 (12집단 × 6개월)
  2 원값 순위    60대+ 12칸을 체류 비중 낮은 순으로 세운 순서
  3 나이 보정    36칸 좁아짐 순위 상위 5칸, 60대+ 12칸 안 상위 3칸

선행: python reanalysis/a0_load_clean.py
실행: python scripts/explore_bakery.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reanalysis"))

import pandas as pd  # noqa: E402

import b0_common as b0  # noqa: E402

KEYS = ["city", "sex", "AGE"]
OLD = ["60대", "70대", "80대"]
BASE_STAY, BASE_MEAL = list(b0.STAY), list(b0.MEAL)
CASES = {
    "제외 (확정안)": (BASE_STAY, BASE_MEAL),
    "체류에 넣음": (BASE_STAY + ["제과점"], BASE_MEAL),
    "식사에 넣음": (BASE_STAY, BASE_MEAL + ["제과점"]),
}


def run(r: pd.DataFrame, d1: pd.DataFrame, stay: list[str], meal: list[str]) -> dict:
    b0.STAY, b0.MEAL = stay, meal  # faces()가 모듈 전역을 읽는다
    seg = b0.adjust(b0.faces(r, d1, KEYS)).set_index(KEYS)
    month = b0.faces(r, d1, KEYS + ["month"]).stay.unstack("month")

    lower = sum(int((month.loc[(c, s, a)] < month.loc[(c, s, "50대")]).sum())
                for c in ["춘천", "강남"] for s in ["남성", "여성"] for a in OLD)
    old = seg[seg.index.get_level_values("AGE").isin(OLD)]
    label = lambda idx: [" ".join(i) for i in idx]
    return {
        "월별 안정성 (72칸 중 50대보다 낮음)": lower,
        "원값 순위 (체류 낮은 순, 60대+ 12칸)": label(old.stay.sort_values().index),
        "나이 보정 상위 5 (36칸)": label(seg.narrow.sort_values(ascending=False).index[:5]),
        "나이 보정 상위 3 (60대+ 12칸)": label(old.narrow.sort_values(ascending=False).index[:3]),
        "체류 비중": seg.stay,
    }


def main() -> None:
    r, d1 = b0.load()
    r["month"] = r.date.dt.month
    d1["month"] = d1.date.dt.month
    res = {name: run(r, d1, *defs) for name, defs in CASES.items()}
    base = res["제외 (확정안)"]

    for key in ["월별 안정성 (72칸 중 50대보다 낮음)", "원값 순위 (체류 낮은 순, 60대+ 12칸)",
                "나이 보정 상위 5 (36칸)", "나이 보정 상위 3 (60대+ 12칸)"]:
        print(f"■ {key}")
        for name, v in res.items():
            same = "" if name == "제외 (확정안)" else ("  → 같음" if v[key] == base[key] else "  → 다름")
            shown = ", ".join(v[key]) if isinstance(v[key], list) else v[key]
            print(f"  {name:10s} {shown}{same}")
        print()

    print("■ 체류 비중 변화 (체류에 넣음 − 제외, %p)")
    d = (res["체류에 넣음"]["체류 비중"] - base["체류 비중"]).unstack("AGE")[b0.AGES]
    print(d.round(2).to_string())


if __name__ == "__main__":
    main()
