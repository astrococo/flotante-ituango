import pandas as pd, numpy as np, json, warnings; warnings.filterwarnings('ignore')
import statsmodels.api as sm
from scipy.stats import spearmanr
D=pd.read_pickle('/home/claude/work/q29/D.pkl'); D['mec']=D.mf_mec+D.ma_mec
exec(open('/home/claude/work/prep.py').read().split('d=df.join')[0]); qall=q.sitiopresa_f
lqa=np.log(qall); anqa=lqa-lqa.rolling(365,min_periods=180).median()
q=D.sitiopresa_f; anq=anqa.reindex(D.index); ewa42=anqa.ewm(halflife=42).mean(); ewa56=anqa.ewm(halflife=56).mean()
W=pd.DataFrame({'mf':D.mf_mec.resample('W-SUN').sum()+D.mf_man.resample('W-SUN').sum(),'mfm':D.mf_mec.resample('W-SUN').sum(),'mec':D.mec.resample('W-SUN').sum(),
  'dop':D.op_mec.resample('W-SUN').sum(),'vq':(D.volquetas*D.op_mec).resample('W-SUN').sum(),
  'd2300':(q>2300).resample('W-SUN').sum(),'d1866':((q>1866)&(q<=2300)).resample('W-SUN').sum(),
  'qw':anq.resample('W-SUN').mean(),'ew42':ewa42.reindex(D.index).resample('W-SUN').last(),'ew56':ewa56.reindex(D.index).resample('W-SUN').last(),
  'n':D.op_mec.resample('W-SUN').size()})
W=W[(W.n==7)]
W['fix']=(W.index>='2026-04-01')&(W.index<='2026-10-04')
W['y']=np.log(W.mf+50); W['lvq']=np.log(W.vq+1)
W['m']=W.index.month; S=pd.get_dummies(W.m,prefix='m',drop_first=True).astype(float)
W=pd.concat([W,S],axis=1)
tr=W[(W.index<'2025-01-01')&~W.fix]; te=W[(W.index>='2025-01-01')&~W.fix]
def fit(cols,name):
    X=sm.add_constant(tr[cols]); m=sm.OLS(tr.y,X).fit(cov_type='HAC',cov_kwds={'maxlags':3})
    pt=m.predict(sm.add_constant(te[cols],has_constant='add'))
    r_tr=np.corrcoef(m.fittedvalues,tr.y)[0,1]; r_te=np.corrcoef(pt,te.y)[0,1]
    print(f'{name:55s} r ent {r_tr:.2f}  r val {r_te:.2f}  R² val {r_te**2:.2f}')
    return m,r_tr,r_te
res={}
print('ρ simple caudal semanal vs MF semanal (ent):',round(spearmanr(tr.qw,tr.mf)[0],2),' (val):',round(spearmanr(te.qw,te.mf)[0],2))
for name,cols in [('solo caudal de la semana',['qw']),
                  ('caudal: parada (días >2.300 y 1.866–2.300)',['d2300','d1866']),
                  ('caudal: parada + llegada (media exp. 42 d)',['d2300','d1866','ew42']),
                  ('caudal: parada + llegada (56 d)',['d2300','d1866','ew56']),
                  ('esfuerzo (volqueta-días)',['lvq']),
                  ('esfuerzo + caudal (parada + llegada 56 d)',['lvq','d2300','d1866','ew56']),
                  ('esfuerzo + caudal + mes',['lvq','d2300','d1866','ew56']+list(S.columns))]:
    m,a,b=fit(cols,name); res[name]=dict(r_ent=round(a,3),r_val=round(b,3),coef={k:round(float(v),3) for k,v in m.params.items() if not k.startswith('m_')},p={k:round(float(v),3) for k,v in m.pvalues.items() if not k.startswith('m_')})
print(json.dumps(res['esfuerzo + caudal (parada + llegada 56 d)'],ensure_ascii=False))
print(json.dumps(res['caudal: parada + llegada (56 d)'],ensure_ascii=False))
json.dump(res,open('/home/claude/work/q29/reg.json','w'),indent=1,ensure_ascii=False); W.to_pickle('/home/claude/work/q29/Wreg.pkl')
