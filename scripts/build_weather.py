"""기상청 ASOS 일자료를 일자 × 시군구 기상 테이블로 정제한다 (B4).

지금까지는 모델마다 날씨 출처가 달랐고 7/1~8/24 보유분만 있었다. ASOS 한 출처로
2025-07-01~12-31 전 기간을 덮어 보정·모델이 같은 기상값을 쓰게 한다.

원본: 기상자료개방포털 → 종관기상관측(ASOS) → 일자료 → CSV 내려받기
      지점 서울(108)·춘천(101), 기간 2025-07-01~2025-12-31
      항목 평균·최저·최고기온, 일강수량, 일 최심신적설
      → data/external/kma_asos/ 에 그대로 두고 meta.json 기록 (register_external.py --init kma_asos)

정제 규칙
  * cp949 인코딩. 열 이름에 단위가 붙어 있어 앞부분으로 찾는다 (예: '평균기온(°C)')
  * 강수량·신적설이 비어 있으면 0으로 둔다. ASOS는 비·눈이 없던 날을 공란으로 내려준다
    단, 기간 내내 값이 하나도 없는 지점은 관측을 안 한 것으로 보고 결측으로 남긴다
    (춘천 101은 2025년 하반기 적설이 전부 공란이다. 같은 날 서울은 5.1cm)
  * 기온 결측은 채우지 않고 남긴 뒤 개수를 출력한다

실행: python scripts/build_weather.py
산출: data/processed/ext_weather.parquet (SGG_NM, 일자, 평균기온, 최저기온, 최고기온, 강수량, 신적설)
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd

from balgil.data import PROCESSED_DIR, ROOT

SRC_DIR = ROOT / "data" / "external" / "kma_asos"
STATION = {108: "서울 강남구", 101: "강원 춘천시"}  # 강남구에는 ASOS 지점이 없어 서울(108)을 쓴다
PERIOD = pd.date_range("2025-07-01", "2025-12-31", freq="D")
COLUMNS = {  # 원본 열 이름의 앞부분 → 정제 후 이름
    "평균기온(": "평균기온",
    "최저기온(": "최저기온",
    "최고기온(": "최고기온",
    "일강수량": "강수량",
    "일 최심신적설(": "신적설",  # "일 최심신적설 시각(hhmi)"과 구분
}
ZERO_IF_MISSING = ["강수량", "신적설"]


def _pick(raw: pd.DataFrame, prefix: str) -> str | None:
    hits = [c for c in raw.columns if c.strip().startswith(prefix)]
    return hits[0] if hits else None


def load_asos() -> pd.DataFrame:
    files = sorted(SRC_DIR.glob("*.csv"))
    if not files:
        raise SystemExit(f"ASOS 원본이 없습니다: {SRC_DIR.relative_to(ROOT)}/*.csv")
    raw = pd.concat([pd.read_csv(p, encoding="cp949") for p in files], ignore_index=True)

    out = pd.DataFrame({"지점": raw["지점"].astype(int), "일자": pd.to_datetime(raw["일시"])})
    for prefix, name in COLUMNS.items():
        col = _pick(raw, prefix)
        if col is None:
            print(f"[경고] '{prefix}' 열이 없습니다 — 내려받을 때 항목을 선택했는지 확인하세요")
            out[name] = pd.NA
        else:
            out[name] = pd.to_numeric(raw[col], errors="coerce")
    for col in ZERO_IF_MISSING:
        observed = out.groupby("지점")[col].transform(lambda s: s.notna().any())
        out.loc[observed, col] = out.loc[observed, col].fillna(0)
        for st in sorted(out.loc[~observed, "지점"].unique()):
            print(f"[주의] 지점 {st}의 {col} 값이 전부 비어 있어 0으로 채우지 않고 결측으로 둡니다 (미관측 추정)")

    out = out[out["지점"].isin(STATION) & out["일자"].isin(PERIOD)].drop_duplicates(["지점", "일자"])
    out.insert(0, "SGG_NM", out.pop("지점").map(STATION))
    return out.sort_values(["SGG_NM", "일자"]).reset_index(drop=True)


def main() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    w = load_asos()

    print(f"■ 기상 {len(w):,}행 (기대값 {len(STATION) * len(PERIOD)}행 = 지점 {len(STATION)} × {len(PERIOD)}일)")
    for sgg, d in w.groupby("SGG_NM"):
        missing = PERIOD.difference(d["일자"])
        temp_na = d[["평균기온", "최저기온", "최고기온"]].isna().sum().to_dict()
        print(f"  [{sgg}] {len(d)}일, 빠진 날 {len(missing)}개"
              + (f" ({missing[0].date()} 등)" if len(missing) else "")
              + f", 기온 결측 {temp_na}")

    monthly = w.assign(월=w["일자"].dt.month).groupby(["SGG_NM", "월"]).agg(
        평균기온=("평균기온", "mean"), 강수량=("강수량", "sum"), 신적설=("신적설", lambda s: s.sum(min_count=1)), 강수일=("강수량", lambda s: (s > 0).sum())
    )
    print("\n■ 월별 요약")
    print(monthly.round(1).to_string())

    w.to_parquet(PROCESSED_DIR / "ext_weather.parquet", index=False)
    print("\n저장: data/processed/ext_weather.parquet")


if __name__ == "__main__":
    main()
