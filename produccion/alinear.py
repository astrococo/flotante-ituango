import pickle,re,collections,pandas as pd,numpy as np,warnings;warnings.filterwarnings('ignore')
from openpyxl.utils import coordinate_to_tuple,get_column_letter
from tidy import fecha
D=pickle.load(open('d1.pkl','rb'));T=pickle.load(open('tidy.pkl','rb'))
g=collections.defaultdict(dict)
for k,c in D['Info_día_PHI-integrado']['cells'].items():
    r,cc=coordinate_to_tuple(k);g[r][get_column_letter(cc)]=c
X=pd.read_csv('/home/claude/work/site/datos/extraccion_caudal_depurado.csv',parse_dates=['fecha']).set_index('fecha')
SRC={'mfman':('D','C','J','mf_man_d','Viajes-diario-MF_Manual'),'mfmec':('F','C','AA','mf_mec_d','Viajes-MF-Mecanizado-EPM'),'maman':('L','I','S','ma_man_d','Viajes-diario-macrofitas_Manual'),'mamec':('N','I','AB','ma_mec_d','Viajes-Macrofitas_Mecanizado')}
OUT={}
for k,(ic,dc,vc,xc,sn) in SRC.items():
    df=T[k][0].set_index('row');v=pd.to_numeric(df[vc],errors='coerce').fillna(0)
    refs=collections.defaultdict(list)
    for r in sorted(g):
        if r<26: continue
        c=g[r].get(ic)
        if not c or not c['f']: continue
        m=re.search(r"'([^']+)'!([A-Z]+)(\d+)",c['f'])
        if m and m[1]==sn: refs[int(m[3])].append(fecha(g[r].get(dc,{}).get('v')))
    rows=[]
    for r in df.index:
        fr=df.at[r,'fecha'];ds=refs.get(r,[])
        rows.append(dict(row=r,fecha_hoja=fr,fecha_informe=ds[0] if len(ds)==1 else (ds if ds else None),n_ref=len(ds),valor=v[r]))
    A=pd.DataFrame(rows)
    # comparar: suma por fecha_informe (filas con 1 referencia) vs DatosExtracción
    one=A[A.n_ref==1].copy();one['f']=pd.to_datetime(one.fecha_informe)
    multi=A[A.n_ref>1];none_=A[(A.n_ref==0)&(A.valor!=0)]
    s=one.groupby('f').valor.sum()
    for _,r in multi.iterrows():
        for d in r.fecha_informe: s.loc[pd.Timestamp(d)]=s.get(pd.Timestamp(d),0)+r.valor
    t=X[xc].fillna(0);idx=t.index.union(s.index)
    dif=(s.reindex(idx,fill_value=0)-t.reindex(idx,fill_value=0));bad=dif[dif.abs()>0.01]
    shift=one[(one.f.notna())&(pd.to_datetime(one.fecha_hoja)!=one.f)&(one.valor.notna())]
    print(f'== {k}: filas {len(A)} | re-fechar {len(shift)} (con valor≠0: {(shift.valor!=0).sum()}) | referenciadas 2 veces {len(multi)} | no referenciadas con valor {len(none_)} | días donde aún no coincide {len(bad)}')
    print('   no coincide:',[(str(i.date()),round(x,2)) for i,x in bad.items()][:12])
    OUT[k]=(A,bad)
pickle.dump(OUT,open('alinear.pkl','wb'))
