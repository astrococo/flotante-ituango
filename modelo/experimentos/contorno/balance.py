import pandas as pd, numpy as np, json, warnings; warnings.filterwarnings('ignore')
exec(open('/home/claude/work/q30/bateria.py').read().split("# ---------- A.")[0])
J=json.load(open('/home/claude/work/site/datos/satelite/contorno/serie.json'))
def df(src):
    R=pd.DataFrame.from_dict(J.get(src) or {},orient='index')
    if len(R): R.index=pd.to_datetime(R.index)
    return R.sort_index()
S=df('optico')
for X in (df('landsat'),df('radar')):
    if len(X): S=S.combine_first(X)
dn0='t'+[t for t in J['tramos'] if float(t.split('..')[0])>=0][0].replace('..','_')
def semanal(col):
    r=S[col].dropna(); r=r[r.index>=I0]
    d=pd.Series(np.nan,index=pd.date_range(r.index.min(),r.index.max())); d[r.index]=r.values
    gap=pd.Series(r.index,index=r.index).diff().dt.days.reindex(d.index).bfill()
    return d.interpolate().where(gap<=21).resample('W-SUN').last()
K=round(11.8*1e4/160,1)
ret,dn,arr=semanal('ret'),semanal(dn0),semanal('arriba')
Wd=D[I0:I1]; E=(Wd.mf_tot+Wd.ma_tot).resample('W-SUN').sum()
q=D.sitiopresa_f; qm=q.resample('W-SUN').mean(); d23=(q>2300).resample('W-SUN').sum()
X=pd.concat([E.rename('E'),ret.diff().rename('dr'),dn.diff().rename('dd'),arr.diff().rename('da'),qm.rename('q'),d23.rename('d23')],axis=1).dropna()
X['acu']=X.dr*K; X['pasa']=X.dd*K; X['lleg']=X.E+X.acu+X.pasa; X['acuA']=X.da*K; X['llegA']=X.E+X.acuA+X.pasa
X['grupo']=np.where(X.d23>0,'alta',np.where(X.q>=1500,'media','baja'))
G=X.groupby('grupo').agg(n=('E','size'),q=('q','mean'),E=('E','mean'),acu=('acu','mean'),pasa=('pasa','mean'),lleg=('lleg','mean'),acuA=('acuA','mean'),llegA=('llegA','mean')).round(0)
print(G); print('semanas',len(X),X.index.min().date(),X.index.max().date())
rng=np.random.default_rng(1); a=X[X.grupo=='alta']; b=X[X.grupo!='alta']
def ic(col):
    bs=[a[col].sample(len(a),replace=True,random_state=rng.integers(1e9)).mean()-b[col].sample(len(b),replace=True,random_state=rng.integers(1e9)).mean() for _ in range(4000)]
    return [round(float(np.percentile(bs,5))),round(float(np.percentile(bs,95)))]
dif={c:dict(dif=round(float(a[c].mean()-b[c].mean())),ic90=ic(c)) for c in ['E','acu','pasa','lleg','acuA','llegA']}
print(dif)
# relación con el caudal (desplazamiento circular)
rel={}
for nm,col in [('extraido','E'),('llegada','lleg'),('llegada_contorno','llegA')]:
    r,p,n=shift_test(X.q.apply(np.log),X[col]); rel[nm]=dict(r=round(float(r),3),p=p,n=n)
print(rel)
json.dump(dict(kappa=K,tramo_abajo=dn0,grupos={g:{k:float(v) for k,v in r.items()} for g,r in G.iterrows()},dif_alta_vs_resto=dif,rel_caudal=rel,n=len(X),
  desde=str(X.index.min().date()),hasta=str(X.index.max().date())),open('/home/claude/work/q31/balance.json','w'),indent=1)
