exec(open('/home/claude/work/q28/base.py').read())
from scipy.stats import spearmanr, pearsonr
from statsmodels.tsa.ar_model import AutoReg
out={}
D=d['2019-08-01':'2026-09-30']
M=pd.DataFrame({'mf':D.mf_tot.resample('MS').sum(),'act':D.act.resample('MS').sum(),'q':D.sitiopresa_f.resample('MS').mean(),'qv':D.virginia.resample('MS').mean(),'ma':D.ma_tot.resample('MS').sum()})
M['rate']=M.mf/M.act.clip(lower=1)
an=lambda s: np.log(s)-np.log(s).groupby(s.index.month).transform('median')
for per,a in [('2019-2026','2019-08-01'),('oct2021-2026','2021-10-01')]:
    m=M[a:]
    x=an(m.q); y=an(m.rate.clip(lower=1)); ya=an(m.mf.clip(lower=1)); yma=an(m.ma.clip(lower=1))
    # autocorrelación de las anomalías
    ac=lambda s,L: s.autocorr(L)
    print(per,'autocorr anomalía caudal L1,L3,L6:',[round(ac(x,L),2) for L in (1,3,6)],' MF:',[round(ac(y,L),2) for L in (1,3,6)])
    fit=AutoReg(x.dropna().values,lags=1,trend='c').fit(); ph=fit.params
    xe=x-ph[0]-ph[1]*x.shift(1); yf=y-ph[0]-ph[1]*y.shift(1); yaf=ya-ph[0]-ph[1]*ya.shift(1); ymf=yma-ph[0]-ph[1]*yma.shift(1)
    rows=[]
    for L in range(0,13):
        z=pd.concat([x.shift(L),y],axis=1).dropna(); r0=spearmanr(z.iloc[:,0],z.iloc[:,1])
        z2=pd.concat([xe.shift(L),yf],axis=1).dropna(); r1=pearsonr(z2.iloc[:,0],z2.iloc[:,1])
        z3=pd.concat([xe.shift(L),ymf],axis=1).dropna(); r3=pearsonr(z3.iloc[:,0],z3.iloc[:,1])
        rows.append(dict(L=L,rho_crudo=round(float(r0[0]),2),p_crudo=round(float(r0[1]),3),r_preblanq=round(float(r1[0]),2),p_preblanq=round(float(r1[1]),3),r_preblanq_MA=round(float(r3[0]),2),n=len(z2)))
    out[per]=rows
    print(pd.DataFrame(rows).to_string(index=False))
# promedios anuales (hidrológicos): caudal del año y MF del año siguiente
Y=M.resample('YE').agg({'q':'mean','mf':'sum','rate':'mean','act':'sum'}); print(Y.round(0))
json.dump(out,open('/home/claude/work/q28/mensual2.json','w'),indent=1)
