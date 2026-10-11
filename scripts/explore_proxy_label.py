"""B1 — 모델 ②의 대리 라벨 전제를 점검한다 (1인세대율 라벨이 발길 지표로 서는가).

기획안 7절 모델 ②는 대리 라벨을 **행정동 × 성 × 연령의 1인세대율 상위 20% vs 하위 20%**로 두고,
발길 지표(터전·양·질)로 그것을 맞힌다. 음성 대조는 30·40대 라벨을 같은 절차로 돌려 보는 것이다.

수경 B2(`scripts/explore_negative_control.py`)가 동 단위에서 "고령에서도 도시 안에서는 맞지 않는다"를
찾았다. 그 결과가 모델 ②의 전제를 깨는지 보려면 라벨을 **기획안이 쓰려던 단위**로 올려 두고
세 가지를 더 봐야 한다. 이 스크립트가 그 세 가지다.

  1 재현   수경 B2를 동 단위에서 다시 계산한다 (입력이 같으면 같은 값이 나와야 한다)
  2 분해   동 × 성 × 연령 라벨의 분산을 성·연령이 몇 % 설명하는가, 그리고 성·연령만으로
           상위 20% / 하위 20%를 가르면 AUC가 얼마인가 — 발길을 하나도 몰라도 나오는 점수
  3 순수   성·연령 칸 안에서(= 같은 성·연령끼리 동만 비교) 발길 지표가 1인세대율을 가르는가

발길 지표는 동 단위, 카드 양·질 지표는 도시 × 성 × 연령 단위다(`분석결과.md` 4.6절). 그래서
동 × 성 × 연령 라벨에서 모든 입력은 '동만의 함수' 또는 '(도시,성,연령)만의 함수'다. 2와 3을
나눠 보지 않으면 성·연령이 만든 점수를 발길이 맞힌 것으로 읽게 된다.

라벨: 행안부 「성/연령별 주민등록 1인세대수」 ÷ 「연령별 인구현황」, 2025년 12월 한 시점.
발길 지표: A4 동 패널 6개 + 터전 점수(통신).

선행
  - 동 패널: `data/processed/features_dong.parquet` (수경 `scripts/build_dong_panel.py`, PR #12).
    없으면 `reanalysis/reference/features_dong.csv`(같은 값)로 돌린다. 둘 다 없으면
    BALGIL_DONG_PANEL 환경변수로 경로를 준다.
  - 행안부 원본: `data/external/mois_single_household`, `mois_population` (PR #10).
    다른 곳에 두었으면 BALGIL_EXT_DIR 환경변수로 상위 폴더를 준다.
실행: python scripts/explore_proxy_label.py
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

EXT = Path(os.environ.get("BALGIL_EXT_DIR", ROOT / "data" / "external"))
PANEL_CANDIDATES = [
    Path(os.environ["BALGIL_DONG_PANEL"]) if os.environ.get("BALGIL_DONG_PANEL") else None,
    ROOT / "data" / "processed" / "features_dong.parquet",
    ROOT / "reanalysis" / "reference" / "features_dong.csv",
]

SGG = {"강남구": "서울 강남구", "춘천시": "강원 춘천시"}
CITY_OF_SGG = {"서울 강남구": "강남", "강원 춘천시": "춘천"}
FEATURES = ["60대이상_비중", "60대이상_여성비중", "저녁비중", "일요일_평일비", "겨울유지", "60대이상_규모", "터전점수_통신"]
# 수경 B2와 같은 두 구간 (동 단위, 성 합계)
DONG_BANDS = {"고령(65+)": range(65, 101), "30·40대": range(30, 50)}
# 기획안이 라벨에 쓰려던 단위 (동 × 성 × 연령 5구간)
AGE_BANDS = {"30대": range(30, 40), "40대": range(40, 50), "50대": range(50, 60), "60대": range(60, 70), "70대+": range(70, 101)}
SEXES = ["남", "여"]
# 5% 유의 기준 (스피어만, 양측). 동이 22·25개뿐이라 이 밑의 상관은 0과 구분되지 않는다
SIG = {"강남": 0.42, "춘천": 0.40}
# reanalysis/reference/features_dong.csv → 동 패널 열 이름
REF_COLS = {
    "이름(추정)": "ADM_NM", "60대 이상 규모": "60대이상_규모", "60대 이상 비중": "60대이상_비중",
    "여성 비중": "60대이상_여성비중", "일요일÷평일": "일요일_평일비", "저녁 비중": "저녁비중",
    "12월÷9월": "겨울유지", "터전 점수(통신)": "터전점수_통신",
}


def read_mois(slug: str, sex: str) -> pd.DataFrame:
    """동 × 나이(0~100) 표. '… 신북읍(5111025000)'에서 이름·코드를 뽑고 시군구 합계 행을 뺀다."""
    frames = []
    for path in sorted((EXT / slug).glob("*.csv")):
        raw = pd.read_csv(path, encoding="cp949", thousands=",")
        sgg = next(v for k, v in SGG.items() if k in path.stem)
        area = raw.iloc[:, 0].str.extract(r"(?P<name>\S+)\s*\((?P<MOIS_CD>\d{10})\)$")
        pat = re.compile(rf"_{sex}_(\d+)세")
        ages = {c: int(pat.search(c).group(1)) for c in raw.columns if pat.search(c)}
        df = raw[list(ages)].rename(columns=ages)
        df.index = pd.MultiIndex.from_arrays(
            [[sgg] * len(df), area["name"], area["MOIS_CD"]], names=["SGG_NM", "ADM_NM", "MOIS_CD"])
        frames.append(df[~area["MOIS_CD"].str.endswith("00000").values])
    return pd.concat(frames)


def rate(sex: str, bands: dict) -> pd.DataFrame:
    """1인세대수 ÷ 인구 (%). 구간마다 한 열을 가진 동 단위 표."""
    hh, pop = read_mois("mois_single_household", sex), read_mois("mois_population", sex)
    out = pd.DataFrame({b: hh[list(r)].sum(axis=1) / pop[list(r)].sum(axis=1) * 100 for b, r in bands.items()})
    return out.reset_index()


def load_panel() -> pd.DataFrame:
    for path in PANEL_CANDIDATES:
        if path is None or not path.exists():
            continue
        if path.suffix == ".parquet":
            panel = pd.read_parquet(path)
        else:
            panel = pd.read_csv(path, encoding="utf-8-sig").rename(columns=REF_COLS)
            panel["SGG_NM"] = panel["도시"].map({v: k for k, v in CITY_OF_SGG.items()})
            panel["ADM_NM"] = panel["ADM_NM"].str.replace(r"\(.*\)$", "", regex=True)  # 개포3동(구 일원2동)
        print(f"동 패널: {path} ({len(panel)}행)")
        return panel[["SGG_NM", "도시", "ADM_NM", *FEATURES]]
    raise SystemExit("동 패널이 없습니다. scripts/build_dong_panel.py를 먼저 돌리거나 BALGIL_DONG_PANEL을 주세요.")


def auc(score: pd.Series, label: pd.Series) -> float:
    """label 1이 0보다 높은 점수를 받을 확률 (동점 0.5)."""
    pos, neg = score[label == 1].values, score[label == 0].values
    if not len(pos) or not len(neg):
        return float("nan")
    return float(np.mean([(p > n) + 0.5 * (p == n) for p in pos for n in neg]))


def split_auc(df: pd.DataFrame, label_col: str, score_col: str, q: float = 0.2, by: str | None = None) -> tuple[float, int]:
    """상위 q vs 하위 q를 score로 가르는 AUC. 순위는 by 안에서(없으면 표 전체에서) 매긴다."""
    rank = (lambda col: df.groupby(by)[col].rank(pct=True)) if by else (lambda col: df[col].rank(pct=True))
    pct = rank(label_col)
    sub = df[(pct >= 1 - q) | (pct <= q)]
    return auc(rank(score_col)[sub.index], (pct[sub.index] >= 1 - q).astype(int)), len(sub)


def eta_sq(df: pd.DataFrame, value: str, by: list[str]) -> float:
    """by 조합의 평균이 value 분산의 몇 %를 설명하는가 (집단 간 제곱합 ÷ 총 제곱합)."""
    y = df[value]
    ss_tot = ((y - y.mean()) ** 2).sum()
    ss_res = ((y - df.groupby(by)[value].transform("mean")) ** 2).sum()
    return float(1 - ss_res / ss_tot)


def main() -> None:
    panel = load_panel()

    # ------------------------------------------------------------------ 1. 수경 B2 재현
    dong = panel.merge(rate("계", DONG_BANDS), on=["SGG_NM", "ADM_NM"], how="left")
    missing = dong[dong["MOIS_CD"].isna()]["ADM_NM"].tolist()
    print(f"행안부 연결: {dong['MOIS_CD'].notna().sum()}/{len(dong)}" + (f" — 미연결 {missing}" if missing else ""))
    dong = dong.dropna(subset=["MOIS_CD"])

    print("\n■ 1. 수경 B2 재현 — 동 단위, 도시 안 스피어만 상관 (지표 → 1인세대율)")
    rows = [{"도시": c, "지표": f, **{b: g[f].corr(g[b], method="spearman") for b in DONG_BANDS}}
            for c, g in dong.groupby("도시") for f in FEATURES]
    print(pd.DataFrame(rows).pivot(index="지표", columns="도시", values=list(DONG_BANDS)).round(2).to_string())
    for b in DONG_BANDS:
        a, n = split_auc(dong, b, "60대이상_비중", by="도시")
        pooled = dong["60대이상_비중"].corr(dong[b], method="spearman")
        print(f"  {b}: 상위/하위 20% AUC {a:.3f} ({n}동) | 두 도시를 섞은 상관 {pooled:.2f}")

    # ------------------------------------------------------------------ 2. 기획안 단위 라벨
    cells = pd.concat([rate(s, AGE_BANDS).assign(성=s) for s in SEXES])
    cells = cells.melt(id_vars=["SGG_NM", "ADM_NM", "MOIS_CD", "성"], var_name="연령", value_name="1인세대율")
    cells = cells.merge(panel, on=["SGG_NM", "ADM_NM"], how="inner")
    print(f"\n■ 2. 기획안 단위 라벨 — 동 × 성 × 연령 {len(cells)}행 "
          f"({cells.ADM_NM.nunique()}동 × {len(SEXES)}성 × {len(AGE_BANDS)}연령)")
    print("  칸 평균 1인세대율(%)")
    print(cells.pivot_table(index=["성", "연령"], columns="도시", values="1인세대율", aggfunc="mean").round(1).to_string())

    print("\n  2-1. 라벨 분산을 무엇이 설명하는가 (도시 안, %)")
    rows = [{"도시": c, "성·연령이 설명": eta_sq(g, "1인세대율", ["성", "연령"]),
             "동이 설명": eta_sq(g, "1인세대율", ["ADM_NM"])} for c, g in cells.groupby("도시")]
    print((pd.DataFrame(rows).set_index("도시") * 100).round(1).to_string())

    print("\n  2-2. 발길을 하나도 쓰지 않고 성·연령 평균만으로 상위/하위 20%를 가르면")
    naive = []
    for c, g in cells.groupby("도시"):
        g = g.assign(칸평균=g.groupby(["성", "연령"])["1인세대율"].transform("mean"))
        a_cell, n = split_auc(g, "1인세대율", "칸평균")
        a_flow, _ = split_auc(g, "1인세대율", "60대이상_비중")
        naive.append({"도시": c, "칸(상위+하위)": n, "성·연령 평균 AUC": a_cell, "참고 60대이상_비중 AUC": a_flow})
    print(pd.DataFrame(naive).round(3).to_string(index=False))

    # ------------------------------------------------------------------ 3. 칸 안에서의 순수 기여
    print("\n■ 3. 성·연령 칸 안에서 발길 지표가 동을 가르는가 (칸마다 동 22·25개)")
    rows = []
    for (c, sx, a), g in cells.groupby(["도시", "성", "연령"]):
        for f in FEATURES:
            rows.append({"도시": c, "성": sx, "연령": a, "지표": f,
                         "rho": g[f].corr(g["1인세대율"], method="spearman"),
                         "AUC": split_auc(g, "1인세대율", f)[0]})
    cell = pd.DataFrame(rows)
    summary = cell.groupby(["지표", "도시"]).apply(
        lambda x: pd.Series({"|rho| 중앙값": x.rho.abs().median(), "rho 최솟값": x.rho.min(), "rho 최댓값": x.rho.max(),
                             "유의한 칸": int((x.rho.abs() >= SIG[x.name[1]]).sum()), "칸 수": len(x),
                             "AUC 중앙값": x.AUC.median()}), include_groups=False)
    print(summary.round(2).to_string())
    print("\n  60대이상_비중 — 칸별 rho (기획안 기대: 60대·70대+ 에서 양수)")
    print(cell[cell.지표 == "60대이상_비중"].pivot_table(index=["성", "연령"], columns="도시", values="rho").round(2).to_string())

    # ------------------------------------------------------------------ 판정
    old = cell[(cell.지표 == "60대이상_비중") & (cell.연령.isin(["60대", "70대+"]))]
    print("\n■ 판정")
    for r in naive:
        print(f"  · {r['도시']}: 성·연령 평균만으로 라벨 상위/하위 20%를 가르는 AUC {r['성·연령 평균 AUC']:.3f} (발길 정보 0)")
    print(f"  · 같은 성·연령 안에서 60대이상_비중의 |rho| 중앙값 {old.rho.abs().median():.2f}, "
          f"유의한 칸 {int((old.rho.abs() >= old.도시.map(SIG)).sum())}/{len(old)} "
          f"(60대·70대+ 칸만, 5% 기준 강남 {SIG['강남']}·춘천 {SIG['춘천']})")
    print("  · 라벨을 맞히는 힘이 성·연령 구성에서 나오고 발길 지표가 칸 안에서 동을 가르지 못하면,")
    print("    모델 ②의 AUC는 발길이 아니라 연령 구성을 맞힌 값이다.")


if __name__ == "__main__":
    main()
