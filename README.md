# 발길 — 2026 빅콘테스트 주제2

> 고립은 발길이 좁아지고 끊기는 일이다. 발길을 재면(양·질·연속성·터전) 확인해 줄 사람이 같이 나온다.

사회적 고립 예방·대응 AI 에이전트. 신한카드·SK 통신 데이터로 발길의 네 면을 재고, 끊김이 잡히면 본인이 등록한 단골 가게를 거쳐 확인합니다.

· 수경(지표·에이전트) · 현수(터전·화면) · 윤지(모델·통합)

---

## 처음 온 사람은 이 순서로

| 순서 | 문서 | 무엇을 알 수 있나 |
|---|---|---|
| 1 | [`docs/실행계획.md`](docs/실행계획.md) | **내가 무엇을 언제까지 해야 하는지** |
| 2 | [`docs/협업규칙.md`](docs/협업규칙.md) | 브랜치·커밋·수치 출처 규칙 |
| 3 | [`docs/기획안_발길.md`](docs/기획안_발길.md) | 무엇을 만드는가 |
| 4 | [`docs/분석결과.md`](docs/분석결과.md) | 그 근거와 아직 비어 있는 곳 |
| 5 | [`docs/제출요건.md`](docs/제출요건.md) | 마감·제출 방법·제출물 형태 (확인 완료) |
| 6 | [`docs/보고서_목차.md`](docs/보고서_목차.md) | 발표자료·보고서 목차와 공통 서식 |
| 7 | [`docs/설계자료_요구항목.md`](docs/설계자료_요구항목.md) | 규정상 함께 내는 설계자료 2종 |

**지금 할 일은 [Issues](../../issues)에 트랙별로 있습니다.** 자기 것에 Assign하고 시작하세요.

---

## 환경 준비

```bash
git clone https://github.com/hsoo23/balgil.git
cd balgil
python -m venv .venv && source .venv/bin/activate   # 윈도우: .venv\Scripts\activate
pip install -r requirements.txt
```

**Python 3.11 이상**이 필요합니다. `geopandas==1.2.0`이 3.11부터 지원합니다.

`requirements.txt`는 **버전을 고정해 두었습니다.** 셋이 다른 버전으로 작업하면 제출 전 재현 확인(체크리스트 11번)에서 터집니다. 버전을 올려야 하면 혼자 올리지 말고 회의에서 함께 올린 뒤 커밋합니다.

> `requirements.txt`의 주석은 **영어(ASCII)로만** 씁니다. 한국어 윈도우에서 pip가 이 파일을 cp949로 읽어, 한글 주석이 있으면 `pip install -r`이 `UnicodeDecodeError`로 실패합니다(#2). 설명은 이 README에 둡니다.

## 데이터 배치

제공 데이터(`data/raw/`)와 정제 산출물(`data/processed/`)은 git에 올리지 않습니다. 제공 데이터는 대회가 준 것이라 재배포 범위가 불분명하고 용량도 큽니다. 각자 아래처럼 배치합니다.

외부 원본(`data/external/`)과 팀 공용 기준표(`data/reference/`)는 git에 올립니다 — 규정이 **활용한 원본 파일 제출**을 요구하고, 셋이 같은 파일을 쓰지 않으면 조회 조건이 조금만 달라도 수치가 어긋나기 때문입니다. 다만 **100MB를 넘는 원본은 `meta.json`(출처·받는 법)만** 올립니다(아래 외부 데이터 참고).

```
data/raw/card/신한카드_빅콘테스트2026_데이터1.txt        # 일자 × 6시간대
data/raw/card/신한카드_빅콘테스트2026_데이터2_수정.txt   # 일자 × 고객 거주 시도 (수정본)
data/raw/sk/flow_{age,time,wkdy}_pop_2025{07..12}.csv   # SK 통신인구
data/raw/docs/                                           # 주제설명자료, 테이블 정의서
```

외부 데이터는 `data/raw/`가 아니라 **`data/external/<슬러그>/`**에 원본 그대로 둡니다. 스크립트가 이 경로를 읽고, 출처는 같은 폴더의 `meta.json`에 남깁니다(`python scripts/register_external.py --init <슬러그>`).

**`sgis_boundary`와 `sbiz_store`는 원본이 100MB를 넘어 git에 올리지 않습니다.** 받는 곳과 방법은 각 폴더의 `meta.json`에 있으니 각자 받아 같은 폴더에 둡니다.

```
data/external/sgis_boundary/bnd_dong_00_2025_2Q.shp     # SGIS 행정동 경계 (전 데이터 연결 기준표)
data/external/sbiz_store/*.csv                          # 소상공인 상가(상권)정보 (현수)
data/external/kma_asos/*.csv                            # 기상청 ASOS 일자료 서울108·춘천101 (현수)
data/external/fac_senior_center/*.csv                   # 전국마을회관및경로당표준데이터 (현수)
data/external/fac_library/*.csv                        # 전국도서관표준데이터 (현수)
data/external/mois_single_household/*.csv              # 행안부 1인세대 (윤지)
data/external/mois_population/*.csv                    # 행안부 주민등록 인구 (윤지)
```

받아야 할 데이터와 담당·기한은 [`docs/실행계획.md`](docs/실행계획.md) 6절에 있습니다.

## 파이프라인

```bash
python scripts/build_processed.py     # 제공 데이터 정제 → data/processed/*.parquet
python scripts/build_external.py      # 외부 데이터 정제
python scripts/build_spatial.py       # 행정동 기준으로 전 데이터 연결
python scripts/build_dong_code.py     # 47개 동 코드 대조표 → data/reference/dong_code.csv (C1, git에 올림)
python scripts/fetch_facility_api.py  # 경로당·도서관 전국 전체를 Open API로 받기 (.env 키 필요)
python scripts/build_facility.py      # 경로당·도서관 좌표 → 행정동, 동별 시설 수 (C3)
python scripts/build_ground.py        # 47개 동 터전 표(통신·상가·시설) → data/reference/dong_ground.csv (C3, git에 올림)
python scripts/build_weather.py       # ASOS 일자 × 시군구 기상 테이블 (B4)
python scripts/explore_weather.py     # 기상 결합표 → data/reference/weather_daily.csv, 끊김·예상과 대조 (B4, git에 올림)
python scripts/build_priority.py      # 동 우선순위표·도달 효율 → data/reference/dong_priority.csv, reach_efficiency.csv (C5, git에 올림)
python scripts/build_features.py      # 지표 산출
```

정제 규칙은 `src/balgil/data.py`, 지표 정의는 `src/balgil/features.py`에 모여 있습니다.

> `features.py`의 알려진 버그 두 개는 고쳤습니다 — `주류판매` 두 분류 중복(A3, 수경, 중복 검사 assert 추가), 상가 패턴 누락(C2, 현수 — 중분류 정확 비교, 오락은 #8 D안대로 노래방만, 요리 주점·독서실 제외 #24).

## 담당자 화면 (D3)

```bash
pip install -r app/requirements-app.txt     # 분석 고정 버전 + streamlit·folium
streamlit run app/balgil_app.py             # 탭 4개: 주간 브리핑 · 발길 상세 · 지도 · 보정 전·후
# http://localhost:8501/?screen=3 처럼 붙이면 그 화면만 (캡처·데모용)
```

화면은 git에 있는 파일만 읽어서 **원본 데이터 없이도 뜹니다** — `reanalysis/reference/`(재분석 결과)와 `data/reference/app/`(지도·시설·SHAP). 원본이 바뀌면 `python scripts/build_app_data.py`로 다시 만듭니다.

## 검증 스크립트

분석 주장의 근거를 다시 뽑습니다. **보고서에 쓸 수치는 여기서 나온 값만 씁니다.**

```bash
python scripts/explore_quality.py     # 질 지표 검증 10종 (지표 교체 근거)
python scripts/explore_external.py    # 외부 데이터 해상도, 점포 버그, 계절성
python scripts/explore_signals.py     # 기존 인용 수치 재현
```

## 노션 공유

```bash
python scripts/make_notion.py         # docs/ → docs/notion/ (상대 링크 제거)
pbcopy < docs/notion/실행계획.md
```

---

## 디렉터리

```
src/balgil/      데이터 정제·지표 정의 (공용 모듈)
scripts/         실행 스크립트 (build_* 파이프라인, explore_* 검증)
docs/            기획안·분석결과·실행계획·협업규칙
docs/notion/     노션 복붙용 (파생물, make_notion.py로 생성)
docs/archive/    폐기한 이전 기획안 (기록용)
data/            원본·정제 데이터 (git 제외)
reports/         자동 생성 리포트
```

## 지금 상태

| | 상태 |
|---|---|
| 개념·설계 | 확정 (「발길」 네 면) |
| 업종 분류 | **확정** — 확정안 + 오락 D안(노래방만 체류형), 제과점 제외 유지 ([#2](https://github.com/hsoo23/bigcontest-balgil/issues/2) 결정, #9·#13 머지) |
| 지표 산출 | **패널 2종 완료** — `features_segment`(36칸)·`features_dong`(47동), 결측 0 (#12 머지, 목표 10/13보다 빠름) |
| 모델 | 재분석 2개 **재실행 완료**, 재현 17/17 (#16). **통합본 4개는 코드가 없어 재실행 불가** ([#14](https://github.com/hsoo23/bigcontest-balgil/issues/14)) |
| 에이전트 | `src/balgil/agent.py` **뼈대** — 양·질·끊김·보정·터전·상태 판정·명부 교차·문장 틀. 상대방·자원·종결은 D4 가상 데이터 뒤(10/18–20). 실행 `python scripts/run_agent.py`, 입력 형식 `docs/agent_입력형식.md` |
| 화면 | 미착수 (10/12 시작) |
| 제출 마감 | **10/26(월) 확정.** 본 제출물은 **발표자료** ([제출요건](docs/제출요건.md)) |

## 이슈

| # | 내용 | 담당 |
|---|---|---|
| [#1](../../issues/1) | ✅ 제출 마감 확인 — 10/26(월), 본체는 발표자료 | 윤지 (10/9 완료) |
| [#2](../../issues/2) | 회의 ① 킥오프 — 안건 9개 | 전원 (10/10) |
| [#3](../../issues/3) | [A] 지표 확정 | 수경 |
| [#4](../../issues/4) | [C] 터전·화면 | 현수 |
| [#5](../../issues/5) | [B·E] 모델·통합 | 윤지 |
| [#6](../../issues/6) | 회의 ② 수치 동결 | 전원 (10/17) |
| [#7](../../issues/7) | 회의 ③ 최종 점검 | 전원 (10/24) |
