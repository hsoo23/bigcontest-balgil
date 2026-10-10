"""조기성 — 끊김을 기존 격월 탐색보다 며칠 빨리 잡는가.

기획안 정의: 끊김 발생일에서 다음 탐색일까지의 평균 지연일. 기존 체계(격월)와 발길(주간)을 비교한다.

가정 (문서에 탐색 날짜가 없어 드러내 놓고 둔다)
  격월 탐색  매 홀수 달 1일 / 매 짝수 달 1일 — 두 경우의 평균
  주간 루프  매주 한 번. 요일 7가지의 평균
  발생일    재분석 b2가 찾은 끊김 시작일 14건(reanalysis/reference/closure.csv),
            그리고 2025-07-01~12-31 모든 날에 고르게 생긴다고 본 경우

선행: python reanalysis/b2_continuity.py (또는 reference/closure.csv)
실행: python scripts/explore_earliness.py
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CLOSURE = ROOT / "data" / "processed" / "reanalysis" / "closure.csv"
if not CLOSURE.exists():
    CLOSURE = ROOT / "reanalysis" / "reference" / "closure.csv"

DAYS = pd.date_range("2025-07-01", "2025-12-31")
HORIZON = pd.date_range("2025-07-01", "2026-03-31")  # 12월 끊김의 다음 탐색일까지 덮는다


def delay(events: pd.Series, runs: pd.DatetimeIndex) -> pd.Series:
    """발생일에서 그날 또는 그 뒤 첫 탐색일까지의 일수."""
    idx = runs.searchsorted(events.values)
    return pd.Series((runs[idx] - events.values).days, index=events.index)


def schedules() -> dict[str, list[pd.DatetimeIndex]]:
    first = HORIZON[HORIZON.day == 1]
    return {
        "격월": [first[first.month % 2 == 1], first[first.month % 2 == 0]],
        "주간": [HORIZON[HORIZON.dayofweek == d] for d in range(7)],
    }


def main() -> None:
    br = pd.read_csv(CLOSURE, parse_dates=["시작"])
    events = {"실제 끊김 14건": br["시작"], "모든 날 (184일)": pd.Series(DAYS)}

    rows = []
    for ev_name, ev in events.items():
        for sch_name, variants in schedules().items():
            d = pd.concat([delay(ev, runs) for runs in variants])
            rows.append({"발생일": ev_name, "탐색": sch_name, "평균 지연(일)": round(d.mean(), 1), "최대(일)": int(d.max())})
    res = pd.DataFrame(rows)
    print("■ 다음 탐색일까지 지연 (가정은 위 docstring)")
    print(res.to_string(index=False))

    for ev_name in events:
        x = res[res["발생일"] == ev_name].set_index("탐색")["평균 지연(일)"]
        print(f"  {ev_name}: 격월 {x['격월']}일 → 주간 {x['주간']}일, {x['격월'] - x['주간']:.1f}일 빠름, {x['격월'] / x['주간']:.1f}배")

    # 탐색일이 오기 전에 이미 끊김이 끝나는가 (끊김 지속 일수 < 지연). 탐색 요일·달마다 세고 평균
    print(f"\n■ 실제 끊김 {len(br)}건 중 탐색일 전에 이미 끝난 것 (끊김 지속 중앙값 {br['일수'].median():.0f}일)")
    for name, variants in schedules().items():
        gone = [int((br["일수"] < delay(br["시작"], runs)).sum()) for runs in variants]
        print(f"  {name}: 평균 {sum(gone) / len(gone):.1f}건 (경우별 {gone})")
    print("  → 주간 루프도 그날 상태만 보면 놓친다. 지난 7일 창을 돌아보는 판정이어야 한다(D1).")


if __name__ == "__main__":
    main()
