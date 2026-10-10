"""b2. 연속성 — 끊김 판정, 보정 전·후 헛경보, 주황/빨강 구분, 종결 2층 (트랙 B3·모델 ④)
집단: 도시 × 성별 × 연령(60대·70대·80대) 12개.  발길 종류: 대면(체류+식사) / 필수(장보기·병원·약국)
7일 창. 보정 3단계를 차례로 켠다:
  (0) 보정 없음: 6개월 평균 대비      (1) 계절형 보정: 앞뒤 4주 같은 요일 중앙값 대비
  (2) 공통 충격 보정: (1)에서 같은 도시 30·40대의 같은 종류 발길 편차를 뺌 → 어르신만의 끊김
끊김 = 편차가 평소 흔들림(강건 표준편차)의 3배 이상 아래.  주황 = 대면만 끊김, 빨강 = 필수까지 끊김.
출력: data/processed/reanalysis/nomed_break_daily.csv, break_summary.csv, false_alarm.csv, closure.csv
"""
import sys; sys.path.insert(0, __import__('os').path.dirname(__file__)); from b0_common import *
import warnings; warnings.filterwarnings('ignore'); pd.set_option('display.width', 230)
r, d1 = load(); r['kind'] = np.where(r.ind.isin(STAY + MEAL), '대면', np.where(r.ind.isin([i for i in ESS if i not in MED]), '필수', '기타'))
r['band'] = r.AGE.map({'30대': '3040', '40대': '3040', '60대': '60대', '70대': '70대', '80대': '80대'}); r = r.dropna(subset=['band'])
def roll(s): return s.rolling(7, min_periods=7).sum()
def zs(x, mask):
    n = x[mask].dropna(); sd = 1.4826 * (n - n.median()).abs().median(); return (x - n.median()) / sd
normal = ~pd.Series(DAYS, index=DAYS).isin(HOL) & ~pd.Series(DAYS, index=DAYS).isin(pd.date_range('2025-10-03', '2025-10-15'))
rows = []
for c in ['춘천', '강남']:
    ref = {k: r[(r.city == c) & (r.band == '3040') & (r.kind == k)].groupby('date').cnt.sum().reindex(DAYS).fillna(0) for k in ['대면', '필수']}
    refd = {k: np.log(roll(ref[k]) / roll(base(ref[k]))) for k in ref}
    for sx in ['남성', '여성']:
        for b in ['60대', '70대', '80대']:
            o = {}
            for k in ['대면', '필수']:
                s = r[(r.city == c) & (r.sex == sx) & (r.band == b) & (r.kind == k)].groupby('date').cnt.sum().reindex(DAYS).fillna(0)
                d0 = np.log(roll(s) / (s.mean() * 7)); d1_ = np.log(roll(s) / roll(base(s))); d2_ = d1_ - refd[k]
                o[k] = pd.DataFrame({'d0': d0, 'd1': d1_, 'd2': d2_, 'z0': zs(d0, normal), 'z1': zs(d1_, normal), 'z2': zs(d2_, normal)})
            x = o['대면'].add_prefix('f_').join(o['필수'].add_prefix('e_')); x['city'], x['sex'], x['band'], x['date'] = c, sx, b, DAYS; rows.append(x.dropna(subset=['f_z2']))
B = pd.concat(rows).reset_index(drop=True); B['seg'] = B.city + ' ' + B.sex.str[0] + ' ' + B.band; B['holwk'] = B.date.isin(pd.date_range('2025-10-03', '2025-10-12')) | B.date.isin(pd.date_range('2025-08-15', '2025-08-21')) | B.date.isin(pd.date_range('2025-12-25', '2025-12-31'))
for k in '012': B['al' + k] = (B['f_z' + k] <= -3) | (B['e_z' + k] <= -3)
B['state'] = np.where(B.e_z2 <= -3, '빨강(필수까지 끊김)', np.where(B.f_z2 <= -3, '주황(대면만 끊김)', '-'))
B.round(4).to_csv(OUT / 'nomed_break_daily.csv', index=False, encoding='utf-8-sig')
# 헛경보: 보정 단계별 알림(집단×일) 수
fa = pd.DataFrame({'전체 알림': [int(B['al' + k].sum()) for k in '012'], '공통 사건 주간(추석·광복절·성탄 뒤 7일) 알림': [int((B['al' + k] & B.holwk).sum()) for k in '012'], '그 밖의 날 알림': [int((B['al' + k] & ~B.holwk).sum()) for k in '012']}, index=['(0) 보정 없음', '(1) 계절형 보정', '(2) + 공통 충격 보정'])
fa['공통 사건 주간 감소율(%)'] = (1 - fa.iloc[:, 1] / fa.iloc[0, 1]).mul(100).round(0); print('■ 보정 전·후 알림 수 (12개 집단 × 178일 = %d)' % len(B)); print(fa.to_string()); fa.to_csv(OUT / 'nomed_false_alarm.csv', encoding='utf-8-sig')
print('  추석 주간(10/6~12) 알림: 보정 없음', int((B.al0 & B.date.between('2025-10-06', '2025-10-12')).sum()), '/ 84 → 계절형', int((B.al1 & B.date.between('2025-10-06', '2025-10-12')).sum()), '→ 공통 충격', int((B.al2 & B.date.between('2025-10-06', '2025-10-12')).sum()))
# 집단별 요약
S = B.groupby('seg').agg(주황=('state', lambda x: (x == '주황(대면만 끊김)').sum()), 빨강=('state', lambda x: (x == '빨강(필수까지 끊김)').sum()), 대면흔들림=('f_d2', lambda x: round(1.4826 * (x - x.median()).abs().median(), 3)), 필수흔들림=('e_d2', lambda x: round(1.4826 * (x - x.median()).abs().median(), 3)))
print('■ 집단별 끊김 일수(보정 후, 178일 중)'); print(S.to_string()); S.to_csv(OUT / 'nomed_break_summary.csv', encoding='utf-8-sig')
# 끊김 구간(에피소드)과 종결 2층
ep = []
for seg, x in B.groupby('seg'):
    x = x.set_index('date'); a = x[x.state != '-']
    if a.empty: continue
    blk = (a.index.to_series().diff().dt.days > 3).cumsum()
    for _, e in a.groupby(blk):
        end = e.index.max(); after = x.loc[end + pd.Timedelta(days=1):]
        ess_back = after[after.e_z2 > -1].index.min(); face_back = after[after.f_z2 > -1].index.min()
        ep.append((seg, e.index.min().date(), end.date(), len(e), e.state.mode()[0], round((np.exp(e.f_d2.min()) - 1) * 100), round((np.exp(e.e_d2.min()) - 1) * 100),
                   (ess_back - end).days if pd.notna(ess_back) else None, (face_back - end).days if pd.notna(face_back) else None))
E_ = pd.DataFrame(ep, columns=['집단', '시작', '끝', '일수', '상태', '대면 최저(%)', '필수 최저(%)', '필수 복귀까지(일)', '대면 복귀까지(일)'])
E_['판정'] = np.where(E_['대면 복귀까지(일)'].isna() | (E_['대면 복귀까지(일)'] > E_['필수 복귀까지(일)'].fillna(0) + 7), '필수만 복귀 → 미해소(노랑 유지)', '함께 복귀 → 해소')
print('■ 끊김 구간과 종결 (%d건)' % len(E_)); print(E_.to_string(index=False)); E_.to_csv(OUT / 'nomed_closure.csv', index=False, encoding='utf-8-sig')
print('  구간 수', len(E_), '| 공휴일 주간과 겹치는 구간', int(E_.apply(lambda q: any(pd.Timestamp(q['시작']) <= h + pd.Timedelta(days=7) and pd.Timestamp(q['끝']) >= h for h in HOL), axis=1).sum()), '| 판정:', E_['판정'].value_counts().to_dict())
