exec(open('/home/claude/work/q28/base.py').read())
from statsmodels.tsa.ar_model import AutoReg
res={}
# ---------- semanal: anomalías log, preblanqueo con AR(p) del caudal ----------
W=pd.DataFrame({'mf':d.mf_tot.resample('W-SUN').sum(),'act':d.act.resample('W-SUN').sum(),'op':d.opd.resample('W-SUN').min(),'n':d.opd.resample('W-SUN').size()})
for c in ['olaya','sitiopresa_f','virginia','bolombolo','pintada']:
    W[c]=d[c].resample('W-SUN').mean(); W[c+'_max']=d[c].resample('W-SUN').max()
W=W[(W.n==7)]
W['rate']=np.where(W.act>=2,W.mf/W.act,np.nan)
def anom(s):  # log y quitar estacionalidad (mediana por semana del año) 
    l=np.log(s); woy=s.index.isocalendar().week.values; clim=l.groupby(woy).transform('median'); return l-clim
for per,(a,b) in {'oct2021-2026':(I0,I1),'2019-2026':(pd.Timestamp('2019-08-01'),I1)}.items():
    w=W[a:b].copy()
    yv=anom(w.rate.where(w.op==1))
    for st in ['olaya','sitiopresa_f','virginia','bolombolo','pintada']:
        x=anom(w[st+'_max']).interpolate(limit=2)
        ok=x.notna()
        m=AutoReg(x[ok].values,lags=2,trend='c').fit()
        xe=pd.Series(np.nan,index=x.index); xe[ok]=np.r_[np.full(2,np.nan),m.resid]
        # filtrar y con el mismo AR
        ph=m.params; yf=yv-ph[1]*yv.shift(1)-ph[2]*yv.shift(2)
        out=[]
        for L in range(-2,11):
            z=pd.concat([xe.shift(L),yf],axis=1).dropna(); n=len(z)
            r=float(np.corrcoef(z.iloc[:,0],z.iloc[:,1])[0,1]) if n>20 else np.nan
            out.append(dict(rezago_sem=L,r=round(r,3),n=n,lim95=round(1.96/np.sqrt(n),3)))
        res[f'{per}|{st}']=out
        print(per,st,' '.join(f"{o['rezago_sem']}:{o['r']:+.2f}{'*' if abs(o['r'])>o['lim95'] else ''}" for o in out))
json.dump(res,open('/home/claude/work/q28/ccf_semanal.json','w'),indent=1)
W.to_pickle('/home/claude/work/q28/W.pkl')
