import pandas as pd, numpy as np, json, warnings; warnings.filterwarnings('ignore')
from scipy.stats import spearmanr, pearsonr
from statsmodels.tsa.ar_model import AutoReg
D=pd.read_pickle('/home/claude/work/q29/D.pkl'); D['mec']=D.mf_mec+D.ma_mec
Q=D.sitiopresa_f
W=pd.read_pickle('/home/claude/work/q29/Wsh.pkl')
an=lambda s: s-s.rolling(26,center=True,min_periods=10).median()
y=an(W.sh)
x=an(np.log(Q.resample('W-SUN').mean()))
# preblanqueo AR(2) del caudal semanal
xx=x.dropna(); m=AutoReg(xx.values,lags=2,trend='n').fit(); ph=m.params
xe=x-ph[0]*x.shift(1)-ph[1]*x.shift(2); yy=y.reindex(x.index); yf=yy-ph[0]*yy.shift(1)-ph[1]*yy.shift(2)
print('AR caudal',ph.round(2))
out=[]
for L in range(-2,13):
    z=pd.concat([xe.shift(L),yf],axis=1).dropna(); r,p=pearsonr(z.iloc[:,0],z.iloc[:,1]); out.append((L,round(r,2),round(p,3),len(z)))
print('preblanqueada (r, p, n):',out)
# diario: fracción flotante por día operado vs caudal (media de ventanas previas)
o=D[(D.op_mec==1)&(D.mec>0)].copy(); o['sh']=o.mf_mec/o.mec
for a,b in [(0,7),(7,14),(14,21),(21,28),(28,42),(42,56),(56,84)]:
    qw=np.log(Q).rolling(b-a).mean().shift(a).reindex(o.index)
    print(f'caudal días −{b}..−{a}: ρ={spearmanr(qw,o.sh,nan_policy="omit")[0]:+.2f}', end=' | ')
print()
# ¿la madera llega con la subida (rama ascendente) o con la bajada?
dq=(np.log(Q)-np.log(Q).shift(7)).reindex(o.index)
print('ρ(fracción, cambio del caudal en 7 d)',round(spearmanr(dq,o.sh,nan_policy='omit')[0],2))
json.dump(dict(preblanqueada=out),open('/home/claude/work/q29/share2.json','w'))
