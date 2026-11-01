import pandas as pd, numpy as np, json, warnings; warnings.filterwarnings('ignore')
exec(open('/home/claude/work/bt.py').read())
rm=lambda a,b: float(np.sqrt(np.mean((np.asarray(a)-np.asarray(b))**2)))
y='mf_tot'; M=backtest(y)[['o','h','mult']]
B=pd.read_pickle('exp26/B_mf_tot.pkl').merge(M,on=['o','h'],how='inner')
tr=B[B.o<'2024-01-01']
def bw(L,T):
    a={}
    for h,g in tr.groupby('h'):
        gs=np.linspace(0,1,21); a[h]=gs[np.argmin([rm((k*g[L]+(1-k)*g[T]),g.y) for k in gs])]
    return B.h.map(a)*B[L]+(1-B.h.map(a))*B[T]
v1=bw('lvl8','ltm'); ne=(bw('ew','ltm')+B.ltm)/2
out={}
for k,f in {'v1':v1,'v1×caudal':v1*B.mult,'nueva':ne,'nueva×caudal':ne*B.mult,'clim×caudal':B.ltm*B.mult}.items():
    g2=B[B.o>='2022-01-01']; te=B[B.o>='2024-01-01']
    out[k]={'rmse_2024_26':round(rm(f[te.index],te.y)),**{str(yr):round(1-rm(f[g.index],g.y)/rm(g.ltm,g.y),3) for yr,g in g2.groupby(g2.o.dt.year)}}
print(json.dumps(out,indent=1)); json.dump(out,open('exp26/fl.json','w'),indent=1)
W=weekly(y,QC[y]); B['tgt']=B.o+pd.to_timedelta(B.h*7,unit='D'); B['xsum']=B.tgt.map(W[[f'x{l}' for l in range(7)]].sum(axis=1))
B['m2']=np.where(B.xsum>0,np.maximum(B.mult,1),1.0)
print('frac semanas con exceso',round((B.xsum>0).mean(),3))
for k,f in {'nueva×caudal sólo crecientes':ne*B.m2}.items():
    g2=B[B.o>='2022-01-01']; te=B[B.o>='2024-01-01']
    print(k,{'rmse_2024_26':round(rm(f[te.index],te.y)),**{str(yr):round(1-rm(f[g.index],g.y)/rm(g.ltm,g.y),3) for yr,g in g2.groupby(g2.o.dt.year)}})
g2=B[B.o>='2022-01-01']
for k,f in {'v1×caudal':v1*B.mult,'nueva':ne,'nueva×crec':ne*B.m2}.items(): print(k,'rmse 2022-26',round(rm(f[g2.index],g2.y)),'clim',round(rm(g2.ltm,g2.y)))
