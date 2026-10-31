import pickle,pandas as pd,numpy as np,json,warnings;warnings.filterwarnings('ignore')
from sklearn.linear_model import LinearRegression
D,W=pickle.load(open('semanal_aj.pkl','rb'))
D['c']=D.causa.replace({'sin_texto':'sin_dato','sin_reporte':'sin_dato','no_especificada':'sin_dato'})
cats=['opero','programada','operativa','disponibilidad','externa','sin_dato']
Wk=pd.crosstab(D.index.to_period('W-SUN'),D.c).reindex(columns=cats,fill_value=0);Wk.index=Wk.index.end_time.normalize();Wk=Wk[Wk.sum(1)==7];wk=Wk.loc['2019-09-01':]
mec=D.mec.resample('W-SUN').sum().reindex(wk.index);vq=D.volquetas.resample('W-SUN').sum().reindex(wk.index);vi=D.viajes_mec.resample('W-SUN').sum().reindex(wk.index)
V=W[W.index>='2020-07-01']
r2=lambda y,X:round(LinearRegression().fit(X,y).score(X,y),2)
R2=dict(dias=r2(V.mec,V[['op_mec']]),volq=r2(V.mec,V[['op_mec','volq_dia']]),viajes=r2(V.mec,V[['viajes_mec']]))
Vd=D['2020-07-01':].copy();Vd['qb']=pd.qcut(Vd.q,5);qt=[]
for b,g in Vd.groupby('qb'):
    o=g[g.op_mec==1];qt.append(dict(rango=f'{int(b.left)}–{int(b.right)}',q50=int(g.q.median()),n=len(g),opera=round(g.op_mec.mean(),3),prog=round(g.prog.mean(),3),oper=round(g.oper.mean(),3),disp=round(g.disp.mean(),3),m3dia=round(o.mec.median()),volq=round(o.volquetas.median(),1)))
lib=(7-W.prog);yr=[]
for y,g in D['2019-09-01':].groupby(D['2019-09-01':].index.year):
    o=g[g.op_mec==1];n=len(g)
    yr.append(dict(anio=int(y),dias=n,opero=round(g.op_mec.mean()*7,2),prog=round(g.prog.mean()*7,2),oper=round(g.oper.mean()*7,2),disp=round(g.disp.mean()*7,2),m3dia=round(o.mec.median()),volq=round(o.volquetas.median(),1),mf_share=round(g.mf_mec.sum()/max(1,g.mec.sum()),2),hora=round(o.hora_inicio.median(),2) if o.hora_inicio.notna().any() else None,man_sem=round(g.man.sum()/n*7)))
E=dict(corte='2026-10-10',fuente='Hoja de viajes OT3_001 ajustada a las fechas de DatosExtracción',semanas=[d.strftime('%Y-%m-%d') for d in wk.index],dias={c:wk[c].astype(int).tolist() for c in cats},
  mec=[round(float(v)) for v in mec],volq=[int(v) for v in vq],viajes=[round(float(v),1) for v in vi],caudal=qt,anual=yr,libres26=round(float(lib.iloc[-26:].mean()),2),r2=R2,
  backtest=dict(base={'tot':[1615,1845],'mf':[885,998],'ma':[973,1110]},prog={'tot':[1397,1577],'mf':[773,858],'ma':[932,1043]},calendario={'tot':[1622,1834]},caudal_oraculo={'tot':[1600,1833]},oraculo_dias={'tot':[1188,1220]}))
json.dump(E,open('out/esfuerzo.json','w'),ensure_ascii=False,separators=(',',':'))
C=D[['op_mec','volquetas','viajes_mec','hora_inicio','causa','mf_mec','ma_mec','mf_man','ma_man','viajes_parihuela','viajes_lancha','viajes_cosechadora','org_ma_activas','org_mf_activas']].copy()
C['puerto']=D.puerto.astype(str).str.strip().str.replace(r'^Puerto\s+','',regex=True).str.rstrip('.').replace({'nan':''})
C.round(3).to_csv('out/esfuerzo_diario.csv',index_label='fecha')
print(R2,E['libres26']);print(pd.DataFrame(yr)[['anio','opero','prog','oper','disp','m3dia','mf_share']].to_string());print(pd.DataFrame(qt)[['rango','opera','disp','m3dia']].to_string())
