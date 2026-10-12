"""발길 에이전트 (D1) — 뼈대.

판단은 규칙이 하고, 이 파일은 재분석 산출물을 읽어 도구 11개를 한 흐름으로 묶는다.
LLM은 부르지 않는다. 문장은 고정 틀에 계산값을 슬롯으로 넣는다(E6 5.2).

지금 되는 것 (데이터로 되는 도구)
  measure_breadth · measure_quality   양·질      ← features_segment(_month)  (A2, PR #12)
  detect_break · correct_shock        연속성      ← reanalysis break_daily    (b2_continuity, 7일 창)
  map_ground                          터전        ← features_dong             (A4, PR #12)
  rate_state                          네 상태 판정
  match_roster                        명부 교차    ← 가상 명부 (입력 형식: docs/agent_입력형식.md)
  draft_outreach                      고정 문장 틀
아직 안 되는 것 (D4 가상 데이터·자원 정제본이 필요, 10/18~20)
  find_counterpart · match_resource · log_outcome

단위 원칙 (#14, #20)
  끊김·좁아짐은 시군구 × 성 × 연령 집단이다. 카드 지표는 동에 붙이지 않는다.
  명부는 같은 칸(시군구 × 성 × 연령대)으로 거르고, 행정동은 대상자 주소에서만 가져와 터전을 붙인다.
  판정은 실행일 하루가 아니라 지난 7일 창이다(조기성: 실행일만 보면 끊김 14건 중 평균 5.7건을 놓친다).

입력은 data/processed/ 산출물을 먼저 찾고, 없으면 저장소에 커밋된 reanalysis/reference/ 를 쓴다.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from balgil.data import PROCESSED_DIR, ROOT

REANALYSIS_DIR = PROCESSED_DIR / "reanalysis"
REFERENCE_DIR = ROOT / "reanalysis" / "reference"

CITY_SGG = {"강남": "서울 강남구", "춘천": "강원 춘천시"}
SGG_CITY = {v: k for k, v in CITY_SGG.items()}
BREAK_AGES = ["60대", "70대", "80대"]  # 끊김 감시 대상 (b2_continuity와 같음)
COMPARE_AGE = "50대"                   # 양·질을 견주는 기준 연령 (기획안 9절 시나리오)
WINDOW_DAYS = 7
NARROW_TOP = 7                         # 90대 뺀 32칸 중 좁아짐 상위 7칸(21.9%) — 모델 라벨과 같은 선
GROUND_BOTTOM = 0.2                    # 도시 안 터전점수 하위 20%를 터전 없음 후보로 (기획안 3절 분위수 기준)
SEVERITY = {"빨강(필수까지 끊김)": 2, "주황(대면만 끊김)": 1, "-": 0}

# reanalysis/reference/features_dong.csv → 동 패널 열 이름
_REF_DONG = {"행정동코드": "ADM_CD", "이름(추정)": "ADM_NM", "60대 이상 비중": "60대이상_비중",
             "일요일÷평일": "일요일_평일비", "저녁 비중": "저녁비중", "12월÷9월": "겨울유지",
             "터전 점수(통신)": "터전점수_통신", "순위": "터전순위_통신"}
_SK_OLD_CODE = {"11230740": "11230511"}  # 개포3동 (build_dong_panel.py와 같음)


# ------------------------------------------------------------------ 입력
def _first(*paths: Path) -> Path:
    for p in paths:
        if p.exists():
            return p
    raise FileNotFoundError(f"입력이 없습니다: {[str(p) for p in paths]}")


@dataclass
class Inputs:
    segment: pd.DataFrame        # 36칸 × 6개월 평균 (양·질·좁아짐 점수)
    segment_month: pd.DataFrame  # 36칸 × 월
    breaks: pd.DataFrame         # 12집단 × 일 (보정 단계별 편차와 판정)
    dong: pd.DataFrame           # 47동 (터전)
    sources: dict = field(default_factory=dict)


def load_inputs() -> Inputs:
    p_seg = _first(PROCESSED_DIR / "features_segment.parquet", REFERENCE_DIR / "features_segment.csv")
    p_mon = _first(PROCESSED_DIR / "features_segment_month.parquet", REFERENCE_DIR / "features_segment_month.csv")
    p_brk = _first(REANALYSIS_DIR / "break_daily.csv", REFERENCE_DIR / "break_daily.csv")
    p_dong = _first(PROCESSED_DIR / "features_dong.parquet", REFERENCE_DIR / "features_dong.csv")

    read = lambda p: pd.read_parquet(p) if p.suffix == ".parquet" else pd.read_csv(p, encoding="utf-8-sig")
    seg, mon, brk, dong = read(p_seg), read(p_mon).rename(columns={"m": "month"}), read(p_brk), read(p_dong)

    brk["date"] = pd.to_datetime(brk["date"])
    brk["AGE"] = brk["band"]
    if "SGG_NM" not in dong:  # reference CSV
        dong = dong.rename(columns=_REF_DONG)
        dong["ADM_CD"] = dong["ADM_CD"].astype(str).replace(_SK_OLD_CODE)
        dong["ADM_NM"] = dong["ADM_NM"].str.replace(r"\(.*\)$", "", regex=True)
        dong["SGG_NM"] = dong["도시"].map(CITY_SGG)
    dong["ADM_CD"] = dong["ADM_CD"].astype(str)
    return Inputs(seg, mon, brk, dong, {"segment": p_seg, "segment_month": p_mon, "breaks": p_brk, "dong": p_dong})


def seg_name(city: str, sex: str, age: str) -> str:
    return f"{city} {sex[0]} {age}"


def _row(df: pd.DataFrame, city: str, sex: str, age: str) -> pd.Series:
    r = df[(df["city"] == city) & (df["sex"] == sex) & (df["AGE"] == age)]
    if r.empty:
        raise KeyError(f"집단 없음: {city} {sex} {age}")
    return r.iloc[0]


# ------------------------------------------------------------------ 양·질
def measure_breadth(inp: Inputs, city: str, sex: str, age: str, month: int | None = None) -> dict:
    """유효 발길 수(1/Σp²). month를 주면 그 달, 아니면 6개월 값. 같은 도시·성 50대와 견준다."""
    df = inp.segment if month is None else inp.segment_month[inp.segment_month["month"] == month]
    v, ref = _row(df, city, sex, age)["breadth"], _row(df, city, sex, COMPARE_AGE)["breadth"]
    return {"값": float(v), "50대": float(ref), "50대 대비": float(v / ref)}


def measure_quality(inp: Inputs, city: str, sex: str, age: str, month: int | None = None) -> dict:
    """체류 비중(%, 거주자 결제 건수 기준, 분모는 전 업종). 같은 도시·성 50대와 견준다."""
    df = inp.segment if month is None else inp.segment_month[inp.segment_month["month"] == month]
    v, ref = _row(df, city, sex, age)["stay"], _row(df, city, sex, COMPARE_AGE)["stay"]
    return {"값": float(v), "50대": float(ref), "50대 대비": float(v / ref)}


def narrow_cells(inp: Inputs) -> pd.DataFrame:
    """좁아짐 집단: 나이·도시 효과를 덜어 낸 좁아짐 점수(narrow)로 90대 뺀 32칸 중 상위 7칸."""
    s = inp.segment[inp.segment["AGE"] != "90대"].copy()
    s["좁아짐순위"] = s["narrow"].rank(ascending=False).astype(int)
    return s[s["좁아짐순위"] <= NARROW_TOP].sort_values("좁아짐순위")


# ------------------------------------------------------------------ 연속성
def _window(inp: Inputs, city: str, sex: str, age: str, as_of: pd.Timestamp) -> pd.DataFrame:
    b = inp.breaks
    w = b[(b["city"] == city) & (b["sex"] == sex) & (b["band"] == age)
          & b["date"].between(as_of - pd.Timedelta(days=WINDOW_DAYS - 1), as_of)]
    return w.sort_values("date")


def detect_break(inp: Inputs, city: str, sex: str, age: str, as_of: pd.Timestamp) -> dict:
    """지난 7일 창에서 보정 후(z2) 끊김이 있었는가. 빨강 = 필수까지 끊김, 주황 = 대면만 끊김."""
    w = _window(inp, city, sex, age, as_of)
    hit = w[w["state"] != "-"]
    worst = max(hit["state"], key=SEVERITY.get) if len(hit) else "-"
    pct = lambda d: int(round((np.exp(d.min()) - 1) * 100)) if len(d) else 0
    return {"상태": worst, "끊김 일수": len(hit), "창 일수": len(w),
            "끊긴 날": [d.strftime("%m/%d") for d in hit["date"]], "공휴일 주간": bool(w["holwk"].any()),
            "대면 최저(%)": pct(w["f_d2"]), "필수 최저(%)": pct(w["e_d2"])}


def correct_shock(inp: Inputs, city: str, sex: str, age: str, as_of: pd.Timestamp) -> dict:
    """보정 단계별로 창 안의 경보 일수. (0) 보정 없음 → (1) 계절형 → (2) + 같은 도시 30·40대 차감."""
    w = _window(inp, city, sex, age, as_of)
    return {"보정 없음": int(w["al0"].sum()), "계절형 보정": int(w["al1"].sum()), "공통 충격 보정": int(w["al2"].sum())}


# ------------------------------------------------------------------ 터전
def map_ground(inp: Inputs, adm_cd: str) -> dict:
    """동의 터전(통신). 터전점수는 도시 안 순위 평균이고 낮을수록 약하다. 공급 지표로 쓴다(#6)."""
    d = inp.dong[inp.dong["ADM_CD"] == str(adm_cd)]
    if d.empty:
        raise KeyError(f"동 패널에 없는 행정동코드: {adm_cd}")
    r = d.iloc[0]
    n = int((inp.dong["도시"] == r["도시"]).sum())
    return {"동": r["ADM_NM"], "도시": r["도시"], "터전점수": float(r["터전점수_통신"]), "순위": int(r["터전순위_통신"]),
            "동 수": n, "하위 20%": int(r["터전순위_통신"]) <= int(np.ceil(n * GROUND_BOTTOM)),
            "저녁비중": float(r["저녁비중"]), "일요일_평일비": float(r["일요일_평일비"])}


def ground_alerts(inp: Inputs) -> pd.DataFrame:
    """도시마다 터전점수 하위 20% 동 — 사람이 아니라 동 단위 정책으로 나간다."""
    out = []
    for city, g in inp.dong.groupby("도시"):
        k = int(np.ceil(len(g) * GROUND_BOTTOM))
        out.append(g.nsmallest(k, "터전점수_통신"))
    return pd.concat(out)[["도시", "ADM_CD", "ADM_NM", "터전점수_통신", "터전순위_통신"]]


# ------------------------------------------------------------------ 판정
@dataclass
class State:
    집단: str
    상태: str          # 끊김(빨강) / 끊김(주황) / 좁아짐 / 정상
    근거: dict


def rate_state(inp: Inputs, city: str, sex: str, age: str, as_of: pd.Timestamp) -> State:
    """네 상태 중 집단 단위 셋을 판정한다. 터전 없음은 동 단위라 ground_alerts가 따로 낸다(기획안 3절)."""
    month = as_of.month
    ev = {"양": measure_breadth(inp, city, sex, age, month), "질": measure_quality(inp, city, sex, age, month)}
    narrow = narrow_cells(inp)
    ev["좁아짐 상위"] = bool(((narrow["city"] == city) & (narrow["sex"] == sex) & (narrow["AGE"] == age)).any())
    if age in BREAK_AGES:
        ev["연속성"] = detect_break(inp, city, sex, age, as_of)
        ev["보정"] = correct_shock(inp, city, sex, age, as_of)
        if ev["연속성"]["상태"] != "-":
            color = "빨강" if ev["연속성"]["상태"].startswith("빨강") else "주황"
            return State(seg_name(city, sex, age), f"끊김({color})", ev)
    return State(seg_name(city, sex, age), "좁아짐" if ev["좁아짐 상위"] else "정상", ev)


# ------------------------------------------------------------------ 명부·상대방·자원
ROSTER_COLUMNS = ["대상자ID", "시군구", "성", "연령대", "행정동코드", "마지막접촉일", "명부종류"]


def read_roster(path: Path) -> pd.DataFrame:
    r = pd.read_csv(path, dtype={"행정동코드": str}, encoding="utf-8-sig")
    missing = [c for c in ROSTER_COLUMNS if c not in r]
    if missing:
        raise ValueError(f"명부에 필수 열이 없습니다: {missing} (docs/agent_입력형식.md)")
    r["마지막접촉일"] = pd.to_datetime(r["마지막접촉일"])
    return r


def match_roster(roster: pd.DataFrame, city: str, sex: str, age: str, as_of: pd.Timestamp, top_n: int = 3) -> pd.DataFrame:
    """끊긴 칸(시군구 × 성 × 연령대)으로 명부를 거르고, 마지막 접촉이 오래된 순으로 top_n명.
    행정동은 거르는 데 쓰지 않는다 — 결과에 붙여 터전과 상대방 후보를 찾는 데만 쓴다."""
    m = roster[(roster["시군구"] == CITY_SGG[city]) & (roster["성"] == sex) & (roster["연령대"] == age)].copy()
    m["경과일"] = (as_of - m["마지막접촉일"]).dt.days
    return m.sort_values("경과일", ascending=False).head(top_n).assign(칸_인원=len(m))


def find_counterpart(*_, **__):
    """발길이 닿던 곳 후보 3~4곳: 집단의 대면 업종 집중 × 대상자 동의 가게·경로당 × 게이트키퍼 지정.
    입력: docs/agent_입력형식.md 「발길이 닿던 곳」 표 (D4). 10/18~20에 붙인다."""
    raise NotImplementedError("D4 가상 데이터(발길이 닿던 곳 표)가 들어오면 붙입니다 — 10/18~20")


def match_resource(*_, **__):
    """상태별 자원 후보: 복지로·1365 정제본(res_*.parquet)을 거리·반복성·대면성으로 정렬(기획안 6절)."""
    raise NotImplementedError("자원 정제본(scripts/fetch_welfare_api.py 산출)을 받아 10/18~20에 붙입니다")


def log_outcome(*_, **__):
    """종결 기록(개인·집단)과 임계값 되먹임. 기록 형식은 docs/agent_입력형식.md 「종결 기록」."""
    raise NotImplementedError("종결 기록 형식 확정(10/17) 뒤에 붙입니다")


# ------------------------------------------------------------------ 문장 틀
def draft_outreach(st: State, people: pd.DataFrame | None = None) -> str:
    """고정 문장 틀 + 수치 슬롯. 명부의 이름·연락처·주소는 문장에 넣지 않는다(E6 4절)."""
    e = st.근거
    q, b = e["질"], e["양"]
    lines = [f"**{st.상태} · {st.집단}**",
             f"〈양〉 유효 발길 수 {b['값']:.1f} — 같은 도시·성 50대({b['50대']:.1f})의 {b['50대 대비']:.0%}.",
             f"〈질〉 체류 비중 {q['값']:.1f}% — 50대({q['50대']:.1f}%)의 {q['50대 대비']:.0%}."]
    if "연속성" in e:
        c, s = e["연속성"], e["보정"]
        if c["상태"] != "-":
            kind = "필수 발길(장보기·병원·약국)까지" if c["상태"].startswith("빨강") else "대면 발길만"
            lines.append(f"〈연속성〉 지난 {WINDOW_DAYS}일 중 {c['끊김 일수']}일({', '.join(c['끊긴 날'])}) {kind} 평소 흔들림의 3배 밖으로 "
                         f"줄었습니다(대면 최저 {c['대면 최저(%)']:+d}%, 필수 최저 {c['필수 최저(%)']:+d}%).")
            lines.append(f"〈보정〉 같은 7일에 보정 없이 {s['보정 없음']}일 → 계절 보정 {s['계절형 보정']}일 → "
                         f"같은 도시 30·40대 차감 {s['공통 충격 보정']}일.")
            if e.get("동시 끊김"):
                k, n = e["동시 끊김"]
                lines.append(f"〈동시〉 같은 도시 고령 {n}개 집단 중 {k}개가 같은 7일에 함께 끊겼습니다"
                             + (" (공휴일 주간과 겹침)" if c["공휴일 주간"] else "")
                             + ". 30·40대를 빼고도 남은 공통 사건일 수 있습니다.")
        else:
            lines.append(f"〈연속성〉 지난 {WINDOW_DAYS}일 끊김 없음.")
    if people is not None and len(people):
        days = " · ".join(f"{d}일" for d in people["경과일"])
        lines.append(f"〈명부〉 이 칸에 드는 대상자 {int(people['칸_인원'].iloc[0])}명 중 마지막 접촉이 가장 오래된 {len(people)}명 ({days}).")
        lines += [f"  - {r.대상자ID}: 접촉 {r.경과일}일 전 · 〈터전〉 {r.터전}" for r in people.itertuples()]
    if st.상태.startswith("끊김") and e.get("동시 끊김"):
        lines.append("▸ 권고: 개별 전화 전에 공통 사건(명절·한파·지역 행사)인지 먼저 확인합니다. 사건이 아니면 1단계 전화부터.")
    elif st.상태.startswith("끊김"):
        lines.append("▸ 권고: 1단계 전화. 닿지 않으면 본인이 등록한 발길이 닿던 곳(단골 가게·경로당)에 문의"
                     + (" → 방문 전 복지서비스 후보를 붙입니다." if "빨강" in st.상태 else "."))
    elif st.상태 == "좁아짐":
        lines.append("▸ 권고: 사람이 아니라 동 단위 자원(프로그램·봉사 일감)으로 냅니다.")
    return "\n".join(lines)


# ------------------------------------------------------------------ 주간 루프
def weekly_briefing(inp: Inputs, as_of: pd.Timestamp, roster: pd.DataFrame | None = None, top_n: int = 3) -> str:
    """끊김 루프(주 1회) 한 번. 60·70·80대 12집단을 판정하고, 끊긴 칸만 명부와 교차한다."""
    states = [rate_state(inp, c, s, a, as_of) for c in CITY_SGG for s in ["남성", "여성"] for a in BREAK_AGES]
    broken = sorted([st for st in states if st.상태.startswith("끊김")], key=lambda st: st.상태 != "끊김(빨강)")
    # 같은 도시 고령 6집단 중 절반 이상이 같은 창에서 끊기면 개인 사건보다 공통 사건을 먼저 의심한다(기획안 2절)
    for city in CITY_SGG:
        same = [st for st in broken if st.집단.startswith(city)]
        if len(same) >= len(BREAK_AGES):
            for st in same:
                st.근거["동시 끊김"] = (len(same), 2 * len(BREAK_AGES))
    blocks, n_people = [], 0
    for st in broken:
        city, sx, age = st.집단.split()
        people = None
        if roster is not None:
            people = match_roster(roster, city, {"남": "남성", "여": "여성"}[sx], age, as_of, top_n)
            people = people.assign(터전=[f"{g['동']} 터전 약한 순 {g['순위']}/{g['동 수']}" + (" (하위 20%)" if g["하위 20%"] else "")
                                       for g in (map_ground(inp, cd) for cd in people["행정동코드"])])
            n_people += len(people)
        blocks.append(draft_outreach(st, people))
    narrow = narrow_cells(inp)
    ground = ground_alerts(inp)
    head = [f"# 주간 브리핑 — {as_of:%Y-%m-%d} 기준 (지난 {WINDOW_DAYS}일 창)",
            f"끊김 {len(broken)}개 집단 (빨강 {sum(st.상태 == '끊김(빨강)' for st in broken)} · 주황 {sum(st.상태 == '끊김(주황)' for st in broken)})"
            + (f", 확인 권고 {n_people}명" if roster is not None else ", 명부 없음 — 교차 생략"),
            f"좁아짐 {len(narrow)}개 집단·터전 없음 후보 {len(ground)}개 동은 사람이 아니라 동 단위로 나갑니다.", ""]
    tail = ["", "## 좁아짐 (90대 뺀 32칸 중 상위 7칸)"]
    tail += [f"- {r.seg} (점수 {r.narrow:+.2f}, {r.좁아짐순위}위)" + (" — 청년: 끊김 감시 대상 아님" if r.AGE in ("10대", "20대") else "")
             for r in narrow.itertuples()]
    tail += ["", f"## 터전 없음 후보 (도시 안 터전점수 하위 {GROUND_BOTTOM:.0%}, 공급 지표)"]
    tail += [f"- {r.도시} {r.ADM_NM} (약한 순 {r.터전순위_통신}위)" for r in ground.itertuples()]
    return "\n".join(head + ["\n\n".join(blocks) if blocks else "이번 주 끊김 없음."] + tail)


def main() -> None:
    ap = argparse.ArgumentParser(description="발길 에이전트 주간 브리핑 (D1 뼈대)")
    ap.add_argument("--as-of", default=None, help="기준일 YYYY-MM-DD (기본: 끊김 자료의 마지막 날)")
    ap.add_argument("--roster", type=Path, default=None, help="가상 명부 CSV (docs/agent_입력형식.md)")
    ap.add_argument("--top", type=int, default=3)
    a = ap.parse_args()
    inp = load_inputs()
    as_of = pd.Timestamp(a.as_of) if a.as_of else inp.breaks["date"].max()
    roster = read_roster(a.roster) if a.roster else None
    print(weekly_briefing(inp, as_of, roster, a.top))
    print("\n입력: " + ", ".join(f"{k}={Path(v).relative_to(ROOT)}" for k, v in inp.sources.items()))


if __name__ == "__main__":
    main()
