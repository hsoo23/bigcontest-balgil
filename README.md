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

**지금 할 일은 [Issues](../../issues)에 트랙별로 있습니다.** 자기 것에 Assign하고 시작하세요.

---

## 환경 준비

```bash
git clone https://github.com/hsoo23/balgil.git
cd balgil
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

`requirements.txt`는 **버전을 고정해 두었습니다.** 셋이 다른 버전으로 작업하면 제출 전 재현 확인에서 터집니다. 버전을 올려야 하면 회의에서 함께 올립니다.

## 데이터 배치

원본 데이터는 git에 올리지 않습니다(`data/`는 gitignore). 각자 아래처럼 배치합니다.

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
python scripts/build_weather.py       # ASOS 일자 × 시군구 기상 테이블 (B4)
python scripts/build_features.py      # 지표 산출
```

정제 규칙은 `src/balgil/data.py`, 지표 정의는 `src/balgil/features.py`에 모여 있습니다.

> **주의**: `features.py`에 알려진 버그가 두 개 있습니다 — `주류판매`가 두 분류에 중복(A3, 수경), 상가 패턴이 체류형 점포 4,547개 누락(커피 2,950 + 욕탕·유원지·도서관, C2, 현수 — `track-c`에서 수정). 10/11까지 각자 고칩니다.

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
| 업종 분류 | **10/10 회의에서 승인 예정** |
| 지표 산출 | A 트랙 진행 중 (10/13 패널 완료 목표) |
| 모델 | 재분석 2개 완료, 통합본 4개는 새 분류로 재실행 대기 |
| 에이전트 | 통합본 `agent.py` 작동. 네 면 구조로 리팩터 대기 |
| 화면 | 미착수 (10/12 시작) |
| 제출 마감 | **미확정 — 확인 필요** ([#1](../../issues/1)) |

## 이슈

| # | 내용 | 담당 |
|---|---|---|
| [#1](../../issues/1) | ⚠️ 제출 마감 확인 | 윤지 (10/8) |
| [#2](../../issues/2) | 회의 ① 킥오프 — 안건 9개 | 전원 (10/10) |
| [#3](../../issues/3) | [A] 지표 확정 | 수경 |
| [#4](../../issues/4) | [C] 터전·화면 | 현수 |
| [#5](../../issues/5) | [B·E] 모델·통합 | 윤지 |
| [#6](../../issues/6) | 회의 ② 수치 동결 | 전원 (10/17) |
| [#7](../../issues/7) | 회의 ③ 최종 점검 | 전원 (10/24) |
