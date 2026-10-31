import pickle,re,pandas as pd,numpy as np,warnings;warnings.filterwarnings('ignore')
from obs import norm,hora_inicio
T=pickle.load(open('tidy_aj.pkl','rb'));R=pickle.load(open('mec_aj.pkl','rb'))
num=lambda s:pd.to_numeric(s,errors='coerce').fillna(0)
COR=[]  # registro de correcciones
def fix_dates(k,df):
    return df.dropna(subset=['fecha'])
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
mfm['vol']=mfm.vol_rep
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
D.index.name='fecha'
pickle.dump((D,COR,plates),open('daily_aj.pkl','wb'))
print(D[['mf_man','mf_mec','ma_man','ma_mec']].sum().round(1).to_dict(), 'total',round(D[['mf_man','mf_mec','ma_man','ma_mec']].sum().sum(),1))
for c in COR: print(c)
