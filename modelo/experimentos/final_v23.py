import pandas as pd, numpy as np, json, warnings; warnings.filterwarnings('ignore')
exec(open('/home/claude/work/bt.py').read())
rm=lambda a,b: float(np.sqrt(np.mean((np.asarray(a)-np.asarray(b))**2)))
gs=np.linspace(0,1,21)
CFG={'mf_tot':dict(w1=0.0,s=0.25),'ma_tot':dict(w1=0.5,s=0.5)}
P=json.load(open('/home/claude/work/params_v21.json')); R={}
for y,cf in CFG.items():
    B=pd.read_pickle(f'/home/claude/work/exp26/B_{y}.pkl').merge(backtest(y)[['o','h','mult']],on=['o','h'],how='inner')
    B['m']=np.clip(np.sqrt(B.mult),0.7,1.5)
    tr=B[B.o<'2024-01-01']
    a8={h:float(gs[np.argmin([rm(k*g.lvl8+(1-k)*g.ltm,g.y) for k in gs])]) for h,g in tr.groupby('h')}
    aew={h:float(gs[np.argmin([rm(k*g.ew+(1-k)*g.ltm,g.y) for k in gs])]) for h,g in tr.groupby('h')}
    v1=B.h.map(a8)*B.lvl8+(1-B.h.map(a8))*B.ltm; ewb=B.h.map(aew)*B.ew+(1-B.h.map(aew))*B.ltm
    B['nc']=(cf['w1']*v1+(1-cf['w1'])*((1-cf['s'])*ewb+cf['s']*B.ltm))*B.m
    B['r']=(B.y+50)/(B.nc+50); Bq=B[B.o>='2022-01-01'].copy()
    q=Bq.groupby('h').r.quantile([0.1,0.25,0.5,0.75,0.9]).unstack(); rmn=Bq.groupby('h').r.mean()
    for lab,f in [('central',Bq.nc),('p50cal',(Bq.nc+50)*Bq.h.map(q[0.5])-50)]:
        print(y,lab,'rmse',round(rm(f,Bq.y)),{yr:round(1-rm(f[x.index],x.y)/rm(x.ltm,x.y),3) for yr,x in Bq.groupby(Bq.o.dt.year)})
    R[y]=dict(B=B,Bq=Bq,q=q,rmn=rmn,a8=a8,aew=aew,v1=v1[Bq.index] if False else None)
    p=dict(P[y])
    p.update(mezcla=dict(w1=cf['w1'],s=cf['s']),a8_h=[a8[h] for h in range(1,14)],a_h=[aew[h] for h in range(1,14)],ewma_hl=6,lt_desde='2019-07-01',usa_caudal=True,shrink=cf['s'],k=1.0)
    p['q']={str(c):(q[c].round(3).tolist() if c!=0.5 else [1.0]*13) for c in q.columns}; p['rmean']=rmn.round(3).tolist()
    met=[]
    for h,g in Bq.groupby('h'):
        p50=g.nc; cov=float(((g.r>=q.loc[h,0.1])&(g.r<=q.loc[h,0.9])).mean())
        met.append(dict(h=int(h),clim=round(rm(g.ltm,g.y)),pers=round(rm(g.lvl8,g.y)),modelo=round(rm(p50,g.y)),mae=round(float(np.mean(abs(g.y-p50)))),
            skill_clim=round(1-rm(p50,g.y)/rm(g.ltm,g.y),3),skill_pers=round(1-rm(p50,g.y)/rm(g.lvl8,g.y),3),cobertura80=round(cov,2),n=len(g),media_obs=round(float(g.y.mean())),sesgo=round(float((p50-g.y).mean()))))
    p['metricas']=met
    cal=Bq[Bq.o<'2024-01-01']; val=Bq[Bq.o>='2024-01-01']; qq=cal.groupby('h').r.quantile([.1,.9]).unstack(); v=val.join(qq,on='h')
    p['cobertura80_fuera_muestra']=round(float(((v.r>=v[0.1])&(v.r<=v[0.9])).mean()),3)
    v1s=(Bq.h.map(a8)*Bq.lvl8+(1-Bq.h.map(a8))*Bq.ltm)
    v22=0.5*(Bq.h.map(aew)*Bq.ew+(1-Bq.h.map(aew))*Bq.ltm)+0.5*Bq.ltm
    p['skill_anual']={str(yr):dict(v1=round(1-rm(v1s[x.index],x.y)/rm(x.ltm,x.y),3),v22=round(1-rm(v22[x.index],x.y)/rm(x.ltm,x.y),3),v23=round(1-rm(x.nc,x.y)/rm(x.ltm,x.y),3)) for yr,x in Bq.groupby(Bq.o.dt.year)}
    p['rmse_total']=dict(clim=round(rm(Bq.ltm,Bq.y)),pers=round(rm(Bq.lvl8,Bq.y)),v1=round(rm(v1s,Bq.y)),v22=round(rm(v22,Bq.y)),v23=round(rm(Bq.nc,Bq.y)),v2=round(rm(Bq.nc,Bq.y)))
    p['k_regla']='v2.3: mezcla fija por horizonte de L8 (w1), media exponencial (1−w1, encogida s hacia LT) y multiplicador de caudal acotado'
    p['nota_caudal']='Multiplicador de caudal √exp(·) acotado a 0,7–1,5, igual que en la app; en el backtest causal 2022–2026 reduce el error en ambos componentes.'
    P[y]=p; print(y,'skill',p['skill_anual'],'rmse',p['rmse_total'],'cob',p['cobertura80_fuera_muestra'])
P['version']='2.3 (1-nov-2026)'
json.dump(P,open('/home/claude/work/q27/params_v23.json','w'),indent=1,ensure_ascii=False)
