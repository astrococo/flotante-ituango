import pickle,re,collections,pandas as pd,numpy as np,datetime as dt
from openpyxl.utils import coordinate_to_tuple,get_column_letter
D=pickle.load(open('d1.pkl','rb'))
def grid(n):
    rows=collections.defaultdict(dict)
    for k,c in D[n]['cells'].items():
        r,cc=coordinate_to_tuple(k);rows[r][get_column_letter(cc)]=c
    return rows
def fecha(v):
    if isinstance(v,(dt.datetime,dt.date)): return pd.Timestamp(v)
    if isinstance(v,str):
        m=re.match(r'\s*(\d{1,2})/(\d{1,2})/(\d{4})',v)
        if m: return pd.Timestamp(int(m[3]),int(m[2]),int(m[1]))
    if isinstance(v,(int,float)) and 30000<v<50000: return pd.Timestamp('1899-12-30')+pd.Timedelta(days=v)
    return None
SPEC={'mamec':('Viajes-Macrofitas_Mecanizado',4),'mfmec':('Viajes-MF-Mecanizado-EPM',8),'maman':('Viajes-diario-macrofitas_Manual',8),'mfman':('Viajes-diario-MF_Manual',7)}
out={}
for k,(n,h) in SPEC.items():
    g=grid(n);hdr={c:str(v['v']).replace('\n',' ').strip() for c,v in g[h].items() if v['v'] is not None}
    recs=[]
    for r in sorted(g):
        if r<=h: continue
        f=fecha(g[r].get('A',{}).get('v'))
        rec=dict(row=r,fecha=f,fecha_raw=g[r].get('A',{}).get('v'))
        for c,v in g[r].items():
            if c=='A':continue
            rec[c]=v['v'];rec['_f_'+c]=v['f']
            if v['com']: rec['_com_'+c]=v['com']
        recs.append(rec)
    df=pd.DataFrame(recs);out[k]=(df,hdr);print(k,n,len(df),'filas; sin fecha:',df.fecha.isna().sum(),'rango',df.fecha.min(),df.fecha.max())
    print('   encabezados:',hdr)
pickle.dump(out,open('tidy.pkl','wb'))
