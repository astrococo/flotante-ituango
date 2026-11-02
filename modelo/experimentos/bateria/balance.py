import pandas as pd, numpy as np, json, warnings; warnings.filterwarnings('ignore')
exec(open('/home/claude/work/q30/bateria.py').read().split("# ---------- A.")[0])
J=json.load(open('/home/claude/work/site/datos/satelite/retenido/serie.json'))
def df(src):
    R=pd.DataFrame.from_dict(J.get(src) or {},orient='index')
    if len(R): R.index=pd.to_datetime(R.index)
    return R.sort_index()
O=df('optico'); Rr=df('radar'); S=O.combine_first(Rr) if len(Rr) else O
r=S['ret'].dropna(); r=r[r.index>=I0]
# serie diaria interpolada solo entre observaciones separadas ≤ 21 días
d=pd.Series(np.nan,index=pd.date_range(r.index.min(),r.index.max())); d[r.index]=r.values
gap=pd.Series(r.index,index=r.index).diff().dt.days.reindex(d.index).bfill()
di=d.interpolate().where(gap<=21)
wk=di.resample('W-SUN').last(); dret=wk.diff()   # ha/semana
Wd=D[I0:I1]; E=pd.DataFrame({'mf':Wd.mf_tot.resample('W-SUN').sum(),'ma':Wd.ma_tot.resample('W-SUN').sum()}); E['tot']=E.mf+E.ma
q=D.sitiopresa_f; lq=np.log(q); anq=(lq-lq.rolling(365,min_periods=180).median()).ewm(halflife=7).mean().resample('W-SUN').last()
d23=(q>2300).resample('W-SUN').sum()
X=pd.concat([E.tot,dret.rename('dret'),anq.rename('q'),d23.rename('d23'),wk.rename('ret')],axis=1).dropna()
print('semanas con balance:',len(X), X.index.min().date(), X.index.max().date())
print('extraccion semanal mediana m3:',X.tot.median(), ' |Δret| mediana ha:',X.dret.abs().median(), ' p90:',X.dret.abs().quantile(.9))
out={}
for k in [0,238,738,2550]:
    arr=X.tot+k*X.dret
    r1,p1,n1=shift_test(X.q,arr); r2,p2,n2=shift_test(X.d23,arr)
    out[k]=dict(r_q=round(r1,3),p_q=p1,r_d23=round(r2,3),p_d23=p2,n=n1,frac_var=round(float((k*X.dret).var()/arr.var()),3))
    print(k,out[k])
json.dump(dict(n=len(X),kappa=out),open('/home/claude/work/q30/balance.json','w'),indent=1)
