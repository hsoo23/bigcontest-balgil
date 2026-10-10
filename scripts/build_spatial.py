"""행정동을 기준으로 제공 데이터와 외부 데이터를 연결한다.

데이터마다 행정동 식별자가 다르다.
  SK 유동인구   : BLOCK_CD 앞 8자리 (11230510)      — SGIS 행정동 코드와 동일 체계
  SGIS 경계     : ADM_CD (11230510) + ADM_NM (역삼1동) — 코드와 이름을 잇는 기준표
  행안부 통계   : 읍면동명 (역삼1동)                   — 행정표준코드(1168051000)라 코드 조인 불가
  상가정보      : 행정동명 + 점포 좌표(WGS84)          — 행정표준코드 8자리(11680640)

따라서 SGIS 경계를 기준표로 삼아 SK는 코드로, 행안부는 이름으로 연결하고,
상가정보는 점포 좌표를 EPSG:5179로 변환해 경계에 공간 조인한다(이름 필드와 교차 검증).

실행: python scripts/build_spatial.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import geopandas as gpd
import pandas as pd

from balgil.data import PROCESSED_DIR, ROOT, SK_KINDS, TARGET_SGG

BOUNDARY = ROOT / "data" / "external" / "sgis_boundary" / "bnd_dong_00_2025_2Q.shp"
EXPECTED_DONG = {"서울 강남구": 22, "강원 춘천시": 25}


def load_dong() -> gpd.GeoDataFrame:
    """대상 시군구의 행정동 경계. 전 데이터를 잇는 기준표가 된다."""
    dong = gpd.read_file(BOUNDARY)
    dong = dong[dong["ADM_CD"].str[:5].isin(TARGET_SGG)].copy()
    dong["SGG_NM"] = dong["ADM_CD"].str[:5].map(TARGET_SGG)
    return dong[["ADM_CD", "ADM_NM", "SGG_NM", "geometry"]]


def link_sk(dong: gpd.GeoDataFrame) -> pd.DataFrame:
    """SK 격자에 행정동 코드·이름을 붙인다. BLOCK_CD 앞 8자리가 곧 ADM_CD이다."""
    cells = pd.concat(
        [
            pd.read_parquet(PROCESSED_DIR / f"sk_{kind}.parquet", columns=["BLOCK_CD", "X_COORD", "Y_COORD", "SGG_NM"])
            for kind in SK_KINDS
        ],
        ignore_index=True,
    ).drop_duplicates(["BLOCK_CD", "X_COORD", "Y_COORD"])
    cells["ADM_CD"] = cells["BLOCK_CD"].str[:8]

    out = cells.merge(dong[["ADM_CD", "ADM_NM"]], on="ADM_CD", how="left")
    matched = out["ADM_NM"].notna()
    print(f"[SK] 코드 조인: 격자 {len(out):,}개 중 {matched.sum():,}개 ({matched.mean():.1%})")

    # 행정동 개편으로 코드가 어긋난 격자는 좌표로 현재 행정동을 찾는다.
    # (예: SK의 11230740은 2025년 2분기 경계에 없고, 경계의 11230511 개포3동은 SK에 없다)
    if (~matched).any():
        left = out[~matched].drop(columns=["ADM_CD", "ADM_NM"])
        pts = gpd.GeoDataFrame(left, geometry=gpd.points_from_xy(left["X_COORD"], left["Y_COORD"]), crs=dong.crs)
        fixed = gpd.sjoin(pts, dong[["ADM_CD", "ADM_NM", "geometry"]], how="left", predicate="within")
        fixed = pd.DataFrame(fixed.drop(columns=["geometry", "index_right"]))
        print(f"[SK] 좌표 보완: {fixed['ADM_NM'].notna().sum():,}개 추가 연결 "
              f"(옛 코드 {sorted(out.loc[~matched, 'ADM_CD'].unique())} → {sorted(fixed['ADM_NM'].dropna().unique())})")
        out = pd.concat([out[matched], fixed], ignore_index=True)
        matched = out["ADM_NM"].notna()

    print(f"[SK] 최종 연결 {matched.sum():,}개 ({matched.mean():.1%}), 행정동 {out.loc[matched, 'ADM_CD'].nunique()}개")

    # 좌표 기반 공간 조인으로 코드 연결이 맞는지 표본 검증한다.
    sample = out[matched].sample(min(3000, int(matched.sum())), random_state=0)
    pts = gpd.GeoDataFrame(sample, geometry=gpd.points_from_xy(sample["X_COORD"], sample["Y_COORD"]), crs=dong.crs)
    sj = gpd.sjoin(pts, dong[["ADM_CD", "geometry"]].rename(columns={"ADM_CD": "ADM_CD_SPATIAL"}), how="left", predicate="within")
    agree = (sj["ADM_CD"] == sj["ADM_CD_SPATIAL"]).mean()
    print(f"[SK] 좌표 공간 조인과 코드 조인의 일치율 {agree:.1%} (표본 {len(sample):,}개)")

    out.loc[matched].to_parquet(PROCESSED_DIR / "sk_cell_adm.parquet", index=False)
    return out


def link_store(dong: gpd.GeoDataFrame) -> pd.DataFrame:
    """점포 좌표(WGS84)를 행정동 경계에 공간 조인한다."""
    store = pd.read_parquet(PROCESSED_DIR / "ext_store.parquet")
    pts = gpd.GeoDataFrame(
        store, geometry=gpd.points_from_xy(store["경도"], store["위도"]), crs="EPSG:4326"
    ).to_crs(dong.crs)
    sj = gpd.sjoin(pts, dong[["ADM_CD", "ADM_NM", "geometry"]], how="left", predicate="within").drop(columns="geometry")

    matched = sj["ADM_CD"].notna()
    agree = (sj.loc[matched, "행정동명"] == sj.loc[matched, "ADM_NM"]).mean()
    print(f"[상가] 점포 {len(sj):,}개 중 {matched.sum():,}개 연결 ({matched.mean():.1%}), "
          f"자체 행정동명과 일치율 {agree:.1%}")

    sj.loc[matched].drop(columns="index_right").to_parquet(PROCESSED_DIR / "store_adm.parquet", index=False)
    return sj


def link_mois(dong: gpd.GeoDataFrame) -> pd.DataFrame:
    """행안부 통계를 읍면동 이름으로 연결한다."""
    hh = pd.read_parquet(PROCESSED_DIR / "ext_single_household.parquet")
    hh = hh.drop(columns=["ADM_CD", "ADM_NM"], errors="ignore")  # 재실행 시 중복 컬럼 방지
    names = dong[["ADM_CD", "ADM_NM", "SGG_NM"]]
    out = hh.merge(names, left_on=["SGG_NM", "읍면동명"], right_on=["SGG_NM", "ADM_NM"], how="left")

    missing = sorted(out.loc[out["ADM_CD"].isna(), "읍면동명"].unique())
    print(f"[행안부] 행정동 {out['읍면동명'].nunique()}개 중 미매칭 {len(missing)}개" + (f": {missing}" if missing else ""))
    out.to_parquet(PROCESSED_DIR / "ext_single_household.parquet", index=False)
    return out


def main() -> None:
    dong = load_dong()
    found = dong.groupby("SGG_NM")["ADM_CD"].nunique().to_dict()
    print(f"[기준표] 행정동 {found} (기대값 {EXPECTED_DONG})")
    dong.drop(columns="geometry").to_parquet(PROCESSED_DIR / "dong_master.parquet", index=False)

    link_sk(dong)
    link_store(dong)
    link_mois(dong)
    print("\n연결 완료: sk_cell_adm / store_adm / ext_single_household / dong_master")


if __name__ == "__main__":
    main()
