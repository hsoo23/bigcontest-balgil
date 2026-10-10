"""[미이식 — 실행 불가] 입력 sk_dong.csv·sk_age.pkl을 만드는 코드가 없음. scripts/build_dong_panel.py가 대체한다(결과 동일). 원본 보존용.
b4. 터전 패널 (트랙 C1·C2 중 통신 데이터로 가능한 부분) — 47개 행정동
동마다: 60대 이상 유동 규모·비중, 여성 비중, 일요일÷평일, 저녁(18~23시) 비중, 60대 이상 12월÷9월.
터전 점수(통신 부분) = 60대 이상 비중(높을수록) · 저녁 비중(낮을수록) · 일요일÷평일(낮을수록) · 겨울 유지(낮을수록)의 도시 안 순위 평균.
월별로 따로 계산해 순위가 달마다 유지되는지도 본다.
상가(체류 업종 가게 수)·1인세대·시설은 외부 데이터가 필요해 빈 칸으로 둔다 → 팀이 채울 열.
출력: balgil/out/features_dong.csv, dong_stability.csv
"""
import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore'); pd.set_option('display.width', 230)
g = pd.read_csv('out/sk_dong.csv', dtype={'dong': str})
a = pd.read_pickle('out/sk_age.pkl').dropna(subset=['city']); ac = [c for c in a.columns if 'FLOW' in c]; a['old'] = a.MAN_FLOW_POP_CNT_60GU + a.WMAN_FLOW_POP_CNT_60GU; a['tot'] = a[ac].sum(axis=1)
m = a.groupby(['city', 'dong', 'STD_YM'])[['old', 'tot']].sum(); m['share'] = m.old / m.tot; sh = m.share.unstack('STD_YM'); sh.index = sh.index.set_levels(sh.index.levels[1].astype(str), level=1)
for c, asc in [('old_share', False), ('evening', True), ('sun_ratio', True), ('old_dec_sep', True)]: g['R_' + c] = g.groupby('city')[c].rank(ascending=asc)
g['터전점수'] = g[[c for c in g if c.startswith('R_')]].mean(axis=1); g['터전순위'] = g.groupby('city')['터전점수'].rank(method='first').astype(int)
st = []
for c in ['춘천', '강남']:
    x = sh.loc[c]; rk = x.rank(ascending=False); cor = rk.corr(method='spearman'); st.append((c, len(x), round(cor.values[np.triu_indices(6, 1)].min(), 3), round(cor.values[np.triu_indices(6, 1)].mean(), 3), int((rk.loc[rk.mean(axis=1).nsmallest(5).index] <= 5).all(axis=1).sum())))
S = pd.DataFrame(st, columns=['도시', '동 수', '월별 순위 상관 최솟값', '평균', '상위 5개 동 중 6개월 내내 5위 안']); print(S.to_string(index=False)); S.to_csv('balgil/out/dong_stability.csv', index=False, encoding='utf-8-sig')
o = g[['city', 'dong', 'name', 'old_daily', 'old_share', 'old_female', 'sun_ratio', 'evening', 'old_dec_sep', '터전점수', '터전순위']].sort_values(['city', '터전순위']).round(3)
o.columns = ['도시', '행정동코드', '이름(추정)', '60대 이상 규모', '60대 이상 비중', '여성 비중', '일요일÷평일', '저녁 비중', '12월÷9월', '터전 점수(통신)', '순위']
for c in ['체류 업종 가게 수(상가정보)', '65세 이상 1인세대(행안부)', '경로당·복지관 수(표준데이터)']: o[c] = '미확보'
print(o.groupby('도시').head(7).to_string(index=False)); o.to_csv('balgil/out/features_dong.csv', index=False, encoding='utf-8-sig')
for c in ['춘천', '강남']:
    x = g[g.city == c]; print(c, '60대 이상 비중 범위 %.2f~%.2f | 비중~저녁 r=%.2f | 비중~일요일 r=%.2f' % (x.old_share.min(), x.old_share.max(), np.corrcoef(x.old_share, x.evening)[0, 1], np.corrcoef(x.old_share, x.sun_ratio)[0, 1]))
