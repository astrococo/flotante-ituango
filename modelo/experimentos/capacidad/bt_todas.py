import pandas as pd, numpy as np, json, warnings; warnings.filterwarnings('ignore')
exec(open('/home/claude/work/prep.py').read())
d['opd']=((d.sin_operacion==0)&(d.mec_off==0)).astype(int)
rm=lambda a,b: float(np.sqrt(np.mean((np.asarray(a)-np.asarray(b))**2)))
PP=json.load(open('/home/claude/work/params_v21.json'))
q=d.sitiopresa_f
out={}
for y in ['mf_tot','ma_tot']:
    p=PP[y]; w1=p['mezcla']['w1']; s=p['shrink']
    W=pd.DataFrame({'y':d[y].resample('W-SUN').sum(),'op':d.opd.resample('W-SUN').min(),'n':d.opd.resample('W-SUN').size(),
                    'd23':(q>2300).resample('W-SUN').sum(),'d19':((q>1866)&(q<=2300)).resample('W-SUN').sum(),'d15':((q>1500)&(q<=1866)).resample('W-SUN').sum()})
    W=W[(W.n==7)&(W.index>='2019-07-07')]
    recs=[]
    for i,o in enumerate(W.index):
        if o<pd.Timestamp('2021-01-01'): continue
        H=W.iloc[:i+1]; ho=H[H.op==1]
        if len(ho)<30: continue
        l8=ho.y.tail(8).median(); lt=ho.y.median(); ew=ho.y.ewm(halflife=6).mean().iloc[-1]
        last=H.tail(104); fp=last.y.mean()/max(last[last.op==1].y.mean(),1)
        for h in range(1,5):
            if i+h>=len(W): break
            r=W.iloc[i+h]; a8=p['a8_h'][h-1]; a=p['a_h'][h-1]
            nc=w1*(a8*l8+(1-a8)*lt)+(1-w1)*((1-s)*(a*ew+(1-a)*lt)+s*lt)
            recs.append(dict(o=o,h=h,y=r.y,op=r.op,nc=nc,fp=fp,d23=r.d23,d19=r.d19,d15=r.d15,ltm=lt))
    B=pd.DataFrame(recs); B['base']=B.nc*B.fp
    # factor por días de caudal alto en la semana objetivo, estimado dejando fuera el año (sobre todas las semanas)
    def fitk(tr):
        # razón media y/nc por clase de días >2.300 (0, 1–3, 4–7)
        cl=lambda x: np.select([x==0,x<=3],[0,1],2)
        r=tr.assign(c=cl(tr.d23)).groupby('c').apply(lambda g:(g.y.sum())/(g.nc.sum()))
        return {int(k):float(v) for k,v in r.items()}, cl
    f=[]; ks={}
    for yr in range(2022,2027):
        tr=B[B.o.dt.year!=yr]; k,cl=fitk(tr); te=B[B.o.dt.year==yr]; ks[yr]=k
        f.append(te.nc*pd.Series(cl(te.d23),index=te.index).map(lambda c:k.get(int(c),1.0)))
    B['fq']=pd.concat(f)
    g=B[B.o>='2022-01-01']
    res=dict(rmse_paros_constante=round(rm(g.base,g.y)),rmse_paros_por_caudal=round(rm(g.fq,g.y)),
             semanas_con_caudal_alto=int((g.d23>0).sum()),
             en_esas_semanas=dict(constante=round(rm(g.base[g.d23>0],g.y[g.d23>0])),por_caudal=round(rm(g.fq[g.d23>0],g.y[g.d23>0])),obs_media=round(float(g.y[g.d23>0].mean())),pron_const=round(float(g.base[g.d23>0].mean())),pron_caudal=round(float(g.fq[g.d23>0].mean()))),
             anual={int(yr):(round(1-rm(x.base,x.y)/rm(x.ltm*x.fp,x.y),3),round(1-rm(x.fq,x.y)/rm(x.ltm*x.fp,x.y),3)) for yr,x in g.groupby(g.o.dt.year)},
             factores=fitk(B)[0])
    out[y]=res; print(y,json.dumps(res,ensure_ascii=False))
json.dump(out,open('/home/claude/work/q29/bt_todas.json','w'),indent=1,ensure_ascii=False)
