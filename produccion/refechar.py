import pickle,pandas as pd,numpy as np,warnings;warnings.filterwarnings('ignore')
OUT=pickle.load(open('alinear.pkl','rb'))
X=pd.read_csv('/home/claude/work/site/datos/extraccion_caudal_depurado.csv',parse_dates=['fecha']).set_index('fecha')
X=X[X.reportado==1]
FIX={('mamec',1425):'2023-07-20',('maman',18):'2019-09-02',('mfman',9):'2019-08-23'}
CFG={'mfman':'mf_man_d','mfmec':'mf_mec_d','maman':'ma_man_d','mamec':'ma_mec_d'}
NEW={};MOV=[]
for k,xc in CFG.items():
    A,_=OUT[k];t=X[xc].fillna(0).copy()
    if k=='maman': kg=X['ma_man_kg'].fillna(0).copy()
    mp={}
    for _,r in A[A.n_ref==1].iterrows():
        di=pd.Timestamp(r.fecha_informe);fh=pd.Timestamp(FIX.get((k,r.row),r.fecha_hoja)) if pd.notna(r.fecha_hoja) or (k,r.row) in FIX else None
        if fh is None or fh.year<2019 or fh==di: continue
        mp[di]=fh
    s=pd.Series(0.0,index=t.index.union(pd.DatetimeIndex(sorted(set(mp.values())))).unique());sk=s.copy()
    for d,v in t.items():
        nd=mp.get(d,d);s[nd]+=v
        if k=='maman': sk[nd]+=kg[d]
        if nd!=d and v!=0: MOV.append((k,d,nd,v))
    NEW[k]=s
    if k=='maman': NEW['ma_kg']=sk
    print(k,'valores movidos (≠0):',sum(1 for m in MOV if m[0]==k),'| total antes',round(t.sum(),2),'después',round(s.sum(),2),'| desfases',pd.Series([(m[2]-m[1]).days for m in MOV if m[0]==k]).value_counts().head(5).to_dict())
D=pd.DataFrame(NEW).fillna(0).sort_index()
# fechas con fila: las de DatosExtracción más las que reciben valores
D=D[D.index.isin(X.index)|(D.abs().sum(1)>0)]
print('filas',len(D),'antes',len(X))
pickle.dump((D,MOV),open('datos_refechados.pkl','wb'))
