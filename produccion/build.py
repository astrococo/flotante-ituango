import pickle,re,pandas as pd,numpy as np,warnings;warnings.filterwarnings('ignore')
from obs import norm,hora_inicio
T=pickle.load(open('tidy.pkl','rb'));R=pickle.load(open('mec.pkl','rb'))
num=lambda s:pd.to_numeric(s,errors='coerce').fillna(0)
COR=[]  # registro de correcciones
def fix_dates(k,df):
    df=df.copy()
    if k=='mamec':
        df.loc[df.row==1425,'fecha']=pd.Timestamp('2023-07-20');COR.append(('Viajes-Macrofitas_Mecanizado',1425,'Fecha 02/01/1900 → 20/07/2023 (entre 19 y 21 de julio)'))
        df=df[df.row!=1193];COR.append(('Viajes-Macrofitas_Mecanizado',1193,'Fila duplicada de 30/11/2022 (mismos viajes por volqueta, misma observación): se elimina; el informe la contaba como un día más (+102 m³) y corría un día las fechas siguientes'))
        df=df[~df.row.isin([2322,2323,2324])];COR.append(('Viajes-Macrofitas_Mecanizado','2322–2324','Tres filas extra con fecha 01/01/2026 (sin extracción, vacaciones): se eliminan; corrían las fechas del informe'))
    if k=='maman':
        df.loc[df.row==18,'fecha']=pd.Timestamp('2019-09-02');COR.append(('Viajes-diario-macrofitas_Manual',18,'Fecha 02/09/2020 → 02/09/2019 (orden de filas)'))
        extra=[]
        for r,dias in [(13,['2019-08-13','2019-08-14']),(14,['2019-08-15','2019-08-16']),(15,['2019-08-24','2019-08-26','2019-08-28'])]:
            base=df[df.row==r].iloc[0]
            for d in dias:
                e=base.copy();e['fecha']=pd.Timestamp(d)
                for c in ['L','O','R','S','E','F','G','C','D']:
                    if c in e and isinstance(e[c],(int,float)): e[c]=e[c]/len(dias)
                extra.append(e)
            COR.append(('Viajes-diario-macrofitas_Manual',r,f'Registro de varios días ({base.fecha_raw}) repartido en partes iguales'))
        df=pd.concat([df[~df.row.isin([13,14,15])],pd.DataFrame(extra)])
    if k=='mfman':
        df.loc[df.row==9,'fecha']=pd.Timestamp('2019-08-23');COR.append(('Viajes-diario-MF_Manual',9,'Fecha 23/08/2020 → 23/08/2019 (orden de filas)'))
    return df.dropna(subset=['fecha'])
# ---------- mecanizado: viajes físicos por volqueta y volumen ----------
mam,plm,trm=R['mamec'];mfm,plf,trf=R['mfmec']
mam=fix_dates('mamec',mam.assign(**{f'_t_{c}':trm[c] for c in plm}));mfm=fix_dates('mfmec',mfm.assign(**{f'_t_{c}':trf[c] for c in plf}))
# volumen MF faltante 3–9 abr 2026: viajes × m³/viaje de cada volqueta × 0,56 (fórmula vigente en filas vecinas)
ref=mfm[mfm.row==2414]['_f_AA'].iloc[0] if (mfm.row==2414).any() else None
co=dict((c,float(x)) for c,x in re.findall(r'\(([A-Z]+)\d+\*([\d.]+)\)',str(ref)))
mfm['vol']=mfm.vol_rep
for i in mfm.index[mfm.row.between(2415,2421)]:
    v=0.56*sum(co.get(c,17.0)*mfm.at[i,f'_t_{c}'] for c in plf);mfm.at[i,'vol']=v
COR.append(('Viajes-MF-Mecanizado-EPM','2415–2421',f'3–9 abr 2026: {mfm[mfm.row.between(2415,2421)].viajes_sum.sum():.0f} viajes registrados sin volumen (celda de m³ vacía). Se calcula con la fórmula de la fila 2414: {mfm[mfm.row.between(2415,2421)].vol.sum():,.0f} m³'))
for r in [1737,1738]:
    COR.append(('Viajes-MF-Mecanizado-EPM',r,'Volumen digitado sin viajes en día de descanso de EPM (73,9 y 110,9 m³): se mantiene, marcado como dudoso'))
for r in [1735,1736,1739]:
    COR.append(('Viajes-MF-Mecanizado-EPM',r,'Volumen digitado distinto de viajes × capacidad (fila con observación de volquetas varadas o en otras labores): se mantiene el valor digitado'))
def daily_mec(df,pl,vol,obs):
    g=df.groupby('fecha');out=pd.DataFrame({vol:g['vol'].sum() if 'vol' in df else g['vol_rep'].sum(),'obs_'+vol:g[obs].first()})
    for c,p in pl.items(): out[p+'_'+vol]=g[f'_t_{c}'].sum()
    out['puerto_'+vol]=g[{'mamec':'AC','mfmec':'AB'}['mamec' if vol=='ma_mec' else 'mfmec']].first()
    return out
mam['vol']=mam.vol_rep
A=daily_mec(mam,plm,'ma_mec','AE');B=daily_mec(mfm,plf,'mf_mec','AD')
M=A.join(B,how='outer')
plates=sorted(set(plm.values())|set(plf.values()))
for p in plates: M['v_'+p]=(M[p+'_ma_mec'].fillna(0) if p+'_ma_mec' in M else 0)+(M[p+'_mf_mec'].fillna(0) if p+'_mf_mec' in M else 0)
M['viajes_mec']=M[['v_'+p for p in plates]].sum(1);M['volquetas']=(M[['v_'+p for p in plates]]>0).sum(1)
M['obs_mec']=(M.obs_ma_mec.fillna('').astype(str)+' || '+M.obs_mf_mec.fillna('').astype(str)).str.strip(' |')
M['hora_inicio']=M.obs_mec.map(hora_inicio)
M['puerto']=M.puerto_ma_mec.fillna(M.puerto_mf_mec)
# ---------- manual ----------
mam_=fix_dates('maman',T['maman'][0]);mfm_=fix_dates('mfman',T['mfman'][0])
for c in ['B','C','D','E','F','G','H','I','J','K','L','M','N','O','P','Q','R','S','T']: mam_[c]=num(mam_[c])
for c in ['B','C','D','E','F','G','H','I','J']: mfm_[c]=num(mfm_[c])
g=mam_.groupby('fecha')
MA=pd.DataFrame({'ma_man':g.S.sum(),'ma_man_kg':g.R.sum(),'viajes_parihuela':g.L.sum(),'viajes_lancha':g.M.sum(),'viajes_cosechadora':g.N.sum(),
   'sector_ma':g.U.first(),'obs_ma_man':g.W.first()})
ORG={'C':'Aso Sabanalarga','D':'Aso Liborina','E':'Aso Ituango','F':'JAC Valle de Toledo','G':'Ecoambientamos','H':'JAC Angelina','J':'JAC Mogotes','B':'EPM cosechadora'}
for c,n in ORG.items(): MA['ma_'+n]=g[c].sum()
MA['org_ma_activas']=(MA[['ma_'+n for n in ORG.values()]]>0).sum(1)
g=mfm_.groupby('fecha')
MF=pd.DataFrame({'mf_man':g.J.sum(),'sector_mf':g.K.first(),'obs_mf_man':g.M.first()})
ORGF={'B':'Aso Sabanalarga','C':'Aso Liborina','D':'Aso Ituango','E':'Ecoambientamos','F':'JAC Valle de Toledo','G':'JAC Mogotes','H':'JAC Angelina'}
for c,n in ORGF.items(): MF['mf_'+n]=g[c].sum()
MF['org_mf_activas']=(MF[['mf_'+n for n in ORGF.values()]]>0).sum(1)
D=M.join(MA,how='outer').join(MF,how='outer')
D=D.reindex(pd.date_range('2019-07-03','2026-10-10'))
for c in ['ma_mec','mf_mec','ma_man','mf_man','viajes_mec','volquetas']: D[c]=D[c].fillna(0)
# acumulado mensual de dic-2019 (748 m³ el 28/12/2019): se reparte en diciembre, igual que en la depuración vigente
if D.loc['2019-12-28','mf_man']>=748-1e-6:
    D.loc['2019-12-28','mf_man']-=748;D.loc['2019-12-01':'2019-12-28','mf_man']+=748/28
    COR.append(('Viajes-diario-MF_Manual',128,'28/12/2019: 748 m³ = acumulado de viajes del mes (nota de la hoja). Se reparte en 28 días (26,71 m³/día)'))
D.index.name='fecha'
pickle.dump((D,COR,plates),open('daily.pkl','wb'))
print(D[['mf_man','mf_mec','ma_man','ma_mec']].sum().round(1).to_dict(), 'total',round(D[['mf_man','mf_mec','ma_man','ma_mec']].sum().sum(),1))
for c in COR: print(c)
