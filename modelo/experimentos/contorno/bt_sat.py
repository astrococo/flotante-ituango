"""¿El inventario satelital aguas arriba (contorno) mejora el pronóstico semanal? Backtest v2.3 2022–2026, h 1–4, dejando fuera un año."""
import pandas as pd, numpy as np, json, warnings, sys; warnings.filterwarnings('ignore')
exec(open('/home/claude/work/bt.py').read())
rm=lambda a,b: float(np.sqrt(np.mean((np.asarray(a)-np.asarray(b))**2)))
gs=np.linspace(0,1,21); CFG={'mf_tot':dict(w1=0.0,s=0.25),'ma_tot':dict(w1=0.5,s=0.5)}; BB={}
for y,cf in CFG.items():
    B=pd.read_pickle(f'/home/claude/work/exp26/B_{y}.pkl').merge(backtest(y)[['o','h','mult']],on=['o','h'],how='inner')
    B['m']=np.clip(np.sqrt(B.mult),0.7,1.5); tr=B[B.o<'2024-01-01']
    a8={h:float(gs[np.argmin([rm(k*g.lvl8+(1-k)*g.ltm,g.y) for k in gs])]) for h,g in tr.groupby('h')}
    aew={h:float(gs[np.argmin([rm(k*g.ew+(1-k)*g.ltm,g.y) for k in gs])]) for h,g in tr.groupby('h')}
    v1=B.h.map(a8)*B.lvl8+(1-B.h.map(a8))*B.ltm; ewb=B.h.map(aew)*B.ew+(1-B.h.map(aew))*B.ltm
    B['nc']=(cf['w1']*v1+(1-cf['w1'])*((1-cf['s'])*ewb+cf['s']*B.ltm))*B.m
    BB[y]=B[(B.o>='2022-01-01')&(B.h<=4)][['o','h','y','nc']]
J=json.load(open('/home/claude/work/site/datos/satelite/contorno/serie.json'))
def df(s):
    R=pd.DataFrame.from_dict(J.get(s) or {},orient='index'); R.index=pd.to_datetime(R.index); return R.sort_index()
res={}
for var in ['arriba','ret','lejos']:
  for fuente in ['optico+landsat','con radar']:
    S=df('optico').combine_first(df('landsat'))
    if fuente=='con radar': S=S.combine_first(df('radar'))
    if var=='lejos':
        c=[k for k in S.columns if k.startswith('t-') and float(k[1:].split('_')[1])<=-10]; s=S[c].sum(axis=1,min_count=len(c)-1)
    else: s=S[var]
    s=s.dropna()
    def at(o):
        w=s[(s.index>o-pd.Timedelta(days=21))&(s.index<=o)]; h=s[(s.index>o-pd.Timedelta(days=365))&(s.index<=o)]
        if not len(w) or len(h)<10: return np.nan
        return np.log((w.iloc[-1]+2)/(h.median()+2))
    for y in ['mf_tot','ma_tot']:
        B=BB[y].copy(); B['a']=B.o.map({o:at(o) for o in B.o.unique()}); B=B.dropna(subset=['a'])
        B['lr']=np.log((B.y+50)/(B.nc+50)); B['yr']=B.o.dt.year; pred=pd.Series(index=B.index,dtype=float)
        for yr in B.yr.unique():
            t=B[B.yr!=yr]; b=float(np.clip(np.cov(t.a,t.lr)[0,1]/np.var(t.a),-0.5,0.5)); v=B.yr==yr
            pred[v]=(B.nc[v]+50)*np.exp(b*B.a[v])-50
        r0,r1=rm(B.nc,B.y),rm(pred,B.y)
        # bootstrap por bloques de origen
        o=B.o.unique(); rng=np.random.default_rng(0); d=[]
        e0=(B.nc-B.y)**2; e1=(pred-B.y)**2; G=pd.DataFrame({'o':B.o,'e0':e0,'e1':e1}).groupby('o').sum()
        for _ in range(2000):
            sm=G.loc[rng.choice(G.index,len(G))]; d.append(np.sqrt(sm.e1.sum()/len(B))-np.sqrt(sm.e0.sum()/len(B)))
        res[f'{var}|{fuente}|{y}']=dict(n=len(B),rmse_base=round(r0),rmse_sat=round(r1),cambio_pct=round((r1/r0-1)*100,1),ic90=[round(float(np.percentile(d,5))),round(float(np.percentile(d,95)))],
            rho_resid=round(float(B.a.corr(B.lr,method='spearman')),3))
        print(var,fuente,y,res[f'{var}|{fuente}|{y}'])
json.dump(res,open('/home/claude/work/q31/bt_sat.json','w'),indent=1,ensure_ascii=False)
