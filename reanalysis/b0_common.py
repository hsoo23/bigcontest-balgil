"""발길 공통 정의 — 업종 3분할(체류 / 식사 / 익명)과 병원·약국
체류: 머물며 얼굴을 익히는 곳. 식사: 밥집. 익명: 반복해도 얼굴을 기억하지 않는 곳.
(팀 「발길」 문서의 수치 — 강남 체류 중 커피 75~87%, 춘천 연령 간 최대/최소 2.78배 — 를 재현하는 정의. 제과점은 어느 쪽에도 넣지 않았음: 팀 확인 필요)
"""
import pandas as pd, numpy as np
from pathlib import Path
# 저장소로 옮기며 바꾼 것: 입출력 경로만. 정제본·결과는 data/processed/reanalysis/ (git 제외)
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data' / 'processed' / 'reanalysis'; OUT.mkdir(parents=True, exist_ok=True)
STAY = ['커피전문점', '미용실', '미용서비스', '싸우나/목욕탕', '안마/마사지', '노래방', '유흥업소', '스포츠시설', '헬스장', '실내/실외골프장', '학원/학습지']
MEAL = ['한식', '중식', '일식', '양식', '기타요식']
ANON = ['편의점', '할인점/슈퍼마켓/양판점', '기타식품', '농수산물', '정육점', '주류판매', '패스트푸드']
MED = ['약국', '일반병원', '종합병원', '한의원', '치과병원', '기타의료', '보건소']
ESS = ['할인점/슈퍼마켓/양판점', '편의점', '기타식품', '농수산물', '정육점'] + MED          # 필수 발길
HOLIDAYS = {'2025-08-15': '광복절', '2025-10-03': '개천절', '2025-10-05': '추석 연휴', '2025-10-06': '추석', '2025-10-07': '추석 연휴', '2025-10-08': '대체공휴일', '2025-10-09': '한글날', '2025-12-25': '성탄절'}
HOL = pd.to_datetime(list(HOLIDAYS)); CHUSEOK = pd.date_range('2025-10-03', '2025-10-09'); DAYS = pd.date_range('2025-07-01', '2025-12-31')
AGES = ['10대', '20대', '30대', '40대', '50대', '60대', '70대', '80대', '90대']
def load():
    d2 = pd.read_pickle(OUT / 'card2.pkl'); d1 = pd.read_pickle(OUT / 'card1.pkl'); return d2[d2.resident].copy(), d1
def base(s, k=4):
    """평소 = 앞뒤 4주 같은 요일 중앙값(공휴일 제외). 느린 계절 변화는 여기서 흡수된다(계절형 보정)."""
    ok = s[~s.index.isin(HOL)]; o = {}
    for d in s.index:
        v = [ok[x] for x in (d + pd.Timedelta(days=7 * i) for i in range(-k, k + 1) if i != 0) if x in ok.index]; o[d] = np.median(v) if len(v) >= 3 else np.nan
    return pd.Series(o)
def faces(a, b, keys):
    """a: 데이터2(주민) 부분집합, b: 데이터1 부분집합 → 발길의 양·질과 구성"""
    g = a.groupby(keys + ['ind']).cnt.sum().unstack('ind').fillna(0); tot = g.sum(axis=1); p = g.div(tot, axis=0)
    f = lambda L: p[[c for c in L if c in p]].sum(axis=1) * 100
    t = b.groupby(keys + ['tslot']).cnt.sum().unstack().fillna(0); eve = (t['18_23'] + t['00_05']) / t.sum(axis=1) * 100
    c = b.groupby(keys + ['ind', 'tslot', b.date.dt.dayofweek.rename('dow')]).cnt.sum(); cs = c.groupby(level=list(range(len(keys)))).sum(); slot = 1 / ((c / cs) ** 2).groupby(level=list(range(len(keys)))).sum()
    return pd.DataFrame({'breadth': 1 / (p ** 2).sum(axis=1), 'slots': slot.reindex(tot.index), 'stay': f(STAY), 'meal': f(MEAL), 'anon': f(ANON), 'med': f(MED), 'evening': eve.reindex(tot.index), 'n': tot})
def adjust(I, cols=('breadth', 'stay')):
    """나이·나이제곱·도시로 설명되는 부분을 덜어 낸 표준화 잔차. 좁아짐 점수 = -(양 z + 질 z)/2"""
    I = I.reset_index(); age = I.AGE.str[:2].astype(int) + 5; X = np.column_stack([np.ones(len(I)), age, age ** 2, (I.city == '강남').astype(int)])
    for c in cols:
        beta, *_ = np.linalg.lstsq(X, I[c].values, rcond=None); r_ = I[c].values - X @ beta; I[c + '_z'] = r_ / r_.std()
    I['narrow'] = -(I[[c + '_z' for c in cols]].mean(axis=1)); return I
