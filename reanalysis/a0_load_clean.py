"""01. 카드 데이터 로딩·정제
- 탭 구분 CP949, 금액·건수 숫자 변환, 연령 표기 공백 제거
- 데이터1의 법인 행 제거 (개인 소비만)
- 날짜, 요일, 공휴일 표시
출력: out/card1.pkl (시간대 포함), out/card2.pkl (거주 시도 포함)
"""
import pandas as pd, numpy as np, sys, os
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]  # 저장소로 옮기며 경로만 바꿈
DATA = sys.argv[1] if len(sys.argv) > 1 else str(ROOT / 'data' / 'raw' / 'card') + '/'
OUT = str(ROOT / 'data' / 'processed' / 'reanalysis') + '/'
os.makedirs(OUT, exist_ok=True)

def load(path):
    d = pd.read_csv(path, sep='\t', encoding='cp949', dtype=str)
    d['TS_AT'] = pd.to_numeric(d['TS_AT']); d['USE_CNT'] = pd.to_numeric(d['USE_CNT'])
    d['AGE'] = d['AGE_CCD'].str.replace(' ', '', regex=False)
    d['date'] = pd.to_datetime(d['TA_YMD'], format='%Y%m%d')
    d['city'] = d['MCT_SGG_CD'].map({'서울 강남구': '강남', '강원 춘천시': '춘천'})
    d = d.rename(columns={'MCT_RY_CD': 'ind', 'SEX_CCD': 'sex', 'TS_AT': 'amt', 'USE_CNT': 'cnt'})
    return d

d1 = load(DATA + '신한카드_빅콘테스트2026_데이터1.txt')
d2 = load(DATA + '신한카드_빅콘테스트2026_데이터2_수정.txt')
n_corp = int((d1.sex == '법인').sum())
d1 = d1[d1.sex != '법인'].copy()
d1 = d1.rename(columns={'TIME_GB': 'tslot'})[['date', 'tslot', 'city', 'ind', 'sex', 'AGE', 'amt', 'cnt']]
d2 = d2.rename(columns={'CLN_SGG_CD': 'home'})[['date', 'city', 'ind', 'home', 'sex', 'AGE', 'amt', 'cnt']]
# 지역 주민 여부: 가맹점 시군구가 속한 시도에 거주
d2['resident'] = ((d2.city == '춘천') & (d2.home == '강원')) | ((d2.city == '강남') & (d2.home == '서울'))
d1.to_pickle(OUT + 'card1.pkl'); d2.to_pickle(OUT + 'card2.pkl')
print('법인 행 제거:', n_corp, '| 데이터1 개인 행:', len(d1), '| 데이터2 행:', len(d2))
print('기간:', d1.date.min().date(), '~', d1.date.max().date(), '| 일수', d1.date.nunique())
