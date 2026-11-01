import pickle,pandas as pd,numpy as np,warnings;warnings.filterwarnings('ignore')
OUT=pickle.load(open('alinear.pkl','rb'));Dn,_=pickle.load(open('datos_refechados.pkl','rb'))
FIX={('mamec',1425):'2023-07-20',('maman',18):'2019-09-02',('mfman',9):'2019-08-23'}
CFG={'mfman':('J','mfman'),'mfmec':('AA','mfmec'),'maman':('S','maman'),'mamec':('AB','mamec')}
E=[];APP=[]
for k,(vc,dc) in CFG.items():
    A,_=OUT[k];A=A.copy();A['fh']=pd.to_datetime(A.fecha_hoja,errors='coerce')
    A['nueva']=[pd.Timestamp(FIX[(k,r)]) if (k,r) in FIX else f for r,f in zip(A.row,A.fh)]
    for _,r in A[(A.nueva!=A.fh)&A.nueva.notna()].iterrows(): E.append((k,r.row,'A',r.fh,r.nueva,'Fecha de la hoja corregida (fecha imposible o fuera de orden)'))
    t=Dn[dc];val=A.set_index('row').valor.copy()
    A=A[A.nueva.notna()]
    s=pd.Series(val[A.row].values,index=A.nueva.values).groupby(level=0).sum()
    for d in t.index.union(s.index):
        tv=t.get(d,0.0);sv=s.get(d,0.0)
        if abs(tv-sv)<=0.005: continue
        rows=A[A.nueva==d]
        if len(rows)==0: APP.append((k,d,tv));continue
        main=rows.sort_values('n_ref',ascending=False).row.iloc[0]
        for o in [x for x in rows.row if x!=main]:
            if val[o]!=0: E.append((k,o,vc,val[o],0.0,'Fila repetida o no incluida en DatosExtracción'));val[o]=0.0
        cur=sum(val[x] for x in rows.row)
        if abs(cur-tv)>0.005: E.append((k,main,vc,val[main],tv,'Valor ajustado al de DatosExtracción'));val[main]=tv
P=pd.DataFrame(E,columns=['hoja','fila','col','antes','despues','motivo']);AP=pd.DataFrame(APP,columns=['hoja','fecha','valor'])
print(P.groupby(['hoja','col']).size().to_string());print(P[P.col!='A'][['hoja','fila','antes','despues','motivo']].to_string()[:3500]);print(AP.to_string())
pickle.dump((P,AP),open('plan.pkl','wb'))
