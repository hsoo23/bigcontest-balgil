"""발길 — 담당자 화면 4개 (D3, 시연용).

실행: streamlit run app/balgil_app.py      (?screen=1~4 를 붙이면 그 화면만 — 캡처·데모용)
의존: app/requirements-app.txt (분석 쪽 requirements.txt에 화면 라이브러리를 더한 것)

읽는 파일은 모두 git에 있다 — 원본 데이터가 없어도 뜬다.
  reanalysis/reference/   재분석 결과 (끊김·보정·주간 패널)
  data/reference/app/     scripts/build_app_data.py가 만든 지도·시설·SHAP, 화면 ①의 agent.py 표(대상자 표는 가상 명부)
  data/reference/         dong_priority.csv · reach_efficiency.csv (화면 ③ 공급 × 필요, build_priority.py)
캡처: python scripts/capture_screens.py → reports/screens/ (제출 체크리스트 9번)

원칙
  * 집단 지표(양·질·연속성)는 시군구 × 성 × 연령까지만. 동 단위로 보여 주는 것은 터전뿐이다.
  * 화면 ①은 D1 agent.py 판정(빨강·주황·노랑·초록 넷)을 그대로 보인다. 기획안 3절 5단계의 초록·연두 구분과
    장보기형·병원약국형 구분은 agent.py에 규칙이 생기면 따라 바꾼다(#4 수경 코멘트).
  * 숫자는 docs/최종수치표.md와 같다 — 화면이 새 숫자를 만들지 않고 위 파일만 읽는다.
  * 읽는 순서를 정한다: 질문(제목) → 답 카드 한 장(「그래서 무엇을」 + 오늘 할 일) → 그림 → 세부는 접어 둔다.
    방법·출처 설명은 화면에 두지 않고 보고서(06·07·08절 · E5)에 맡긴다 — 담당자 화면에는 답과 그림만(10/26).

겉모양은 app/style.py(Stripe DESIGN.md 토큰). 데이터 색은 dataviz 기준 팔레트(검증: validate_palette.js)
  신호(빨강·주황·노랑)  status critical/serious/warning — 색만으로 말하지 않고 항상 점·글자를 같이 단다
  터전 지도         순차 파랑 한 가지 (진할수록 값이 큼)
  지도 위 시설 점   주황(경로당)·청록(도서관) — 범주 2·3번, 전 쌍 CVD ΔE 9.2 통과
  대응(공급 × 필요) 1순위 파랑·형평 주황·연결 청록 = 범주 1~3번(--pairs all 통과, 청록 대비 2.8:1이라 표·툴팁·
                    모서리 글자를 함께 둔다), 유지는 회색. 이때 시설 점은 색을 빼고 먹색(속 빈 점·채운 점)으로 바꾼다
  SHAP 막대         발산 파랑(확률을 낮춤)·빨강(높임)
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import altair as alt
import folium
import geopandas as gpd
import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

sys.path.insert(0, str(Path(__file__).resolve().parent))
import style as ui  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
REF = ROOT / "reanalysis" / "reference"
APP = ROOT / "data" / "reference" / "app"

# ── 데이터 색 (dataviz reference palette) ──────────────────────────────
SERIOUS, CRITICAL, WARNING, CALM = "#ec835a", "#d03b3b", "#fab219", "#c3ccd7"
BLUE_RAMP = ["#cde2fb", "#86b6ef", "#3987e5", "#256abf", "#104281"]  # 순차 100·250·400·500·650
POS, NEG = "#e34948", "#2a78d6"  # 발산: 확률을 높임 / 낮춤
SERIES = ["#2a78d6", "#eb6834"]  # 범주 1·2번 (선 두 개)
FAC_COLOR = {"경로당": "#eb6834", "도서관": "#1baf7a"}
SHADE = "#eef2f7"  # 공통 사건 주간 배경 띠


FEATURE_KO = {
    "m3": "좁아짐 3주 평균", "narrow": "이번 주 좁아짐", "d_narrow": "좁아짐 변화",
    "breadth_z": "발길 수 (양)", "d_breadth_z": "발길 수 변화",
    "stay_z": "체류 비중 (질)", "d_stay_z": "체류 비중 변화",
    "meal": "식사 비중", "anon": "익명 비중", "med": "병원·약국 비중", "evening": "저녁 결제 비중",
}
WEEK0 = pd.Timestamp("2025-07-07")  # weekly_panel의 w=0 주의 월요일

st.set_page_config(page_title="발길 — 담당자 화면", page_icon="👣", layout="wide", initial_sidebar_state="expanded")
st.html(ui.CSS)  # <style>만 있으면 앱 전체에 적용된다


@alt.theme.register("balgil", enable=True)
def chart_theme():
    return {
        "config": {
            "background": "transparent",  # 카드 바탕을 그대로 — 테마가 바뀌어도 차트만 다른 색이 되지 않게
            "font": ui.FONT,
            "padding": {"top": 8, "left": 4, "right": 8, "bottom": 4},
            "view": {"stroke": None},
            "axis": {"labelColor": ui.MUTE, "titleColor": ui.MUTE, "gridColor": ui.HAIRLINE, "domain": False,
                     "tickColor": ui.HAIRLINE, "labelFontSize": 11, "titleFontSize": 11, "titleFontWeight": 400,
                     "labelPadding": 6},
            "legend": {"labelColor": ui.INK_2, "labelFontSize": 12, "symbolSize": 80, "titleFontSize": 11},
            "title": {"color": ui.INK, "fontSize": 14, "fontWeight": 600, "anchor": "start", "offset": 12,
                      "subtitleColor": ui.MUTE, "subtitleFontSize": 12, "subtitleFontWeight": 400},
        }
    }


def card(key: str):
    return st.container(border=True, key=f"card_{key}")


def html(s: str):
    st.markdown(s, unsafe_allow_html=True)


# ── 데이터 ─────────────────────────────────────────────────────────────
@st.cache_data
def load_breaks(nomed: bool) -> pd.DataFrame:
    b = pd.read_csv(REF / ("nomed_break_daily.csv" if nomed else "break_daily.csv"), parse_dates=["date"])
    b["face_pct"] = (np.exp(b["f_d2"]) - 1) * 100
    b["ess_pct"] = (np.exp(b["e_d2"]) - 1) * 100
    b["week"] = b["date"] - pd.to_timedelta(b["date"].dt.weekday, unit="D")
    return b


@st.cache_data
def load_agent() -> tuple[pd.DataFrame, pd.DataFrame]:
    summ = pd.read_csv(APP / "agent_summary.csv", parse_dates=["기준일"])
    groups = pd.read_csv(APP / "agent_groups.csv", parse_dates=["기준일"])
    groups["상대방업종"] = groups["상대방업종"].fillna("")
    if "궂은날" in groups:  # agent.py 날씨 꼬리표(#31 수경). 표를 그 뒤에 다시 만들어야 열이 생긴다
        groups["궂은날"] = groups["궂은날"].fillna("")
    for c in ("다음행동", "자원후보"):  # agent.py next_step·match_resource(#44 수경). 표를 그 뒤에 다시 만들어야 열이 생긴다
        if c in groups:
            groups[c] = groups[c].fillna("")
    return summ, groups


@st.cache_data
def load_people() -> pd.DataFrame | None:
    """확인 권고 대상자 × 주. 가상 명부(D4, data/synthetic/roster_가상.csv)를 넣어 돌린 agent.py 표다."""
    path = APP / "agent_people.csv"
    if not path.exists():
        return None
    pp = pd.read_csv(path, parse_dates=["기준일"], dtype={"행정동코드": str})
    for c in ("등록장소", "후보장소"):  # 장소 표(D4, #59)를 넣어 만든 표에만 있다. 예전 표는 열이 없다
        if c in pp:
            pp[c] = pp[c].fillna("")
    return pp


@st.cache_data
def load_false_alarm(nomed: bool) -> pd.DataFrame:
    return pd.read_csv(REF / ("nomed_false_alarm.csv" if nomed else "false_alarm.csv"), index_col=0)


@st.cache_data
def load_weekly() -> pd.DataFrame:
    p = pd.read_csv(REF / "weekly_panel.csv")
    p["week"] = WEEK0 + pd.to_timedelta(p["w"] * 7, unit="D")
    return p


@st.cache_data
def load_shap() -> pd.DataFrame:
    return pd.read_csv(APP / "shap_weekly.csv")


@st.cache_data
def load_map() -> gpd.GeoDataFrame:
    return gpd.read_file(APP / "dong_map.geojson")


@st.cache_data
def load_facilities() -> pd.DataFrame:
    return pd.read_csv(APP / "facilities.csv")


def signed(x: float) -> str:
    r = int(round(x))
    return "0%" if r == 0 else f"{r:+d}%"


# ── ① 주간 브리핑 ──────────────────────────────────────────────────────
# agent.py(D1) 신호 넷. 색만으로 말하지 않고 항상 점·글자를 같이 단다
SIGNAL = {
    "빨강": ("빨강 · 필수형 끊김", CRITICAL),
    "주황": ("주황 · 대면형 끊김", SERIOUS),
    "노랑": ("노랑 · 좁아짐", WARNING),
    "초록": ("초록 · 평온", CALM),
}
sig_dot = lambda c: f"<span class='bg-dot' style='background:{c};margin-right:5px'></span>"  # noqa: E731
SIGNAL_ORDER = {"빨강": 0, "주황": 1, "노랑": 2, "초록": 3}
DEMO_AS_OF = "2025-10-12"  # 시연 주 10/06~10/12 (#49 2번). 보조 장면 10/01 주황은 10/05 주
DEMO_SEG = "춘천 여성 70대"  # 화면 ② 기본 집단 — 시연 칸(08절 8.1)


def next_action(r: pd.Series, n_same: int) -> str:
    """agent.py draft_outreach의 권고와 같은 순서 (07_에이전트 7.5, #2)."""
    if r["신호"] in ("빨강", "주황") and r["동시끊김"]:
        return f"공통 사건 먼저 확인 — 같은 도시 {n_same}개 집단 동시"
    if r["신호"] == "빨강":
        return "본인 전화 → 닿지 않으면 발길이 닿던 곳 → 방문 (복지서비스 후보)"
    if r["신호"] == "주황":
        return "본인 전화 → 닿지 않으면 발길이 닿던 곳"
    if r["신호"] == "노랑":
        return "동 단위 프로그램·봉사 일감 (사람이 아님)"
    return "—"


SHORT = {"빨강": "필수형 끊김", "주황": "대면형 끊김", "노랑": "좁아짐", "초록": "평온"}
SEXES, AGES = ["남", "여"], ["60대", "70대", "80대"]


# agent.py 날씨 꼬리표(「큰비 2일(10/10·10/11)」)를 담당자가 읽는 말로. 기준은 scripts/explore_weather.py
WEATHER_WORDS = {"큰비": "비가 많이 온 날", "폭염": "폭염", "한파": "한파", "대설": "눈이 많이 온 날"}


def weather_words(tag: str) -> str:
    """「큰비 2일(10/10·10/11) · 한파 1일(…)」 → 「비가 많이 온 날 2일 · 한파 1일」. 날짜는 뺀다."""
    tag = re.sub(r"\([^)]*\)", "", tag)
    return re.sub(r"\S+(?= \d+일)", lambda m: WEATHER_WORDS.get(m.group(), m.group()), tag).strip()


def briefing_answer(g: pd.DataFrame, n_people: int) -> tuple[str, str, list | None]:
    """이번 주 답 — (한 줄, 덧말, 오늘 할 일). agent.py 권고 순서(07_에이전트 7.5)를 할 일 세 칸으로 편다.
    첫인상에서 읽히도록 한 줄은 짧게, 근거 숫자는 아래 타일·신호판이 맡는다."""
    broken = g[g["신호"].isin(["빨강", "주황"])]
    same = broken[broken["동시끊김"]]
    if broken.empty:
        n_y = int((g["신호"] == "노랑").sum())
        return ("<b>끊긴 집단이 없습니다</b>",
                f"좁아진 {n_y}개 집단은 동 단위 프로그램·봉사로 나갑니다" if n_y else "다음 주에 다시 봅니다", None)
    # 궂은 날은 「비가 많이 온 날 2일」처럼 말로만 — 날짜는 아래 자세히 표에 있다. 같은 날씨인 도시는 한데 묶는다
    wx = {c: d["궂은날"].replace("", np.nan).dropna() for c, d in broken.groupby("도시")}
    by_wx: dict[str, list[str]] = {}
    for c, v in wx.items():
        if len(v):
            by_wx.setdefault(weather_words(v.iloc[0]), []).append(c)
    wx_txt = " · ".join(f"{'·'.join(cs)}{' 모두' if len(cs) > 1 else ''} {w}" for w, cs in by_wx.items())
    wx_sub = f"<br>날씨 탓일 수도 있습니다 — {ui.esc(wx_txt)}" if wx_txt else ""
    if not same.empty:
        return (f"고령 <b>{len(same)}개 집단</b>이 도시마다 함께 끊겼습니다",
                f"한 사람씩 전화하기 전에 <b>공통 사건</b>부터 확인하세요{wx_sub}",
                [("공통 사건 확인", "명절·궂은 날·행사면 전화는 미룹니다", True),
                 (f"아니면 {n_people}명에게 전화", "칸마다 가장 오래 끊긴 3명 (가상 명부)", False),
                 ("닿지 않으면 가게·경로당 → 방문", "가져갈 복지서비스는 아래", False)])
    if n_people == 0:
        return (f"<b>{len(broken)}개 집단</b>이 끊겼지만 명부에 대상자가 없습니다",
                f"신호는 집단 단위라 명부에 없는 어르신은 사람 목록에 오르지 않습니다{wx_sub}", None)
    return (f"<b>{len(broken)}개 집단</b>이 끊겼습니다 — <b>{n_people}명</b>에게 먼저 전화하세요",
            f"같은 도시에서 함께 끊긴 집단이 없어 개인 확인부터 합니다{wx_sub}",
            [(f"{n_people}명에게 전화", "칸마다 가장 오래 끊긴 3명 (가상 명부)", True),
             ("닿지 않으면 발길이 닿던 곳", "평소 가게나 경로당·마을회관에 묻습니다", False),
             ("그래도 비면 방문", "빨강이면 복지서비스 후보를 붙여 갑니다", False)])


def signal_tile(r: pd.Series | None) -> str:
    """신호판 한 칸 — 색 띠 · 신호 이름 · 큰 숫자 하나 · 끊긴 날. 나머지(날씨·업종·다음 행동)는 접힌 표에."""
    if r is None:
        return "<div class='bg-tile calm'><div class='v'>—</div></div>"
    sig = r["신호"]
    color = SIGNAL[sig][1]
    head = f"<div class='s'><span class='bg-dot' style='background:{color}'></span>{SHORT[sig]}</div>"
    if sig in ("빨강", "주황"):
        v = r["필수_7일최저_pct"] if sig == "빨강" else r["대면_7일최저_pct"]
        return (f"<div class='bg-tile' style='border-top-color:{color};background:{ui.tint(color, .08)}'>{head}"
                f"<div class='v'>{signed(v)}</div><div class='d'>끊긴 날 {int(r['끊김일수'])}일</div></div>")
    word = "동 단위 자원" if sig == "노랑" else "평소대로"
    return f"<div class='bg-tile calm' style='border-top-color:{color}'>{head}<div class='v'>{word}</div><div class='d'>&nbsp;</div></div>"


def signal_matrix(g: pd.DataFrame):
    """12개 집단을 (도시 · 성) 넷 × 연령 셋 한 판으로 — 표를 읽지 않아도 어디가 빨간지 먼저 보인다."""
    by = g.set_index("집단")
    cells = ["<div></div>"] + [f"<div class='ax top'>{a}</div>" for a in AGES]
    for city in sorted(g["도시"].unique()):
        for sx in SEXES:
            cells.append(f"<div class='ax'>{ui.esc(city)} {sx}</div>")
            cells += [signal_tile(by.loc[k] if (k := f"{city} {sx} {a}") in by.index else None) for a in AGES]
    leg = "".join(f"<span><span class='bg-dot' style='background:{SIGNAL[k][1]}'></span>{SHORT[k]}</span>" for k in SIGNAL)
    html(f"<div class='bg-board'><div class='hd'><div><div class='bg-sec' style='margin:0'>12개 집단 신호</div>"
         f"<div class='sub'>숫자 = 지난 7일 중 가장 크게 준 날의 발길 (보정 뒤)</div></div><div class='lg'>{leg}</div></div>"
         f"<div class='bg-mx'>{''.join(cells)}</div></div>")


def signal_table(g: pd.DataFrame):
    g = g.assign(_o=g["신호"].map(SIGNAL_ORDER))
    same = g[g["동시끊김"]].groupby("도시").size()
    has_wx = "날씨가능" in g
    rows = []
    for _, r in g.sort_values(["_o", "집단"]).iterrows():
        label, color = SIGNAL[r["신호"]]
        broken = r["신호"] in ("빨강", "주황")
        # 알림은 지우지 않고 꼬리표만 단다(B4 메모 4절). 상태 색이 아니라 글자로만 보인다
        wx = (f"<span class='sm'>{_items(weather_words(r['궂은날']), stack=True)}</span>"
              if has_wx and broken and r["날씨가능"] else "")
        rows.append({
            # 칸을 여섯으로 — 보조 정보(날씨 · 끊긴 날)는 둘째 줄로 내려 좁은 폭에서도 글자가 쪼개지지 않게
            "신호 · 날씨 가능": ui.badge(SHORT[r["신호"]], color) + wx,
            "집단": ui.esc(r["집단"]) + (f"<span class='sm'>끊긴 날 {int(r['끊김일수'])}일</span>" if broken else ""),
            "발길 최저": (f"대면 {signed(r['대면_7일최저_pct'])}<span class='sm' style='color:inherit'>필수 "
                       f"{signed(r['필수_7일최저_pct'])}</span>") if broken else "—",
            "평소 닿던 업종": _items(r["상대방업종"], stack=True) if broken and r["상대방업종"] else "—",
            # agent.py가 낸 문구를 그대로 쓴다(브리핑과 갈리지 않게). 열이 없는 옛 표에서만 화면 규칙으로
            "다음 행동": ui.esc(r["다음행동"] if r.get("다음행동") else next_action(r, int(same.get(r["도시"], 0)))),
            "_calm": r["신호"] == "초록",
        })
    cols = [("신호 · 날씨 가능", "w-sig"), ("집단", "nw"), ("발길 최저", "n nw"), ("평소 닿던 업종", "m nw"), ("다음 행동", "m")]
    html(ui.table(cols, rows, dim_key="_calm"))


# 주 고르기 — 끌어서 맞추는 막대 대신 목록에서 바로 고르고, ◀ ▶로 한 주씩 넘긴다(10/26 현수 의견).
# 공휴일이 든 주에는 꼬리표를 단다 — 담당자가 「그 주」를 이름으로 찾는다
WEEK_TAGS = {"2025-08-11": "광복절", "2025-09-29": "추석 연휴", "2025-10-06": "추석 연휴",
             "2025-12-22": "성탄절"}


def week_label(monday: pd.Timestamp) -> str:
    tag = WEEK_TAGS.get(f"{monday:%Y-%m-%d}")
    return f"{monday:%m/%d}~{monday + pd.Timedelta(days=6):%m/%d}" + (f" · {tag}" if tag else "")


def week_picker(where, label: str, options: list, default, fmt, key: str):
    """목록 + ◀ ▶. 값은 session_state[key] 하나에 두고, 버튼은 그 값을 한 칸 옮긴다."""
    if st.session_state.get(key) not in options:
        st.session_state[key] = default
    sel, prev, nxt = where.columns([6, 1, 1], vertical_alignment="bottom", gap="small")
    i = options.index(st.session_state[key])
    step = lambda d: st.session_state.__setitem__(key, options[i + d])  # noqa: E731
    prev.button("◀", key=f"{key}_prev", help="지난주", disabled=i == 0, on_click=step, args=(-1,),
                use_container_width=True)
    nxt.button("▶", key=f"{key}_next", help="다음 주", disabled=i == len(options) - 1, on_click=step, args=(1,),
               use_container_width=True)
    return sel.selectbox(label, options, key=key, format_func=fmt)


def screen_briefing():
    summ, groups = load_agent()
    days = list(summ["기준일"])
    top, ctl = st.columns([3, 2], vertical_alignment="bottom")
    top.markdown(ui.topbar("주간 브리핑", "이번 주 누구를 먼저 확인할까 — 60대 이상 12개 집단"), unsafe_allow_html=True)
    demo = pd.Timestamp(DEMO_AS_OF)
    as_of = week_picker(ctl, "주 (월~일)", days, demo if demo in days else days[-1],
                        lambda d: week_label(d - pd.Timedelta(days=6)), "wk_brief")
    sm = summ[summ["기준일"] == as_of].iloc[0]
    g = groups[groups["기준일"] == as_of].copy()
    pp = load_people()
    p = pp[pp["기준일"] == as_of] if pp is not None else pd.DataFrame()
    text, sub, steps = briefing_answer(g, len(p))
    wk = f"{as_of - pd.Timedelta(days=6):%m/%d}~{as_of:%m/%d}"

    main, rail = st.columns([2.3, 1], gap="medium")
    with main:
        html(ui.hero_card(f"이번 주 답 · {wk}", text, sub))
        n, n_prev = int(sm["확인권고_집단"]), int(sm["지난주_확인권고_집단"])
        # 공통 충격 보정은 경보를 지우기도(명절) 드러내기도(30·40대는 그대로인데 고령만 준 주) 한다.
        # 그래서 "남은"이 아니라 "보정 뒤"로 부르고, 늘어난 주는 늘어났다고 적는다 (10/01 강남 남 60대 주황이 그 예)
        a0, a1, a2 = (int(sm[k]) for k in ("경보일_보정없음", "경보일_계절보정", "경보일_공통충격보정"))
        html(ui.kpis([
            ui.kpi("확인 권고 집단", f"{n}", ui.PRIMARY, "users", f"지난주 {n_prev}개", unit="/ 12"),
            # 신호판·배지와 같은 색 점 — 타일 바탕은 발표자료 색이라 신호 색은 점으로만 보인다
            ui.kpi("필수형 끊김", f"{int(sm['빨강'])}", CRITICAL, "alert", f"{sig_dot(CRITICAL)}빨강 신호"),
            ui.kpi("대면형 끊김", f"{int(sm['주황'])}", SERIOUS, "bell", f"{sig_dot(SERIOUS)}주황 신호"),
            ui.kpi("보정 뒤 경보일", f"{a2}", "#1baf7a", "shield", f"보정 없이 {a0}" + (" · 늘어남" if a2 > a0 else ""))]))
        # 사람을 먼저 — 담당자가 이번 주 할 일(전화)이 맨 위, 그 근거인 집단 신호는 아래로
        people_section(as_of, g, p)
        st.write("")
        signal_matrix(g)
        with st.expander("집단별 자세히 — 끊긴 날 · 발길 최저 · 날씨 · 평소 닿던 업종 · 다음 행동"):
            signal_table(g)
    with rail:
        if steps:
            html(ui.timeline("오늘 할 일", "위에서부터 차례로", steps))
        resource_lines(g)


# ── ② 발길 상세 ────────────────────────────────────────────────────────
N_DONG = {"강남": 22, "춘천": 25}  # 터전 순위의 분모 (도시 안 동 수)


def _short_places(text: str, dong: str) -> str:
    """agent.py 장소 글(「(가상) 교동 한식 1 (한식 · 지정) · …」)을 표 칸에 맞게 줄인다. 가상 가게는 「(가상) 동 」 머리와
    이름에 이미 든 업종 꼬리를 떼고(「한식 1」), 경로당·마을회관은 실제 이름이라 그대로 둔다. 가상 표기는 열 제목·설명에 있다."""
    def short(m: re.Match) -> str:
        return m.group(1) if m.group(1).startswith(m.group(2)) else m.group(0)
    return re.sub(r"\(가상\) (?:" + re.escape(dong) + r" )?([^()]+?) \(([^()·]+?)(?: · 지정)?\)", short, text)


def _items(text: str, stack: bool = False) -> str:
    """「한식 30% · 약국 20%」 → 항목마다 줄을 바꾸지 않는 덩어리로. 표 칸이 좁아도 「커피전문 / 점」처럼 쪼개지지 않는다.
    stack이면 한 줄에 하나씩 쌓는다."""
    parts = [ui.esc(x) for x in text.split(" · ")]
    if stack:
        return "".join(f"<span class='it' style='display:block'>{x}</span>" for x in parts)
    return " · ".join(f"<span class='it'>{x}</span>" for x in parts)


def _place(r: pd.Series) -> str:
    # 본인이 등록한 곳이 있으면 그곳 하나, 없으면 그 동의 후보 (agent.py place_candidates)
    if r.get("등록장소"):
        return f"<b>본인 등록</b><span class='sm' style='color:inherit'>{_items(_short_places(r['등록장소'], r['행정동']), stack=True)}</span>"
    if r.get("후보장소"):
        return f"후보<span class='sm' style='color:inherit'>{_items(_short_places(r['후보장소'], r['행정동']), stack=True)}</span>"
    return "—"


# agent.py `_window_text` 가 만든 글 — 두 꼴이다.
#   가게 먼저 — 한식 87곳 · 약국 13곳 · 중식 10곳 (경로당·마을회관 9곳)
#   경로당·마을회관 먼저 — 경로당·마을회관 11곳 (가게: 한식 4곳)
# 화면에는 **창구를 가른 비교**를 보인다. 업종별 수만 늘어놓으면 「한식 271곳에 전화하라는 말인가」로
# 읽히는데, 실제로 묻는 곳은 오른쪽 열의 최대 4곳이고 이 수는 「가게 쪽인가 경로당 쪽인가」의 근거다.
WINDOW_SHOP = re.compile(r"^가게 먼저 — (.*) \((경로당·마을회관 [\d,]+곳|경로당 수 없음[^)]*)\)$")
WINDOW_CENTER = re.compile(r"^경로당·마을회관 먼저 — (경로당·마을회관 [\d,]+곳) \(가게: (.*)\)$")


def _re_first_int(s: str) -> int | None:
    m = re.search(r"([\d,]+)곳", s)
    return int(m.group(1).replace(",", "")) if m else None


def _window_cell(text: str) -> str:
    """창구 판단 칸 — 「가게 110곳 ↔ 경로당·마을회관 9곳」과 업종 내역. 꼴이 다르면 원문을 그대로 둔다."""
    m, center_first = WINDOW_SHOP.match(text), False
    if not m:
        m, center_first = WINDOW_CENTER.match(text), True
    if not m:
        return ui.esc(text)
    shops_txt, centers_txt = (m.group(2), m.group(1)) if center_first else (m.group(1), m.group(2))
    n = [int(x.replace(",", "")) for x in re.findall(r"([\d,]+)곳", shops_txt)]
    total = f"가게 {sum(n):,}곳" if n else shops_txt
    detail = re.sub(r"\s*([\d,]+)곳", lambda m: " " + m.group(1), shops_txt) if n else ""
    win = "경로당·마을회관" if center_first else "가게"
    mark = lambda s, on: f"<b>{ui.esc(s)}</b>" if on else ui.esc(s)
    # 3배 규칙이 보이게 — 「경로당 9곳」만으로는 왜 가게 쪽인지 알 수 없다(SHOP_PER_CENTER = 3)
    cn = _re_first_int(centers_txt)
    right = f"{centers_txt} × 3 = {cn * 3:,}곳" if cn is not None else centers_txt
    out = f"<span class='it'>{mark(total, win == '가게')}</span> <span class='it'>↔ {mark(right, win != '가게')}</span>"
    return out + (f"<span class='sm'>{_items(detail)}</span>" if detail else "")


def person_row(r: pd.Series, sig: str) -> str:
    color = SIGNAL[sig][1]
    where = "경로당·마을회관 먼저" if r["창구"].startswith("경로당") else "가게 먼저"
    place = (f"본인 등록 · {_short_places(r['등록장소'], r['행정동'])}" if r.get("등록장소") else
             f"후보 · {_short_places(r['후보장소'], r['행정동'])}" if r.get("후보장소") else "")
    return (f"<div class='row'><div class='av' style='background:{ui.tint(color, .14)};color:{color}'>{ui.esc(r['대상자ID'])}</div>"
            f"<div class='who'><b>{ui.esc(r['집단'])}</b><span>{ui.esc(r['행정동'])} · {ui.esc(r['명부종류'])}</span></div>"
            f"<div class='who'><span class='bg-chip' style='margin:0 0 3px;display:inline-block'>{where}</span>"
            f"<span>{ui.esc(place)}</span></div>"
            f"<div class='days'>{int(r['경과일'])}<small>일</small></div></div>")


def people_section(as_of: pd.Timestamp, g: pd.DataFrame, p: pd.DataFrame):
    """끊긴 칸 × 가상 명부 → 이번 주 먼저 확인할 사람 (기획안 4절 0단계). 칸은 시군구 × 성 × 연령대이고,
    동은 대상자 주소에서만 붙인다. 이름·연락처는 화면에 없다(E6 4절). 가장 오래 끊긴 다섯만 줄로, 나머지는 접힌 표로."""
    if load_people() is None:
        return
    if p.empty:
        html("<div class='bg-callout'>이번 주에는 확인할 사람이 없습니다. 좁아짐(노랑)은 사람이 아니라 동 단위 자원으로 나갑니다.</div>")
        return
    sig_of = g.set_index("집단")["신호"]
    top = p.sort_values(["경과일", "집단"], ascending=[False, True]).head(5)
    rows = "".join(person_row(r, sig_of[r["집단"]]) for _, r in top.iterrows())
    # 열 제목은 줄과 같은 격자에 둔다 — 머리 오른쪽에 몰아 두면 「먼저 물을 곳」이 날짜 열 위에 떠 보인다
    head = ("<div class='row colh'><span></span><span>대상자 · 주소 동</span><span>먼저 물을 곳</span>"
            "<span style='text-align:right'>접촉 뒤</span></div>")
    html(f"<div class='bg-board'><div class='hd'><div><div class='bg-sec' style='margin:0'>먼저 확인할 사람 {len(p)}명</div>"
         f"<div class='sub'>마지막 접촉이 오래된 순 · <b>가상 명부</b>(41명, 실제 인물이 아닙니다)</div></div>"
         f"</div><div class='bg-plist'>{head}{rows}</div></div>")
    with st.expander(f"{len(p)}명 전체 — 집단 · 주소 동 · 창구 · 물어볼 장소"):
        people_table(p, g)


def people_table(p: pd.DataFrame, g: pd.DataFrame):
    n_cell = g.set_index("집단")["명부_칸인원"] if "명부_칸인원" in g else pd.Series(dtype=float)
    order = g.set_index("집단")["신호"].map(SIGNAL_ORDER)
    p = p.assign(_o=p["집단"].map(order)).sort_values(["_o", "집단", "경과일"], ascending=[True, True, False])
    has_place = "후보장소" in p
    rows = []
    for _, r in p.iterrows():
        city = r["집단"].split()[0]
        label, color = SIGNAL[g.set_index("집단").loc[r["집단"], "신호"]]
        n = n_cell.get(r["집단"])
        rows.append({
            # 칸을 여섯으로 — 신호는 대상자 ID 색으로, 창구 판단 근거는 창구 아래 둘째 줄로
            "대상자": (f"<span class='bg-badge' style='background:{ui.tint(color, .14)};color:{color};font-weight:800'>"
                    f"{ui.esc(r['대상자ID'])}</span><span class='sm'>{ui.esc(r['명부종류'])}</span>"),
            "집단 · 주소 동": ui.esc(r["집단"]) + (f" <span style='color:{ui.MUTE};font-size:12px'>칸 {int(n)}명 중</span>"
                                             if pd.notna(n) else "")
                         + (f"<span class='sm'><span class='it'>{ui.esc(r['행정동'])}</span> · "
                            f"<span class='it'>터전 {int(r['터전순위'])}/{N_DONG.get(city, '')}(약한 순)</span></span>"),
            "마지막 접촉": f"{int(r['경과일'])}일 전",
            "먼저 물을 창구": f"<b>{ui.esc(r['창구'])}</b><span class='sm'>{_window_cell(r['물어볼곳'])}</span>",
            "물어볼 장소 (가상 가게)": _place(r) if has_place else "",
        })
    cols = [("대상자", ""), ("집단 · 주소 동", ""), ("마지막 접촉", "n nw"), ("먼저 물을 창구", "w-win")]
    html(ui.table(cols + ([("물어볼 장소 (가상 가게)", "m")] if has_place else []), rows))


def resource_lines(g: pd.DataFrame):
    """이 주에 가져갈 것 — agent.py match_resource(#44)가 상태별로 고른 자원 후보 3개. 집단 단위라 같은 도시·같은
    신호면 같은 후보가 나오므로 묶어 한 장씩 보인다. 사람에게 맞춘 추천이 아니다."""
    if "자원후보" not in g or not (g["자원후보"] != "").any():
        return
    kind = {"빨강": "방문 때 가져갈 복지서비스", "주황": "만남이 생기는 봉사·프로그램", "노랑": "동 단위로 나갈 봉사 일감"}
    x = g[g["자원후보"] != ""].assign(_o=lambda d: d["신호"].map(SIGNAL_ORDER)).sort_values(["_o", "도시"])
    html("<div class='bg-sec' style='margin-top:4px'>이 주에 가져갈 것</div>")
    for (sig, city, res), d in x.groupby(["신호", "도시", "자원후보"], sort=False):
        # 이름을 자르지 않는다 — 잘린 이름은 담당자가 복사해 찾을 수 없다. 긴 이름은 칩 안에서 줄을 바꾼다
        chips = "".join(f"<span class='bg-chip'>{ui.esc(s.strip())}</span>"
                        for s in res.split(" · "))
        html(f"<div class='bg-res'><div class='h'>{ui.badge(SHORT[sig], SIGNAL[sig][1])} <b>{ui.esc(city)}</b> "
                     f"<span>{kind.get(sig, '')}</span></div>{chips}</div>")


def trend(df: pd.DataFrame, fields: dict[str, str], title: str, sub: str, wk: pd.Timestamp, height: int = 200) -> alt.Chart:
    long = df.melt(id_vars=["week"], value_vars=list(fields), var_name="k", value_name="값")
    long["지표"] = long["k"].map(fields)
    names = list(fields.values())
    enc_color = alt.Color("지표:N", scale=alt.Scale(domain=names, range=SERIES[: len(names)]),
                          legend=alt.Legend(orient="bottom", title=None, direction="horizontal")
                          if len(names) > 1 else None)
    x = alt.X("week:T", title=None, axis=alt.Axis(format="%m/%d", tickCount=6, grid=False))
    ln = alt.Chart(long).mark_line(strokeWidth=2).encode(
        x=x, y=alt.Y("값:Q", title=None, axis=alt.Axis(tickCount=4)), color=enc_color,
        tooltip=[alt.Tooltip("week:T", title="주", format="%m/%d"), "지표:N", alt.Tooltip("값:Q", format="+.2f")])
    pt = alt.Chart(long[long["week"] == wk]).mark_point(size=80, filled=True, stroke=ui.CANVAS, strokeWidth=2,
                                                        opacity=1).encode(x="week:T", y="값:Q", color=enc_color)
    rule = alt.Chart(pd.DataFrame({"week": [wk]})).mark_rule(color=ui.MUTE, strokeDash=[3, 3]).encode(x="week:T")
    zero = alt.Chart(pd.DataFrame({"y": [0]})).mark_rule(color="#c9d3df").encode(y="y:Q")
    return (zero + rule + ln + pt).properties(title=alt.Title(title, subtitle=sub), height=height)


def screen_detail():
    html(ui.topbar("발길 상세", "왜 이 집단인가 — 양 · 질 · 연속성 · 터전 네 면과 모델의 근거"))
    p, s, m = load_weekly(), load_shap(), load_map()
    segs = sorted(s["seg"].unique())
    c1, c2 = st.columns([1, 2])
    # 기본값은 시연 장면(08절 8.1): 춘천 여성 70대, DEMO_AS_OF가 끝나는 주
    seg = c1.selectbox("집단 (시군구 × 성 × 연령)", segs, index=segs.index(DEMO_SEG) if DEMO_SEG in segs else 0)
    weeks = sorted(int(x) for x in s["w"].unique())
    demo_w = (pd.Timestamp(DEMO_AS_OF) - pd.Timedelta(days=6) - WEEK0).days // 7
    w = week_picker(c2, "주 (월~일)", weeks, demo_w if demo_w in weeks else weeks[-1],
                    lambda i: week_label(WEEK0 + pd.Timedelta(days=7 * int(i))), "wk_detail")
    wk = WEEK0 + pd.Timedelta(days=7 * int(w))
    g = p[p["seg"] == seg].sort_values("w")
    row = s[(s["seg"] == seg) & (s["w"] == w)].iloc[0]
    val = lambda f: float(g.loc[g["w"] == w, f].iloc[0])  # noqa: E731

    sv = pd.DataFrame({"변수": [FEATURE_KO[f] for f in FEATURE_KO], "기여": [row[f] for f in FEATURE_KO]})
    sv["방향"] = np.where(sv["기여"] >= 0, "확률을 높임", "확률을 낮춤")
    sv = sv.reindex(sv["기여"].abs().sort_values(ascending=False).index).head(6)
    html(detail_answer(seg, wk, row, val, sv))
    html(ui.kpis([
        ui.kpi("다음 주 좁아짐 상위 진입", f"{row['확률'] * 100:.0f}", ui.PRIMARY, "percent", "좁아짐 분류 모델", unit="%"),
        ui.kpi("양 · 발길 수", f"{val('breadth_z'):+.2f}", SERIES[0], "users", f"z · {side(val('breadth_z'))}"),
        ui.kpi("질 · 체류 비중", f"{val('stay_z'):+.2f}", "#1baf7a", "home", f"z · {side(val('stay_z'))}"),
        ui.kpi("연속성 · 3주 평균", f"{val('m3'):+.2f}", SERIES[1], "pulse", f"이번 주 {val('narrow'):+.2f} · 높을수록 좁아짐")]))
    a, b = st.columns(2)
    with a, card("qty"):
        st.altair_chart(trend(g, {"breadth_z": "발길 수"}, "양 — 몇 곳에 닿는가", "유효 발길 수, 나이 보정 z", wk),
                        width="stretch")
    with b, card("qual"):
        st.altair_chart(trend(g, {"stay_z": "체류 비중"}, "질 — 얼굴을 아는 곳인가", "체류 업종 비중, 나이 보정 z", wk),
                        width="stretch")
    a, b = st.columns(2)
    with a, card("cont"):
        st.altair_chart(trend(g, {"narrow": "이번 주", "m3": "3주 평균"}, "연속성 — 늘 가던 대로 가는가",
                              "좁아짐 점수 (높을수록 좁아짐)", wk, height=290), width="stretch")  # 옆 터전 카드와 높이를 맞춘다
    city = seg.split()[0]
    weak = m[m["도시"] == city].sort_values("터전순위_통신").head(5)
    with b, card("ground"):
        html(f"<div class='bg-sec'>터전 — 닿을 곳이 있는가 <span style='color:{ui.MUTE};font-weight:400'>"
             f"· {city}, 동 단위</span></div>")
        html(ui.table([("동", ""), ("터전 순위", "n"), ("체류형 점포 /천명", "n"), ("경로당·마을회관", "n")],
                      [{"동": ui.esc(r.ADM_NM), "터전 순위": f"{r.터전순위_통신}",
                        "체류형 점포 /천명": f"{r.체류형점포_천명당:.1f}", "경로당·마을회관": f"{int(r.경로당수)}"}
                       for r in weak.itertuples()]))
        html(f"<div style='font-size:12px;color:{ui.MUTE};margin-top:8px'>터전이 약한 순 5개 동 · 이 표만 동 단위입니다</div>")

    span = float(sv["기여"].abs().max()) * 1.35
    lo, hi = (-span if (sv["기여"] < 0).any() else -span * 0.15), (span if (sv["기여"] > 0).any() else span * 0.15)
    bars = alt.Chart(sv).mark_bar(height=16, cornerRadiusEnd=4).encode(
        x=alt.X("기여:Q", title=None, axis=alt.Axis(format="+.2f", tickCount=5), scale=alt.Scale(domain=[lo, hi])),
        y=alt.Y("변수:N", sort=None, title=None,
                axis=alt.Axis(labelColor=ui.INK_2, labelFontSize=12, labelOverlap=False, labelLimit=160)),
        color=alt.Color("방향:N", scale=alt.Scale(domain=["확률을 높임", "확률을 낮춤"], range=[POS, NEG]),
                        legend=alt.Legend(orient="bottom", title=None, direction="horizontal")),
        tooltip=["변수:N", alt.Tooltip("기여:Q", format="+.3f")])
    lab = lambda df, align, dx: alt.Chart(df).mark_text(align=align, dx=dx, color=ui.INK_2, fontSize=11).encode(  # noqa: E731
        x="기여:Q", y=alt.Y("변수:N", sort=list(sv["변수"])), text=alt.Text("기여:Q", format="+.3f"))
    labels = lab(sv[sv["기여"] >= 0], "left", 6) + lab(sv[sv["기여"] < 0], "right", -6)
    zero = alt.Chart(pd.DataFrame({"x": [0]})).mark_rule(color="#c9d3df").encode(x="x:Q")
    st.write("")
    # 터전 카드와 SHAP을 한 덩어리로 읽지 않게 단을 나눈다(#14 윤지 — 모델 입력에 터전이 없다)
    html(f"<div class='bg-sec' style='margin-top:8px'>모델 근거 <span style='color:{ui.MUTE};font-weight:400'>"
         f"· 집단(시군구 × 성 × 연령) 단위 — 위 터전 표와 따로 읽습니다</span></div>")
    with card("shap"):
        st.altair_chart((zero + bars + labels).properties(
            title=alt.Title("무엇이 확률을 움직였나", subtitle="집단 단위 기여도(SHAP) 상위 6개 — 오른쪽(빨강)은 확률을 높이고 왼쪽(파랑)은 낮춥니다"),
            height=240), width="stretch")


def side(z: float) -> str:
    return "기준보다 낮음" if z < 0 else "기준보다 높음" if z > 0 else "기준과 같음"


def detail_answer(seg: str, wk: pd.Timestamp, row: pd.Series, val, sv: pd.DataFrame) -> str:
    """화면 ② 답 — 확률 한 줄 + 그 확률을 가장 크게 움직인 둘. 수치는 전부 슬롯(E6 5.2)."""
    top = sv.head(2)
    # 항목 하나(「이번 주 좁아짐 +0.096 (높임)」)는 줄을 바꾸지 않는다 — 「(높 / 임)」처럼 끊기지 않게
    why = " · ".join(f"<span style='white-space:nowrap'>{ui.esc(r.변수)} <b>{r.기여:+.3f}</b> "
                     f"({'높임' if r.기여 >= 0 else '낮춤'})</span>" for r in top.itertuples())
    return ui.answer(
        f"{seg} · {wk:%m/%d} 주",
        f"다음 주 좁아짐 상위 7칸에 들어갈 확률 <b>{row['확률'] * 100:.0f}%</b>. "
        f"이번 주 좁아짐 점수 <b>{val('narrow'):+.2f}</b>, 3주 평균 <b>{val('m3'):+.2f}</b>입니다.",
        f"체류 비중 {val('stay_z'):+.2f} · 발길 수 {val('breadth_z'):+.2f} (같은 성·나이 기준 z)<br>"
        f"확률을 가장 크게 움직인 것: {why}")


# ── ③ 지도 ─────────────────────────────────────────────────────────────
QUAD_MODE = "대응 (공급 × 필요)"
METRICS = {
    QUAD_MODE: (None, "공급(통신 터전) 부족 × 필요(고령 1인세대) 큼 — C5 동 우선순위"),
    "터전 점수 (통신)": ("터전점수_통신", "높을수록 터전이 강함"),
    "체류형 점포 (60세+ 천 명당)": ("체류형점포_천명당", "상가정보 · 커피·미용·목욕·운동·노래방·주점"),
    "경로당·마을회관 (60세+ 천 명당)": ("경로당_천명당", "표준데이터 · 공공이 노인 거주지에 배치"),
}
METRIC_FMT = {"터전점수_통신": "{:.2f}", "체류형점포_천명당": "{:.1f}", "경로당_천명당": "{:.1f}"}
# 대응 넷 (build_priority.py ACTION). 지도는 모든 쌍이 맞닿으므로 범주 1~3번만 쓴다(--pairs all 통과, 3번 청록은
# 대비 2.8:1이라 표·툴팁·글자 라벨로 함께 말한다). 「유지」는 할 일이 없는 칸이라 색 대신 회색으로 물린다
QUAD = {
    "1순위": ("#2a78d6", "1순위 · 거점 배치", "공급 부족 · 필요 큼"),
    "형평": ("#eb6834", "형평 · 찾아가기", "공급 부족 · 사람 적음"),
    "연결": ("#1baf7a", "연결 · 있는 곳에 붙이기", "공급 있음 · 필요 큼"),
    "유지": ("#cfd6df", "유지", "공급 있음 · 사람 적음"),
}
# 대응 색과 겹치지 않게 시설은 색 없이 먹색으로: 많은 경로당은 속 빈 점(지도를 덮지 않게), 적은 도서관은 채운 점
FAC_INK = {"경로당": ("#ffffff", ui.INK), "도서관": (ui.INK, "#ffffff")}


@st.cache_data
def load_priority() -> pd.DataFrame:
    p = pd.read_csv(ROOT / "data" / "reference" / "dong_priority.csv", dtype={"ADM_CD": str})
    p["사분면"] = p["대응"].str.split(" — ").str[0]
    return p


@st.cache_data
def load_reach() -> pd.DataFrame:
    return pd.read_csv(ROOT / "data" / "reference" / "reach_efficiency.csv")


def quadrant_chart(p: pd.DataFrame) -> alt.Chart:
    """공급(터전 순위, 왼쪽이 약함) × 필요(고령 1인세대). 칸 이름을 모서리에 글자로 적어 색만으로 말하지 않는다."""
    n, med = len(p), float(p["고령1인세대수"].median())
    cut = n // 2 + 0.5  # build_priority.py: 공급부족 = 터전순위 <= n // 2
    ymax = float(p["고령1인세대수"].max()) * 1.12
    d = p.assign(이름=p["사분면"].map(lambda k: QUAD[k][1]))
    x = alt.X("터전순위_통신:Q", title="터전 순위 (왼쪽일수록 공급 부족)", scale=alt.Scale(domain=[0, n + 1], nice=False),
              axis=alt.Axis(tickCount=5, grid=False))
    y = alt.Y("고령1인세대수:Q", title="고령 1인세대 (명)", scale=alt.Scale(domain=[0, ymax], nice=False),
              axis=alt.Axis(tickCount=4, format=",.0f"))
    dots = alt.Chart(d).mark_circle(size=90, opacity=1, stroke=ui.CANVAS, strokeWidth=1.5).encode(
        x=x, y=y,
        color=alt.Color("사분면:N", scale=alt.Scale(domain=list(QUAD), range=[v[0] for v in QUAD.values()]), legend=None),
        tooltip=[alt.Tooltip("ADM_NM:N", title="동"), alt.Tooltip("이름:N", title="대응"),
                 alt.Tooltip("우선순위:Q", title="우선순위"), alt.Tooltip("터전순위_통신:Q", title="터전 순위"),
                 alt.Tooltip("고령1인세대수:Q", title="고령 1인세대", format=",")])
    top = d[d["사분면"] == "1순위"].nsmallest(3, "우선순위")
    names = alt.Chart(top).mark_text(align="left", dx=7, dy=-6, fontSize=11, color=ui.INK_2).encode(
        x="터전순위_통신:Q", y="고령1인세대수:Q", text="ADM_NM:N")
    rules = (alt.Chart(pd.DataFrame({"x": [cut]})).mark_rule(color="#c9d3df", strokeDash=[3, 3]).encode(x="x:Q")
             + alt.Chart(pd.DataFrame({"y": [med]})).mark_rule(color="#c9d3df", strokeDash=[3, 3]).encode(y="y:Q"))
    corner = pd.DataFrame({"x": [0.4, n + 0.6, 0.4, n + 0.6], "y": [ymax, ymax, 0, 0],
                           "t": ["1순위", "연결", "형평", "유지"],
                           "a": ["left", "right", "left", "right"], "b": ["top", "top", "bottom", "bottom"]})
    corners = alt.layer(*[
        alt.Chart(corner[(corner["a"] == a) & (corner["b"] == b)]).mark_text(
            align=a, baseline=b, dy=4 if b == "top" else -4, fontSize=11, fontWeight=600, color=ui.MUTE)
        .encode(x="x:Q", y="y:Q", text="t:N")
        for a in ("left", "right") for b in ("top", "bottom")])
    return (rules + dots + names + corners).properties(height=260)


def screen_map():
    html(ui.topbar("터전 지도", "어느 동에 닿을 곳이 없나 — 47개 행정동 공급 지표와 시설, 자원을 어디에 먼저 둘까"))
    m, fac, pri = load_map(), load_facilities(), load_priority()
    c1, c2, c3 = st.columns([1, 2, 2])
    city = c1.radio("도시", ["춘천", "강남"], horizontal=True)
    label = c2.selectbox("색으로 볼 지표", list(METRICS))
    show = c3.multiselect("점으로 겹칠 시설", ["경로당", "도서관"], default=["경로당", "도서관"])
    col, hint = METRICS[label]
    quad = label == QUAD_MODE
    g = m[m["도시"] == city].merge(pri[["ADM_CD", "우선순위", "사분면", "고령1인세대수"]], on="ADM_CD", how="left")
    sgg = "강원 춘천시" if city == "춘천" else "서울 강남구"

    if quad:
        g["_c"] = g["사분면"].map(lambda k: QUAD[k][0])
        g["_q"] = g["사분면"].map(lambda k: QUAD[k][1])
    else:
        q = pd.qcut(g[col], 5, labels=False, duplicates="drop")
        g["_c"] = [BLUE_RAMP[int(i)] for i in q]
    center = g.geometry.union_all().centroid
    fmap = folium.Map(location=[center.y, center.x], zoom_start=10 if city == "춘천" else 13,
                      tiles=None, control_scale=True)
    folium.TileLayer("Esri.WorldGrayCanvas", name="배경 지도", control=False).add_to(fmap)
    fields = ["ADM_NM", "터전순위_통신", "체류형점포_천명당", "경로당수", "도서관수", "인구_60세이상"]
    aliases = ["동", "터전 순위(약한 순)", "체류형 점포 /60세+천명", "경로당·마을회관", "도서관", "60세+ 인구"]
    if quad:
        fields = fields[:1] + ["_q", "우선순위", "고령1인세대수"] + fields[1:]
        aliases = aliases[:1] + ["대응", "우선순위", "고령 1인세대"] + aliases[1:]
    tip = folium.GeoJsonTooltip(fields=fields, aliases=aliases,
                                style=f"font-family:{ui.FONT};font-size:12px;color:{ui.INK};")
    folium.GeoJson(
        g.__geo_interface__,
        style_function=lambda f: {"fillColor": f["properties"]["_c"], "color": "#ffffff", "weight": 1.5,
                                  "fillOpacity": 0.88},
        highlight_function=lambda f: {"weight": 3, "color": ui.INK},
        tooltip=tip, name=label).add_to(fmap)
    for kind in show:
        layer = folium.FeatureGroup(name=kind)
        fill, line = FAC_INK[kind] if quad else (FAC_COLOR[kind], "#ffffff")
        for r in fac[(fac["SGG_NM"] == sgg) & (fac["시설종류"] == kind)].itertuples():
            folium.CircleMarker([r.위도, r.경도], radius=3 if quad else 4, color=line, weight=1.2 if quad else 1.5,
                                fill=True,
                                fill_color=fill, fill_opacity=1,
                                tooltip=f"{kind} · {r.시설명} ({r.ADM_NM})").add_to(layer)
        layer.add_to(fmap)

    html(map_answer(g, city, col, label, quad))
    left, right = st.columns([3, 2])
    with left, card("map"):
        html(f"<div class='bg-sec'>{ui.esc(city)} · {ui.esc(label)} <span style='color:{ui.MUTE};font-weight:400'>"
             f"· {ui.esc(hint)}</span></div>")
        components.html(fmap.get_root().render(), height=500)
        if quad:
            fill = ui.legend([(v[1], v[0]) for v in QUAD.values()])
        else:
            lo, hi = g[col].min(), g[col].max()
            fill = (f"<div class='bg-legend' style='gap:4px'><span>{METRIC_FMT[col].format(lo)}&nbsp;</span>"
                    + "".join(f"<span><i style='background:{c};margin:0'></i></span>" for c in BLUE_RAMP)
                    + f"<span>&nbsp;{METRIC_FMT[col].format(hi)} · 5분위, 진할수록 큼</span></div>")

        def dot(k: str) -> str:
            f, b = (FAC_INK[k][0], ui.INK) if quad else (FAC_COLOR[k], FAC_COLOR[k])
            return f"<i style='background:{f};border:1.5px solid {b};width:9px;height:9px;border-radius:50%'></i>"
        facs = "".join(f"<span>{dot(k)}{ui.esc(k)}</span>" for k in show)
        html(fill + (f"<div class='bg-legend' style='margin-top:4px'>{facs}</div>" if show else ""))
    with right:
        if quad:
            map_quadrant_side(g, city)
        else:
            map_metric_side(g, city, col, label)


def map_answer(g: gpd.GeoDataFrame, city: str, col: str | None, label: str, quad: bool) -> str:
    """화면 ③ 답 — 대응 모드면 「어디에 먼저」, 지표 모드면 「어디가 가장 낮은가」."""
    if not quad:
        low = g.sort_values(col).head(3)
        names = " · ".join(ui.esc(x) for x in low["ADM_NM"])
        vals = " · ".join(METRIC_FMT[col].format(v) for v in low[col])
        return ui.answer(f"{city} · {label}", f"<b>{names}</b>이 {ui.esc(label)} 가장 낮은 세 동입니다.",
                         f"값 {vals} — 한 지표만으로 순서를 정하지 않습니다. 순서는 「{QUAD_MODE}」에서 봅니다")
    p = g.sort_values("우선순위")
    short = p["사분면"].isin(["1순위", "형평"])
    first = p[short].head(3)
    r = load_reach()
    r = r[(r["도시"] == city) & r["규칙"].str.startswith("우선순위")].set_index("k")["도달 효율"]
    share = p.loc[short, "고령1인세대수"].sum() / p["고령1인세대수"].sum() * 100
    n_eq = int((p["사분면"] == "형평").sum())
    names = " · ".join(ui.esc(x) for x in first["ADM_NM"])
    return ui.answer(
        f"{city} · 자원을 어디에 먼저",
        f"<b>{names}</b>에 먼저 두세요 — 고령 1인세대가 <b>{r[3]:.2f}배</b> 많이 삽니다",
        # 배수는 도달 효율(06_터전 6.5) — 공급 부족 동에서 3곳을 무작위로 고를 때의 기댓값과 견준다
        f"공급 부족 동 가운데 3곳을 무작위로 고를 때와 견준 값입니다 · "
        f"공급 부족 {int(short.sum())}개 동에 {city} 고령 1인세대의 {share:.1f}%가 삽니다<br>"
        f"형평 칸 {n_eq}곳은 사는 사람은 적지만 달리 닿을 곳이 없어, 찾아가는 서비스로 챙깁니다")


def map_metric_side(g: gpd.GeoDataFrame, city: str, col: str, label: str):
    html(ui.kpis([ui.kpi("경로당·마을회관", f"{int(g['경로당수'].sum())}", FAC_COLOR["경로당"], "home", f"{city} {len(g)}개 동"),
                  ui.kpi("도서관", f"{int(g['도서관수'].sum())}", FAC_COLOR["도서관"], "grid", "공공·작은·어린이")]))
    st.write("")
    html(f"<div class='bg-sec'>{ui.esc(label)} 낮은 동 5곳</div>")
    t = g.sort_values(col).head(5)
    html(ui.table([("동", ""), ("값", "n"), ("터전 순위", "n"), ("경로당·마을회관", "n"), ("60세+ 인구", "n")],
                  [{"동": ui.esc(r.ADM_NM), "값": METRIC_FMT[col].format(getattr(r, col)),
                    "터전 순위": f"{r.터전순위_통신}", "경로당·마을회관": f"{int(r.경로당수)}",
                    "60세+ 인구": f"{int(r.인구_60세이상):,}"} for r in t.itertuples()]))
    st.write("")
    html("<div class='bg-callout'>체류형 점포와 경로당·마을회관은 <b>방향이 반대</b>입니다(춘천 스피어만 −0.79, 상가 × 시설). "
         "면 지역은 가게가 적은 대신 60세 이상 천 명당 경로당이 많아, 한 지수로 더하지 않고 따로 봅니다.</div>")


def map_quadrant_side(g: gpd.GeoDataFrame, city: str):
    p = g.sort_values("우선순위")
    r = load_reach()
    r = r[(r["도시"] == city) & r["규칙"].str.startswith("우선순위")].set_index("k")["도달 효율"]
    short = p["사분면"].isin(["1순위", "형평"])
    share = p.loc[short, "고령1인세대수"].sum() / p["고령1인세대수"].sum() * 100
    html(ui.kpis([ui.kpi("도달 효율 · 우선순위 3곳", f"{r[3]:.2f}", ui.PRIMARY, "trend", f"5곳이면 {r[5]:.2f}배", unit="배"),
                  ui.kpi("부족 동의 고령 1인세대", f"{share:.1f}", "#1baf7a", "users", f"{city} 부족 {int(short.sum())}개 동",
                         unit="%")]))
    st.write("")
    with card("quad"):
        html(f"<div class='bg-sec'>공급 × 필요 <span style='color:{ui.MUTE};font-weight:400'>· {city} {len(p)}개 동, "
             f"점선은 터전 하위 절반 · 1인세대 중앙값</span></div>")
        st.altair_chart(quadrant_chart(p), width="stretch")  # 범례는 지도 아래와 같다 — 칸 이름은 모서리 글자로
    st.write("")
    html("<div class='bg-sec'>먼저 둘 동 — 공급 부족 동</div>")
    html(ui.table([("순위", "n"), ("동", ""), ("대응", ""), ("고령 1인세대", "n")],
                  [{"순위": f"{int(x.우선순위)}", "동": f"<span style='white-space:nowrap'>{ui.esc(x.ADM_NM)}</span>",
                    "대응": ui.badge(QUAD[x.사분면][1], QUAD[x.사분면][0]),
                    "고령 1인세대": f"{int(x.고령1인세대수):,}"}
                   for x in p[short].head(6).itertuples()]))


# ── ④ 보정 전·후 ───────────────────────────────────────────────────────
# 라디오 글자 맨 앞의 "+"는 마크다운 목록으로 읽혀 사라진다 → "계절 + 공통 충격"으로 단계가 누적임을 적는다
STEPS = {"보정 없음": "(0) 보정 없음", "계절형 보정": "(1) 계절형 보정", "계절 + 공통 충격 보정": "(2) + 공통 충격 보정"}
STEP_COL = {"보정 없음": "al0", "계절형 보정": "al1", "계절 + 공통 충격 보정": "al2"}


def cut_rate(v: float) -> str:
    """공통 사건 주간 감소율. 기준(보정 없음)은 비교 대상이 없어 —, 음수는 오히려 늘어난 것이다(수치표 3절)."""
    return f"{v:.0f}%" if v >= 0 else f"−{-v:.0f}% (늘어남)"


def screen_correction():
    html(ui.topbar("보정 전·후", "헛알림을 얼마나 지웠나 — 명절·공휴일처럼 모두가 함께 줄어드는 날을 먼저 지운다"))
    c1, c2 = st.columns([3, 2])
    step = c1.radio("보정 단계", list(STEPS), index=0, horizontal=True)
    nomed = c2.toggle("병원·약국을 필수 발길에서 분리", value=False)
    b, fa = load_breaks(nomed), load_false_alarm(nomed)

    n0, n1, n2 = (int(fa.iloc[i, 0]) for i in range(3))
    h0, h2 = int(fa.iloc[0, 1]), int(fa.iloc[2, 1])
    keys = list(STEPS)
    html(ui.answer(
        "헛알림을 얼마나 지웠나" + (" · 병원·약국 분리" if nomed else ""),
        f"알림 <b>{n0} → {n2}</b>. 공통 사건 주간(추석·광복절·성탄 뒤 7일) 알림은 <b>{h0} → {h2}</b>로 "
        f"<b>{cut_rate(fa.iloc[2, 3])}</b> 줄었습니다.",
        ("계절만 보정하면 오히려 늘고" if n1 > n0 else "계절 보정만으로는 거의 줄지 않고")
        + ", 같은 도시 30·40대가 함께 줄어든 만큼을 빼야 줄어듭니다 — 위 「보정 단계」로 한 단계씩 볼 수 있습니다",
        [(f"{k} · 알림 {int(fa.iloc[i, 0])}",
          f"공통 사건 주간 {int(fa.iloc[i, 1])} · 그 밖의 날 {int(fa.iloc[i, 2])}"
          + ("" if i == 0 else f" · 감소율 {cut_rate(fa.iloc[i, 3])}") + f"<br>{how}", step == k)
         for i, (k, how) in enumerate(zip(keys, ["평소 흔들림과 견준 그대로",
                                                 "앞뒤 4주 같은 요일과 견줌",
                                                 "같은 도시 30·40대의 같은 종류 발길 변화를 뺌"]))]))
    st.write("")

    d = b[["date", "seg", "holwk", STEP_COL[step]]].rename(columns={STEP_COL[step]: "alert"})
    spans = (b[b["holwk"]].drop_duplicates("date")[["date"]]
             .assign(g=lambda x: (x["date"].diff().dt.days != 1).cumsum())
             .groupby("g")["date"].agg(["min", "max"]).reset_index(drop=True))
    spans["max"] = spans["max"] + pd.Timedelta(days=1)
    domain = [b["date"].min().isoformat(), (b["date"].max() + pd.Timedelta(days=1)).isoformat()]
    order = sorted(d["seg"].unique())
    shade = alt.Chart(spans).mark_rect(color=SHADE).encode(x=alt.X("min:T", scale=alt.Scale(domain=domain)), x2="max:T")
    rows = alt.Chart(d).mark_tick(opacity=0).encode(y=alt.Y("seg:N", sort=order, title=None,
                                                            axis=alt.Axis(labelColor=ui.INK_2, labelFontSize=12)))
    cells = alt.Chart(d[d["alert"]]).mark_rect(color=CRITICAL, cornerRadius=2).encode(
        x=alt.X("date:T", title=None, axis=alt.Axis(format="%m/%d", tickCount=12, grid=False),
                scale=alt.Scale(domain=domain)),
        x2=alt.X2("end:T"), y=alt.Y("seg:N", sort=order),
        tooltip=[alt.Tooltip("date:T", title="날짜", format="%Y-%m-%d"), alt.Tooltip("seg:N", title="집단")],
    ).transform_calculate(end="datetime(year(datum.date), month(datum.date), date(datum.date) + 1)")
    with card("heat"):
        st.altair_chart((shade + rows + cells).properties(
            title=alt.Title("집단 × 날짜 알림", subtitle=f"{step}{' · 병원·약국 분리' if nomed else ''} — 빨간 칸이 끊김 판정"),
            height=330), width="stretch")
        html(ui.legend([("알림 (끊김 판정)", CRITICAL), ("공통 사건 주간 (추석·광복절·성탄 뒤 7일)", SHADE)]))


# ── 화면 ───────────────────────────────────────────────────────────────
SCREENS = [("주간 브리핑", "home", screen_briefing), ("발길 상세", "pulse", screen_detail),
           ("터전 지도", "map", screen_map), ("보정 전·후", "sliders", screen_correction)]
q = st.query_params.get("screen", "1")  # ?screen=1~4 — 왼쪽 메뉴도 이 주소로 간다(캡처·데모와 같은 길)
n = int(q) if q in {"1", "2", "3", "4"} else 1
st.html(ui.DECK_CSS)  # 화면 색은 발표자료와 같게(10/26 팀 확정) — 기본 틀(style.CSS) 위에 색만 덮는다
with st.sidebar:
    html(ui.sidebar(n, [(t, ic) for t, ic, _ in SCREENS]))
SCREENS[n - 1][2]()
