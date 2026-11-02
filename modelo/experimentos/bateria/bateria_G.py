"""Familia G: ¿cada término de caudal mejora el pronóstico? Prueba de Diebold–Mariano (pérdida cuadrática, varianza HAC
con 4 rezagos semanales) entre el pronóstico base y el pronóstico con el término, 2022–2026, dejando fuera el año al estimar."""
import pandas as pd, numpy as np, json, warnings; warnings.filterwarnings('ignore')
from scipy.stats import norm
exec(open('/home/claude/work/bt.py').read())
PP=json.load(open('/home/claude/work/params_v21.json'))
def dm(e1,e2,h=4):
    dd=(np.asarray(e1)**2-np.asarray(e2)**2); n=len(dd); m=dd.mean(); g=[np.mean((dd[k:]-m)*(dd[:n-k]-m)) for k in range(h+1)]
    v=g[0]+2*sum((1-k/(h+1))*g[k] for k in range(1,h+1)); s=m/np.sqrt(max(v,1e-9)/n); return s, 2*(1-norm.cdf(abs(s)))
T=[]
def add(n,s,p,extra): T.append(dict(familia='G. Pronóstico',prueba=n,estadistico=round(float(s),3),p=round(float(p),4),**extra))
q=d.sitiopresa_f
Bs={}
for y in ['mf_tot','ma_tot']:
    p=PP[y]; B=pd.read_pickle(f'/home/claude/work/exp26/B_{y}.pkl').merge(backtest(y)[['o','h','mult']],on=['o','h'],how='inner')
    B['m']=np.clip(np.sqrt(B.mult),0.7,1.5); w1=p['mezcla']['w1']; s=p['shrink']; a8=B.h.map(lambda h:p['a8_h'][h-1]); a=B.h.map(lambda h:p['a_h'][h-1])
    B['nc']=(w1*(a8*B.lvl8+(1-a8)*B.ltm)+(1-w1)*((1-s)*(a*B.ew+(1-a)*B.ltm)+s*B.ltm))*B.m
    B['nc0']=(w1*(a8*B.lvl8+(1-a8)*B.ltm)+(1-w1)*((1-s)*(a*B.ew+(1-a)*B.ltm)+s*B.ltm))
    B['ts']=B.o+pd.to_timedelta((B.h-1)*7+1,unit='D'); Bs[y]=B[B.o>='2022-01-01'].sort_values(['o','h'])
# G1–G2: multiplicador de caudal (v2.3 con vs sin)
for y,lab in [('mf_tot','flotante'),('ma_tot','macrófitas')]:
    g=Bs[y]; s_,p_=dm(g.nc0-g.y,g.nc-g.y); add(f'{lab}: multiplicador de caudal acotado (v2.3) vs sin caudal',s_,p_,dict(rmse_sin=round(float(np.sqrt(((g.nc0-g.y)**2).mean()))),rmse_con=round(float(np.sqrt(((g.nc-g.y)**2).mean())))))
# G3: perfil de crecientes (semanas desde el pico, conocido al origen) en flotante
g=Bs['mf_tot'].copy(); pk=[]
for t,v in d.olaya[d.olaya>=1750].sort_values(ascending=False).items():
    if all(abs((t-x).days)>=14 for x in pk): pk.append(t)
pk=pd.DatetimeIndex(sorted(pk))
def kk(r):
    c=pk[pk<=r.o]
    if not len(c): return -1
    k=(r.ts-c[-1]).days//7; return int(k) if 0<=k<=7 else -1
g['k']=[kk(r) for r in g.itertuples()]; f=[]
for yr in range(2022,2027):
    tr=g[(g.o.dt.year!=yr)&(g.k>=0)]; fac={k:float(np.clip(np.median(x.y/x.nc),0.5,2.5)) for k,x in tr.groupby('k') if len(x)>=8}
    te=g[g.o.dt.year==yr]; f.append(te.nc*te.k.map(lambda k:fac.get(k,1.0)))
f=pd.concat(f).reindex(g.index); s_,p_=dm(g.nc-g.y,f-g.y); add('flotante: perfil por semanas desde la creciente (Olaya ≥ 1.750)',s_,p_,dict(rmse_base=round(float(np.sqrt(((g.nc-g.y)**2).mean()))),rmse_termino=round(float(np.sqrt(((f-g.y)**2).mean())))))
# G4: anomalía de caudal 5–7 meses antes
Mq=q.resample('MS').mean(); an=np.log(Mq)-np.log(Mq).groupby(Mq.index.month).transform('median')
g=Bs['mf_tot'].copy(); g['tgt']=g.o+pd.to_timedelta(g.h*7-3,unit='D')
def feat(r):
    m1=(r.tgt-pd.DateOffset(months=7)).to_period('M').to_timestamp(); m2=min((r.tgt-pd.DateOffset(months=5)).to_period('M').to_timestamp(),(r.o-pd.DateOffset(months=1)).to_period('M').to_timestamp())
    v=an[m1:m2]; return v.mean() if len(v) else 0.0
g['x']=[feat(r) for r in g.itertuples()]; g['lr']=np.log((g.y+50)/(g.nc.clip(lower=0)+50)); f=[]
for yr in range(2022,2027):
    tr=g[g.o.dt.year!=yr]; b=np.cov(tr.x,tr.lr)[0,1]/tr.x.var(); te=g[g.o.dt.year==yr]; f.append((te.nc+50)*np.exp(b*te.x)-50)
f=pd.concat(f).reindex(g.index); s_,p_=dm(g.nc-g.y,f-g.y); add('flotante: anomalía de caudal 5–7 meses antes',s_,p_,dict(rmse_base=round(float(np.sqrt(((g.nc-g.y)**2).mean()))),rmse_termino=round(float(np.sqrt(((f-g.y)**2).mean())))))
# G5–G6: factor de parada por días > 2.300 (todas las semanas, h 1–4) — se recalcula como en bt_todas2
exec(open('/home/claude/work/q29/bt_todas.py').read().split("out={}")[0])
for y,lab in [('mf_tot','flotante'),('ma_tot','macrófitas')]:
    p=PP[y]; w1=p['mezcla']['w1']; s=p['shrink']
    W=pd.DataFrame({'y':d[y].resample('W-SUN').sum(),'op':d.opd.resample('W-SUN').min(),'n':d.opd.resample('W-SUN').size(),'d23':(q>2300).resample('W-SUN').sum()}); W=W[(W.n==7)&(W.index>='2019-07-07')]
    recs=[]
    for i,o in enumerate(W.index):
        if o<pd.Timestamp('2021-01-01'): continue
        H=W.iloc[:i+1]; ho=H[H.op==1]
        if len(ho)<30: continue
        l8=ho.y.tail(8).median(); lt=ho.y.median(); ew=ho.y.ewm(halflife=6).mean().iloc[-1]; last=H.tail(104); fp=last.y.mean()/max(last[last.op==1].y.mean(),1)
        for h in range(1,5):
            if i+h>=len(W): break
            r=W.iloc[i+h]; a8=p['a8_h'][h-1]; a=p['a_h'][h-1]; nc=w1*(a8*l8+(1-a8)*lt)+(1-w1)*((1-s)*(a*ew+(1-a)*lt)+s*lt)
            recs.append(dict(o=o,y=r.y,nc=nc,fp=fp,d23=r.d23))
    B=pd.DataFrame(recs); B['base']=B.nc*B.fp; cl=lambda x: np.select([x==0,x<=3],[0,1],2); f=[]
    for yr in range(2022,2027):
        tr=B[B.o.dt.year!=yr]; k=tr.assign(c=cl(tr.d23)).groupby('c').apply(lambda g_:g_.y.sum()/g_.nc.sum()).to_dict(); te=B[B.o.dt.year==yr]
        f.append(te.base*pd.Series(cl(te.d23),index=te.index).map(lambda c:k.get(int(c),1.0)/k[0]))
    f=pd.concat(f); g=B[B.o>='2022-01-01']; f=f.reindex(g.index)
    s_,p_=dm(g.base-g.y,f-g.y); add(f'{lab}: factor de parada por días > 2.300 m³/s (valor con paros)',s_,p_,dict(rmse_base=round(float(np.sqrt(((g.base-g.y)**2).mean()))),rmse_termino=round(float(np.sqrt(((f-g.y)**2).mean())))))
for t in T: print(t)
json.dump(T,open('/home/claude/work/q30/bateria_G.json','w'),indent=1,ensure_ascii=False)
