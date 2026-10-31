import pickle,json,pandas as pd,numpy as np,warnings;warnings.filterwarnings('ignore')
D,W=pickle.load(open('semanal.pkl','rb'));P=json.load(open('/home/claude/work/params_v21.json'))
W=W[W.index>='2019-09-01'].copy();idx=W.index;T=len(W)
LT0=np.where(idx>=pd.Timestamp('2020-07-01'))[0][0]
q=W.q.values;op=W.op_mec.values
pars={'mf':P['mf_tot'],'ma':P['ma_tot']};pars['tot']={k:(P['mf_tot'][k]+P['ma_tot'][k])/2 for k in ['a1','tau']};pars['mec']=pars['tot']
def p_op(i,qq):   # días operados esperados por semana según caudal, con historia hasta i (regresión local por tramos)
    hq=q[LT0:i+1];ho=op[LT0:i+1];b=[0,800,1200,1600,2000,9e9]
    k=np.searchsorted(b,qq,side='right')-1;m=(hq>=b[k])&(hq<b[k+1])
    return ho[m].mean() if m.sum()>=8 else ho.mean()
res=[]
for comp in ['tot','mec','mf','ma']:
    p=pars[comp];y=W[comp].values
    for i in range(T):
        if idx[i]<pd.Timestamp('2022-01-02') or i+1>=T: continue
        act=[k for k in range(LT0,i+1) if y[k]>0]
        L8=np.mean(y[i-7:i+1]);LT=np.median(y[act])
        o8=y[i-7:i+1].sum()/max(1,op[i-7:i+1].sum());oLT=np.median([y[k]/op[k] for k in act if op[k]>0])
        e8=np.mean([p_op(i,q[k]) for k in range(i-7,i+1)])   # días esperados en la ventana reciente, para no contar dos veces
        for h in range(1,14):
            j=i+h
            if j>=T: break
            a=p['a1']*np.exp(-(h-1)/p['tau']);base=a*L8+(1-a)*LT
            fac_pe=p_op(i,q[i])/max(0.5,np.mean([p_op(i,q[k]) for k in range(LT0,i+1)]))
            fac_or=p_op(i,q[j])/max(0.5,np.mean([p_op(i,q[k]) for k in range(LT0,i+1)]))
            res.append(dict(comp=comp,o=idx[i],h=h,y=y[j],BASE=base,Q_persist=a*L8+(1-a)*LT*fac_pe,Q_oraculo=a*L8+(1-a)*LT*fac_or))
R=pd.DataFrame(res)
def boot(g,m1,m2,nb=2000):
    g=g.assign(d=(g[m1]-g.y).abs()-(g[m2]-g.y).abs());s=g.groupby('o').d.sum();c=g.groupby('o').size();oo=s.index.values;bl=[oo[k:k+8] for k in range(0,len(oo),8)]
    r=np.random.default_rng(1);st=[]
    for _ in range(nb):
        sel=np.concatenate([bl[k] for k in r.integers(0,len(bl),len(bl))]);st.append(s.loc[sel].sum()/c.loc[sel].sum())
    return f"{g.d.mean():+.0f} [{np.percentile(st,2.5):+.0f}, {np.percentile(st,97.5):+.0f}]"
rows=[]
for comp in ['tot','mec','mf','ma']:
    for h0,h1 in [(1,4),(5,13)]:
        g=R[(R.comp==comp)&(R.h>=h0)&(R.h<=h1)]
        rows.append(dict(serie=comp,h=f'{h0}-{h1}',BASE=round((g.BASE-g.y).abs().mean()),Qpers=round((g.Q_persist-g.y).abs().mean()),Qor=round((g.Q_oraculo-g.y).abs().mean()),dif_pers=boot(g,'Q_persist','BASE'),dif_or=boot(g,'Q_oraculo','BASE')))
print(pd.DataFrame(rows).to_string(index=False))
