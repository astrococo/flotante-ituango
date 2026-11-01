import pandas as pd, numpy as np, json, warnings; warnings.filterwarnings('ignore')
exec(open('/home/claude/work/prep.py').read())
d['opd']=((d.sin_operacion==0)&(d.mec_off==0)).astype(int)
rm=lambda a,b: float(np.sqrt(np.mean((np.asarray(a)-np.asarray(b))**2)))
out={}
for y in ['mf_tot','ma_tot']:
    act=(d[y]>0).astype(int)
    W=pd.DataFrame({'y':d[y].resample('W-SUN').sum(),'op':d.opd.resample('W-SUN').min(),'n':d.opd.resample('W-SUN').size(),'nact':act.resample('W-SUN').sum()})
    W=W[(W.n==7)&(W.index>='2019-07-07')]
    W['rate']=np.where(W.nact>=2,W.y/W.nact.clip(lower=1),np.nan)
    W['woy']=W.index.isocalendar().week.astype(int)
    recs=[]
    idx=W.index
    for i,o in enumerate(idx):
        if o<pd.Timestamp('2021-01-01'): continue
        H=W.iloc[:i+1]; ho=H[H.op==1]
        if len(ho)<30: continue
        lvl8=ho.y.tail(8).median(); ltm=ho.y.median(); lt52=ho.y[ho.index>o-pd.Timedelta(weeks=52)].median()
        ew=ho.y.ewm(halflife=6).mean().iloc[-1]
        rt=H.rate.dropna(); rlvl=rt.tail(8).median(); rlt=rt.median(); dexp=ho.nact.tail(26).median()
        for h in range(1,14):
            if i+h>=len(W): break
            r=W.iloc[i+h]
            if r.op!=1: continue
            wk=r.woy; past=ho[ho.index<o-pd.Timedelta(weeks=26)]
            dd=np.minimum(abs(past.woy-wk),53-abs(past.woy-wk)); sea=past.y[dd<=3].median() if (dd<=3).sum()>=4 else ltm
            recs.append(dict(o=o,h=h,y=r.y,lvl8=lvl8,ltm=ltm,lt52=lt52,ew=ew,rlvl=rlvl*dexp,rlt=rlt*dexp,sea=sea))
    B=pd.DataFrame(recs)
    tr=B[B.o<'2024-01-01']; te=B[B.o>='2024-01-01']
    def blend(L,T):
        a={}
        for h,g in tr.groupby('h'):
            gs=np.linspace(0,1,21); a[h]=gs[np.argmin([rm(k*g[L]+(1-k)*g[T],g.y) for k in gs])]
        return B.h.map(a)*B[L]+(1-B.h.map(a))*B[T]
    V={'clim_all':B.ltm,'v1 (8 sem + histórico)':blend('lvl8','ltm'),'8 sem + 52 sem':blend('lvl8','lt52'),'EWMA + histórico':blend('ew','ltm'),
       'tasa por día activo':blend('rlvl','rlt'),'8 sem + estacional':blend('lvl8','sea'),'tasa + estacional':blend('rlvl','sea')}
    # combinado: promedio simple de tasa-blend y 8sem+estacional
    V['combinado (tasa/estacional/v1)']=(V['tasa por día activo']+V['8 sem + estacional']+V['v1 (8 sem + histórico)'])/3
    res={}
    for k,f in V.items():
        B['f']=f; g2=B[B.o>='2022-01-01']
        res[k]={'rmse_2024_26':round(rm(B.f[te.index],te.y)),**{str(yr):round(1-rm(g.f,g.y)/rm(g.ltm,g.y),3) for yr,g in g2.groupby(g2.o.dt.year)}}
    out[y]=res
    B.to_pickle(f'/home/claude/work/exp26/B_{y}.pkl')
print(json.dumps(out,indent=1,ensure_ascii=False)); json.dump(out,open('/home/claude/work/exp26/ev.json','w'),indent=1,ensure_ascii=False)
