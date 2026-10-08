"""제공 데이터(SK 유동인구, 신한카드) 로딩 및 정제.

정제 규칙
- SK 유동인구
  * 구분자 '|', UTF-8(BOM) 인코딩, BLOCK_CD는 문자열로 읽는다.
  * 완전 중복 행 제거. 주최 측 공지: flow_time_pop_202512, flow_wkdy_pop_202512는
    모든 행이 2회씩 수록되어 있으므로 중복 제거 후 활용. (다른 월은 중복 없음)
  * BLOCK_CD 앞 5자리 = 시군구 코드, 앞 8자리 = 행정동(읍면동) 코드.
  * 대상 시군구(강남구 11230, 춘천시 32010) 외 인접 시군구 격자는 제외.
- 신한카드
  * 구분자 탭, cp949 인코딩.
  * 연령 '20 대' -> '20대'로 정규화, 성별·연령이 '법인'인 행은 IS_CORP 플래그로 구분.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"

TARGET_SGG = {"11230": "서울 강남구", "32010": "강원 춘천시"}
SK_KINDS = ("age", "time", "wkdy")
SK_KEY = ["STD_YM", "BLOCK_CD", "X_COORD", "Y_COORD"]

CARD_FILES = {
    "card_time": "신한카드_빅콘테스트2026_데이터1.txt",  # 일자 x 6시간대 (주제1 레이아웃)
    "card_resid": "신한카드_빅콘테스트2026_데이터2_수정.txt",  # 일자 x 고객 거주 시도 (주제2 레이아웃)
}


def read_sk_month(kind: str, ym: str, raw_dir: Path = RAW_DIR) -> pd.DataFrame:
    path = raw_dir / "sk" / f"flow_{kind}_pop_{ym}.csv"
    return pd.read_csv(path, sep="|", encoding="utf-8-sig", dtype={"STD_YM": str, "BLOCK_CD": str})


def clean_sk(df: pd.DataFrame, target_only: bool = True) -> tuple[pd.DataFrame, dict]:
    n_raw = len(df)
    df = df.drop_duplicates()
    n_dup = n_raw - len(df)
    assert not df.duplicated(SK_KEY).any(), "중복 제거 후에도 키 중복이 남아 있음"

    df = df.assign(SGG_CD=df["BLOCK_CD"].str[:5], ADM_CD=df["BLOCK_CD"].str[:8])
    n_outside = int((~df["SGG_CD"].isin(TARGET_SGG)).sum())
    if target_only:
        df = df[df["SGG_CD"].isin(TARGET_SGG)]
    df = df.assign(SGG_NM=df["SGG_CD"].map(TARGET_SGG))
    stats = {"rows_raw": n_raw, "dup_removed": n_dup, "outside_sgg": n_outside, "rows_clean": len(df)}
    return df.reset_index(drop=True), stats


def load_sk(kind: str, raw_dir: Path = RAW_DIR, target_only: bool = True) -> tuple[pd.DataFrame, pd.DataFrame]:
    """kind의 전 월(202507~202512)을 읽어 정제 후 결합. (데이터, 월별 정제 통계) 반환."""
    frames, stats = [], []
    for path in sorted((raw_dir / "sk").glob(f"flow_{kind}_pop_*.csv")):
        ym = path.stem.rsplit("_", 1)[-1]
        df, st = clean_sk(read_sk_month(kind, ym, raw_dir), target_only)
        frames.append(df)
        stats.append({"kind": kind, "ym": ym, **st})
    return pd.concat(frames, ignore_index=True), pd.DataFrame(stats)


def load_card(name: str, raw_dir: Path = RAW_DIR) -> pd.DataFrame:
    df = pd.read_csv(raw_dir / "card" / CARD_FILES[name], sep="\t", encoding="cp949")
    df["TA_YMD"] = pd.to_datetime(df["TA_YMD"].astype(str), format="%Y%m%d")
    df["AGE_CCD"] = df["AGE_CCD"].str.replace(" ", "", regex=False)
    df["IS_CORP"] = df["SEX_CCD"].eq("법인")
    for col in ["TS_AT", "USE_CNT"]:
        df[col] = pd.to_numeric(df[col]).astype("int64")
    return df
