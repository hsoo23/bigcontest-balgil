"""A2·A4 집단 지표 패널을 만든다 (36칸, 36칸 × 6개월).

정의는 윤지 재분석 코드(`reanalysis/b0_common.py`)를 그대로 쓴다.
업종 분류는 발길 4분류 확정안(실행계획 2절)이고, 비중은 거주자 결제 건수 기준이다.

선행: python reanalysis/a0_load_clean.py   (카드 원본 → data/processed/reanalysis/card*.pkl)
실행: python scripts/build_segment_panel.py
산출: data/processed/features_segment.parquet        36칸 (도시 2 × 성 2 × 연령 9), 나이 보정·좁아짐 순위 포함
      data/processed/features_segment_month.parquet  36칸 × 6개월 (A2 체류 비중 월별)
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reanalysis"))

from b0_common import adjust, faces, load  # noqa: E402

OUT = ROOT / "data" / "processed"
KEYS = ["city", "sex", "AGE"]


def main() -> None:
    r, d1 = load()

    seg = adjust(faces(r, d1, KEYS))
    seg["seg"] = seg.city + " " + seg.sex + " " + seg.AGE
    seg["rank"] = seg.narrow.rank(ascending=False).astype(int)

    r["month"] = r.date.dt.month
    d1["month"] = d1.date.dt.month
    month = faces(r, d1, KEYS + ["month"]).reset_index()

    for name, df, n in [("features_segment", seg, 36), ("features_segment_month", month, 36 * 6)]:
        miss = int(df.isna().sum().sum())
        print(f"{name}: {len(df)}행 (기대 {n}), 결측 {miss}")
        assert len(df) == n and miss == 0, f"{name} 검증 실패"
        df.to_parquet(OUT / f"{name}.parquet", index=False)

    print("\n저장:", ", ".join(f"data/processed/{n}.parquet" for n in ["features_segment", "features_segment_month"]))


if __name__ == "__main__":
    main()
