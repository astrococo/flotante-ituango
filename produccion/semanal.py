import pickle,pandas as pd,numpy as np,warnings;warnings.filterwarnings('ignore')
from causas import causa
D,C,plates=pickle.load(open('daily.pkl','rb'))
X=pd.read_csv('/home/claude/work/site/datos/extraccion_caudal_depurado.csv',parse_dates=['fecha']).set_index('fecha')
D['q']=X.sitiopresa_f.reindex(D.index);D['nivel']=X.nivel.reindex(D.index);D['olaya']=X.olaya.reindex(D.index)
D['mec']=D.ma_mec+D.mf_mec;D['man']=D.ma_man+D.mf_man;D['tot']=D.mec+D.man;D['mf']=D.mf_man+D.mf_mec;D['ma']=D.ma_man+D.ma_mec
D['op_mec']=(D.viajes_mec>0).astype(int)
D['causa']=np.where(D.op_mec==1,'opero',D.obs_mec.fillna('').map(causa))
D['prog']=(D.causa.isin(['programada','externa'])).astype(int)
D['disp']=(D.causa=='disponibilidad').astype(int);D['oper']=(D.causa=='operativa').astype(int)
D['volq_dia']=D.volquetas
D['op_man']=((D.viajes_parihuela+D.viajes_lancha+D.viajes_cosechadora+(D.mf_man>0))>0).astype(int)
W=pd.DataFrame({k:D[k].resample('W-SUN').sum() for k in ['tot','mec','man','mf','ma','mf_mec','ma_mec','mf_man','ma_man','op_mec','prog','disp','oper','viajes_mec','volq_dia','op_man','viajes_parihuela','viajes_lancha']})
W['q']=D.q.resample('W-SUN').mean();W['qmax']=D.q.resample('W-SUN').max();W['nivel']=D.nivel.resample('W-SUN').mean();W['n']=D.tot.resample('W-SUN').size()
W['hora']=D.hora_inicio.resample('W-SUN').mean()
W['puerto']=D.puerto.resample('W-SUN').agg(lambda s:s.dropna().mode().iloc[0] if s.dropna().size else None)
W=W[W.n==7]
pickle.dump((D,W),open('semanal.pkl','wb'))
