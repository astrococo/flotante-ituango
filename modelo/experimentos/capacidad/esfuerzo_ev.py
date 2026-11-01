import pandas as pd, numpy as np, json, warnings; warnings.filterwarnings('ignore')
D=pd.read_pickle('/home/claude/work/q29/D.pkl'); D['mec']=D.mf_mec+D.ma_mec
E=pd.read_csv('/home/claude/work/q28/eventos.csv',parse_dates=['pico']); pk=list(E.pico)
o=D.copy(); o['vq_op']=o.volquetas.where(o.op_mec==1); o['vpv']=(o.viajes_mec/o.volquetas).where((o.op_mec==1)&(o.volquetas>0)); o['sh']=(o.mf_mec/o.mec).where(o.mec>0)
o['man']=o.mf_man+o.ma_man
cols={'op_mec':'mecanizado operó (fracción de días)','vq_op':'volquetas por día operado','vpv':'viajes por volqueta','sh':'fracción flotante del mecanizado','mec':'m³ mecanizado por día','man':'m³ manual por día','mf_man':'m³ flotante manual por día'}
def prof(t,c):
    ab=pd.concat([o.loc[t-pd.Timedelta(days=120):t-pd.Timedelta(days=29),c],o.loc[t+pd.Timedelta(days=57):t+pd.Timedelta(days=150),c]]); base=ab.mean()
    return [o.loc[t+pd.Timedelta(days=7*k):t+pd.Timedelta(days=7*k+6),c].mean()-base for k in range(-2,8)], base
res={}
for c,lab in cols.items():
    P=np.array([prof(t,c)[0] for t in pk]); b=np.nanmedian([prof(t,c)[1] for t in pk])
    med=np.nanmedian(P,0); res[c]=dict(nombre=lab,base=round(float(b),3),dif=[round(float(v),3) for v in med])
    print(f'{lab:38s} base {b:8.2f} | ' + ' '.join(f'{v:+.2f}' for v in med))
json.dump(res,open('/home/claude/work/q29/esfuerzo_ev.json','w'),indent=1,ensure_ascii=False)
