exec(open('/home/claude/work/q28/base.py').read())
from scipy.stats import spearmanr
q=d.sitiopresa_f; thr=1866
pk=[]
for t,v in q[I0:'2026-08-31'][q[I0:'2026-08-31']>=thr].sort_values(ascending=False).items():
    if all(abs((t-p).days)>=30 for p in pk): pk.append(t)
pk=sorted(pk)
allpk=[]  # todos los picos ≥ 1500 para "días desde la creciente anterior"
for t,v in q[q>=1500].sort_values(ascending=False).items():
    if all(abs((t-p).days)>=14 for p in allpk): allpk.append(t)
allpk=pd.DatetimeIndex(sorted(allpk))
rows=[]
for t in pk:
    pre=d.loc[t-pd.Timedelta(days=28):t-pd.Timedelta(days=1)]
    r=lambda a,b: d.loc[t+pd.Timedelta(days=a):t+pd.Timedelta(days=b)]
    pr=pre.mf_tot.sum()/max(pre.act.sum(),1)
    wk=[r(7*k,7*k+6) for k in range(8)]
    rate=[w.mf_tot.sum()/w.act.sum() if w.act.sum()>=2 else np.nan for w in wk]
    # hidrograma: inicio = último día antes del pico con caudal < 0,8·pico... usar umbral 1500
    seg=q[t-pd.Timedelta(days=20):t+pd.Timedelta(days=20)]
    above=seg[seg>=1500]
    prev=allpk[allpk<t-pd.Timedelta(days=7)]
    v=d.virginia[t-pd.Timedelta(days=4):t].max(); o=d.olaya[t-pd.Timedelta(days=2):t+pd.Timedelta(days=1)].max()
    inter=(d.sitiopresa-d.olaya)[t-pd.Timedelta(days=2):t+pd.Timedelta(days=1)].max()
    rows.append(dict(pico=t.date(),q_pico=round(q[t]),vol_sobre_1500=round(float((above-1500).sum()*86400/1e6),1),dias_sobre_1500=int(len(above)),
        subida_3d=round(float(q[t]-q[t-pd.Timedelta(days=3)])),dias_desde_anterior=int((t-prev[-1]).days) if len(prev) else None,mes=t.month,
        virginia_max=round(v) if v==v else None,aporte_local_max=round(inter) if inter==inter else None,
        mf_pre_dia=round(pr),**{f's{k}':round(rate[k]/pr,2) if pr>0 and rate[k]==rate[k] else None for k in range(8)},
        dias_activos_s0=int(wk[0].act.sum()),dias_activos_s1=int(wk[1].act.sum()),
        mf_extra_8sem=round(float(sum(w.mf_tot.sum() for w in wk)-8*7*pre.mf_tot.sum()/28))))
E=pd.DataFrame(rows); E['resp_s2']=E.s2; E['resp_s2a4']=E[['s2','s3','s4']].mean(axis=1)
pd.set_option('display.width',250); print(E[['pico','q_pico','vol_sobre_1500','dias_sobre_1500','subida_3d','dias_desde_anterior','virginia_max','aporte_local_max','mf_pre_dia','s0','s1','s2','s3','s4','s5','s6','s7','mf_extra_8sem']].to_string(index=False))
print('\neventos con s2>1:',int((E.s2>1).sum()),'de',E.s2.notna().sum(),'| s2>1,5:',int((E.s2>1.5).sum()))
print('mediana s0..s7',[round(float(E[f's{k}'].median()),2) for k in range(8)])
cor={}
for c in ['q_pico','vol_sobre_1500','dias_sobre_1500','subida_3d','dias_desde_anterior','virginia_max','aporte_local_max','mf_pre_dia','mes']:
    for rr in ['resp_s2','resp_s2a4','mf_extra_8sem']:
        r,p=spearmanr(E[c],E[rr],nan_policy='omit'); cor[f'{c}|{rr}']=(round(float(r),2),round(float(p),3))
for k,v in cor.items(): print(k,v)
E.to_csv('/home/claude/work/q28/eventos.csv',index=False); json.dump(cor,open('/home/claude/work/q28/eventos_cor.json','w'),indent=1)
