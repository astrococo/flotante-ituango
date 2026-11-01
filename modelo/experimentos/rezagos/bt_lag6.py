import pandas as pd, numpy as np, json, warnings; warnings.filterwarnings('ignore')
exec(open('/home/claude/work/bt.py').read())
rm=lambda a,b: float(np.sqrt(np.mean((np.asarray(a)-np.asarray(b))**2)))
P=json.load(open('/home/claude/work/params_v21.json'))
q=d.sitiopresa_f
# anomalía mensual (log, respecto a la mediana del mes calendario, con TODOS los años previos al origen → causal aproximado: se usa la climatología 2019–2026 completa; sesgo menor)
Mq=q.resample('MS').mean(); an=np.log(Mq)-np.log(Mq).groupby(Mq.index.month).transform('median')
out={}
for y in ['mf_tot','ma_tot']:
    p=P[y]; B=pd.read_pickle(f'/home/claude/work/exp26/B_{y}.pkl').merge(backtest(y)[['o','h','mult']],on=['o','h'],how='inner')
    B['m']=np.clip(np.sqrt(B.mult),0.7,1.5); w1=p['mezcla']['w1']; s=p['shrink']
    a8=B.h.map(lambda h:p['a8_h'][h-1]); a=B.h.map(lambda h:p['a_h'][h-1])
    B['nc']=(w1*(a8*B.lvl8+(1-a8)*B.ltm)+(1-w1)*((1-s)*(a*B.ew+(1-a)*B.ltm)+s*B.ltm))*B.m
    B['tgt']=B.o+pd.to_timedelta(B.h*7-3,unit='D')
    for lagm in [(4,6),(5,7),(6,8)]:
        # media de la anomalía en los meses [tgt−lag2, tgt−lag1], solo meses completos ≤ origen
        def feat(r):
            m1=(r.tgt-pd.DateOffset(months=lagm[1])).to_period('M').to_timestamp(); m2=(r.tgt-pd.DateOffset(months=lagm[0])).to_period('M').to_timestamp()
            m2=min(m2,(r.o-pd.DateOffset(months=1)).to_period('M').to_timestamp())
            v=an[m1:m2]; return v.mean() if len(v) else np.nan
        B['x']=[feat(r) for r in B.itertuples()]
        B['lr']=np.log((B.y+50)/(B.nc+50))
        f=[]
        for yr in range(2022,2027):
            tr=B[(B.o.dt.year!=yr)&B.x.notna()]; b=np.polyfit(tr.x,tr.lr,1)[0]; te=B[B.o.dt.year==yr]
            f.append(pd.Series(((te.nc+50)*np.exp(b*te.x.fillna(0))-50).values,index=te.index))
        f=pd.concat(f); g=B[B.o>='2022-01-01']
        bfull=np.polyfit(B.x.dropna(),B.lr[B.x.notna()],1)[0]
        res=dict(coef=round(float(bfull),3),rmse_base=round(rm(g.nc,g.y)),rmse=round(rm(f[g.index],g.y)),
                 anual={yr:(round(1-rm(x.nc,x.y)/rm(x.ltm,x.y),3),round(1-rm(f[x.index],x.y)/rm(x.ltm,x.y),3)) for yr,x in g.groupby(g.o.dt.year)})
        out[f'{y}_{lagm}']=res; print(y,lagm,res)
json.dump(out,open('/home/claude/work/q28/bt_lag6.json','w'),indent=1)
