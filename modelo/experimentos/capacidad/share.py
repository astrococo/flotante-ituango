import pandas as pd, numpy as np, json, warnings; warnings.filterwarnings('ignore')
from scipy.stats import spearmanr
from statsmodels.tsa.ar_model import AutoReg
D=pd.read_pickle('/home/claude/work/q29/D.pkl'); D['mec']=D.mf_mec+D.ma_mec
W=pd.DataFrame({'mf':D.mf_mec.resample('W-SUN').sum(),'mec':D.mec.resample('W-SUN').sum(),'q':D.sitiopresa_f.resample('W-SUN').mean(),'qmax':D.sitiopresa_f.resample('W-SUN').max(),'dop':D.op_mec.resample('W-SUN').sum()})
W=W[W.dop>=2]; W['sh']=W.mf/W.mec
W=W[~((W.index>='2026-04-01')&(W.index<='2026-10-04'))]   # abr–sep 2026: división flotante/macrófitas fija (0,457), no medida
print('semanas',len(W),'fracción flotante mediana',round(W.sh.median(),2))
# correlación cruda por rezago (semanas) y por niveles de caudal
for L in range(0,9):
    qL=pd.Series(W.q.values,index=W.index).shift(L) if False else None
Q=pd.read_pickle('/home/claude/work/q29/D.pkl').sitiopresa_f.resample('W-SUN').mean()
res=[]
for L in range(0,13):
    x=Q.shift(L).reindex(W.index); r,p=spearmanr(x,W.sh,nan_policy='omit'); res.append((L,round(r,2),round(p,3)))
print('ρ(fracción flotante semanal, caudal medio semanal con rezago L):',res)
# anomalías: quitar estacionalidad (mes) y tendencia lenta (mediana móvil 26 sem) en ambos
an=lambda s: s-s.rolling(26,center=True,min_periods=10).median()
sh_a=an(W.sh); q_a=an(np.log(Q)).reindex(W.index)
res2=[]
for L in range(0,13):
    x=an(np.log(Q)).shift(L).reindex(W.index); r,p=spearmanr(x,sh_a,nan_policy='omit'); res2.append((L,round(r,2),round(p,3)))
print('ρ anomalías (sin nivel lento):',res2)
# clases de caudal (media de las 4 semanas previas)
q4=Q.rolling(4).mean().shift(1).reindex(W.index)
print(W.groupby(pd.cut(q4,[0,700,900,1200,1500,2000,4000])).sh.agg(['count','median','mean']).round(2))
W.to_pickle('/home/claude/work/q29/Wsh.pkl')
