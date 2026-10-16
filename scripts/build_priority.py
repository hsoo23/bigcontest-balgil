"""동 우선순위표와 도달 효율 (C5) → data/reference/dong_priority.csv, reach_efficiency.csv (git에 올린다).

우선순위는 두 축으로 정한다.
  공급  터전이 약한가 — 통신 터전순위가 도시 안 하위 절반(강남 11, 춘천 12)
  필요  닿아야 할 사람이 많은가 — 행안부 2025-12 고령(60세 이상) 1인세대 수

기획안 정의("터전 하위 동에 배치")만 쓰면 춘천에서는 인구가 적은 면 지역이 뽑혀
같은 수의 동에 배치했을 때 무작위보다 적게 닿는다(아래 reach_efficiency 「터전 하위」 줄).
그래서 터전 하위 절반 안에서 고령 1인세대가 많은 순으로 우선순위를 매긴다.
가게도 사람도 적은 면 지역은 효율이 아니라 형평(닿을 곳이 없다)의 근거로 따로 표시한다.

도달 효율 = 우선순위 상위 k개 동의 고령 1인세대 수 합 ÷ 공급 부족 동 안에서 무작위 k개를 골랐을 때의 기댓값
  질문은 "터전이 약한 동에 쓰기로 했을 때, 필요 축이 얼마나 더 닿게 하나"다(#32 리뷰).
  도시 전체 무작위와 견주면 정렬 기준과 잰 값이 같아(둘 다 고령 1인세대 수) "큰 동을 골랐다"는 뜻밖에 안 된다.
  그래서 도시 전체 무작위 대비 값은 참고로만 함께 낸다. 「1인세대 많은 순」은 터전을 보지 않을 때의 상한이다.

공급 축은 통신 터전만 본다. 그래서 강남 청담동·논현2동처럼 가게는 많아도 통신상 머무는 고령이 적은 동이
  공급 부족에 든다. 대응 문구는 "통신상 머무는 고령이 적다"로 쓰고 체류형 점포 수를 옆에 둔다.

2단계 창구: agent.py counterpart_kind를 그 동 × 고령 6집단(남·여 × 60·70·80대)에 그대로 돌려,
  「경로당·마을회관을 먼저 묻는 집단 수」(0~6)를 적는다. 화면 ①·브리핑이 대상자마다 고르는 창구와 같은 규칙·같은 가게 수다.
  예전에는 동의 체류형 점포 전체로 세어, 같은 3배인데 화면과 5개 동에서 갈렸다(#49 4번, 수경 리뷰).
  경로당수에는 마을회관이 이미 들어 있다(같은 표준데이터, build_facility.py). 마을회관수를 더하면 두 번 센다.
  창구 배수 민감도(window_sensitivity.csv): 배수 2~5에서 두 세는 법이 각각 몇 개 동을 경로당 쪽으로 보내는지.

민감도(reach_sensitivity.csv): 배치할 동 수 k와 공급 부족 경계(터전 하위 1/3·절반·2/3)를 바꿔도
  「우선순위는 공급 부족 동 안 무작위보다 많이 닿고, 터전 하위 k개(기획안 정의)는 무작위와 비슷하다」가 유지되는지 본다.
  본 표 두 파일의 값은 바꾸지 않는다.

선행: build_ground.py
실행: python scripts/build_priority.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import pandas as pd  # noqa: E402

import balgil.agent as agent  # noqa: E402  창구 배수(SHOP_PER_CENTER)와 규칙은 agent.py 한 곳에서만 바꾼다(#49 4번 3배)
from balgil.data import PROCESSED_DIR  # noqa: E402

REF = ROOT / "data" / "reference"
KS = (3, 5)
SENS_KS = (1, 2, 3, 4, 5, 6, 8)  # 민감도: 배치할 동 수
ELDER = [(s, a) for s in ("남성", "여성") for a in ("60대", "70대", "80대")]  # 창구를 세는 고령 6집단
WINDOW_MULTS = (2, 3, 4, 5)  # 창구 배수 민감도
SENS_SHORT = {  # 민감도: 공급 부족을 터전 하위 몇 %로 볼지 (본 표는 절반)
    "하위 1/3": 1 / 3,
    "하위 절반 (본 표)": 1 / 2,
    "하위 2/3": 2 / 3,
}

ACTION = {  # (공급 부족, 필요 큼) → 무엇을 하는가 (기획안 6절)
    (True, True): "1순위 — 거점 배치·정기 프로그램 (통신상 머무는 고령이 적고, 닿아야 할 사람이 많다)",
    (True, False): "형평 — 찾아가는 형태·이동 지원 (통신상 머무는 고령이 적고, 사람도 적다. 연간 예산 제언)",
    (False, True): "연결 — 있는 가게·시설에 모임·봉사를 붙인다",
    (False, False): "유지",
}


def build(short_frac: float = 1 / 2) -> pd.DataFrame:
    g = pd.read_csv(REF / "dong_ground.csv", dtype={"ADM_CD": str})
    hh = pd.read_parquet(PROCESSED_DIR / "ext_single_household.parquet")
    old = hh[hh["연령대"].isin(["60대", "70대이상"])].groupby("ADM_CD")[["일인세대수", "인구수"]].sum()
    g = g.merge(old.rename(columns={"일인세대수": "고령1인세대수"})["고령1인세대수"], left_on="ADM_CD", right_index=True)
    assert g["고령1인세대수"].notna().all() and len(g) == 47
    g["고령1인세대율"] = (g["고령1인세대수"] / g["인구_60세이상"]).round(3)

    n = g.groupby("도시")["ADM_CD"].transform("size")
    g["공급부족"] = g["터전순위_통신"] <= (n * short_frac).astype(int)  # 절반이면 n // 2와 같다
    med = g.groupby("도시")["고령1인세대수"].transform("median")
    g["필요큼"] = g["고령1인세대수"] >= med
    g["대응"] = [ACTION[(a, b)] for a, b in zip(g["공급부족"], g["필요큼"])]
    # 우선순위: 공급 부족 동을 먼저, 그 안에서 고령 1인세대가 많은 순
    g = g.sort_values(["도시", "공급부족", "고령1인세대수"], ascending=[True, False, False])
    g["우선순위"] = g.groupby("도시").cumcount() + 1
    g["경로당먼저_집단수"] = window_counts(g)
    cols = ["도시", "SGG_NM", "ADM_CD", "ADM_NM", "우선순위", "대응", "공급부족", "필요큼", "터전순위_통신",
            "고령1인세대수", "고령1인세대율", "인구_60세이상", "체류형점포수", "경로당수", "마을회관수", "도서관수", "경로당먼저_집단수"]
    return g[cols].reset_index(drop=True)


_INP = None


def window_counts(g: pd.DataFrame, mult: int | None = None) -> list[int]:
    """동마다 고령 6집단 중 agent.counterpart_kind가 「경로당·마을회관」을 먼저 고르는 집단 수.
    상대방 업종 표(segment_industry)가 없으면 counterpart_kind가 가게 수를 0으로 읽어 전부 경로당이 되므로 멈춘다."""
    global _INP
    if _INP is None:
        _INP = agent.load_inputs()
        assert _INP.industry is not None and _INP.dong_stores is not None and _INP.facilities is not None, \
            "segment_industry · dong_industry_stores · fac_dong이 있어야 창구를 셉니다 (원본이 있는 PC에서)"
    old = agent.SHOP_PER_CENTER
    agent.SHOP_PER_CENTER = old if mult is None else mult
    try:
        out = []
        for city, cd in zip(g["도시"], g["ADM_CD"]):
            kinds = [agent.counterpart_kind(_INP, city, s, a, cd) for s, a in ELDER]
            assert all(k["업종"] is not None and len(k["업종"]) for k in kinds), f"{city} {cd}: 상대방 업종이 비었습니다"
            out.append(sum(k["창구"] != "가게" for k in kinds))
        return out
    finally:
        agent.SHOP_PER_CENTER = old


def window_sensitivity(g: pd.DataFrame) -> pd.DataFrame:
    """창구 배수를 바꿔 가며, 경로당·마을회관 쪽으로 가는 동 수를 두 세는 법으로 센다.
    상대방 업종(본 규칙)은 1집단 이상·6집단 전부를 따로 적는다. 체류형 점포 전체는 예전 동 기본값(비교용)."""
    rows = []
    for m in WINDOW_MULTS:
        n = pd.Series(window_counts(g, m), index=g.index)
        stay = g["체류형점포수"] < m * g["경로당수"]
        for city in g["도시"].unique():
            c = g["도시"] == city
            rows.append((city, m, int((n[c] >= 1).sum()), int((n[c] == 6).sum()), int(stay[c].sum()),
                         ", ".join(g.loc[c & (n >= 1), "ADM_NM"] + " " + n[c & (n >= 1)].astype(str) + "/6")))
    return pd.DataFrame(rows, columns=["도시", "배수", "상대방업종_1집단이상_동", "상대방업종_6집단전부_동",
                                       "체류형전체_동(예전 기본값)", "동(경로당 먼저 집단 수)"])


def reach(g: pd.DataFrame, ks=KS) -> pd.DataFrame:
    rules = {
        "터전 하위 (기획안 정의)": lambda x, k: x.nsmallest(k, "터전순위_통신"),
        "우선순위 (터전 하위 절반 ∩ 1인세대 많은 순)": lambda x, k: x.nsmallest(k, "우선순위"),
        "1인세대 많은 순 (터전 무시, 상한)": lambda x, k: x.nlargest(k, "고령1인세대수"),
    }
    rows = []
    for city, x in g.groupby("도시", sort=False):
        short = x[x["공급부족"]]
        for k in ks:
            in_short = k * short["고령1인세대수"].mean()  # 기준: 공급 부족 동 안에서 무작위 k개
            in_city = k * x["고령1인세대수"].mean()  # 참고: 도시 전체에서 무작위 k개
            for name, pick in rules.items():
                sel = pick(x, k)
                hit = sel["고령1인세대수"].sum()
                rows.append((city, k, name, int(hit), round(in_short), round(hit / in_short, 2), round(hit / in_city, 2),
                             ", ".join(sel["ADM_NM"])))
    return pd.DataFrame(rows, columns=["도시", "k", "규칙", "도달(고령 1인세대)", "무작위 기댓값(공급 부족 안)",
                                       "도달 효율", "도달 효율(도시 전체 대비, 참고)", "동"])


def sensitivity() -> pd.DataFrame:
    """k와 공급 부족 경계를 바꿔 가며 도달 효율을 다시 잰다. 공급 부족 동 수보다 큰 k는 뺀다(전부 고르면 1이 된다)."""
    out = []
    for label, frac in SENS_SHORT.items():
        g = build(frac)
        n_short = g.groupby("도시")["공급부족"].sum()
        r = reach(g, SENS_KS)
        r = r[r["k"] < r["도시"].map(n_short)]
        r["규칙"] = r["규칙"].str.replace("터전 하위 절반 ∩", "공급 부족 ∩", regex=False)  # 경계가 바뀌므로
        r.insert(1, "공급부족_경계", label)
        r.insert(2, "공급부족_동", r["도시"].map(n_short).astype(int))
        out.append(r.drop(columns="동"))
    return pd.concat(out, ignore_index=True)


def short_share(g: pd.DataFrame) -> pd.DataFrame:
    """공급 부족 동에 사는 고령 1인세대 비중 — 춘천은 터전 약한 동에 사람이 적다는 사실 자체가 형평 근거다."""
    rows = [(city, int(x["공급부족"].sum()),
             round(x.loc[x["공급부족"], "고령1인세대수"].sum() / x["고령1인세대수"].sum() * 100, 1))
            for city, x in g.groupby("도시", sort=False)]
    return pd.DataFrame(rows, columns=["도시", "공급부족_동", "고령1인세대_비중_%"])


def main() -> None:
    g = build()
    r = reach(g)
    print("■ 도달 효율 (공급 부족 동 안 무작위 = 1)")
    print(r.drop(columns="동").to_string(index=False))
    print("\n■ 공급 부족 동에 사는 고령 1인세대")
    print(short_share(g).to_string(index=False))
    print("\n■ 도시별 우선순위 상위 5")
    for city, x in g.groupby("도시", sort=False):
        print(x.head(5)[["ADM_NM", "터전순위_통신", "고령1인세대수", "고령1인세대율", "경로당먼저_집단수"]].to_string(index=False))
    print("\n■ 사분면 동 수")
    print(g.groupby(["도시", "대응"]).size().to_string())
    s = sensitivity()
    print("\n■ 민감도 — 도달 효율(공급 부족 동 안 무작위 = 1), 규칙별 범위")
    print(s.groupby(["도시", "공급부족_경계", "규칙"])["도달 효율"].agg(["min", "max"]).to_string())
    w = window_sensitivity(g)
    print(f"\n■ 2단계 창구 — 경로당·마을회관을 먼저 묻는 동 (배수 민감도, 본 규칙 {agent.SHOP_PER_CENTER}배)")
    print(w.to_string(index=False))
    w.to_csv(REF / "window_sensitivity.csv", index=False, encoding="utf-8-sig", lineterminator="\n")
    s.to_csv(REF / "reach_sensitivity.csv", index=False, encoding="utf-8-sig", lineterminator="\n")
    g.to_csv(REF / "dong_priority.csv", index=False, encoding="utf-8-sig", lineterminator="\n")
    r.to_csv(REF / "reach_efficiency.csv", index=False, encoding="utf-8-sig", lineterminator="\n")
    print("\n저장: data/reference/dong_priority.csv, reach_efficiency.csv, reach_sensitivity.csv, window_sensitivity.csv")


if __name__ == "__main__":
    main()
