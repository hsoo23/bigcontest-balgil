"""b1. 발길 네 면 지표 패널 (트랙 A2·A4·A5, B5)
출력: data/processed/reanalysis/features_segment.csv (36셀), features_segment_month.csv (36셀×6개월), quality_checks.csv
"""
import sys; sys.path.insert(0, __import__('os').path.dirname(__file__)); from b0_common import *
import warnings; warnings.filterwarnings('ignore'); pd.set_option('display.width', 230)
r, d1 = load(); K = ['city', 'sex', 'AGE']
F = faces(r, d1, K); A = adjust(F); A['seg'] = A.city + ' ' + A.sex + ' ' + A.AGE; A['rank'] = A.narrow.rank(ascending=False).astype(int)
A.round(4).to_csv(OUT / 'features_segment.csv', index=False, encoding='utf-8-sig')
r['m'] = r.date.dt.month; d1['m'] = d1.date.dt.month; FM = faces(r, d1, K + ['m']); FM.round(4).to_csv(OUT / 'features_segment_month.csv', encoding='utf-8-sig')
show = lambda col: F[col].unstack('AGE')[AGES].round(1)
print('■ 양: 유효 발길 수'); print(show('breadth').to_string()); print('■ 양: 생활 시간표 폭(업종×시간대×요일 유효 칸)'); print(show('slots').round(0).to_string())
print('■ 질: 체류 비중(%)'); print(show('stay').to_string()); print('■ 식사 비중(%)'); print(show('meal').to_string()); print('■ 병원·약국 비중(%)'); print(show('med').to_string())
# A5 월별 안정성
q = FM.stay.unstack('m'); chk = []
for c in ['춘천', '강남']:
    for s in ['남성', '여성']:
        for old in ['60대', '70대', '80대']:
            chk.append((c, s, old, int((q.loc[(c, s, old)] < q.loc[(c, s, '50대')]).sum()), round(F.stay[(c, s, old)] / F.stay[(c, s, '50대')], 2), round(q.loc[(c, s, old)].std() / q.loc[(c, s, old)].mean(), 3)))
C = pd.DataFrame(chk, columns=['도시', '성별', '연령', '50대보다 낮은 달(6개월 중)', '50대 대비', '월별 변동계수']); print('■ 월별 안정성'); print(C.to_string(index=False))
# A5 민감도: 체류 업종을 하나씩 빼기
g = r.groupby(K + ['ind']).cnt.sum().unstack('ind').fillna(0); tot = g.sum(axis=1); sens = []
for ind in STAY:
    s = g[[c for c in STAY if c != ind and c in g]].sum(axis=1) / tot
    for c in ['춘천', '강남']:
        for sx in ['남성', '여성']: sens.append((ind, c, sx, round(s[(c, sx, '70대')] / s[(c, sx, '50대')], 2), round(s[(c, sx, '80대')] / s[(c, sx, '70대')], 2)))
S = pd.DataFrame(sens, columns=['뺀 업종', '도시', '성별', '70대÷50대', '80대÷70대']); p = S.pivot_table(index='뺀 업종', columns=['도시', '성별'], values='70대÷50대')
print('■ 민감도: 체류 업종을 하나씩 뺐을 때 70대÷50대 (1보다 작으면 유지)'); print(p.round(2).to_string()); print('  44가지 중 유지:', int((S['70대÷50대'] < 1).sum()), '| 최댓값', S['70대÷50대'].max())
print('  강남 80대÷70대(반등 여부): 기준', round(F.stay[('강남', '남성', '80대')] / F.stay[('강남', '남성', '70대')], 2), round(F.stay[('강남', '여성', '80대')] / F.stay[('강남', '여성', '70대')], 2), '| 커피를 빼면', S[(S['뺀 업종'] == '커피전문점') & (S.도시 == '강남')][['성별', '80대÷70대']].values.tolist())
# B5 양·질 분리
X = A[A.AGE != '90대']; print('■ 양·질 상관(35셀→90대 제외 32셀): 유효 발길 수~체류 비중 r =', round(np.corrcoef(X.breadth, X.stay)[0, 1], 3), '| 나이 보정 뒤 r =', round(np.corrcoef(X.breadth_z, X.stay_z)[0, 1], 3), '| 시간표 폭~체류 r =', round(np.corrcoef(X.slots, X.stay)[0, 1], 3))
# 좁아짐 순위
print('■ 좁아짐 점수(나이 보정, 양·질) 상위'); print(A.sort_values('rank')[['seg', 'breadth', 'stay', 'breadth_z', 'stay_z', 'narrow', 'rank']].round(2).head(12).to_string(index=False))
print('■ 60대 이상 원값 순위(체류 비중 낮은 순)'); print(A[A.AGE.isin(['60대', '70대', '80대'])].sort_values('stay')[['seg', 'breadth', 'stay', 'meal', 'med', 'anon', 'evening', 'rank']].round(1).to_string(index=False))
pd.concat([C.assign(검증='월별'), S.assign(검증='민감도')]).to_csv(OUT / 'quality_checks.csv', index=False, encoding='utf-8-sig')
