import pickle,re,zipfile,shutil,pandas as pd,numpy as np,warnings;warnings.filterwarnings('ignore')
P,AP=pickle.load(open('plan.pkl','rb'))
X=pd.read_csv('/home/claude/work/site/datos/extraccion_caudal_depurado.csv',parse_dates=['fecha']).set_index('fecha')
FILE={'mamec':'xl/worksheets/sheet3.xml','mfmec':'xl/worksheets/sheet4.xml','maman':'xl/worksheets/sheet5.xml','mfman':'xl/worksheets/sheet6.xml'}
SN={'mamec':'Viajes-Macrofitas_Mecanizado','mfmec':'Viajes-MF-Mecanizado-EPM','maman':'Viajes-diario-macrofitas_Manual','mfman':'Viajes-diario-MF_Manual'}
DSTY={'mamec':'458','mfmec':'402','maman':'402','mfman':'402'}
z=zipfile.ZipFile('prod.xlsx');XML={k:z.read(f).decode() for k,f in FILE.items()}
serial=lambda d:(pd.Timestamp(d)-pd.Timestamp('1899-12-30')).days
LOG=[]
def cell_re(ref): return re.compile(rf'<c r="{ref}"(?P<a>[^>]*?)(?:/>|>(?P<b>.*?)</c>)',re.S)
def set_cell(k,ref,val,keep_formula=False,style=None,num=True):
    s=XML[k];m=cell_re(ref).search(s)
    if not m: raise SystemExit(f'no existe {k} {ref}')
    a=m.group('a');b=m.group('b') or ''
    fm=re.search(r'<f[^>]*?(?:/>|>.*?</f>)',b,re.S)
    if fm and 'ref="' in fm.group(0):
        rr=re.search(r'ref="([A-Z]+\d+)(?::([A-Z]+\d+))?"',fm.group(0))
        if rr and rr.group(2) and not keep_formula: raise SystemExit(f'{k} {ref} es maestra de fórmula compartida {rr.group(0)}')
    sty=re.search(r's="(\d+)"',a);sty=style or (sty.group(1) if sty else None)
    f=fm.group(0) if (fm and keep_formula) else ''
    new=f'<c r="{ref}"'+(f' s="{sty}"' if sty else '')+f'>{f}<v>{val:.10g}</v></c>'
    XML[k]=s[:m.start()]+new+s[m.end():]
    return (b[:120])
for _,e in P.iterrows():
    k=e.hoja;ref=f'{e.col}{e.fila}'
    if e.col=='A':
        set_cell(k,ref,serial(e.despues),style=None);continue
    if k=='maman':   # S = R/160: se ajustan los kg (R) y el valor guardado de S
        kg=X.loc[pd.Timestamp(P[(P.hoja==k)&(P.fila==e.fila)&(P.col=='A')].despues.iloc[0]) if ((P.hoja==k)&(P.fila==e.fila)&(P.col=='A')).any() else None,'ma_man_kg'] if False else e.despues*160
        set_cell(k,f'R{e.fila}',kg);set_cell(k,f'S{e.fila}',e.despues,keep_formula=True)
    else: set_cell(k,ref,e.despues)
# maman filas 13–15 (registros de varios días): se reparten los viajes y se fechan
T=pickle.load(open('tidy.pkl','rb'))
spl={13:['2019-08-13','2019-08-14'],14:['2019-08-15','2019-08-16'],15:['2019-08-24','2019-08-26','2019-08-28']}
app=[]
for r,ds in spl.items():
    g=float(T['maman'][0].set_index('row').at[r,'G']);n=len(ds);gg=g/n
    set_cell('maman',f'A{r}',serial(ds[0]),style='402')
    set_cell('maman',f'G{r}',gg);set_cell('maman',f'L{r}',gg,keep_formula=True);set_cell('maman',f'O{r}',gg*80,keep_formula=True);set_cell('maman',f'R{r}',gg*80,keep_formula=True);set_cell('maman',f'S{r}',gg*80/160,keep_formula=True)
    LOG.append((SN['maman'],r,'A, G',f'«{T["maman"][0].set_index("row").at[r,"fecha_raw"]}», {g:g} viajes',f'{ds[0]}, {gg:.4g} viajes','Registro de varios días repartido en partes iguales, como en DatosExtracción'))
    for d in ds[1:]: app.append((d,gg,r))
s=XML['maman'];last=max(int(x) for x in re.findall(r'<row r="(\d+)"',s));rows=''
for i,(d,gg,r) in enumerate(app):
    n=last+1+i
    note=f'Ajuste: parte del registro de la fila {r} repartido para coincidir con DatosExtracción'
    rows+=(f'<row r="{n}" spans="1:26"><c r="A{n}" s="402"><v>{serial(d)}</v></c><c r="G{n}" s="528"><v>{gg:.10g}</v></c><c r="L{n}" s="528"><v>{gg:.10g}</v></c>'
           f'<c r="O{n}" s="403"><v>{gg*80:.10g}</v></c><c r="R{n}" s="499"><v>{gg*80:.10g}</v></c><c r="S{n}" s="499"><v>{gg*80/160:.10g}</v></c>'
           f'<c r="W{n}" t="inlineStr"><is><t>{note}</t></is></c></row>')
    LOG.append((SN['maman'],n,'fila nueva','—',f'{d}, {gg:.4g} viajes, {gg*80/160:.4g} m³',f'Parte del registro de la fila {r}'))
XML['maman']=s.replace('</sheetData>',rows+'</sheetData>',1)
XML['maman']=re.sub(r'<dimension ref="A1:Z\d+"/>',f'<dimension ref="A1:Z{last+len(app)}"/>',XML['maman'])
# empaquetar: sin calcChain y con recálculo al abrir
out=zipfile.ZipFile('out/OT3_001_Produccion_Diaria_10_10_2026_ajustado.xlsx','w',zipfile.ZIP_DEFLATED)
for i in z.infolist():
    if i.filename=='xl/calcChain.xml': continue
    d=z.read(i.filename)
    if i.filename in FILE.values(): d=XML[[k for k,f in FILE.items() if f==i.filename][0]].encode()
    elif i.filename=='[Content_Types].xml': d=re.sub(rb'<Override PartName="/xl/calcChain.xml"[^>]*/>',b'',d)
    elif i.filename=='xl/_rels/workbook.xml.rels': d=re.sub(rb'<Relationship [^>]*Target="calcChain.xml"[^>]*/>',b'',d)
    elif i.filename=='xl/workbook.xml': d=re.sub(rb'<calcPr([^>]*?)/>',lambda m:b'<calcPr'+m.group(1)+b' fullCalcOnLoad="1"/>',d)
    out.writestr(i,d)
out.close()
for _,e in P.iterrows():
    fmt=lambda v:str(pd.Timestamp(v).date()) if e.col=='A' else f'{v:.4g}'
    LOG.append((SN[e.hoja],e.fila,e.col if e.hoja!='maman' or e.col=='A' else 'R (kg) y S (m³)',fmt(e.antes),fmt(e.despues),e.motivo))
pickle.dump(LOG,open('log.pkl','wb'));print('cambios',len(LOG))
