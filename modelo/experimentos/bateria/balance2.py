import pandas as pd, numpy as np, json, warnings; warnings.filterwarnings('ignore')
exec(open('/home/claude/work/q30/bateria.py').read().split("# ---------- A.")[0])
J=json.load(open('/home/claude/work/site/datos/satelite/retenido/serie.json'))
def df(src):
    R=pd.DataFrame.from_dict(J.get(src) or {},orient='index'); R.index=pd.to_datetime(R.index); return R.sort_index()
O=df('optico'); Rr=df('radar'); S=O.combine_first(Rr)
def semanal(col):
    r=S[col].dropna(); r=r[r.index>=I0]
    d=pd.Series(np.nan,index=pd.date_range(r.index.min(),r.index.max())); d[r.index]=r.values
    gap=pd.Series(r.index,index=r.index).diff().dt.days.reindex(d.index).bfill()
    return d.interpolate().where(gap<=21).resample('W-SUN').last()
ret=semanal('ret'); dn=semanal('t0_2.5')
Wd=D[I0:I1]; E=(Wd.mf_tot+Wd.ma_tot).resample('W-SUN').sum()
q=D.sitiopresa_f; lq=np.log(q); anq=(lq-lq.rolling(365,min_periods=180).median()).ewm(halflife=7).mean().resample('W-SUN').last()
X=pd.concat([E.rename('E'),ret.diff().rename('dr'),dn.diff().rename('dd'),anq.rename('q')],axis=1).dropna()
res={}
for k in [0,238,738,2550]:
    a=X.E+k*(X.dr+X.dd); r,p,n=shift_test(X.q,a); res[k]=dict(r=round(r,3),p=p,n=n); print('ret+aguas abajo',k,res[k])
# riesgo: ocupación de la barrera
b=S['bar'].dropna(); b=b[b.index>='2019-07-01']; p90=b.quantile(.9); p75=b.quantile(.75)
qd=q.reindex(b.index)
alto=b>=p90
print('bar mediana',b.median(),'P75',p75,'P90',p90,'n',len(b))
print('P(bar≥P90 | Q>2300)',alto[qd>2300].mean(),len(alto[qd>2300]),' P(bar≥P90 | Q≤2300)',alto[qd<=2300].mean())
yr=b.groupby(b.index.year).agg(['median',lambda x:(x>=p90).mean(),'count']); print(yr)
json.dump(dict(balance_ret_abajo=res,bar=dict(mediana=round(b.median(),1),p75=round(p75,1),p90=round(p90,1),n=len(b),
   p_alto_q_alto=round(float(alto[qd>2300].mean()),3),n_q_alto=int((qd>2300).sum()),p_alto_q_bajo=round(float(alto[qd<=2300].mean()),3))),open('/home/claude/work/q30/balance2.json','w'),indent=1)
