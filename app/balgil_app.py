"""발길 — 담당자 화면 4개 (D3, 시연용).

실행: streamlit run app/balgil_app.py
의존: app/requirements-app.txt (분석 쪽 requirements.txt에 화면 라이브러리를 더한 것)

읽는 파일은 모두 git에 있다 — 원본 데이터가 없어도 뜬다.
  reanalysis/reference/   재분석 결과 (끊김·보정·주간 패널)
  data/reference/app/     scripts/build_app_data.py가 만든 지도·시설·SHAP

원칙
  * 집단 지표(양·질·연속성)는 시군구 × 성 × 연령까지만. 동 단위로 보여 주는 것은 터전뿐이다.
  * 신호등 5단계와 끊김 종류(대면형·장보기형·병원약국형)는 D1 agent.py가 나오면 바꾼다.
    지금은 재분석 b2의 주황(대면만 끊김)·빨강(필수까지 끊김)을 그대로 보인다.
  * 숫자는 10/17 수치 동결 뒤 docs/최종수치표.md 값으로 교체한다.

색 (dataviz 기준 팔레트, 검증: validate_palette.js)
  상태(주황·빨강)   status serious/critical — 색만으로 말하지 않고 항상 아이콘·글자를 같이 단다
  터전 지도         순차 파랑 한 가지 (진할수록 값이 큼)
  지도 위 시설 점   주황(경로당)·청록(도서관) — 범주 2·3번, 전 쌍 CVD ΔE 9.2 통과
  SHAP 막대         발산 파랑(확률을 낮춤)·빨강(높임)
"""
from __future__ import annotations

from pathlib import Path

import altair as alt
import folium
import geopandas as gpd
import numpy as np
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

ROOT = Path(__file__).resolve().parents[1]
REF = ROOT / "reanalysis" / "reference"
APP = ROOT / "data" / "reference" / "app"

# ── 색 (dataviz reference palette, light) ─────────────────────────────
INK, INK_2, MUTED, GRID = "#0b0b0b", "#52514e", "#898781", "#e1e0d9"
SURFACE, NEUTRAL = "#fcfcfb", "#f0efec"
SERIOUS, CRITICAL = "#ec835a", "#d03b3b"
BLUE_RAMP = ["#cde2fb", "#86b6ef", "#3987e5", "#256abf", "#104281"]  # 순차 100·250·400·500·650
POS, NEG = "#e34948", "#2a78d6"  # 발산: 확률을 높임 / 낮춤
SERIES = ["#2a78d6", "#eb6834"]  # 범주 1·2번 (선 두 개)
FAC_COLOR = {"경로당": "#eb6834", "도서관": "#1baf7a"}

STATE = {
    "빨강(필수까지 끊김)": ("🔴", "빨강", "필수까지 끊김", CRITICAL),
    "주황(대면만 끊김)": ("🟠", "주황", "대면만 끊김", SERIOUS),
    "-": ("⚪", "평온", "", NEUTRAL),
}
NEXT_ACTION = "본인 전화 → 닿지 않으면 발길이 닿던 단골이 확인"  # 다섯 마디 4번 (#2)

FEATURE_KO = {
    "m3": "좁아짐 3주 평균 (연속성)", "narrow": "이번 주 좁아짐 (연속성)", "d_narrow": "좁아짐 변화 (연속성)",
    "breadth_z": "발길 수 (양)", "d_breadth_z": "발길 수 변화 (양)",
    "stay_z": "체류 비중 (질)", "d_stay_z": "체류 비중 변화 (질)",
    "meal": "식사 비중", "anon": "익명 비중", "med": "병원·약국 비중", "evening": "저녁 결제 비중",
}
WEEK0 = pd.Timestamp("2025-07-07")  # weekly_panel의 w=0 주의 월요일

st.set_page_config(page_title="발길 — 담당자 화면", page_icon="👣", layout="wide")


@alt.theme.register("balgil", enable=True)
def chart_theme():
    return {
        "config": {
            "background": SURFACE,
            "font": "system-ui, -apple-system, 'Segoe UI', sans-serif",
            "view": {"stroke": None},
            "axis": {"labelColor": MUTED, "titleColor": INK_2, "gridColor": GRID, "domainColor": "#c3c2b7",
                     "tickColor": "#c3c2b7", "labelFontSize": 11, "titleFontSize": 11, "titleFontWeight": 400},
            "legend": {"labelColor": INK_2, "titleColor": INK_2, "labelFontSize": 11, "titleFontSize": 11},
            "title": {"color": INK, "fontSize": 13, "fontWeight": 600, "anchor": "start"},
        }
    }




# ── 데이터 ─────────────────────────────────────────────────────────────
@st.cache_data
def load_breaks(nomed: bool) -> pd.DataFrame:
    b = pd.read_csv(REF / ("nomed_break_daily.csv" if nomed else "break_daily.csv"), parse_dates=["date"])
    b["face_pct"] = (np.exp(b["f_d2"]) - 1) * 100
    b["ess_pct"] = (np.exp(b["e_d2"]) - 1) * 100
    b["week"] = b["date"] - pd.to_timedelta(b["date"].dt.weekday, unit="D")
    return b


@st.cache_data
def load_false_alarm(nomed: bool) -> pd.DataFrame:
    f = pd.read_csv(REF / ("nomed_false_alarm.csv" if nomed else "false_alarm.csv"), index_col=0)
    return f


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


def stat(col, label: str, value, help_text: str | None = None, delta=None):
    col.metric(label, value, delta=delta, delta_color="inverse", help=help_text)


# ── ① 주간 브리핑 ──────────────────────────────────────────────────────
def screen_briefing():
    st.subheader("① 주간 브리핑 — 이번 주 누구를 확인할까")
    b = load_breaks(nomed=False)
    weeks = sorted(b["week"].unique())
    hol_weeks = set(b.loc[b["holwk"], "week"])
    alert_weeks = set(b.loc[b["state"] != "-", "week"])
    # 공통 사건 주간이 아니면서 알림이 하나라도 있는 가장 최근 주 (시연 첫 화면)
    default = max(w for w in weeks if w not in hol_weeks and w in alert_weeks)
    wk = st.select_slider("주 (월요일 시작)", options=weeks, value=default,
                          format_func=lambda d: f"{pd.Timestamp(d):%m/%d} 주")
    cur = b[b["week"] == wk]
    prev = b[b["week"] == wk - pd.Timedelta(days=7)]

    def worst(df: pd.DataFrame) -> pd.Series:
        order = {"빨강(필수까지 끊김)": 2, "주황(대면만 끊김)": 1, "-": 0}
        return df.groupby("seg")["state"].agg(lambda s: max(s, key=order.get))

    w_now, w_prev = worst(cur), worst(prev) if len(prev) else pd.Series(dtype=str)
    flagged = w_now[w_now != "-"]
    n_prev = int((w_prev != "-").sum()) if len(w_prev) else 0

    c1, c2, c3, c4 = st.columns(4)
    stat(c1, "확인 권고 집단", f"{len(flagged)} / 12", "60대 이상 12개 집단 중 이번 주 한 번이라도 끊김이 잡힌 집단",
         delta=(len(flagged) - n_prev) if len(prev) and len(flagged) != n_prev else None)
    stat(c2, "🔴 빨강 (필수까지 끊김)", int((w_now == "빨강(필수까지 끊김)").sum()))
    stat(c3, "🟠 주황 (대면만 끊김)", int((w_now == "주황(대면만 끊김)").sum()))
    stat(c4, "끊긴 날 (집단×일)", int((cur["state"] != "-").sum()), "보정(계절 + 공통 충격) 뒤 남은 알림")

    rows = []
    for seg, state in w_now.sort_values(key=lambda s: s.map({"빨강(필수까지 끊김)": 0, "주황(대면만 끊김)": 1, "-": 2})).items():
        g = cur[cur["seg"] == seg]
        icon, name, desc, _ = STATE[state]
        rows.append({
            "신호": f"{icon} {name}" + (f" · {desc}" if desc else ""),
            "집단": seg,
            "끊긴 날": int((g["state"] != "-").sum()),
            "대면 발길 최저(%)": round(g["face_pct"].min()),
            "필수 발길 최저(%)": round(g["ess_pct"].min()),
            "다음 행동": NEXT_ACTION if state != "-" else "",
        })
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch", height=36 * 13 + 3,
                 column_config={"끊긴 날": st.column_config.NumberColumn(format="%d일"),
                                "대면 발길 최저(%)": st.column_config.NumberColumn(format="%+d%%"),
                                "필수 발길 최저(%)": st.column_config.NumberColumn(format="%+d%%")})
    st.caption("집단 단위(시군구 × 성 × 연령). 발길 변화는 7일 묶음, 계절·30·40대 공통 충격을 보정한 값입니다. "
               "신호 5단계와 끊김 종류(대면형·장보기형·병원약국형)는 D1 `agent.py` 완성 뒤 바뀝니다.")


# ── ② 발길 상세 ────────────────────────────────────────────────────────
def line(df: pd.DataFrame, field: str, title: str, wk: pd.Timestamp, color: str = SERIES[0]) -> alt.Chart:
    base = alt.Chart(df).encode(x=alt.X("week:T", title=None, axis=alt.Axis(format="%m/%d", tickCount=6)))
    ln = base.mark_line(strokeWidth=2, color=color).encode(
        y=alt.Y(f"{field}:Q", title=None),
        tooltip=[alt.Tooltip("week:T", title="주", format="%m/%d"), alt.Tooltip(f"{field}:Q", title=title, format=".2f")])
    pt = alt.Chart(df[df["week"] == wk]).mark_point(size=70, filled=True, color=color, stroke=SURFACE,
                                                     strokeWidth=2, opacity=1).encode(x="week:T", y=f"{field}:Q")
    rule = alt.Chart(pd.DataFrame({"week": [wk]})).mark_rule(color=MUTED, strokeDash=[3, 3]).encode(x="week:T")
    zero = alt.Chart(pd.DataFrame({"y": [0]})).mark_rule(color="#c3c2b7").encode(y="y:Q")
    return (zero + rule + ln + pt).properties(title=title, height=170)


def screen_detail():
    st.subheader("② 발길 상세 — 왜 이 집단인가")
    p, s, m = load_weekly(), load_shap(), load_map()
    segs = sorted(s["seg"].unique())
    c1, c2 = st.columns([1, 2])
    seg = c1.selectbox("집단 (시군구 × 성 × 연령)", segs, index=segs.index("춘천 여성 80대"))
    weeks = sorted(s["w"].unique())
    w = c2.select_slider("주", options=weeks, value=weeks[-1],
                         format_func=lambda i: f"{(WEEK0 + pd.Timedelta(days=7 * int(i))):%m/%d} 주")
    wk = WEEK0 + pd.Timedelta(days=7 * int(w))
    g = p[p["seg"] == seg].sort_values("w")
    row = s[(s["seg"] == seg) & (s["w"] == w)].iloc[0]

    a, b = st.columns(2)
    a.altair_chart(line(g, "breadth_z", "양 — 몇 곳에 닿는가 (발길 수, 나이 보정 z)", wk), width="stretch")
    b.altair_chart(line(g, "stay_z", "질 — 얼굴을 아는 곳인가 (체류 비중, 나이 보정 z)", wk), width="stretch")
    a, b = st.columns(2)
    cont = g.melt(id_vars=["week"], value_vars=["narrow", "m3"], var_name="지표", value_name="값")
    cont["지표"] = cont["지표"].map({"narrow": "이번 주 좁아짐", "m3": "3주 평균"})
    lc = alt.Chart(cont).mark_line(strokeWidth=2).encode(
        x=alt.X("week:T", title=None, axis=alt.Axis(format="%m/%d", tickCount=6)),
        y=alt.Y("값:Q", title=None),
        color=alt.Color("지표:N", scale=alt.Scale(domain=["이번 주 좁아짐", "3주 평균"], range=SERIES),
                        legend=alt.Legend(orient="bottom", title=None)),
        tooltip=[alt.Tooltip("week:T", title="주", format="%m/%d"), "지표:N", alt.Tooltip("값:Q", format=".2f")])
    rule = alt.Chart(pd.DataFrame({"week": [wk]})).mark_rule(color=MUTED, strokeDash=[3, 3]).encode(x="week:T")
    a.altair_chart((rule + lc).properties(title="연속성 — 늘 가던 대로 가는가 (좁아짐 점수)", height=170),
                   width="stretch")

    city = seg.split()[0]
    weak = (m[m["도시"] == city].sort_values("터전순위_통신")
            [["ADM_NM", "터전순위_통신", "체류형점포_천명당", "경로당수"]].head(5)
            .rename(columns={"ADM_NM": "동", "터전순위_통신": "터전 순위(약한 순)",
                             "체류형점포_천명당": "체류형 점포 /60세+천명", "경로당수": "경로당"}))
    with b:
        st.markdown(f"**터전 — 닿을 곳이 있는가** · {city} 안 터전이 약한 동 (동 단위)")
        st.dataframe(weak, hide_index=True, width="stretch")
        st.caption("⚠️ 단위가 다릅니다. 양·질·연속성은 집단(시군구) 단위, 터전은 동 단위입니다. "
                   "카드 지표는 동에 붙이지 않습니다.")

    st.markdown("---")
    sv = pd.DataFrame({"변수": [FEATURE_KO[f] for f in FEATURE_KO], "기여": [row[f] for f in FEATURE_KO]})
    sv["방향"] = np.where(sv["기여"] >= 0, "확률을 높임", "확률을 낮춤")
    sv = sv.reindex(sv["기여"].abs().sort_values(ascending=False).index).head(6)
    bars = alt.Chart(sv).mark_bar(height=14, cornerRadiusEnd=4).encode(
        x=alt.X("기여:Q", title="SHAP 기여 (확률 단위)"),
        y=alt.Y("변수:N", sort=None, title=None),
        color=alt.Color("방향:N", scale=alt.Scale(domain=["확률을 높임", "확률을 낮춤"], range=[POS, NEG]),
                        legend=alt.Legend(orient="top", title=None)),
        tooltip=["변수:N", alt.Tooltip("기여:Q", format="+.3f")])
    labels = alt.Chart(sv).mark_text(align="left", dx=4, color=INK_2, fontSize=11).encode(
        x=alt.X("기여:Q"), y=alt.Y("변수:N", sort=None), text=alt.Text("기여:Q", format="+.3f"))
    zero = alt.Chart(pd.DataFrame({"x": [0]})).mark_rule(color="#c3c2b7").encode(x="x:Q")
    left, right = st.columns([3, 2])
    left.altair_chart((zero + bars + labels).properties(
        title="집단 단위 기여도 — 다음 주 좁아짐 상위 20% 진입 확률 (상위 6개)", height=220), width="stretch")
    with right:
        st.metric("다음 주 좁아짐 상위 진입 확률", f"{row['확률']:.0%}")
        st.markdown(
            f"**근거 문장 (고정 틀)**\n\n{seg}의 {wk:%m/%d} 주 좁아짐 점수는 {row_of(g, w, 'narrow'):+.2f}, "
            f"3주 평균은 {row_of(g, w, 'm3'):+.2f}입니다. 체류 비중은 같은 성·나이 기준 {row_of(g, w, 'stay_z'):+.2f}, "
            f"발길 수는 {row_of(g, w, 'breadth_z'):+.2f}입니다.")
        st.caption("좁아짐 분류 모델(재분석 b3, 랜덤포레스트, 32칸 × 25주)의 SHAP. 모델 입력에 터전 변수가 없어 "
                   "터전 칸은 막대로 설명하지 않습니다. 「병원·약국 비중」 막대는 집단 사이 수준이라, "
                   "\"병원·약국이 그 자리를 채운다\"(집단 안 시간 변화)와 나란히 읽지 않습니다.")


def row_of(g: pd.DataFrame, w: int, field: str) -> float:
    return float(g.loc[g["w"] == w, field].iloc[0])


# ── ③ 지도 ─────────────────────────────────────────────────────────────
METRICS = {
    "터전 점수 (통신, 높을수록 강함)": "터전점수_통신",
    "체류형 점포 (60세+ 천 명당)": "체류형점포_천명당",
    "경로당·마을회관 (60세+ 천 명당)": "경로당_천명당",
}


def screen_map():
    st.subheader("③ 지도 — 어느 동에 닿을 곳이 없나")
    m, fac = load_map(), load_facilities()
    c1, c2, c3 = st.columns([1, 2, 2])
    city = c1.radio("도시", ["춘천", "강남"], horizontal=True)
    label = c2.selectbox("색으로 볼 지표", list(METRICS))
    show = c3.multiselect("점으로 겹칠 시설", ["경로당", "도서관"], default=["경로당", "도서관"])
    col = METRICS[label]
    g = m[m["도시"] == city].copy()
    sgg = "강원 춘천시" if city == "춘천" else "서울 강남구"

    q = pd.qcut(g[col], 5, labels=False, duplicates="drop")
    g["_c"] = [BLUE_RAMP[int(i)] for i in q]
    center = g.geometry.union_all().centroid
    fmap = folium.Map(location=[center.y, center.x], zoom_start=10 if city == "춘천" else 13,
                      tiles=None, control_scale=True)
    folium.TileLayer("Esri.WorldGrayCanvas", name="배경 지도", control=False).add_to(fmap)
    tip = folium.GeoJsonTooltip(
        fields=["ADM_NM", "터전순위_통신", "체류형점포_천명당", "경로당수", "도서관수", "인구_60세이상"],
        aliases=["동", "터전 순위(약한 순)", "체류형 점포 /60세+천명", "경로당·마을회관", "도서관", "60세+ 인구"])
    folium.GeoJson(
        g.drop(columns="_c").assign(_c=g["_c"]).__geo_interface__,
        style_function=lambda f: {"fillColor": f["properties"]["_c"], "color": SURFACE, "weight": 1.5, "fillOpacity": 0.85},
        highlight_function=lambda f: {"weight": 3, "color": INK},
        tooltip=tip, name=label).add_to(fmap)
    for kind in show:
        layer = folium.FeatureGroup(name=kind)
        for r in fac[(fac["SGG_NM"] == sgg) & (fac["시설종류"] == kind)].itertuples():
            folium.CircleMarker([r.위도, r.경도], radius=4, color=SURFACE, weight=1.5, fill=True,
                                fill_color=FAC_COLOR[kind], fill_opacity=1,
                                tooltip=f"{kind} · {r.시설명} ({r.ADM_NM})").add_to(layer)
        layer.add_to(fmap)
    folium.LayerControl(collapsed=False).add_to(fmap)

    left, right = st.columns([3, 2])
    with left:
        st_folium(fmap, height=520, use_container_width=True, returned_objects=[])
        lo, hi = g[col].min(), g[col].max()
        st.markdown(
            " ".join(f"<span style='display:inline-block;width:18px;height:10px;background:{c};"
                     f"border-radius:2px;margin-right:2px'></span>" for c in BLUE_RAMP)
            + f" <span style='color:{INK_2};font-size:12px'>{label}: 낮음 {lo:.1f} → 높음 {hi:.1f} (5분위)</span>"
            + "".join(f" &nbsp; <span style='color:{FAC_COLOR[k]}'>●</span>"
                      f" <span style='color:{INK_2};font-size:12px'>{k}</span>" for k in show),
            unsafe_allow_html=True)
    with right:
        st.markdown(f"**{city} — {label} 낮은 동 5곳**")
        t = g.sort_values(col)[["ADM_NM", col, "터전순위_통신", "경로당수", "인구_60세이상"]].head(5)
        st.dataframe(t.rename(columns={"ADM_NM": "동", col: "값", "터전순위_통신": "터전 순위"}),
                     hide_index=True, width="stretch")
        st.caption("체류형 점포와 경로당은 방향이 반대입니다(춘천 스피어만 −0.79). 면 지역은 가게가 적은 대신 "
                   "노인 인구 대비 경로당이 많습니다. 그래서 한 지수로 더하지 않고 따로 보여 줍니다(#6). "
                   "사회복지시설은 공개 데이터에 좌표가 없어 넣지 않았습니다.")


# ── ④ 보정 전·후 ───────────────────────────────────────────────────────
STEPS = {"(0) 보정 없음": "al0", "(1) 계절형 보정": "al1", "(2) + 공통 충격 보정": "al2"}


def screen_correction():
    st.subheader("④ 보정 전·후 — 헛알림을 얼마나 지웠나")
    c1, c2 = st.columns([3, 2])
    step = c1.radio("보정 단계", list(STEPS), index=0, horizontal=True)
    nomed = c2.toggle("병원·약국을 필수 발길에서 분리", value=False)
    b, fa = load_breaks(nomed), load_false_alarm(nomed)
    al = STEPS[step]

    base = fa.loc["(0) 보정 없음"]
    cur = fa.loc[step]
    k1, k2, k3 = st.columns(3)
    is_base = step == "(0) 보정 없음"
    stat(k1, "전체 알림 (집단×일)", int(cur["전체 알림"]),
         delta=None if is_base else int(cur["전체 알림"] - base["전체 알림"]))
    stat(k2, "공통 사건 주간 알림", int(cur.iloc[1]), "추석·광복절·성탄 뒤 7일. 모두가 같이 줄어드는 날이라 헛알림",
         delta=None if is_base else int(cur.iloc[1] - base.iloc[1]))
    stat(k3, "공통 사건 주간 감소율", f"{(1 - cur.iloc[1] / base.iloc[1]) * 100:.0f}%")

    d = b[["date", "seg", "holwk", al]].rename(columns={al: "alert"})
    d["알림"] = np.where(d["alert"], "알림", "없음")
    spans = (b[b["holwk"]].drop_duplicates("date")[["date"]]
             .assign(g=lambda x: (x["date"].diff().dt.days != 1).cumsum())
             .groupby("g")["date"].agg(["min", "max"]).reset_index(drop=True))
    spans["max"] = spans["max"] + pd.Timedelta(days=1)
    shade = alt.Chart(spans).mark_rect(color=NEUTRAL).encode(x="min:T", x2="max:T")
    cells = alt.Chart(d[d["alert"]]).mark_rect(color=CRITICAL, cornerRadius=1).encode(
        x=alt.X("date:T", title=None, axis=alt.Axis(format="%m/%d", tickCount=12),
                scale=alt.Scale(domain=[b["date"].min().isoformat(), (b["date"].max() + pd.Timedelta(days=1)).isoformat()])),
        x2=alt.X2("end:T"),
        y=alt.Y("seg:N", title=None, sort=sorted(d["seg"].unique())),
        tooltip=[alt.Tooltip("date:T", title="날짜", format="%Y-%m-%d"), alt.Tooltip("seg:N", title="집단")],
    ).transform_calculate(end="datetime(year(datum.date), month(datum.date), date(datum.date) + 1)")
    ylab = alt.Chart(d).mark_tick(opacity=0).encode(y=alt.Y("seg:N", sort=sorted(d["seg"].unique()), title=None))
    st.altair_chart((shade + ylab + cells).properties(
        title=f"집단 × 날짜 알림 — {step}{' · 병원·약국 분리' if nomed else ''}", height=320), width="stretch")
    st.markdown(f"<span style='display:inline-block;width:14px;height:10px;background:{CRITICAL};border-radius:2px'></span>"
                f" <span style='color:{INK_2};font-size:12px'>알림(끊김 판정) &nbsp;</span>"
                f"<span style='display:inline-block;width:14px;height:10px;background:{NEUTRAL};border:1px solid {GRID}'></span>"
                f" <span style='color:{INK_2};font-size:12px'>공통 사건 주간 (추석·광복절·성탄 뒤 7일)</span>",
                unsafe_allow_html=True)
    st.caption("보정을 끄면 추석 주간이 알림으로 뒤덮입니다. 계절형 보정만으로는 줄지 않고, "
               "같은 도시 30·40대가 함께 줄어든 만큼을 빼는 공통 충격 보정에서 크게 줄어듭니다. "
               "출처: 재분석 b2 (`reanalysis/reference/false_alarm.csv`).")
    with st.expander("표로 보기"):
        st.dataframe(fa, width="stretch")


# ── 화면 ───────────────────────────────────────────────────────────────
st.title("발길 — 담당자 화면")
st.caption("시연용 화면입니다. 집단 지표는 실제 분석 결과(신한카드·SK·상가·공공데이터)이고, "
           "개인 단위 사례가 나오면 모두 **가상**입니다. 수치는 10/17 동결 뒤 최종수치표 값으로 바뀝니다.")
SCREENS = {"① 주간 브리핑": screen_briefing, "② 발길 상세": screen_detail, "③ 지도": screen_map, "④ 보정 전·후": screen_correction}
only = st.query_params.get("screen")  # ?screen=1~4 → 그 화면만 (캡처·데모용)
if only in {"1", "2", "3", "4"}:
    list(SCREENS.values())[int(only) - 1]()
else:
    for tab, draw in zip(st.tabs(list(SCREENS)), SCREENS.values()):
        with tab:
            draw()
