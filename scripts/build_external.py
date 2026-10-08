"""외부 공공데이터를 분석 대상 지역으로 정제해 data/processed에 저장한다.

대상: 서울 강남구, 강원 춘천시
  - mois_single_household + mois_population: 행정동 x 성별 x 연령대 1인세대수와 1인세대율
  - sbiz_store: 점포 단위 상가(상권)정보 → 대상 시군구만 추출

주의: 행정동 코드 체계가 데이터마다 다르다.
  SK 유동인구 BLOCK_CD  : 11230510 (강남구 11230, 춘천시 32010) — 구 행정자치부 체계
  행안부 1인세대        : 1168051000 (강남구 1168) — 행정표준코드 10자리
  상가정보 행정동코드     : 11680640 (강남구 11680, 춘천시 51110) — 행정표준코드 8자리
따라서 코드로 직접 조인할 수 없다. 행정동 이름 또는 좌표 기반 공간 조인이 필요하다.

실행: python scripts/build_external.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd

from balgil.data import PROCESSED_DIR, ROOT

EXTERNAL_DIR = ROOT / "data" / "external"
TARGET_SGG_NM = {"강남구": "서울 강남구", "춘천시": "강원 춘천시"}
AGE_BANDS = {"30대": range(30, 40), "40대": range(40, 50), "50대": range(50, 60), "60대": range(60, 70), "70대이상": range(70, 111)}


def _read_mois(slug: str) -> pd.DataFrame:
    """행안부 행정동 x 성별 x 1세 단위 통계를 대상 지역만 읽는다."""
    src = next((EXTERNAL_DIR / slug).glob("*.csv"))
    raw = pd.read_csv(src, encoding="cp949", thousands=",")
    return raw[raw["시군구명"].isin(TARGET_SGG_NM)].reset_index(drop=True)


def _by_band(raw: pd.DataFrame, value_name: str) -> pd.DataFrame:
    rows = []
    for band, ages in AGE_BANDS.items():
        for sex, suffix in (("남성", "남자"), ("여성", "여자")):
            cols = [f"{a}세{suffix}" for a in ages if f"{a}세{suffix}" in raw.columns]
            rows.append(
                raw[["시도명", "시군구명", "읍면동명", "행정기관코드"]]
                .assign(성별=sex, 연령대=band, **{value_name: raw[cols].sum(axis=1)})
            )
    return pd.concat(rows, ignore_index=True)


def build_single_household() -> pd.DataFrame:
    """행정동 x 성별 x 연령대 1인세대수와 그 비율.

    1인세대율 = 1인세대수 / 같은 행정동·성별·연령대 인구. 5060 타겟의 대리 라벨이다.
    """
    hh = _by_band(_read_mois("mois_single_household"), "일인세대수")
    pop = _by_band(_read_mois("mois_population"), "인구수")

    keys = ["시군구명", "읍면동명", "성별", "연령대"]
    out = hh.merge(pop[keys + ["인구수"]], on=keys, how="left")
    out["SGG_NM"] = out["시군구명"].map(TARGET_SGG_NM)
    out["일인세대율"] = out["일인세대수"] / out["인구수"]
    out.to_parquet(PROCESSED_DIR / "ext_single_household.parquet", index=False)
    return out


def build_store() -> pd.DataFrame:
    """대상 시군구의 점포 목록. 관계형 소비 인프라 공급량 산출에 사용한다."""
    frames = []
    for path in sorted((EXTERNAL_DIR / "sbiz_store").glob("*.csv")):
        for chunk in pd.read_csv(path, encoding="utf-8", dtype=str, chunksize=200_000, low_memory=False):
            frames.append(chunk[chunk["시군구명"].isin(TARGET_SGG_NM)])
    out = pd.concat(frames, ignore_index=True)
    out["SGG_NM"] = out["시군구명"].map(TARGET_SGG_NM)
    for col in ("경도", "위도"):
        out[col] = pd.to_numeric(out[col])
    out.to_parquet(PROCESSED_DIR / "ext_store.parquet", index=False)
    return out


def main() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    hh = build_single_household()
    target = hh[hh["연령대"].isin(["50대", "60대"])]
    print("■ 5060 1인세대율(%) = 1인세대수 / 해당 인구")
    rate = target.groupby(["SGG_NM", "성별", "연령대"]).apply(
        lambda d: round(d["일인세대수"].sum() / d["인구수"].sum() * 100, 1), include_groups=False
    )
    print(rate.unstack([1, 2]).to_string(), "\n")

    print("■ 5060 남성 1인세대율 상위·하위 5개 행정동")
    male = target[target["성별"] == "남성"].groupby(["SGG_NM", "읍면동명"]).apply(
        lambda d: pd.Series({"일인세대수": int(d["일인세대수"].sum()), "인구수": int(d["인구수"].sum()),
                             "일인세대율(%)": round(d["일인세대수"].sum() / d["인구수"].sum() * 100, 1)}),
        include_groups=False,
    ).sort_values("일인세대율(%)", ascending=False)
    print(pd.concat([male.head(5), male.tail(5)]).to_string(), "\n")

    store = build_store()
    print(f"■ 점포 {len(store):,}개")
    print(store.groupby("SGG_NM")["상권업종대분류명"].value_counts().groupby(level=0).head(5).to_string())


if __name__ == "__main__":
    main()
