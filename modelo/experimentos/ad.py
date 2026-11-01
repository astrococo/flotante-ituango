import pandas as pd, numpy as np, json
rm=lambda a,b: float(np.sqrt(np.mean((np.asarray(a)-np.asarray(b))**2)))
def blendw(B,tr,L,T):
    a={}
    for h,g in tr.groupby('h'):
        gs=np.linspace(0,1,21); a[h]=gs[np.argmin([rm(k*g[L]+(1-k)*g[T],g.y) for k in gs])]
    return B.h.map(a)*B[L]+(1-B.h.map(a))*B[T]
out={}
for y in ['mf_tot','ma_tot']:
    B=pd.read_pickle(f'/home/claude/work/exp26/B_{y}.pkl'); B['tgt']=B.o+pd.to_timedelta(B.h*7,unit='D')
    tr=B[B.o<'2024-01-01']
    C={'clim':B.ltm,'v1':blendw(B,tr,'lvl8','ltm'),'ewma':blendw(B,tr,'ew','ltm'),'l52':blendw(B,tr,'lvl8','lt52')}
    for k,v in C.items(): B['c_'+k]=v
    res={}
    for name,cands in {'v1 sola':['v1'],'adapt clim/v1':['clim','v1'],'adapt clim/v1/ewma/52':['clim','v1','ewma','l52'],'media ewma+clim':None}.items():
        if cands is None: B['fa']=(B.c_ewma+B.c_clim)/2
        else:
            ch={}
            for o in B.o.unique():
                p=B[(B.tgt<=o)&(B.tgt>o-pd.Timedelta(weeks=52))]
                ch[o]=cands[0] if len(p)<100 else min(cands,key=lambda c: rm(p['c_'+c],p.y))
            B['fa']=[r['c_'+ch[o]] for o,(_,r) in zip(B.o,B.iterrows())]
        g2=B[B.o>='2022-01-01']; te=B[B.o>='2024-01-01']
        res[name]={'rmse_2024_26':round(rm(te.fa,te.y)),**{str(yr):round(1-rm(g.fa,g.y)/rm(g.ltm,g.y),3) for yr,g in g2.groupby(g2.o.dt.year)}}
    out[y]=res
print(json.dumps(out,indent=1)); json.dump(out,open('/home/claude/work/exp26/ad.json','w'),indent=1)
