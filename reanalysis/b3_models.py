"""b3. 모델 재실행 (트랙 B1) — 발길 지표로
① 좁아짐 분류: 32칸 × 26주(지표 패널 36칸에서 90대 4칸 제외). 주마다 양(유효 발길 수)·질(체류 비중)을 나이 보정해 좁아짐 점수를 만들고,
   '다음 주에 좁아짐 상위 7칸(32칸의 21.9%)에 드는가'를 맞힌다. 기준선(이번 주 그대로) / 로지스틱 / 랜덤포레스트.
   평가: 시간순 분할(마지막 4주)과 칸을 통째로 빼는 교차검증. 핵심은 '새로 들어오는 칸'을 미리 잡는가.
② 발길 예상: 60대 이상 12개 집단의 하루 대면 발길(체류+식사). 과거만 쓰는 기준선(지난 4주 같은 요일 중앙값) 대 그래디언트 부스팅.
출력: data/processed/reanalysis/weekly_panel.csv, model_score.csv, forecast_score.csv
"""
import sys; sys.path.insert(0, __import__('os').path.dirname(__file__)); from b0_common import *
import warnings; warnings.filterwarnings('ignore'); pd.set_option('display.width', 250)
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor
from sklearn.metrics import roc_auc_score, f1_score, precision_score, recall_score
r, d1 = load(); wk = lambda s: (s - pd.Timestamp('2025-06-30')).dt.days // 7
r['w'] = wk(r.date); d1['w'] = wk(d1.date); K = ['city', 'sex', 'AGE']; keep = [a for a in AGES if a != '90대']
r = r[r.AGE.isin(keep)]; d1 = d1[d1.AGE.isin(keep)]; rows = []
for w in range(26):
    I = adjust(faces(r[r.w == w], d1[d1.w == w], K)); I['w'] = w; rows.append(I)
P = pd.concat(rows, ignore_index=True); P['seg'] = P.city + ' ' + P.sex + ' ' + P.AGE; P['old'] = P.AGE.isin(['60대', '70대', '80대'])
P['top'] = (P.groupby('w').narrow.rank(ascending=False) <= 7).astype(int); P = P.sort_values(['seg', 'w'])
for c in ['narrow', 'stay_z', 'breadth_z']: P['d_' + c] = P.groupby('seg')[c].diff().fillna(0)
P['m3'] = P.groupby('seg').narrow.transform(lambda x: x.rolling(3, min_periods=1).mean()); P['y'] = P.groupby('seg').top.shift(-1)
P.round(4).to_csv(OUT / 'weekly_panel.csv', index=False, encoding='utf-8-sig'); D = P.dropna(subset=['y']).copy(); D['y'] = D.y.astype(int)
F = ['breadth_z', 'stay_z', 'narrow', 'd_narrow', 'd_stay_z', 'd_breadth_z', 'm3', 'meal', 'anon', 'med', 'evening']
print('표본', len(D), '| 양성', round(D.y.mean(), 3), '| 새로 들어옴', int(((D.top == 0) & (D.y == 1)).sum()), '| 빠져나감', int(((D.top == 1) & (D.y == 0)).sum()))
def ev(te, p, name, tag):
    yh = (p >= .5).astype(int); new = (te.top == 0).values
    return dict(평가=tag, 모델=name, AUC=roc_auc_score(te.y, p), F1=f1_score(te.y, yh), 정밀도=precision_score(te.y, yh, zero_division=0), 재현율=recall_score(te.y, yh),
                새진입=int((new & (te.y == 1)).sum()), 새진입_잡음=int((new & (te.y == 1) & (yh == 1)).sum()), 새진입_AUC=roc_auc_score(te.y[new], p[new]) if te.y[new].nunique() > 1 else np.nan, 경보=int(yh.sum()))
LR = lambda: LogisticRegression(class_weight='balanced', max_iter=2000); RF = lambda: RandomForestClassifier(n_estimators=300, min_samples_leaf=5, class_weight='balanced', random_state=0)
from sklearn.preprocessing import StandardScaler; from sklearn.pipeline import make_pipeline
out = []; tr, te = D[D.w <= 20], D[D.w > 20]
out.append(ev(te, te.top.values.astype(float), '기준선(이번 주 그대로)', '마지막 4주'))
for n, m in [('로지스틱', make_pipeline(StandardScaler(), LR())), ('랜덤포레스트', RF())]: out.append(ev(te, m.fit(tr[F], tr.y).predict_proba(te[F])[:, 1], n, '마지막 4주'))
ps = {'로지스틱': np.zeros(len(D)), '랜덤포레스트': np.zeros(len(D))}
for s in D.seg.unique():
    i = (D.seg == s).values
    ps['로지스틱'][i] = make_pipeline(StandardScaler(), LR()).fit(D[~i][F], D[~i].y).predict_proba(D[i][F])[:, 1]; ps['랜덤포레스트'][i] = RF().fit(D[~i][F], D[~i].y).predict_proba(D[i][F])[:, 1]
out.append(ev(D, D.top.values.astype(float), '기준선(이번 주 그대로)', '칸 통째로 빼기'))
for n in ps: out.append(ev(D, ps[n], n, '칸 통째로 빼기'))
O = D[D.old]; io = D.old.values; out.append(ev(O, O.top.values.astype(float), '기준선(이번 주 그대로)', '60대 이상 12칸만'))
for n in ps: out.append(ev(O, ps[n][io], n, '60대 이상 12칸만'))
R = pd.DataFrame(out); print(R.round(3).to_string(index=False)); R.round(4).to_csv(OUT / 'model_score.csv', index=False, encoding='utf-8-sig')
rng = np.random.default_rng(0); segs = D.seg.unique(); dif = []
for _ in range(1000):
    pick = rng.choice(segs, len(segs)); idx = np.concatenate([np.where(D.seg.values == s)[0] for s in pick]); y = D.y.values[idx]
    if len(set(y)) < 2: continue
    dif.append(roc_auc_score(y, ps['랜덤포레스트'][idx]) - roc_auc_score(y, D.top.values[idx].astype(float)))
print('AUC 차이(랜덤포레스트−기준선) 95%% 구간: %.3f ~ %.3f' % tuple(np.percentile(dif, [2.5, 97.5])))
rf = RF().fit(D[F], D.y); print('중요도:', dict(sorted(zip(F, rf.feature_importances_.round(3)), key=lambda x: -x[1])))
# 주별 60대 이상 좁아짐 순위 안정성
Po = P[P.old].copy(); Po['rk'] = Po.groupby('w').narrow.rank(ascending=False)
st = Po.groupby('seg').agg(평균순위=('rk', 'mean'), 상위3위_주수=('rk', lambda x: (x <= 3).sum()), 체류비중=('stay', 'mean')).sort_values('평균순위').round(2); print('■ 60대 이상 12칸 안 좁아짐 순위(26주)'); print(st.to_string()); st.to_csv(OUT / 'old_rank_weekly.csv', encoding='utf-8-sig')
# ② 발길 예상
r['band'] = r.AGE.where(r.AGE.isin(['60대', '70대', '80대'])); f = r[r.band.notna() & r.ind.isin(STAY + MEAL)]; fc = []
for (c, sx, b), g in f.groupby(['city', 'sex', 'band']):
    s = g.groupby('date').cnt.sum().reindex(DAYS).fillna(0); X = pd.DataFrame({'y': s})
    X['b4'] = pd.concat([s.shift(7 * i) for i in range(1, 5)], axis=1).median(axis=1); X['l7'] = s.shift(7); X['l14'] = s.shift(14); X['r7'] = s.shift(1).rolling(7).mean(); X['dow'] = X.index.dayofweek; X['hol'] = X.index.isin(HOL).astype(int); X['dom'] = X.index.day
    X = X.dropna(); tr, te = X[X.index < '2025-11-15'], X[X.index >= '2025-11-15']; FF = ['b4', 'l7', 'l14', 'r7', 'dow', 'hol', 'dom']
    p = GradientBoostingRegressor(n_estimators=200, max_depth=3, learning_rate=.05, random_state=0).fit(tr[FF], tr.y).predict(te[FF]); nh = te.hol == 0
    fc.append((c, sx, b, round(te.y.mean()), (te.y - te.b4).abs().div(te.y)[nh].mean() * 100, (te.y - p).__abs__().div(te.y)[nh].mean() * 100, (te.y - te.b4).abs()[nh].mean(), np.abs(te.y - p)[nh].mean()))
FC = pd.DataFrame(fc, columns=['도시', '성별', '연령', '하루 평균 건수', '기준선 MAPE', '부스팅 MAPE', '기준선 MAE', '부스팅 MAE']).round(1); print('■ 발길 예상(11/15~12/31, 공휴일 제외)'); print(FC.to_string(index=False)); print('중앙값 MAPE 기준선 %.1f / 부스팅 %.1f' % (FC['기준선 MAPE'].median(), FC['부스팅 MAPE'].median())); FC.to_csv(OUT / 'forecast_score.csv', index=False, encoding='utf-8-sig')
