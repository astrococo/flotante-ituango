"""Caudales medios diarios del IDEAM (bucket público s3-estacionesideam) para estaciones cercanas al embalse de Ituango.
Catálogo nacional de estaciones: datos.gov.co hp9r-jxuu. Salida en datos/ideam/."""
import os, io, json, urllib.request, urllib.parse, pandas as pd
O='datos/ideam'; os.makedirs(O,exist_ok=True)
log=open(f'{O}/registro.txt','w')
def L(*a): print(*a); log.write(' '.join(map(str,a))+'\n'); log.flush()
def get(u,t=120): return urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'flotante-ituango'}),timeout=t).read()
BB=(6.3,7.6,-76.3,-75.3)   # lat, lat, lon, lon: Cauca medio alrededor de Ituango
C=pd.DataFrame(json.loads(get('https://www.datos.gov.co/resource/hp9r-jxuu.json?$limit=20000')))
L('catálogo',len(C),list(C.columns))
lat=pd.to_numeric(C.get('latitud'),errors='coerce'); lon=pd.to_numeric(C.get('longitud'),errors='coerce')
E=C[lat.between(BB[0],BB[1])&lon.between(BB[2],BB[3])].copy()
E.to_csv(f'{O}/estaciones.csv',index=False); L('estaciones en el recuadro',len(E))
base='https://datos.ideam.gov.co/s3-estacionesideam/observaciones/historicos/csv/Q_MEDIA_D/'
res=[]
for r in E.itertuples():
    cod=str(r.codigo).zfill(10)
    try:
        b=get(base+f'{cod}-Q_MEDIA_D.csv'); open(f'{O}/q_{cod}.csv','wb').write(b)
        d=pd.read_csv(io.BytesIO(b)); res.append(dict(codigo=cod,nombre=getattr(r,'nombre',''),municipio=getattr(r,'municipio',''),filas=len(d),cols='|'.join(d.columns[:8])))
        L('ok',cod,getattr(r,'nombre',''),len(d))
    except Exception as e:
        if '404' not in str(e) and 'Not Found' not in str(e): L('error',cod,repr(e)[:150])
pd.DataFrame(res).to_csv(f'{O}/con_caudal.csv',index=False); L('estaciones con caudal diario',len(res))
