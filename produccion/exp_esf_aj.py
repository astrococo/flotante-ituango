import pickle,json,pandas as pd,numpy as np,warnings;warnings.filterwarnings('ignore')
D,W=pickle.load(open('semanal_aj.pkl','rb'));P=json.load(open('/home/claude/work/params_v21.json'))
W=W[W.index>='2019-09-01'].copy();idx=W.index;T=len(W)
LT0=np.where(idx>=pd.Timestamp('2020-07-01'))[0][0]
W['libres']=7-W.prog            # días no programados como descanso
H=13;res=[]
pars={'mf':P['mf_tot'],'ma':P['ma_tot'],'tot':{'a1':(P['mf_tot']['a1']+P['ma_tot']['a1'])/2,'tau':(P['mf_tot']['tau']+P['ma_tot']['tau'])/2}}
for comp in ['tot','mf','ma','mec']:
    p=pars.get(comp,pars['tot']);y=W[comp].values;lib=W.libres.values;op=W.op_mec.values
    for i in range(T):
        if idx[i]<pd.Timestamp('2022-01-02') or i+1>=T: continue
        act=[k for k in range(LT0,i+1) if y[k]>0]
        L8=np.mean(y[i-7:i+1]);LT=np.median(y[act]) if act else L8
        # tasas por día libre y por día operado
        r8=y[i-7:i+1].sum()/max(1,lib[i-7:i+1].sum());rLT=np.median([y[k]/lib[k] for k in act if lib[k]>0])
        o8=y[i-7:i+1].sum()/max(1,op[i-7:i+1].sum());oLT=np.median([y[k]/op[k] for k in act if op[k]>0])
        for h in range(1,H+1):
            j=i+h
            if j>=T: break
            a=p['a1']*np.exp(-(h-1)/p['tau'])
            res.append(dict(comp=comp,o=idx[i],h=h,y=y[j],
                BASE=a*L8+(1-a)*LT,
                PROG=(a*r8+(1-a)*rLT)*lib[j],
                OPER_oraculo=(a*o8+(1-a)*oLT)*op[j]))
R=pd.DataFrame(res);R.to_pickle('exp_esf_aj.pkl')
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
        rows.append(dict(serie=comp,h=f'{h0}-{h1}',n=len(g),media_obs=round(g.y.mean()),BASE=round((g.BASE-g.y).abs().mean()),PROG=round((g.PROG-g.y).abs().mean()),ORACULO=round((g.OPER_oraculo-g.y).abs().mean()),
            dif_PROG=boot(g,'PROG','BASE'),dif_OR=boot(g,'OPER_oraculo','BASE')))
print(pd.DataFrame(rows).to_string(index=False))
