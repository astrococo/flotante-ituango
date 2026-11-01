import pandas as pd, numpy as np, json, warnings; warnings.filterwarnings('ignore')
rm=lambda a,b: float(np.sqrt(np.mean((np.asarray(a)-np.asarray(b))**2)))
gs=np.linspace(0,1,21)
out={}
for y in ['mf_tot','ma_tot']:
    B=pd.read_pickle(f'/home/claude/work/exp26/B_{y}.pkl').reset_index(drop=True); B['tgt']=B.o+pd.to_timedelta(B.h*7,unit='D')
    tr=B[B.o<'2024-01-01']
    def bw(L,T):
        a={h:gs[np.argmin([rm(k*g[L]+(1-k)*g[T],g.y) for k in gs])] for h,g in tr.groupby('h')}
        return B.h.map(a)*B[L]+(1-B.h.map(a))*B[T]
    C={}
    C['v1']=bw('lvl8','ltm'); ewb=bw('ew','ltm')
    for s in [0,0.25,0.5,0.75,1.0]: C[f's{s}']=(1-s)*ewb+s*B.ltm
    C['v22']=C['s0.5']
    C['media v1+v22']=(C['v1']+C['v22'])/2
    C['media v1+ewb+lt']=(C['v1']+ewb+B.ltm)/3
    C['estacional']=B.sea
    C['media v22+estac']=(C['v22']+B.sea)/2
    for k,v in C.items(): B['c_'+k]=v
    def adapt(cands,win=52,minn=100,crit='rmse'):
        ch={}; 
        for o in sorted(B.o.unique()):
            p=B[(B.tgt<=o)&(B.tgt>o-pd.Timedelta(weeks=win))]
            ch[o]=cands[len(cands)//2] if len(p)<minn else min(cands,key=lambda c: rm(p['c_'+c],p.y))
        return pd.Series([B.at[i,'c_'+ch[o]] for i,o in zip(B.index,B.o)],index=B.index)
    def stack(cands,win=104,minn=150):
        # pesos no negativos por mínimos cuadrados en ventana causal, suma 1 (via proyección simple)
        from scipy.optimize import nnls
        f=pd.Series(np.nan,index=B.index)
        for o in sorted(B.o.unique()):
            p=B[(B.tgt<=o)&(B.tgt>o-pd.Timedelta(weeks=win))]; idx=B.index[B.o==o]
            if len(p)<minn: w=np.ones(len(cands))/len(cands)
            else:
                w,_=nnls(p[['c_'+c for c in cands]].values,p.y.values); w=w/w.sum() if w.sum()>0 else np.ones(len(cands))/len(cands)
            f[idx]=B.loc[idx,['c_'+c for c in cands]].values@w
        return f
    C['adapt s{0..1}']=adapt(['s0','s0.25','s0.5','s0.75','s1.0'])
    C['adapt v1/v22/lt']=adapt(['v1','v22','s1.0'])
    C['stack v1,ewb,lt,est']=stack(['v1','s0','s1.0','estacional'])
    C['stack v1,v22']=stack(['v1','v22'])
    g=B[B.o>='2022-01-01']; res={}
    for k,v in C.items():
        res[k]={'rmse':round(rm(v[g.index],g.y)),**{str(yr):round(1-rm(v[x.index],x.y)/rm(x.ltm,x.y),3) for yr,x in g.groupby(g.o.dt.year)}}
        res[k]['min']=min(res[k][str(yr)] for yr in range(2022,2027))
    out[y]=res
    print(y); 
    for k,r in sorted(res.items(),key=lambda x:x[1]['rmse']): print(f'  {k:24s}',r)
    B.assign(**{('C_'+k):v for k,v in C.items()}).to_pickle(f'/home/claude/work/q27/B_{y}.pkl')
json.dump(out,open('/home/claude/work/q27/cand.json','w'),indent=1,ensure_ascii=False)
