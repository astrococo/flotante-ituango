"""Compila la app en archivos separados: index.html (estructura y estilos), app.js (lógica) y datos/app/*.json (datos)."""
import json, re, hashlib, os
t=open('template.html').read()
js=t.split('<script>\n(function(){',1)[1].rsplit('})();\n</script>',1)[0]
def seg(a,b):
    i=js.index(a); j=js.index(b,i); return js[i:j]
parts=[seg('"use strict";','/* ---------- pronóstico ---------- */'),seg('/* ---------- charts helpers ---------- */','/* ---------- vistas ---------- */'),
       seg('function aggSeries','function renderModel'),seg('function renderReq','/* ---------- navegación ---------- */')]
JS='(function(){\n'+'\n'.join(parts)+open('v2/new.js').read().rsplit('</script>',1)[0]
JS=JS.replace("ticks:{callback:v=>nf(v)}}}}","ticks:{callback:v=>nf(v,(Math.abs(v)<5&&!Number.isInteger(v))?2:0)}}}}")
assert "const ORIG=JSON.parse(document.getElementById('payload').textContent);" in JS
JS=JS.replace("const ORIG=JSON.parse(document.getElementById('payload').textContent);","let ORIG=null;")
JS=JS.replace("r.src.esfuerzo=S.src.esfuerzo;","r.src.esfuerzo=S.src.esfuerzo;r.src.audit=S.src.audit;")
old="  (async()=>{await loadRepoExcel();await loadLive()})();"
assert old in JS
JS=JS.replace(old,"""  S.src._xlsxName='datos/DatosExtraccion.xlsx';S.src._repo=true;S.src._same=true;renderLive();
  loadLive();
  fetch('datos/app/extra.json?v=__VX__',{cache:'no-cache'}).then(r=>r.json()).then(x=>{Object.assign(ORIG,x);Object.assign(S.src,x);const h=(location.hash||'#pronostico').slice(1);if(['auditoria','operacion','pronostico'].includes(h))renderView(h)}).catch(()=>{});""")
old="if(window.Chart) init(); else window.addEventListener('load',init);"
assert old in JS
JS=JS.replace(old,"""fetch('datos/app/base.json?v=__VB__',{cache:'no-cache'}).then(r=>{if(!r.ok)throw new Error('HTTP '+r.status);return r.json()}).then(j=>{ORIG=j;init()})
  .catch(e=>{const m=document.getElementById('load-msg');if(m){m.hidden=false;m.textContent='No se pudieron cargar los datos ('+e.message+'). Recargue la página.'}});""")
assert JS.rstrip().endswith('})();') or True
head=open('v2/head.html').read(); body=open('v2/body.html').read()
body=body.replace('<script id="payload" type="application/json">__DATA__</script>','')
D=json.load(open('platform_data.json'))
D['params']=json.load(open('params_v21.json')); D['kgm3']=[160.0,160.0]
D['xlsx_sha']=hashlib.sha256(open('site/datos/DatosExtraccion.xlsx','rb').read()).hexdigest()
X={'audit':json.load(open('audit_ui.json')),'esfuerzo':json.load(open('prod/out/esfuerzo.json'))}
os.makedirs('site/datos/app',exist_ok=True)
dump=lambda o:json.dumps(o,ensure_ascii=False,separators=(',',':'))
b=dump(D); x=dump(X)
open('site/datos/app/base.json','w').write(b); open('site/datos/app/extra.json','w').write(x)
h=lambda s:hashlib.sha1(s.encode()).hexdigest()[:10]
JS=JS.replace('__VB__',h(b)).replace('__VX__',h(x)).replace('__XLSX_URL__','vendor/xlsx.full.min.js')
open('site/app.js','w').write(JS)
html=head.replace('__CHARTJS__','<script src="vendor/chart.umd.min.js" defer></script>\n<script src="app.js?v='+h(JS)+'" defer></script>')+body
html=html.replace('<main','<div id="load-msg" class="banner" hidden></div>\n<main',1) if '<main' in html else html
# quitar el </script> final del bloque viejo si quedó
html=html.rstrip()+'\n</body>\n</html>\n'
open('site/index.html','w').write(html)
for f in ['site/index.html','site/app.js','site/datos/app/base.json','site/datos/app/extra.json']: print(f,os.path.getsize(f)//1024,'KB')
