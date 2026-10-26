"""화면 겉모양 — 토큰과 HTML 조각.

배치는 SaaS 대시보드 틀(왼쪽 메뉴 · 위 제목줄 · 큰 답 카드 · 색 타일 숫자 · 오른쪽 할 일 타임라인)을 따른다
(Figma 커뮤니티 「Saas Task Management Dashboard Design」을 참고했고, 그림·아이콘은 가져오지 않고 새로 그렸다).
발길의 표지는 신발 자국 한 쌍(logo_svg) — 메뉴 머리와 답 카드의 발자국 길에 쓴다.
아래는 처음 겉모양(Stripe DESIGN.md)에서 그대로 둔 원칙이다.

크롬(바탕·글자·카드·탭)만 Stripe 토큰을 쓴다. 데이터 색(신호·지도·차트)은 balgil_app.py의
dataviz 검증 팔레트를 그대로 둔다 — 색각 이상 검증을 통과한 색만 데이터에 쓴다.

Stripe 원칙 중 가져온 것
  * 글자는 순검정이 아니라 짙은 남색 ink(#0d253d), 보조는 ink-mute(#64748d)
  * 남보라 primary(#533afd)는 선택·강조에만 아껴 쓴다 (한 화면에 채운 요소 하나)
  * 숫자 칸은 표 숫자(tnum) + 살짝 좁힌 자간
  * 카드: 흰 바탕, 1px hairline(#e3e8ee), 12px 모서리, 아주 옅은 그림자(level 1)
  * 헤더는 흰 바탕 + hairline. Stripe의 위쪽 그라데이션 띠는 데이터 화면에서 산만해 쓰지 않는다
글꼴: Sohne는 한글이 없어 Pretendard(Inter 계열 한글)로 대신한다.
"""
from __future__ import annotations

import html

INK, INK_2, MUTE = "#1f2340", "#3b4061", "#6b7194"
CANVAS, CANVAS_SOFT, HAIRLINE = "#fffdfb", "#f8f3ee", "#efe7df"
LAVENDER, LAVENDER_SOFT, PEACH, PEACH_SOFT, MINT_SOFT = "#c3b3f2", "#efe9fd", "#f39a82", "#fde8df", "#e4f4ea"
PRIMARY, PRIMARY_DEEP, PRIMARY_SOFT_BG = "#6c5ce7", "#5546d6", "#efedff"
BRAND_DARK = "#1c1e54"
FONT = "'BalgilRound', 'Pretendard Variable', Pretendard, -apple-system, system-ui, sans-serif"
_NSR = "https://hangeul.pstatic.net/hangeul_static/webfont/NanumSquareRound/NanumSquareRound"
# 나눔스퀘어라운드(네이버 한글 웹폰트)는 굵기마다 이름이 따로라 한 이름(BalgilRound)으로 굵기를 묶는다
FONT_FACE = "".join(f"@font-face {{ font-family:'BalgilRound'; font-weight:{w}; font-display:swap; "
                    f"src:url({_NSR}{k}.woff2) format('woff2'); }}\n"
                    for k, w in (("L", 300), ("R", 400), ("B", 700), ("EB", 800)))

CSS = f"""
<style>
@import url("https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css");
{FONT_FACE}
html, body, [class*="st-"], .stApp, button, input, textarea, select {{
  font-family: {FONT} !important; color: {INK};
  font-feature-settings: "ss01";
}}
.stApp {{ background: {CANVAS_SOFT}; }}
[data-testid="stIconMaterial"], .material-symbols-rounded {{ font-family: "Material Symbols Rounded" !important; }}
iframe {{ border-radius: 8px; }}
[data-testid="stHeader"], [data-testid="stToolbar"], footer {{ display: none !important; }}
.block-container {{ padding-top: 0 !important; padding-bottom: 48px; max-width: 1280px; }}

/* 헤더 — 흰 바탕 한 장 + 아래 hairline. 그라데이션 없이 글자로만 무게를 준다 */
.bg-hero {{
  margin: 0 -9999px 28px; padding: 28px 9999px 22px;
  background: {CANVAS};
  border-bottom: 1px solid {HAIRLINE};
}}
.bg-brand {{ display:flex; align-items:baseline; gap:12px; }}
.bg-mark {{ font-size: 30px; font-weight: 600; letter-spacing: -0.6px; color: {INK}; }}
.bg-sub {{ font-size: 15px; font-weight: 400; color: {INK_2}; }}
.bg-note {{ margin-top: 8px; font-size: 13px; color: {MUTE}; letter-spacing: -0.2px; }}
.bg-pill {{ display:inline-block; padding: 3px 10px; border-radius: 9999px; background: {PRIMARY_SOFT_BG};
  color: {PRIMARY_DEEP}; font-size: 12px; font-weight: 500; margin-left: 6px; vertical-align: 2px; }}

/* 탭 */
.stTabs [data-baseweb="tab-list"] {{ gap: 4px; border-bottom: 1px solid {HAIRLINE}; }}
.stTabs [data-baseweb="tab"] {{ height: 44px; padding: 0 14px; color: {MUTE}; font-size: 15px; }}
.stTabs [aria-selected="true"] {{ color: {INK} !important; font-weight: 600; }}
.stTabs [data-baseweb="tab-highlight"] {{ background: {PRIMARY} !important; height: 2px; }}
.stTabs [data-baseweb="tab-border"] {{ display: none; }}

/* 화면 제목 */
.bg-h {{ font-size: 26px; font-weight: 300; letter-spacing: -0.4px; color: {INK}; margin: 18px 0 2px; }}
.bg-h b {{ font-weight: 600; }}
.bg-lead {{ font-size: 14px; color: {MUTE}; margin-bottom: 16px; }}
.bg-sec {{ font-size: 15px; font-weight: 600; color: {INK}; margin: 4px 0 8px; letter-spacing: -0.2px; }}

/* 카드 */
div[data-testid="stVerticalBlockBorderWrapper"][data-test-border="true"],
div.st-key-card, div[class*="st-key-card"] {{
  background: {CANVAS}; border: 1px solid {HAIRLINE} !important; border-radius: 12px;
  box-shadow: rgba(0,55,112,0.08) 0 1px 3px; padding: 20px 22px;
}}
.bg-stat {{ background:{CANVAS}; border:1px solid {HAIRLINE}; border-radius:12px; padding:16px 20px;
  box-shadow: rgba(0,55,112,0.08) 0 1px 3px; height: 100%; }}
.bg-stat .l {{ font-size:13px; color:{MUTE}; letter-spacing:-0.2px; display:flex; align-items:center; gap:6px; }}
.bg-stat .v {{ font-size:32px; font-weight:300; letter-spacing:-0.8px; color:{INK};
  font-feature-settings:"tnum"; margin-top:6px; line-height:1.1; }}
.bg-stat .v small {{ font-size:16px; color:{MUTE}; font-weight:400; letter-spacing:0; }}
.bg-stat .d {{ font-size:12px; color:{MUTE}; margin-top:6px; font-feature-settings:"tnum"; }}
.bg-dot {{ display:inline-block; width:9px; height:9px; border-radius:50%; }}

/* 표 */
.bg-table {{ width:100%; border-collapse:separate; border-spacing:0; background:{CANVAS};
  border:1px solid {HAIRLINE}; border-radius:12px; overflow:hidden; box-shadow: rgba(0,55,112,0.08) 0 1px 3px; }}
.bg-table th {{ text-align:left; font-size:12px; font-weight:500; color:{MUTE}; padding:10px 14px;
  background:{CANVAS_SOFT}; border-bottom:1px solid {HAIRLINE}; letter-spacing:-0.1px; }}
.bg-table td {{ font-size:14px; color:{INK}; padding:12px 12px; border-bottom:1px solid {HAIRLINE}; vertical-align:top;
  line-height:1.5; word-break:keep-all; overflow-wrap:break-word; }}
.bg-table th {{ vertical-align:bottom; word-break:keep-all; }}
.bg-table .nw {{ white-space:nowrap; }}                 /* 짧은 칸(신호·집단·숫자)은 줄을 바꾸지 않는다 */
.bg-table .it {{ white-space:nowrap; }}                 /* 「한식 30%」처럼 목록 한 항목은 한 덩어리로 */
.bg-table .sm {{ display:block; font-size:12px; color:{MUTE}; margin-top:2px; }}
.bg-tablewrap {{ overflow-x:auto; }}
.bg-table td.w-sig {{ min-width:120px; }} .bg-table td.w-win {{ min-width:180px; }}
.bg-table .sm .sm {{ display:block; margin-top:2px; }}
.bg-table tr:last-child td {{ border-bottom:none; }}
.bg-table td.n, .bg-table th.n {{ text-align:right; font-feature-settings:"tnum"; letter-spacing:-0.3px; }}
.bg-table td.m {{ color:{MUTE}; font-size:13px; }}
.bg-table tr.dim td {{ color:{MUTE}; }}
.bg-badge {{ display:inline-flex; align-items:center; gap:6px; padding:2px 10px 2px 8px; border-radius:9999px;
  font-size:12.5px; font-weight:500; border:1px solid {HAIRLINE}; background:{CANVAS}; white-space:nowrap; }}

/* 입력 위젯 */
[data-testid="stWidgetLabel"] p {{ font-size: 13px !important; color: {MUTE} !important; }}
div[data-baseweb="select"] > div {{ border-radius: 8px; border-color: {HAIRLINE}; background:{CANVAS}; }}
[data-testid="stSlider"] [role="slider"] {{ background: {PRIMARY} !important; box-shadow: none !important; }}
[data-testid="stSlider"] div[data-testid="stSliderTickBarMin"],
[data-testid="stSlider"] div[data-testid="stSliderTickBarMax"] {{ color: {MUTE}; }}
.stCaption, [data-testid="stCaptionContainer"] p {{ color: {MUTE} !important; font-size: 12.5px !important; line-height: 1.55; }}
[data-testid="stExpander"] details {{ border-radius: 12px; border-color: {HAIRLINE}; background: {CANVAS}; }}
hr {{ border-color: {HAIRLINE} !important; }}
.bg-legend {{ font-size:12px; color:{MUTE}; display:flex; flex-wrap:wrap; gap:14px; align-items:center; margin-top:8px; }}
.bg-legend i {{ display:inline-block; width:14px; height:10px; border-radius:2px; margin-right:6px; vertical-align:-1px; }}
.bg-callout {{ background:{CANVAS}; border:1px solid {HAIRLINE}; border-left:3px solid {PRIMARY}; border-radius:8px;
  padding:12px 14px; font-size:13.5px; color:{INK_2}; line-height:1.6; }}

/* 답 카드 — 화면마다 맨 위 한 장. 질문(제목) 바로 아래에서 「그래서 무엇을」을 한 문장으로 말한다 */
.bg-answer {{ background:{CANVAS}; border:1px solid {HAIRLINE}; border-radius:14px; padding:20px 24px 18px;
  box-shadow: rgba(0,55,112,0.08) 0 1px 3px; margin: 4px 0 18px; }}
.bg-answer .k {{ font-size:12px; font-weight:600; color:{PRIMARY_DEEP}; letter-spacing:0.2px; margin-bottom:6px; }}
.bg-answer .t {{ font-size:21px; font-weight:400; line-height:1.5; color:{INK}; letter-spacing:-0.4px; }}
.bg-answer .t b {{ font-weight:600; }}
.bg-answer .s {{ font-size:13px; color:{MUTE}; margin-top:6px; }}
.bg-steps {{ display:flex; gap:10px; margin-top:16px; flex-wrap:wrap; }}
.bg-step {{ flex:1 1 220px; border:1px solid {HAIRLINE}; border-radius:10px; padding:12px 14px; background:{CANVAS_SOFT};
  display:flex; gap:12px; align-items:flex-start; }}
.bg-step.on {{ background:{PRIMARY_SOFT_BG}; border-color:#d6d2ff; }}
.bg-step .n {{ flex:none; width:24px; height:24px; border-radius:50%; background:{CANVAS}; border:1px solid {HAIRLINE};
  font-size:12px; font-weight:600; display:flex; align-items:center; justify-content:center; color:{INK_2}; }}
.bg-step.on .n {{ background:{PRIMARY}; border-color:{PRIMARY}; color:#fff; }}
.bg-step .h {{ font-size:14px; font-weight:600; color:{INK}; line-height:1.35; }}
.bg-step .d {{ font-size:12.5px; color:{MUTE}; margin-top:3px; line-height:1.45; }}

/* 신호 칸 — 도시마다 성 × 연령 2 × 3. 색은 위 띠와 점, 글자는 늘 먹색 */
.bg-mx-city {{ font-size:13px; font-weight:600; color:{INK}; margin:2px 0 8px; }}
.bg-mx-city span {{ font-weight:400; color:{MUTE}; }}
.bg-mx {{ display:grid; grid-template-columns: 64px repeat(3, 1fr); gap:8px; align-items:stretch; }}
.bg-mx .ax {{ font-size:12.5px; font-weight:600; color:{INK_2}; display:flex; align-items:center; justify-content:flex-start; }}
.bg-mx .ax.top {{ justify-content:flex-start; padding-left:2px; }}
.bg-tile {{ border:1px solid {HAIRLINE}; border-radius:10px; padding:10px 12px 11px; background:{CANVAS};
  border-top-width:4px; min-height:0; padding:9px 12px; }}
.bg-tile .s {{ font-size:12px; font-weight:600; color:{INK_2}; display:flex; align-items:center; gap:6px; }}
.bg-tile .v {{ font-size:22px; font-weight:400; letter-spacing:-0.6px; color:{INK}; font-feature-settings:"tnum";
  margin-top:4px; line-height:1.2; }}
.bg-tile .v small {{ font-size:12px; color:{MUTE}; letter-spacing:0; margin-left:2px; }}
.bg-tile .d {{ font-size:11.5px; color:{MUTE}; margin-top:3px; line-height:1.4; }}
.bg-tile.calm {{ background:{CANVAS_SOFT}; }}
.bg-tile.calm .v {{ color:{MUTE}; font-size:16px; }}

/* 사람 카드 — 오래 끊긴 순으로 몇 장만. 나머지는 접힌 표 */
.bg-person {{ background:{CANVAS}; border:1px solid {HAIRLINE}; border-radius:12px; padding:14px 16px;
  box-shadow: rgba(0,55,112,0.08) 0 1px 3px; height:100%; }}
.bg-person .top {{ display:flex; justify-content:space-between; align-items:center; gap:8px; }}
.bg-person .id {{ font-size:14px; font-weight:600; color:{INK}; }}
.bg-person .id span {{ font-weight:400; color:{MUTE}; font-size:12.5px; margin-left:4px; }}
.bg-person .big {{ font-size:28px; font-weight:300; letter-spacing:-0.8px; font-feature-settings:"tnum"; margin-top:8px; line-height:1.1; }}
.bg-person .big small {{ font-size:12.5px; color:{MUTE}; letter-spacing:0; margin-left:4px; }}
.bg-person .bar {{ height:4px; border-radius:2px; background:{HAIRLINE}; margin:8px 0 10px; overflow:hidden; }}
.bg-person .bar i {{ display:block; height:100%; border-radius:2px; }}
.bg-person dl {{ margin:0; display:grid; grid-template-columns:auto 1fr; gap:4px 10px; font-size:12.5px; }}
.bg-person dt {{ color:{MUTE}; }}
.bg-person dd {{ margin:0; color:{INK_2}; }}

/* 자원 묶음 */
.bg-res {{ background:{CANVAS}; border:1px solid {HAIRLINE}; border-radius:12px; padding:12px 16px; margin-bottom:8px; }}
.bg-res .h {{ font-size:13.5px; color:{INK}; display:flex; align-items:center; gap:8px; flex-wrap:wrap; }}
.bg-res .h span {{ color:{MUTE}; }}
.bg-chip {{ display:inline-block; padding:4px 10px; border-radius:9999px; background:{CANVAS_SOFT};
  border:1px solid {HAIRLINE}; font-size:12.5px; color:{INK_2}; margin:8px 6px 0 0;
  max-width:100%; white-space:normal; overflow-wrap:anywhere; line-height:1.45; user-select:text; }}

/* ── v2: 대시보드 틀 ───────────────────────────────────────────── */
.block-container {{ padding-top: 28px !important; max-width: 1360px; }}
[data-testid="stSidebar"] {{ background:{CANVAS}; border-right:1px solid {HAIRLINE}; min-width:248px !important; max-width:248px !important; }}
[data-testid="stSidebar"] > div:first-child {{ padding-top: 8px; }}
[data-testid="stSidebarCollapseButton"], [data-testid="stSidebarCollapsedControl"], [data-testid="stSidebarHeader"] {{ display:none !important; }}
.bg-logo {{ display:flex; align-items:center; gap:12px; padding: 18px 6px 26px; }}
.bg-logo .t {{ font-size:22px; font-weight:700; letter-spacing:-0.6px; color:{INK}; line-height:1.1; }}
.bg-logo .s {{ font-size:11.5px; color:{MUTE}; margin-top:2px; }}
.bg-navh {{ font-size:12px; color:{MUTE}; font-weight:600; padding: 0 8px 8px; letter-spacing:0.2px; }}
.bg-nav a {{ display:flex; align-items:center; gap:12px; padding:11px 14px; border-radius:12px; margin-bottom:4px;
  color:{MUTE} !important; text-decoration:none !important; font-size:15px; font-weight:500; }}
.bg-nav a:hover {{ background:{CANVAS_SOFT}; color:{INK} !important; }}
.bg-nav a.on {{ background:{PRIMARY_SOFT_BG}; color:{PRIMARY} !important; font-weight:600; }}
.bg-nav a svg {{ width:20px; height:20px; flex:none; }}
.bg-team {{ margin-top:28px; border:1px solid {HAIRLINE}; border-radius:14px; padding:10px 12px; display:flex; align-items:center; gap:10px; font-size:13px; }}
.bg-team i {{ width:30px; height:30px; border-radius:50%; background:{PRIMARY_SOFT_BG}; display:flex; align-items:center; justify-content:center; font-style:normal; font-weight:700; color:{PRIMARY}; }}
.bg-team span {{ display:block; font-size:11px; color:{MUTE}; }}

.bg-top {{ display:flex; align-items:flex-end; justify-content:space-between; gap:16px; margin-bottom:14px; }}
.bg-top .t {{ font-size:25px; font-weight:800; letter-spacing:-0.8px; color:{INK}; line-height:1.15; }}
.bg-top .s {{ font-size:13px; color:{MUTE}; margin-top:4px; }}
.bg-pill2 {{ display:inline-flex; align-items:center; gap:8px; padding:8px 14px; border-radius:12px; background:{CANVAS};
  border:1px solid #d9d4ff; color:{INK_2}; font-size:13.5px; font-weight:500; white-space:nowrap; }}
.bg-pill2 svg {{ width:16px; height:16px; color:{PRIMARY}; }}

div[data-testid="stVerticalBlockBorderWrapper"][data-test-border="true"],
div.st-key-card, div[class*="st-key-card"] {{ border-radius:18px !important; box-shadow: rgba(31,35,64,0.06) 0 4px 18px !important;
  border-color: transparent !important; }}
.bg-table {{ border-radius:16px; box-shadow: rgba(31,35,64,0.05) 0 4px 14px; border-color:{HAIRLINE}; }}
[data-testid="stExpander"] details {{ border-radius:16px; border-color:transparent; box-shadow: rgba(31,35,64,0.05) 0 4px 14px; }}
.bg-sec {{ font-size:16px; font-weight:800; letter-spacing:-0.4px; margin: 6px 0 10px; }}
.bg-sec span {{ font-size:13px; letter-spacing:0; }}

.bg-heroc {{ background:{CANVAS}; border-radius:20px; padding:26px 28px; box-shadow: rgba(31,35,64,0.06) 0 4px 18px;
  display:flex; align-items:center; gap:24px; margin-bottom:18px; }}
.bg-heroc .body {{ flex:1; min-width:0; }}
.bg-heroc .k {{ font-size:12.5px; color:{MUTE}; margin-bottom:6px; }}
.bg-heroc .t {{ font-size:22px; font-weight:400; line-height:1.4; letter-spacing:-0.5px; color:{INK}; }}
.bg-heroc .t b {{ font-weight:800; color:{PRIMARY_DEEP}; }}
.bg-heroc .s {{ font-size:13px; color:{MUTE}; margin-top:10px; line-height:1.55; }}
.bg-heroc .art {{ flex:none; width:170px; }} .bg-heroc .art svg {{ width:170px; height:auto; }}
.bg-heroc .bg-steps {{ margin-top:16px; }}

.bg-kpis {{ display:grid; grid-template-columns:repeat(4, minmax(0, 1fr)); gap:14px; margin-bottom:18px; }}
.bg-kpis.c2 {{ grid-template-columns:repeat(2, minmax(0, 1fr)); }}
.bg-kpi {{ border-radius:18px; padding:16px 16px; display:flex; align-items:center; gap:14px; height:100%; min-width:0; }}
.bg-kpi > div:last-child {{ min-width:0; }}
.bg-kpi .ic {{ flex:none; width:40px; height:40px; border-radius:50%; display:flex; align-items:center; justify-content:center; }}
.bg-kpi .ic svg {{ width:19px; height:19px; color:#fff; }}
.bg-kpi .v {{ font-size:26px; font-weight:800; letter-spacing:-0.8px; color:{INK}; line-height:1.05; font-feature-settings:"tnum"; }}
.bg-kpi .v small {{ font-size:14px; font-weight:500; color:{INK_2}; margin-left:3px; letter-spacing:0; }}
.bg-kpi .l {{ white-space:nowrap; overflow:hidden; text-overflow:ellipsis; font-size:13px; font-weight:700; color:{INK_2}; margin-top:4px; }}
.bg-kpi .d {{ font-size:11.5px; color:{MUTE}; margin-top:2px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}

.bg-tl {{ background:{CANVAS}; border-radius:18px; padding:20px 20px 10px; box-shadow: rgba(31,35,64,0.06) 0 4px 18px; margin-bottom:16px; }}
.bg-tl .h {{ font-size:16px; font-weight:800; letter-spacing:-0.4px; color:{INK}; }}
.bg-tl .hs {{ font-size:12.5px; color:{MUTE}; margin:2px 0 14px; }}
.bg-tl .it {{ display:flex; gap:12px; padding-bottom:14px; position:relative; }}
.bg-tl .it::before {{ content:""; position:absolute; left:13px; top:28px; bottom:0; width:2px; background:{HAIRLINE}; }}
.bg-tl .it:last-child::before {{ display:none; }}
.bg-tl .n {{ flex:none; width:28px; height:28px; border-radius:50%; background:{CANVAS_SOFT}; border:1px solid {HAIRLINE};
  display:flex; align-items:center; justify-content:center; font-size:12.5px; font-weight:700; color:{MUTE}; z-index:1; }}
.bg-tl .it.on .n {{ background:{PRIMARY}; border-color:{PRIMARY}; color:#fff; }}
.bg-tl .box {{ flex:1; border-left:3px solid {HAIRLINE}; background:{CANVAS_SOFT}; border-radius:4px 12px 12px 4px; padding:9px 12px; }}
.bg-tl .it.on .box {{ border-left-color:{PRIMARY}; background:{PRIMARY_SOFT_BG}; }}
.bg-tl .box b {{ display:block; font-size:14px; color:{INK}; }}
.bg-tl .box span {{ display:block; font-size:12px; color:{MUTE}; margin-top:2px; line-height:1.45; }}

/* v3: 주간 브리핑 — 판(board) 하나에 제목 · 범례 · 내용 */
.bg-board {{ background:{CANVAS}; border-radius:18px; padding:18px 20px 16px; box-shadow: rgba(31,35,64,0.06) 0 4px 18px; margin-bottom:12px; }}
.bg-board .hd {{ display:flex; justify-content:space-between; align-items:flex-end; gap:12px; margin-bottom:14px; }}
.bg-board .sub {{ font-size:12px; color:{MUTE}; margin-top:3px; }}
.bg-board .lg {{ display:flex; gap:12px; font-size:12px; color:{MUTE}; white-space:nowrap; }}
.bg-board .lg span {{ display:inline-flex; align-items:center; gap:5px; }}
.bg-mx {{ grid-template-columns: 58px repeat(3, minmax(0, 1fr)) !important; gap:8px 10px !important; }}
.bg-mx .ax {{ font-size:12px !important; font-weight:700 !important; color:{INK_2} !important; }}
.bg-mx .ax.top {{ color:{MUTE} !important; font-weight:600 !important; padding-left:2px; }}
.bg-tile {{ border:none !important; border-top:4px solid {HAIRLINE} !important; border-radius:12px !important;
  padding:8px 12px 9px !important; background:{CANVAS_SOFT}; }}
.bg-tile .s {{ font-size:11.5px !important; font-weight:700 !important; }}
.bg-tile .v {{ font-size:24px !important; font-weight:800 !important; margin-top:2px !important; }}
.bg-tile.calm .v {{ font-size:14px !important; font-weight:700 !important; color:{MUTE}; margin-top:8px !important; }}
.bg-tile .d {{ font-size:11px !important; margin-top:1px !important; }}
.bg-plist .row {{ display:grid; grid-template-columns: 52px minmax(0, 1fr) minmax(0, 1.2fr) 56px; align-items:center; gap:14px;
  padding:10px 0; border-top:1px solid {HAIRLINE}; }}
.bg-plist .colh {{ font-size:12px; color:{MUTE}; padding:0 0 8px !important; }}
.bg-plist .row:first-child {{ border-top:none; padding-top:2px; }}
.bg-plist .av {{ width:46px; height:30px; border-radius:10px; font-size:12px; font-weight:800; display:flex; align-items:center; justify-content:center; }}
.bg-plist .who b {{ display:block; font-size:13.5px; color:{INK}; }}
.bg-plist .who span {{ display:block; font-size:12px; color:{MUTE}; margin-top:1px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
.bg-plist .bar {{ height:8px; border-radius:4px; background:{CANVAS_SOFT}; overflow:hidden; }}
.bg-plist .bar i {{ display:block; height:100%; border-radius:4px; }}
.bg-plist .days {{ text-align:right; font-size:20px; font-weight:800; color:{INK}; font-feature-settings:"tnum"; }}
.bg-plist .days small {{ font-size:12px; color:{MUTE}; font-weight:600; margin-left:2px; }}
.bg-res {{ border:none !important; border-radius:16px !important; box-shadow: rgba(31,35,64,0.06) 0 4px 18px; padding:14px 16px !important; }}
.bg-res .h {{ font-size:13px !important; }}
.bg-chip {{ font-size:12px !important; padding:4px 10px !important; margin:8px 6px 0 0 !important; }}
[data-testid="stExpander"] summary p {{ font-size:13.5px !important; color:{INK_2} !important; }}
.st-key-card_cont, .st-key-card_ground {{ min-height:369px; }}

/* ── v4: 크림 바탕 · 라벤더 메뉴 · 파스텔 카드 ─────────────────────── */
.stApp {{ background:{CANVAS_SOFT} !important; }}
/* 메뉴 — 크림보다 한 톤 밝은 아이보리. 고른 화면은 복숭아 알약 + 코랄 글자 (로고 복숭아와 한 색 계열) */
[data-testid="stSidebar"] {{ background:#fffaf6 !important; border-right:1px solid {HAIRLINE} !important; }}
.bg-logo .t {{ color:{INK}; }} .bg-logo .s {{ color:{MUTE}; }}
.bg-navh {{ color:{MUTE}; }}
.bg-nav a {{ color:{INK_2} !important; font-weight:600; }}
.bg-nav a:hover {{ background:#f8efe8; color:{INK} !important; }}
.bg-nav a.on {{ background:{PEACH_SOFT}; color:#c9553b !important; box-shadow:none; }}
.bg-team {{ background:{CANVAS}; border-color:{HAIRLINE}; color:{INK}; }}
.bg-team i {{ background:{PEACH}; color:#fff; }} .bg-team span {{ color:{MUTE}; }}

div[data-testid="stVerticalBlockBorderWrapper"][data-test-border="true"],
div.st-key-card, div[class*="st-key-card"], .bg-board, .bg-tl, .bg-res, .bg-heroc, .bg-table, [data-testid="stExpander"] details {{
  background:{CANVAS} !important; border-radius:24px !important; box-shadow: rgba(120,90,60,0.08) 0 8px 24px !important; }}
.bg-table {{ border-radius:18px !important; }}
.bg-table th {{ background:#faf6f2 !important; }}
.bg-heroc {{ background:linear-gradient(120deg, {PEACH_SOFT} 0%, #fdf0ea 60%, #fbf4ee 100%) !important; }}
.bg-heroc .art svg circle {{ fill:#fff6f1; }}
.bg-heroc .t b {{ color:#d0573c !important; }}

.bg-kpis {{ gap:16px !important; }}
.bg-kpi {{ display:block !important; border-radius:24px !important; padding:16px 18px 16px !important; min-height:0;
  box-shadow: rgba(120,90,60,0.06) 0 6px 18px; border:1px solid rgba(255,255,255,.8); }}
.bg-kpi .l {{ font-size:13px !important; font-weight:700 !important; color:{INK_2} !important; margin:0 0 10px !important; }}
.bg-kpi .ic {{ width:42px !important; height:42px !important; border-radius:14px !important; margin-bottom:10px;
  background-image:linear-gradient(150deg, rgba(255,255,255,.38), rgba(255,255,255,0) 60%) !important; }}
.bg-kpi .v {{ font-size:30px !important; }}
.bg-kpi .d {{ margin-top:4px !important; font-weight:600; }}

.bg-tl .it.on .box {{ background:{LAVENDER_SOFT} !important; }}
.bg-tl .box {{ background:#faf6f2 !important; border-left-color:{HAIRLINE} !important; }}
.bg-tl .it.on .box {{ border-left-color:{PRIMARY} !important; }}
.bg-tile {{ background:#faf6f2; border-radius:14px !important; }}
.bg-chip {{ background:#faf6f2 !important; border-color:{HAIRLINE} !important; }}
.bg-plist .row {{ border-top-color:{HAIRLINE} !important; }}
.bg-pill2 {{ border-color:{HAIRLINE}; border-radius:9999px; }}
.bg-steps .bg-step {{ background:#faf6f2; border-color:{HAIRLINE}; border-radius:16px; }}
.bg-steps .bg-step.on {{ background:{LAVENDER_SOFT}; border-color:#d9cffb; }}
</style>
"""


def esc(x) -> str:
    return html.escape(str(x))








def badge(text: str, color: str) -> str:
    return f"<span class='bg-badge'><span class='bg-dot' style='background:{color}'></span>{esc(text)}</span>"


def table(columns: list[tuple[str, str]], rows: list[dict], dim_key: str | None = None) -> str:
    """columns: [(제목, 'n'=숫자 오른쪽 정렬 | 'm'=흐린 글자 | 'nw'=줄 바꾸지 않음 | '', 띄어 써서 겹쳐도 된다)].
    값에 HTML을 넣으려면 미리 만들어 둔다 — 둘째 줄은 <span class='sm'>, 목록 항목은 <span class='it'>."""
    head = "".join(f"<th class='{c}'>{esc(t)}</th>" for t, c in columns)
    body = []
    for r in rows:
        cls = " class='dim'" if dim_key and r.get(dim_key) else ""
        body.append(f"<tr{cls}>" + "".join(f"<td class='{c}'>{r[t]}</td>" for t, c in columns) + "</tr>")
    # 칸이 좁으면 글자를 쪼개지 말고 옆으로 밀리게 — 넘치면 표만 가로로 스크롤된다
    return (f"<div class='bg-tablewrap'><table class='bg-table'><thead><tr>{head}</tr></thead>"
            f"<tbody>{''.join(body)}</tbody></table></div>")


def legend(items: list[tuple[str, str]]) -> str:
    return "<div class='bg-legend'>" + "".join(f"<span><i style='background:{c}'></i>{esc(t)}</span>"
                                                for t, c in items) + "</div>"


def tint(color: str, a: float = 0.10) -> str:
    """데이터 색을 흰 바탕에 옅게 깐다 — 칸 배경용. 글자 색으로는 쓰지 않는다."""
    c = color.lstrip("#")
    r, g, b = (int(c[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{a})"


def answer(kicker: str, text: str, sub: str = "", steps: list[tuple[str, str, bool]] | None = None) -> str:
    """화면 맨 위 답 카드(hero_card). text·sub는 HTML(<b>)을 받는다. steps: [(제목, 설명, 강조)].
    단계 칸이 있으면 그림을 빼서 칸에 자리를 준다."""
    return hero_card(kicker, text, sub, steps, art=not steps)


# ── 아이콘 · 표지 ────────────────────────────────────────────────────
_ICON = {
    "users": '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
    "alert": '<path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><path d="M12 9v4"/><path d="M12 17h.01"/>',
    "bell": '<path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/>',
    "shield": '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="m9 12 2 2 4-4"/>',
    "trend": '<polyline points="23 18 13.5 8.5 8.5 13.5 1 6"/><polyline points="17 18 23 18 23 12"/>',
    "percent": '<path d="M19 5 5 19"/><circle cx="6.5" cy="6.5" r="2.5"/><circle cx="17.5" cy="17.5" r="2.5"/>',
    "pin": '<path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/>',
    "pulse": '<polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>',
    "home": '<path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><path d="M9 22V12h6v10"/>',
    "calendar": '<rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/>',
    "grid": '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/>',
    "map": '<polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6"/><path d="M8 2v16M16 6v16"/>',
    "sliders": '<path d="M4 21v-7M4 10V3M12 21v-9M12 8V3M20 21v-5M20 12V3M1 14h6M9 8h6M17 16h6"/>',
    "check": '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>',
}


def icon(name: str) -> str:
    return (f'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
            f'stroke-linejoin="round">{_ICON[name]}</svg>')


# 신발 자국 하나 — 앞창(발끝이 넓고 아치 쪽으로 좁아짐)과 떨어진 뒷굽. 원점이 가운데, 발끝이 위(-y)다.
# 왼발 기준으로 그리고 오른발은 좌우를 뒤집는다(flip)
_SHOE = ('<path d="M-1 -14 C5 -14 7.2 -8 6.6 -3 C6.1 1 4.4 4 3.2 5 L-3.6 5 C-5.2 2 -6.2 -3 -6.1 -6.2 '
         'C-6 -11 -4.4 -14 -1 -14Z"/>'
         '<path d="M-3.7 7.2 L3.3 7.2 C3.8 10.2 2.7 13.6 -0.3 13.6 C-3.3 13.6 -4.3 10.2 -3.7 7.2Z"/>')


def shoe(x: float, y: float, rot: float, color: str, op: float = 1.0, scale: float = 1.0, flip: bool = False) -> str:
    sx = -scale if flip else scale
    return (f'<g transform="translate({x} {y}) rotate({rot}) scale({sx} {scale})" fill="{color}" opacity="{op}">'
            f'{_SHOE}</g>')


def logo_svg(size: int = 40) -> str:
    """발길 표지 — 동그라미 안에 흰 신발 자국 한 쌍(왼발 아래, 오른발이 한 걸음 앞)."""
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 40 40"><defs><linearGradient id="lg" x1="0" y1="0" x2="0" y2="1">'
            f'<stop offset="0" stop-color="#f8b4a0"/><stop offset="1" stop-color="{PEACH}"/></linearGradient></defs>'
            f'<circle cx="20" cy="20" r="20" fill="url(#lg)"/>'
            + shoe(15.2, 22.5, 18, "#fff", 1, 0.62) + shoe(24.6, 17.5, 18, "#fff", 1, 0.62, flip=True) + '</svg>')


def trail_svg() -> str:
    """답 카드 오른쪽 그림 — 왼쪽 아래에서 오른쪽 위로 걸어가다 흐려지는 신발 자국 네 쌍(발길이 좁아지고 끊기는 모양).
    발끝은 걷는 방향(rot)을 보고, 왼발은 진행 방향의 왼쪽, 오른발은 오른쪽에 반걸음 앞서 놓는다."""
    import math
    (x0, y0), (x1, y1) = (34, 124), (200, 18)
    ang = math.degrees(math.atan2(x1 - x0, y0 - y1))            # 위(-y)에서 시계 방향 각
    dx, dy = (x1 - x0), (y1 - y0)
    n = math.hypot(dx, dy)
    ux, uy = dx / n, dy / n                                      # 진행 방향
    lx, ly = uy, -ux                                             # 진행 방향의 왼쪽
    g = ""
    for i, op in enumerate([1.0, 0.72, 0.45, 0.2]):
        cx, cy = x0 + dx * i / 3.4, y0 + dy * i / 3.4
        g += shoe(cx + lx * 7, cy + ly * 7, ang, PRIMARY, op, 1.0)
        g += shoe(cx - lx * 7 + ux * 12, cy - ly * 7 + uy * 12, ang, "#a29bfe", op, 1.0, flip=True)
    return (f'<svg viewBox="0 0 220 150" width="170"><circle cx="140" cy="78" r="62" fill="{PRIMARY_SOFT_BG}"/>{g}</svg>')


def sidebar(active: int, items: list[tuple[str, str]]) -> str:
    nav = "".join(f'<a href="?screen={i}" target="_self" class="{"on" if i == active else ""}">{icon(ic)}{esc(t_)}</a>'
                  for i, (t_, ic) in enumerate(items, 1))
    return (f'<div class="bg-logo">{logo_svg(42)}<div><div class="t">발길</div><div class="s">고립 조기 발견 에이전트</div></div></div>'
            f'<div class="bg-navh">담당자 화면</div><div class="bg-nav">{nav}</div>'
            f'<div class="bg-team"><i>또</i><div>또커톤<span>빅콘테스트 2026</span></div></div>')


def topbar(title: str, sub: str, pill: str = "", pill_icon: str = "calendar") -> str:
    p = f'<span class="bg-pill2">{icon(pill_icon)}{esc(pill)}</span>' if pill else ""
    return f'<div class="bg-top"><div><div class="t">{esc(title)}</div><div class="s">{esc(sub)}</div></div>{p}</div>'


def hero_card(kicker: str, text: str, sub: str = "", steps: list[tuple[str, str, bool]] | None = None, art: bool = True) -> str:
    st_ = ""
    if steps:
        st_ = "<div class='bg-steps'>" + "".join(
            f"<div class='bg-step{' on' if on else ''}'><div class='n'>{i}</div><div><div class='h'>{h}</div>"
            f"<div class='d'>{d}</div></div></div>" for i, (h, d, on) in enumerate(steps, 1)) + "</div>"
    s = f"<div class='s'>{sub}</div>" if sub else ""
    a = f"<div class='art'>{trail_svg()}</div>" if art else ""
    return (f"<div class='bg-heroc'><div class='body'><div class='k'>{esc(kicker)}</div><div class='t'>{text}</div>{s}{st_}</div>"
            f"{a}</div>")


def kpis(cards: list[str]) -> str:
    """숫자 타일을 한 판(grid)에 — 열마다 따로 그리면 덧말 길이에 따라 높이가 들쭉날쭉해진다."""
    return f"<div class='bg-kpis{' c2' if len(cards) == 2 else ''}'>{''.join(cards)}</div>"


def kpi(label: str, value: str, color: str, icon_name: str, sub: str = "", unit: str = "") -> str:
    u = f"<small>{esc(unit)}</small>" if unit else ""
    d = f"<div class='d'>{sub}</div>" if sub else ""
    return (f"<div class='bg-kpi' style='background:{tint(color, .11)}'><div class='l'>{esc(label)}</div>"
            f"<div class='ic' style='background:{color};box-shadow:0 6px 14px {tint(color, .35)}, inset 0 2px 0 rgba(255,255,255,.35)'>"
            f"{icon(icon_name)}</div><div class='v'>{esc(value)}{u}</div>{d}</div>")


def timeline(title: str, sub: str, items: list[tuple[str, str, bool]]) -> str:
    its = "".join(f"<div class='it{' on' if on else ''}'><div class='n'>{i}</div><div class='box'><b>{h}</b><span>{d}</span></div></div>"
                  for i, (h, d, on) in enumerate(items, 1))
    return f"<div class='bg-tl'><div class='h'>{esc(title)}</div><div class='hs'>{esc(sub)}</div>{its}</div>"


# 발표자료(발길_발표자료_최종.pdf)와 같은 색 — 짙은 남색 · 하늘색 · 옅은 하늘색. 모양(둥근 모서리 · 옅은 그림자 ·
# 둥근 글꼴 · 채운 타일)은 위 기본 틀을 그대로 두고 색만 덮는다(10/26 팀 확정). 그라데이션은 쓰지 않는다
_DECK = dict(navy="#0a2647", navy2="#16395f", sky="#6cb5ea", sky_d="#3d8fd1", sky_m="#cfe5f7", pale="#eaf4fc",
             bg="#f3f7fb", line="#e1e9f2", ink="#0a2647", mute="#5d6f86")
DECK_CSS = ("""<style>
.stApp {{ background:{bg} !important; }}
[data-testid="stSidebar"] {{ background:{navy} !important; border-right:none !important; }}
.bg-logo svg circle, .bg-logo svg rect {{ fill:{sky} !important; }}
.bg-logo .t {{ color:#fff !important; }} .bg-logo .s {{ color:#a9bcd3 !important; }}
.bg-navh {{ color:#8ea3bd !important; }}
.bg-nav a {{ color:#d5dfeb !important; }}
.bg-nav a:hover {{ background:{navy2} !important; color:#fff !important; }}
.bg-nav a.on {{ background:{sky} !important; color:{navy} !important; box-shadow:0 6px 16px rgba(108,181,234,.35) !important; }}
.bg-team {{ background:{navy2} !important; border:none !important; color:#fff !important; }}
.bg-team i {{ background:{sky} !important; color:{navy} !important; }} .bg-team span {{ color:#8ea3bd !important; }}

.bg-top .t, .bg-sec {{ color:{ink} !important; }}
.bg-top .s, .bg-sec span {{ color:{mute} !important; }}
div.st-key-card, div[class*="st-key-card"], .bg-board, .bg-tl, .bg-res, .bg-table, [data-testid="stExpander"] details {{
  background:#fff !important; border-radius:22px !important; box-shadow: rgba(10,38,71,0.06) 0 6px 20px !important; }}
.bg-table {{ border-radius:16px !important; }}
.bg-table th {{ background:{pale} !important; color:{navy} !important; }}
.bg-heroc {{ background:{navy} !important; border-radius:24px !important; box-shadow: rgba(10,38,71,0.18) 0 10px 28px !important; }}
.bg-heroc .k {{ color:#a9bcd3 !important; }} .bg-heroc .t {{ color:#fff !important; }} .bg-heroc .s {{ color:#c7d4e3 !important; }}
.bg-heroc .t b, .bg-heroc .s b {{ color:{sky} !important; }}
.bg-heroc .art svg circle {{ fill:{navy2} !important; }}
.bg-heroc .art svg g {{ fill:{sky} !important; }}
.bg-heroc .bg-step {{ background:{navy2} !important; border:none !important; border-radius:16px !important; }}
.bg-heroc .bg-step .h {{ color:#fff !important; }} .bg-heroc .bg-step .d {{ color:#b9c8da !important; }}
.bg-heroc .bg-step .n {{ background:transparent !important; border-color:#5f86ad !important; color:#b9c8da !important; }}
.bg-heroc .bg-step.on {{ background:{sky} !important; }}
.bg-heroc .bg-step.on .h, .bg-heroc .bg-step.on .d {{ color:{navy} !important; }}
.bg-heroc .bg-step.on .n {{ background:{navy} !important; border-color:{navy} !important; color:#fff !important; }}

/* 숫자 타일 — 왼쪽 아이콘 원 + 오른쪽 숫자, 색은 남색 · 하늘 · 옅은 하늘 */
.bg-kpi {{ display:grid !important; grid-template-columns:40px minmax(0, 1fr); grid-template-rows:auto auto auto;
  column-gap:12px !important; row-gap:0; align-items:center; align-content:center; justify-items:start; text-align:left;
  border:none !important; box-shadow:none !important; border-radius:20px !important; padding:16px 14px !important; }}
.bg-kpi .ic {{ grid-column:1; grid-row:1 / span 3; width:40px !important; height:40px !important; border-radius:50% !important;
  margin:0 !important; background-image:none !important; box-shadow:none !important; }}
.bg-kpi .v {{ grid-column:2; grid-row:1; }}
.bg-kpi .l {{ grid-column:2; grid-row:2; margin:3px 0 0 !important; white-space:normal !important; word-break:keep-all; line-height:1.3; }}
.bg-kpi .d {{ grid-column:2; grid-row:3; }}
.bg-kpis .bg-kpi:nth-child(1) {{ background:{navy} !important; }}
.bg-kpis .bg-kpi:nth-child(1) .ic {{ background:{sky} !important; }} .bg-kpis .bg-kpi:nth-child(1) .ic svg {{ color:{navy} !important; }}
.bg-kpis .bg-kpi:nth-child(1) .v, .bg-kpis .bg-kpi:nth-child(1) .v small {{ color:{sky} !important; }}
.bg-kpis .bg-kpi:nth-child(1) .l {{ color:#fff !important; }} .bg-kpis .bg-kpi:nth-child(1) .d {{ color:#a9bcd3 !important; }}
.bg-kpis .bg-kpi:nth-child(2) {{ background:{sky} !important; }}
.bg-kpis .bg-kpi:nth-child(3) {{ background:{sky_m} !important; }}
.bg-kpis .bg-kpi:nth-child(4) {{ background:{pale} !important; }}
.bg-kpis .bg-kpi:not(:first-child) .ic {{ background:{navy} !important; }}
.bg-kpis .bg-kpi:not(:first-child) .v, .bg-kpis .bg-kpi:not(:first-child) .v small,
.bg-kpis .bg-kpi:not(:first-child) .l {{ color:{navy} !important; }}
.bg-kpis .bg-kpi:not(:first-child) .d {{ color:#33506f !important; }}

.bg-tl .box {{ background:{bg} !important; border-left-color:{line} !important; }}
.bg-tl .it.on .box {{ background:{pale} !important; border-left-color:{sky_d} !important; }}
.bg-tl .it.on .n {{ background:{navy} !important; border-color:{navy} !important; color:#fff !important; }}
.bg-tile {{ background:{bg}; }}
.bg-tile.calm {{ background:{bg} !important; }}
.bg-tl .n {{ background:#fff !important; border-color:{line} !important; }}
[data-testid="stSlider"] [role="slider"] {{ background:{sky_d} !important; }}
.bg-chip {{ background:{pale} !important; border-color:#d6e8f7 !important; color:{navy} !important; }}
.bg-steps .bg-step {{ background:{bg} !important; border-color:{line} !important; }}
.bg-steps .bg-step.on {{ background:{pale} !important; border-color:#cfe3f5 !important; }}
.bg-steps .bg-step.on .n {{ background:{navy} !important; border-color:{navy} !important; }}
</style>""").format(**_DECK)
