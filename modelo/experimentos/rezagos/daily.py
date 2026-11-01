exec(open('/home/claude/work/q28/base.py').read())
from statsmodels.tsa.ar_model import AutoReg
res={}
D=d[I0:I1].copy()
doy=D.index.dayofyear
def anom(s):
    l=np.log(s); return l-l.groupby(doy).transform(lambda v: v.rolling(1).median()).groupby(doy).transform('median')
y=np.log(D.mf_tot.where(D.mf_tot>0)); y=y-y.rolling(91,center=True,min_periods=30).median()   # quita nivel lento (esfuerzo, estación)
for st in ['olaya','sitiopresa','virginia']:
    x=np.log(D[st]).interpolate(limit=5); x=x-x.rolling(91,center=True,min_periods=30).median()
    ok=x.notna(); m=AutoReg(x[ok].values,lags=3,trend='c').fit(); ph=m.params
    xe=pd.Series(np.nan,index=x.index); xe[ok]=np.r_[np.full(3,np.nan),m.resid]
    yf=y-ph[1]*y.shift(1)-ph[2]*y.shift(2)-ph[3]*y.shift(3)
    out=[]
    for L in range(-7,57):
        z=pd.concat([xe.shift(L),yf],axis=1).dropna(); n=len(z)
        out.append(dict(L=L,r=float(np.corrcoef(z.iloc[:,0],z.iloc[:,1])[0,1]),n=n))
    O=pd.DataFrame(out); O['lim']=1.96/np.sqrt(O.n)
    # suma por semanas de rezago (respuesta acumulada)
    O['sem']=np.floor(O.L/7).astype(int)
    S=O.groupby('sem').r.sum()
    res[st]=dict(diario=[dict(L=int(r.L),r=round(r.r,3)) for r in O.itertuples()],lim95=round(float(O.lim.mean()),3),suma_semana={int(k):round(float(v),3) for k,v in S.items()})
    sig=O[abs(O.r)>O.lim]
    print(st,'lim',round(O.lim.mean(),3),'| significativos:',', '.join(f"{int(r.L)}d {r.r:+.2f}" for r in sig.itertuples()))
    print('   suma por semana de rezago',{int(k):round(v,2) for k,v in S.items()})
json.dump(res,open('/home/claude/work/q28/ccf_diario.json','w'),indent=1)
