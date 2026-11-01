exec(open('/home/claude/work/q28/base.py').read())
import statsmodels.api as sm
res={}
D=d[I0:I1].copy()
# variable dependiente semanal: log m³ MF por día con extracción, anomalía frente a mediana móvil de 13 semanas previas (quita nivel/esfuerzo lento, causal)
W=pd.DataFrame({'mf':D.mf_tot.resample('W-SUN').sum(),'act':D.act.resample('W-SUN').sum(),'q':D.sitiopresa_f.resample('W-SUN').max(),'qv':D.virginia.resample('W-SUN').max()})
W['rate']=np.where(W.act>=2,W.mf/W.act,np.nan)
base=W.rate.shift(1).rolling(13,min_periods=6).median()
W['y']=np.log(W.rate/base)
out={}
for thr in [1200,1500,1866,2100]:
    W['x']=(W.q-thr).clip(lower=0)/1000
    X=pd.concat({f'x{L}':W.x.shift(L) for L in range(0,9)},axis=1)
    Z=pd.concat([W.y,X],axis=1).dropna()
    mdl=sm.OLS(Z.y,sm.add_constant(Z.drop(columns='y'))).fit(cov_type='HAC',cov_kwds={'maxlags':4})
    b=mdl.params.drop('const'); ci=mdl.conf_int().drop('const')
    # bootstrap por bloques de 8 semanas para la suma de rezagos 2–4
    rng=np.random.default_rng(0); n=len(Z); bs=[]
    for _ in range(500):
        idx=np.concatenate([np.arange(s,min(s+8,n)) for s in rng.integers(0,n-8,n//8+1)])[:n]
        zz=Z.iloc[idx]; m2=sm.OLS(zz.y,sm.add_constant(zz.drop(columns='y'))).fit(); bs.append(m2.params[['x2','x3','x4']].sum())
    out[thr]=dict(n=n,coef={k:round(float(v),3) for k,v in b.items()},ic95={k:[round(float(ci.loc[k,0]),3),round(float(ci.loc[k,1]),3)] for k in b.index},
                  p={k:round(float(mdl.pvalues[k]),3) for k in b.index},suma_2a4=round(float(b[['x2','x3','x4']].sum()),3),suma_2a4_ic=[round(float(np.percentile(bs,2.5)),3),round(float(np.percentile(bs,97.5)),3)],r2=round(float(mdl.rsquared),3),semanas_con_exceso=int((W.x>0).sum()))
    print(thr,'n',n,'R2',out[thr]['r2'],'sem>umbral',out[thr]['semanas_con_exceso'])
    print('   coef por 1.000 m³/s·sem de exceso (log):',' '.join(f"L{k[1:]}:{v:+.2f}{'*' if out[thr]['p'][k]<0.05 else ''}" for k,v in out[thr]['coef'].items()))
    print('   suma rezagos 2–4 sem:',out[thr]['suma_2a4'],'IC95 bootstrap',out[thr]['suma_2a4_ic'])
json.dump(out,open('/home/claude/work/q28/rezagos_distribuidos.json','w'),indent=1)
