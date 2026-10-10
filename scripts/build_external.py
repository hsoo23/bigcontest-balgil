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

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd

from balgil.data import PROCESSED_DIR, ROOT

EXTERNAL_DIR = ROOT / "data" / "external"
TARGET_SGG_NM = {"강남구": "서울 강남구", "춘천시": "강원 춘천시"}
AGE_RANGE = range(0, 101)  # 원본 CSV의 1세 단위 열 범위
AGE_BANDS = {"30대": range(30, 40), "40대": range(40, 50), "50대": range(50, 60), "60대": range(60, 70), "70대이상": range(70, 111)}


def _read_mois(slug: str) -> pd.DataFrame:
    """행안부 행정동 x 성별 x 1세 단위 통계를 대상 지역만 읽는다.

    jumin.mois.go.kr의 CSV는 한 행이 한 행정동이고, 지역이 `행정구역` 한 칸에
    "서울특별시 강남구 신사동(1168051000)" 형태로 들어 있다. 값 컬럼은
    `2025년12월_남_65세`처럼 기간·성별·나이가 이름에 붙어 있다.
    여기서 그 둘을 풀어 `시도명/시군구명/읍면동명/행정기관코드` + `65세남자` 꼴로 바꾼다.
    원본은 가공하지 않고 읽는 쪽에서 맞춘다 — 규정상 활용한 원본 파일을 그대로 제출한다.
    """
    frames = []
    for src in sorted((EXTERNAL_DIR / slug).glob("*.csv")):
        raw = pd.read_csv(src, encoding="cp949", thousands=",")
        region = raw["행정구역"].astype(str).str.strip()
        parsed = region.str.extract(r"^(?P<이름>.*?)\s*\((?P<행정기관코드>\d+)\)$")
        parts = parsed["이름"].str.split(r"\s+", expand=True)
        out = pd.DataFrame({
            "시도명": parts[0],
            "시군구명": parts[1] if parts.shape[1] > 1 else pd.NA,
            "읍면동명": parts[2] if parts.shape[1] > 2 else pd.NA,
            "행정기관코드": parsed["행정기관코드"],
        })
        # 시군구 합계 행(읍면동 없음)은 버린다. 동 단위만 쓴다.
        keep = out["읍면동명"].notna()
        values = {}
        for col in raw.columns[1:]:
            m = re.fullmatch(r"\d{4}년\d{2}월_(계|남|여)_(\d{1,3})세( 이상)?", col)
            if not m:
                continue
            sex = {"남": "남자", "여": "여자", "계": "계"}[m.group(1)]
            # errors="coerce"로 넘기면 형식이 바뀐 달의 자료가 결측이 되고,
            # 아래 sum()이 결측을 건너뛰어 조용히 작은 값이 나온다. 바로 멈춘다.
            values[f"{m.group(2)}세{sex}"] = pd.to_numeric(raw[col], errors="raise")
        # 계·남·여 x 0~100세 = 303개. 열 이름 형식이 바뀌면 정규식이 안 맞고
        # _by_band()가 빈 열 목록을 더해 0을 돌려주므로, 여기서 먼저 확인한다.
        if len(values) != 3 * len(AGE_RANGE):
            raise ValueError(f"{src.name}: 값 열이 {len(values)}개다. {3 * len(AGE_RANGE)}개를 기대했다")
        out = pd.concat([out, pd.DataFrame(values)], axis=1)
        frames.append(out[keep])
    both = pd.concat(frames, ignore_index=True)
    return both[both["시군구명"].isin(TARGET_SGG_NM)].reset_index(drop=True)


def _by_band(raw: pd.DataFrame, value_name: str) -> pd.DataFrame:
    rows = []
    for band, ages in AGE_BANDS.items():
        for sex, suffix in (("남성", "남자"), ("여성", "여자")):
            cols = [f"{a}세{suffix}" for a in ages if f"{a}세{suffix}" in raw.columns]
            if not cols:
                raise ValueError(f"{band} {sex}에 해당하는 열이 없다. 열 이름 형식을 확인하라")
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
