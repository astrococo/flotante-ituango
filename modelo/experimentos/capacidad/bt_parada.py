import pandas as pd, numpy as np, json, warnings; warnings.filterwarnings('ignore')
exec(open('/home/claude/work/bt.py').read())
rm=lambda a,b: float(np.sqrt(np.mean((np.asarray(a)-np.asarray(b))**2)))
PP=json.load(open('/home/claude/work/params_v21.json'))
q=d.sitiopresa_f; out={}
for y in ['mf_tot','ma_tot']:
    p=PP[y]; B=pd.read_pickle(f'/home/claude/work/exp26/B_{y}.pkl').merge(backtest(y)[['o','h','mult']],on=['o','h'],how='inner')
    B['m']=np.clip(np.sqrt(B.mult),0.7,1.5); w1=p['mezcla']['w1']; s=p['shrink']; a8=B.h.map(lambda h:p['a8_h'][h-1]); a=B.h.map(lambda h:p['a_h'][h-1])
    B['nc']=(w1*(a8*B.lvl8+(1-a8)*B.ltm)+(1-w1)*((1-s)*(a*B.ew+(1-a)*B.ltm)+s*B.ltm))*B.m
    B['ts']=B.o+pd.to_timedelta((B.h-1)*7+1,unit='D')
    for thr in [2100,2300,2500]:
        dd=(q>thr).astype(int)
        B['dpar']=[int(dd[t:t+pd.Timedelta(days=6)].sum()) for t in B.ts]            # días sobre el umbral en la semana objetivo (caudal real)
        B['lr']=np.log((B.y+50)/(B.nc.clip(lower=0)+50))
        f=[]
        for yr in range(2022,2027):
            tr=B[(B.o.dt.year!=yr)&np.isfinite(B.lr)]; c=float(np.clip(np.cov(tr.dpar,tr.lr)[0,1]/max(tr.dpar.var(),1e-9),-0.6,0.2)); te=B[B.o.dt.year==yr]
            f.append((te.nc+50)*np.exp(c*te.dpar)-50)
        f=pd.concat(f); g=B[B.o>='2022-01-01']
        Bf=B[np.isfinite(B.lr)]; c_all=np.cov(Bf.dpar,Bf.lr)[0,1]/Bf.dpar.var()
        out[f'{y}_{thr}']=dict(coef=round(float(c_all),3),factor_7dias=round(float(np.exp(7*c_all)),2),semanas_con_dias=int((g.dpar>0).sum()),rmse_base=round(rm(g.nc,g.y)),rmse=round(rm(f[g.index],g.y)),
            anual={int(yr):(round(1-rm(x.nc,x.y)/rm(x.ltm,x.y),3),round(1-rm(f[x.index],x.y)/rm(x.ltm,x.y),3)) for yr,x in g.groupby(g.o.dt.year)},
            solo_semanas_parada=dict(n=int((g.dpar>0).sum()),rmse_base=round(rm(g.nc[g.dpar>0],g.y[g.dpar>0])),rmse=round(rm(f[g.index][g.dpar>0],g.y[g.dpar>0]))))
        print(y,thr,out[f'{y}_{thr}'])
json.dump(out,open('/home/claude/work/q29/bt_parada.json','w'),indent=1)
