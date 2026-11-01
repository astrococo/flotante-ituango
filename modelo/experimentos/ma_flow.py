import pandas as pd, numpy as np, json, warnings; warnings.filterwarnings('ignore')
exec(open('/home/claude/work/bt.py').read())
rm=lambda a,b: float(np.sqrt(np.mean((np.asarray(a)-np.asarray(b))**2)))
out={}
for y in ['ma_tot','mf_tot']:
    M=backtest(y)[['o','h','mult']]
    B=pd.read_pickle(f'/home/claude/work/q27/B_{y}.pkl').merge(M,on=['o','h'],how='inner')
    B['m_app']=np.clip(np.sqrt(B.mult),0.7,1.5)   # como en la app: √exp(lin) acotado
    g=B[B.o>='2022-01-01']; res={}
    for k in ['C_v1','C_v22','C_s0.25','C_media v1+v22','C_media v1+ewb+lt']:
        for fl in [0,1]:
            v=g[k]*(g.m_app if fl else 1)
            res[k[2:]+(' ×caudal' if fl else '')]={'rmse':round(rm(v,g.y)),**{str(yr):round(1-rm(v[x.index],x.y)/rm(x.ltm,x.y),3) for yr,x in g.groupby(g.o.dt.year)}}
    out[y]=res; print(y)
    for k,r in sorted(res.items(),key=lambda x:x[1]['rmse']): print(f'  {k:28s}',r)
json.dump(out,open('/home/claude/work/q27/flow.json','w'),indent=1,ensure_ascii=False)
