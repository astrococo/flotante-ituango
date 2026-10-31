import pickle,pandas as pd,numpy as np,warnings;warnings.filterwarnings('ignore')
OUT=pickle.load(open('alinear.pkl','rb'));T=pickle.load(open('tidy.pkl','rb'))
X=pd.read_csv('/home/claude/work/site/datos/extraccion_caudal_depurado.csv',parse_dates=['fecha']).set_index('fecha')
X=X[X.reportado==1]
CFG={'mfman':('J','mf_man_d',6),'mfmec':('AA','mf_mec_d',4),'maman':('S','ma_man_d',5),'mamec':('AB','ma_mec_d',3)}
E=[]  # (k,row,col,old,new,motivo)
APP=[]
for k,(vc,xc,sh) in CFG.items():
    A,_=OUT[k];A=A.copy();df=T[k][0].set_index('row')
    A['fh']=pd.to_datetime(A.fecha_hoja)
    A['nueva']=A.fh
    for i,r in A.iterrows():
        if r.n_ref==1: A.at[i,'nueva']=pd.Timestamp(r.fecha_informe)
        elif r.n_ref>1:
            ds=[pd.Timestamp(x) for x in r.fecha_informe];A.at[i,'nueva']=r.fh if r.fh in ds else ds[-1]
    for _,r in A[(A.nueva!=A.fh)&A.nueva.notna()].iterrows():
        E.append((k,r.row,'A',r.fh,r.nueva,'Fecha alineada con DatosExtracción (fila tomada por Info_día_PHI-integrado para ese día)'))
    t=X[xc].fillna(0)
    val=A.set_index('row').valor.copy();nueva=A.set_index('row').nueva
    # filas con dos referencias: el otro día necesita su valor
    for _,r in A[A.n_ref>1].iterrows():
        for d in [pd.Timestamp(x) for x in r.fecha_informe]:
            if d==nueva[r.row]: continue
            cand=A[(A.nueva==d)&(A.row!=r.row)]
            if len(cand)==1:
                rr=cand.row.iloc[0]
                if abs(val[rr]-r.valor)>1e-9: E.append((k,rr,vc,val[rr],r.valor,f'DatosExtracción repite aquí el valor de la fila {r.row} ({str(pd.Timestamp(r.fecha_hoja).date())}); esta fila tenía {val[rr]:g}'));val[rr]=r.valor
            else: APP.append((k,d,r.valor,f'Día que DatosExtracción toma de la fila {r.row} (repetida)'))
    s=pd.Series(val.values,index=nueva.values).groupby(level=0).sum()
    days=t.index.union(s.dropna().index)
    for d in days:
        if pd.isna(d): continue
        tv=t.get(d,0.0);sv=s.get(d,0.0)
        if abs(tv-sv)<=0.005: continue
        rows=A[A.nueva==d]
        if len(rows)==0: APP.append((k,d,tv,'Día presente en DatosExtracción sin fila en la hoja de viajes'));continue
        main=rows.sort_values('n_ref',ascending=False).row.iloc[0];others=[x for x in rows.row if x!=main]
        for o in others:
            if val[o]!=0: E.append((k,o,vc,val[o],0.0,'Fila que DatosExtracción no incluye (Info_día_PHI-integrado no la toma)'));val[o]=0.0
        cur=sum(val[x] for x in rows.row)
        if abs(cur-tv)>0.005: E.append((k,main,vc,val[main],tv,'Valor ajustado al de DatosExtracción'));val[main]=tv
P=pd.DataFrame(E,columns=['hoja','fila','col','antes','despues','motivo']);AP=pd.DataFrame(APP,columns=['hoja','fecha','valor','motivo'])
print(P.groupby(['hoja','col']).size().to_string());print(P[P.col!='A'].to_string()[:6000]);print(AP.to_string())
pickle.dump((P,AP),open('plan.pkl','wb'))
