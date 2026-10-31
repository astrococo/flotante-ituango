import pickle,json,pandas as pd,numpy as np,warnings;warnings.filterwarnings('ignore')
D,W=pickle.load(open('semanal.pkl','rb'));C=pickle.load(open('cal.pkl','rb'));D=D.join(C)
P=json.load(open('/home/claude/work/params_v21.json'))
D['prog']=D.causa.isin(['programada','externa']).astype(int)
D['tipo']=np.select([D.navidad==1,D.ssanta==1,D.fest==1,D.dom==1,D.sab==1],['nav','ss','fest','dom','sab'],'lv')
W=W[W.index>='2019-09-01'].copy();idx=W.index;T=len(W);W['libres']=7-W.prog
LT0=np.where(idx>=pd.Timestamp('2020-07-01'))[0][0]
def libres_esperados(o,j):   # con datos hasta el domingo o, días libres esperados en la semana j
    hist=D.loc[o-pd.Timedelta(days=181):o]
    pt=hist.groupby('tipo').prog.mean();pl=hist.prog.mean()
    dias=D.loc[j-pd.Timedelta(days=6):j,'tipo']
    return 7-sum(pt.get(t,pl) for t in dias)
pars={'mf':P['mf_tot'],'ma':P['ma_tot']};pars['tot']={k:(P['mf_tot'][k]+P['ma_tot'][k])/2 for k in ['a1','tau']};pars['mec']=pars['tot']
res=[];cache={}
for comp in ['tot','mec','mf','ma']:
    p=pars[comp];y=W[comp].values;lib=W.libres.values
    for i in range(T):
        if idx[i]<pd.Timestamp('2022-01-02') or i+1>=T: continue
        act=[k for k in range(LT0,i+1) if y[k]>0]
        L8=np.mean(y[i-7:i+1]);LT=np.median(y[act])
        r8=y[i-7:i+1].sum()/max(1,lib[i-7:i+1].sum());rLT=np.median([y[k]/lib[k] for k in act if lib[k]>0])
        for h in range(1,14):
            j=i+h
            if j>=T: break
            if (i,j) not in cache: cache[(i,j)]=libres_esperados(idx[i],idx[j])
            a=p['a1']*np.exp(-(h-1)/p['tau']);rate=a*r8+(1-a)*rLT
            res.append(dict(comp=comp,o=idx[i],h=h,y=y[j],BASE=a*L8+(1-a)*LT,PROG_conocido=rate*lib[j],PROG_calendario=rate*cache[(i,j)]))
R=pd.DataFrame(res);R.to_pickle('exp_cal.pkl')
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
        rows.append(dict(serie=comp,h=f'{h0}-{h1}',BASE=round((g.BASE-g.y).abs().mean()),CAL=round((g.PROG_calendario-g.y).abs().mean()),CONOC=round((g.PROG_conocido-g.y).abs().mean()),dif_CAL=boot(g,'PROG_calendario','BASE'),dif_CONOC=boot(g,'PROG_conocido','BASE')))
print(pd.DataFrame(rows).to_string(index=False))
