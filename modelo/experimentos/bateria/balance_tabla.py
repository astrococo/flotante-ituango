import pandas as pd, numpy as np, json, warnings; warnings.filterwarnings('ignore')
exec(open('/home/claude/work/q30/bateria.py').read().split("# ---------- A.")[0])
J=json.load(open('/home/claude/work/site/datos/satelite/retenido/serie.json'))
def df(src):
    R=pd.DataFrame.from_dict(J.get(src) or {},orient='index'); R.index=pd.to_datetime(R.index); return R.sort_index()
S=df('optico').combine_first(df('radar'))
def semanal(col):
    r=S[col].dropna(); r=r[r.index>=I0]
    d=pd.Series(np.nan,index=pd.date_range(r.index.min(),r.index.max())); d[r.index]=r.values
    gap=pd.Series(r.index,index=r.index).diff().dt.days.reindex(d.index).bfill()
    return d.interpolate().where(gap<=21).resample('W-SUN').last()
K=round(11.8*1e4/160,1)
ret=semanal('ret'); dn=semanal('t0_2.5')
Wd=D[I0:I1]; E=(Wd.mf_tot+Wd.ma_tot).resample('W-SUN').sum()
q=D.sitiopresa_f; qm=q.resample('W-SUN').mean(); d23=(q>2300).resample('W-SUN').sum()
X=pd.concat([E.rename('E'),ret.diff().rename('dr'),dn.diff().rename('dd'),qm.rename('q'),d23.rename('d23'),ret.rename('ret'),dn.rename('dn')],axis=1).dropna()
X['acu']=X.dr*K; X['pasa']=X.dd*K; X['lleg']=X.E+X.acu+X.pasa
X['grupo']=np.where(X.d23>0,'alta',np.where(X.q>=1500,'media','baja'))
G=X.groupby('grupo').agg(n=('E','size'),q=('q','mean'),E=('E','mean'),acu=('acu','mean'),pasa=('pasa','mean'),lleg=('lleg','mean')).round(0)
print(G); print('total',len(X),X.index.min().date(),X.index.max().date())
# diferencias alta vs resto, bootstrap IC
rng=np.random.default_rng(1); a=X[X.grupo=='alta']; b=X[X.grupo!='alta']
def ic(col):
    bs=[a[col].sample(len(a),replace=True,random_state=rng.integers(1e9)).mean()-b[col].sample(len(b),replace=True,random_state=rng.integers(1e9)).mean() for _ in range(4000)]
    return [round(float(np.percentile(bs,5))),round(float(np.percentile(bs,95)))]
dif={c:dict(dif=round(float(a[c].mean()-b[c].mean())),ic90=ic(c)) for c in ['E','acu','pasa','lleg']}
print(dif)
# ejemplo: semana alta con más días > 2300
ej=a.sort_values(['d23','q'],ascending=False).head(3); print(ej[['q','d23','E','ret','dr','dn','dd','acu','pasa','lleg']].round(1))
out=dict(kappa=K,grupos={g:{k:float(v) for k,v in r.items()} for g,r in G.iterrows()},dif_alta_vs_resto=dif,n=len(X),desde=str(X.index.min().date()),hasta=str(X.index.max().date()),
  ejemplos=[dict(semana=str(i.date()),q=round(r.q),d23=int(r.d23),E=round(r.E),ret0=round(r.ret-r.dr,1),ret1=round(r.ret,1),dn0=round(r.dn-r.dd,1),dn1=round(r.dn,1),acu=round(r.acu),pasa=round(r.pasa),lleg=round(r.lleg)) for i,r in ej.iterrows()])
json.dump(out,open('/home/claude/work/q30/balance_tabla.json','w'),indent=1)
