# 외부 공공데이터 목록

대회 규정상 외부 데이터는 무료·공개 데이터만 사용할 수 있고(유료 데이터 사용 시 수상 취소),
출처와 수집 방법을 명시하고 활용한 원본 파일을 함께 제출해야 합니다.

- 원본 파일은 가공 없이 `data/external/<슬러그>/`에 보관하고 **git에 함께 올립니다** (제공 데이터 `data/raw/`는 올리지 않습니다)
- 출처는 같은 폴더의 `meta.json`에 기록합니다. `python scripts/register_external.py --init <슬러그>`로 템플릿을 만듭니다.
- 아래 표는 `python scripts/register_external.py` 실행 시 자동으로 갱신됩니다.

<!-- BEGIN: 자동 생성 -->
| 슬러그 | 데이터셋 | 제공처 | 기준 시점 | 공간 단위 | 수집일 | 라이선스 | 출처 |
|---|---|---|---|---|---|---|---|
| `fac_library` | 전국도서관표준데이터 | 공공데이터포털 표준데이터 (각 지자체 제공) | 지자체별 데이터기준일자(referenceDate) — 강남 2025-12-26, 춘천 2025-11-12~2026-05-18 | 시설 좌표(WGS84) | 2026-10-10 | 이용허락범위 제한 없음 (공공데이터포털 메타데이터 기준, 무료·공개) | [링크](https://www.data.go.kr/data/15013109/standard.do) |
| `fac_senior_center` | 전국마을회관및경로당표준데이터 | 공공데이터포털 표준데이터 (각 지자체 제공) | 지자체별 데이터기준일자(crtrYmd) — 강남 2024-07-09, 춘천 2025-07-09 | 시설 좌표(WGS84) | 2026-10-10 | 이용허락범위 제한 없음 (공공데이터포털 메타데이터 기준, 무료·공개) | [링크](https://www.data.go.kr/data/15114136/standard.do) |
| `kma_asos` | 종관기상관측(ASOS) 일자료 — 서울(108)·춘천(101), 2025-07-01~2025-12-31 | 기상청 기상자료개방포털 | 2025-12-31 | 관측 지점 (시군구 대표) | 2026-10-10 | 공공누리 제1유형 (출처표시) — 같은 ASOS 일자료의 공공데이터포털 등록본(15059093) 기준, 무료·공개. 출처: 기상청 기상자료개방포털 | [링크](https://data.kma.go.kr/data/grnd/selectAsosRltmList.do?pgmNo=36) |
| `mois_population` | 행정동별 연령별 인구현황 | 행정안전부 (주민등록 인구통계, jumin.mois.go.kr) | 2025-12-31 | 행정동 | 2026-10-10 | 이용허락범위 제한 없음 (공공누리 제1유형, 무료·공개) | [링크](https://jumin.mois.go.kr/ageStatMonth.do) |
| `mois_single_household` | 행정동별 성/연령별 주민등록 1인세대수 | 행정안전부 (주민등록 인구통계, jumin.mois.go.kr) | 2025-12-31 | 행정동 | 2026-10-10 | 이용허락범위 제한 없음 (공공누리 제1유형, 무료·공개) | [링크](https://jumin.mois.go.kr/sexdAge1Hshd.do?sttsGbn=admm) |
| `sbiz_store` | 소상공인시장진흥공단_상가(상권)정보 (2026-06 기준) | 소상공인시장진흥공단 | 2026-06-30 | 점포 좌표(WGS84) + 행정동코드 | 2026-10-10 | 이용허락범위 제한 없음 (공공데이터포털 메타데이터 기준, 무료·공개) | [링크](https://www.data.go.kr/data/15083033/fileData.do) |
| `sgis_boundary` | 센서스용 행정구역경계(읍면동) 2025년 2분기 — bnd_dong_00_2025_2Q | 통계청 SGIS(통계지리정보서비스) | 2025-06-30 | 행정동 경계 폴리곤 (EPSG:5179) | 2026-10-10 | 이용허락범위 제한 없음 — 같은 기관(국가데이터처)이 공공데이터포털에 등록한 SGIS 경계 자료(15141768) 기준, 무료·공개. SGIS 포털 자체 약관은 별도 확인 필요 | [링크](https://sgis.kostat.go.kr) |
| `volunteer_1365` | 행정안전부_봉사참여정보서비스_GW | 행정안전부 | 2026-10-14 | 시도·시군구 코드 | 2026-10-14 | 이용허락범위 제한 없음 | [링크](https://www.data.go.kr/data/15157582/openapi.do) |
| `welfare_central` | 한국사회보장정보원_중앙부처복지서비스 | 한국사회보장정보원 | 2026-10-14 | 전국(지역 구분 없음) | 2026-10-14 | 이용허락범위 제한 없음 | [링크](https://www.data.go.kr/data/15090532/openapi.do) |
| `welfare_local` | 한국사회보장정보원_지자체복지서비스 | 한국사회보장정보원 | 2026-10-14 | 시군구 | 2026-10-14 | 이용허락범위 제한 없음 | [링크](https://www.data.go.kr/data/15108347/openapi.do) |

### 원본 파일

**`fac_library`** — Open API(https://api.data.go.kr/openapi/tn_pubr_public_lbrry_api)로 전국 3,597건을 1000건씩 받았다. 포털 파일 다운로드는 5만 건 상한에 잘려 쓰지 않는다. 합친 CSV를 이 폴더에 두고(git에 올림), 페이지별 원본 응답(JSON)은 raw/에 로컬로만 둔다. 다시 받으려면 python scripts/fetch_facility_api.py fac_library
- `전국도서관표준데이터_API_20261010.csv` — 1.2 MB, SHA-256 `7985e15db389e6de…`

**`fac_senior_center`** — Open API(https://api.data.go.kr/openapi/tn_pubr_public_vill_hall_sen_cent_api)로 전국 51,586건을 1000건씩 받았다. 포털 파일 다운로드는 5만 건 상한에 잘려 쓰지 않는다. 합친 CSV를 이 폴더에 두고(git에 올림), 페이지별 원본 응답(JSON)은 raw/에 로컬로만 둔다. 다시 받으려면 python scripts/fetch_facility_api.py fac_senior_center
- `전국마을회관및경로당표준데이터_API_20261010.csv` — 12.6 MB, SHA-256 `11b2d14007e00efb…`

**`kma_asos`** — 자료형태 일자료, 항목 기온·강수·적설 전체를 CSV로 받은 원본 그대로(OBS_ASOS_DD_20261010112520.csv, cp949). 지점별 184일 전부 있음. 강남구에는 ASOS 지점이 없어 서울(108)을 대표로 쓴다. 춘천(101)은 기간 내 적설 열이 전부 공란이라 미관측으로 보고 결측 처리한다.
- `OBS_ASOS_DD_20261010112520.csv` — 0.0 MB, SHA-256 `7e0dafb2dfca091b…`

**`mois_population`** — 수집 방법 — scripts/fetch_mois.py로 받았습니다. 조회 조건은 mois_single_household와 같습니다. 행정구역 서울특별시 강남구·강원특별자치도 춘천시, 조회기간 월간 2025년 12월, 등록구분 전체, 구분 계·남·여, 연령 구분 단위 1세, 연령 조회 범위 0세~100세 이상, CSV(cp949). 같은 스크립트를 다시 돌리면 바이트까지 같은 파일이 나오는 것을 확인했습니다. 내려받은 원본을 가공 없이 보관합니다. 1인세대율의 분모로 mois_single_household와 같은 축(동·성·1세)입니다.
- `202512_행정동별_연령별_인구현황_강남구.csv` — 0.0 MB, SHA-256 `ad7ffeb6c60267af…`
- `202512_행정동별_연령별_인구현황_춘천시.csv` — 0.0 MB, SHA-256 `9239314bf612cb7f…`

**`mois_single_household`** — 수집 방법 — scripts/fetch_mois.py로 받았습니다. 조회 조건은 행정구역 서울특별시 강남구(1168000000)·강원특별자치도 춘천시(5111000000), 조회기간 월간 2025년 12월(이 통계표는 검색기간이 1개월로 제한됩니다), 등록구분 전체, 구분 계·남·여, 연령 구분 단위 1세, 연령 조회 범위 0세~100세 이상, 파일 형식 CSV(cp949)입니다. 같은 스크립트를 다시 돌리면 바이트까지 같은 파일이 나오는 것을 확인했습니다. 내려받은 원본을 가공 없이 그대로 보관하며, 분석 코드(build_external.py)가 이 형식에 맞춰 읽습니다. 컬럼은 '2025년12월_계_65세' 형태이고 지역은 '서울특별시 강남구 신사동(1168051000)'처럼 한 칸에 들어 있습니다. 강남구 22개 동 + 춘천시 25개 읍면동, 각 파일에 시군구 합계 1행이 포함됩니다. 1인세대율의 분자이며 분모는 mois_population입니다.
- `202512_행정동별_성연령별_1인세대수_강남구.csv` — 0.0 MB, SHA-256 `26011e4c18f29ca6…`
- `202512_행정동별_성연령별_1인세대수_춘천시.csv` — 0.0 MB, SHA-256 `7031301da092b9e4…`

**`sbiz_store`** — 공공데이터포털 파일 다운로드(소상공인시장진흥공단_상가(상권)정보_20260630.zip, 시도별 CSV 16개) 중 서울·강원 두 파일만 압축 해제해 그대로 둔다. 대상 점포 강남구 66,269 + 춘천시 17,984 = 84,253개(분석결과.md와 같은 판). 서울 CSV가 302MB라 GitHub 한도를 넘어 git에는 이 meta.json만 올린다.
- `[필독]파일열람방법.txt` — 0.0 MB, SHA-256 `b81d2af050e9df2c…` · **git 미포함 — 수집 방법은 위 note**
- `소상공인시장진흥공단_상가(상권)정보_강원_202606.csv` — 62.6 MB, SHA-256 `6505ddc859141a3c…` · **git 미포함 — 수집 방법은 위 note**
- `소상공인시장진흥공단_상가(상권)정보_서울_202606.csv` — 301.9 MB, SHA-256 `08d3fd08b3784025…` · **git 미포함 (100MB 초과) — 해시로 대조**

**`sgis_boundary`** — SGIS 로그인 → 자료신청 → 행정구역 경계(읍면동), 기준 2025년 2분기, 전국으로 받은 shp 세트(shp·shx·dbf·prj·cpg) 그대로. 전국 3,559개 동, 대상 강남구 22·춘천시 25개. .shp가 135MB라 GitHub 한도를 넘어 git에는 이 meta.json만 올린다. 원본은 각자 같은 방법으로 받아 이 폴더에 둔다.
- `bnd_dong_00_2025_2Q.cpg` — 0.0 MB, SHA-256 `3ad3031f5503a440…` · **git 미포함 — 수집 방법은 위 note**
- `bnd_dong_00_2025_2Q.dbf` — 0.1 MB, SHA-256 `55ef3b6114e10424…` · **git 미포함 — 수집 방법은 위 note**
- `bnd_dong_00_2025_2Q.prj` — 0.0 MB, SHA-256 `e21b26451491c617…` · **git 미포함 — 수집 방법은 위 note**
- `bnd_dong_00_2025_2Q.shp` — 135.0 MB, SHA-256 `8f5dec93ce06be03…` · **git 미포함 (100MB 초과) — 해시로 대조**
- `bnd_dong_00_2025_2Q.shx` — 0.0 MB, SHA-256 `b04b98b8807bff24…` · **git 미포함 — 수집 방법은 위 note**

**`volunteer_1365`** — 1365 자원봉사 모집 일감. 서울·강원 전체를 받아 시군구 코드로 대상 지역을 거른다
- `raw/강원특별자치도_p001.xml` — 0.0 MB, SHA-256 `a4a1f920c7838d1d…`
- `raw/강원특별자치도_p002.xml` — 0.0 MB, SHA-256 `f4a82d89b491565e…`
- `raw/강원특별자치도_p003.xml` — 0.0 MB, SHA-256 `74efd95c44728c48…`
- `raw/서울특별시_p001.xml` — 0.0 MB, SHA-256 `7063ad0f0eba469b…`
- `raw/서울특별시_p002.xml` — 0.0 MB, SHA-256 `f5437e91298ff284…`
- `raw/서울특별시_p003.xml` — 0.0 MB, SHA-256 `fea4f3f8c14f8951…`
- `raw/서울특별시_p004.xml` — 0.0 MB, SHA-256 `022d7ff930ac5b0e…`
- `raw/서울특별시_p005.xml` — 0.0 MB, SHA-256 `96cb816a0acfbc6f…`
- `raw/서울특별시_p006.xml` — 0.0 MB, SHA-256 `02bd64042e6632a6…`
- `raw/서울특별시_p007.xml` — 0.0 MB, SHA-256 `78a3eb39e7f345d0…`
- `raw/서울특별시_p008.xml` — 0.0 MB, SHA-256 `95a3cd96d3ed3e5a…`
- `raw/서울특별시_p009.xml` — 0.0 MB, SHA-256 `98f128a9855af15b…`
- `raw/서울특별시_p010.xml` — 0.0 MB, SHA-256 `337bdec3f1aac850…`
- `raw/서울특별시_p011.xml` — 0.0 MB, SHA-256 `67d5863fa9c8b30d…`
- `raw/서울특별시_p012.xml` — 0.0 MB, SHA-256 `d489a2b06bfa23c1…`
- `raw/서울특별시_p013.xml` — 0.0 MB, SHA-256 `c46621686afb8e45…`
- `raw/서울특별시_p014.xml` — 0.0 MB, SHA-256 `1cb59af4e0a436e1…`
- `raw/서울특별시_p015.xml` — 0.0 MB, SHA-256 `370dc973f2c114ba…`
- `raw/서울특별시_p016.xml` — 0.0 MB, SHA-256 `0d62cbd6bec35e3a…`
- `raw/서울특별시_p017.xml` — 0.0 MB, SHA-256 `35dbad95e83a1352…`
- `raw/서울특별시_p018.xml` — 0.0 MB, SHA-256 `80afa4f693587419…`
- `raw/서울특별시_p019.xml` — 0.0 MB, SHA-256 `244a7a0fa3edb4d8…`
- `raw/서울특별시_p020.xml` — 0.0 MB, SHA-256 `40fae19bbca744e5…`
- `raw/서울특별시_p021.xml` — 0.0 MB, SHA-256 `685507d9fa149c16…`
- `raw/서울특별시_p022.xml` — 0.0 MB, SHA-256 `6cab42e8f3d6df2a…`
- `raw/서울특별시_p023.xml` — 0.0 MB, SHA-256 `8bcc79cb6f498b72…`
- `raw/서울특별시_p024.xml` — 0.0 MB, SHA-256 `937b863775bffd3e…`
- `raw/서울특별시_p025.xml` — 0.0 MB, SHA-256 `2a7c6ba40e5670aa…`
- `raw/서울특별시_p026.xml` — 0.0 MB, SHA-256 `444b91c577b23e9b…`
- `raw/서울특별시_p027.xml` — 0.0 MB, SHA-256 `1e1c1433ac6da49d…`
- `raw/서울특별시_p028.xml` — 0.0 MB, SHA-256 `3133f41cd6c512dc…`

**`welfare_central`** — 복지로 중앙부처 복지서비스 목록. API 활용신청 후 인증키로 수집
- `raw/central_p001.xml` — 0.1 MB, SHA-256 `fd9c6cfc9056ed6b…`
- `raw/central_p002.xml` — 0.1 MB, SHA-256 `c7d945d1a305618b…`
- `raw/central_p003.xml` — 0.1 MB, SHA-256 `4caba9ec10651d40…`
- `raw/central_p004.xml` — 0.1 MB, SHA-256 `24c0c3de800dcfc9…`
- `raw/central_p005.xml` — 0.1 MB, SHA-256 `46709a57247310eb…`

**`welfare_local`** — 복지로 지자체 복지서비스. 강남구·춘천시만 조회
- `raw/강남구_p001.xml` — 0.0 MB, SHA-256 `9d09fd7141546f7d…`
- `raw/춘천시_p001.xml` — 0.0 MB, SHA-256 `591a51d388aea903…`

<!-- END: 자동 생성 -->
