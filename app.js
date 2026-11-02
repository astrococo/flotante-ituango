(function(){
"use strict";
let ORIG=null;
let S=null; // estado actual
const DAY=864e5;
const MES=['ene','feb','mar','abr','may','jun','jul','ago','sep','oct','nov','dic'];
const DOWL=['Lun','Mar','Mié','Jue','Vie','Sáb','Dom'];
const d0=s=>Date.UTC(+s.slice(0,4),+s.slice(5,7)-1,+s.slice(8,10));
const iso=t=>new Date(t).toISOString().slice(0,10);
const fmtD=t=>{const d=new Date(t);return d.getUTCDate()+' '+MES[d.getUTCMonth()]+' '+d.getUTCFullYear()};
const fmtDs=t=>{const d=new Date(t);return d.getUTCDate()+' '+MES[d.getUTCMonth()]};
const dowM=t=>(new Date(t).getUTCDay()+6)%7;
const nf=(v,dg=0)=>v==null||isNaN(v)?'–':v.toLocaleString('es-CO',{maximumFractionDigits:dg,minimumFractionDigits:dg});
const median=a=>{const b=a.filter(x=>x!=null&&!isNaN(x)).sort((x,y)=>x-y);if(!b.length)return NaN;const m=b.length>>1;return b.length%2?b[m]:(b[m-1]+b[m])/2};
const css=n=>getComputedStyle(document.documentElement).getPropertyValue(n).trim();

/* ---------- construcción del estado (depuración) ---------- */
function build(src){
  const D=src.data, n=D.n, t0=d0(D.start);
  const T=Array.from({length:n},(_,i)=>t0+i*DAY);
  const z=v=>v==null?0:v;
  const mf_man=D.mf_man.map(z), mf_mec=D.mf_mec.map(z), ma_man=D.ma_man.map(z), ma_mec=D.ma_mec.map(z);
  const rep=D.rep.slice();
  const mf=mf_man.map((v,i)=>v+mf_mec[i]), ma=ma_man.map((v,i)=>v+ma_mec[i]), tot=mf.map((v,i)=>v+ma[i]);
  let last=-1; for(let i=n-1;i>=0;i--) if(rep[i]){last=i;break}
  const first=rep.indexOf(1);
  // caudal Sitio Presa: observado o estimado desde Olaya (ajuste lineal) + interpolación corta
  const [a,b]=src.sp_fit;
  let q=D.sitiopresa.map((v,i)=>v!=null?v:(D.olaya[i]!=null?a*D.olaya[i]+b:null));
  q=interp(q,20);
  // regímenes sobre todo el registro (un día sin reporte cuenta como 0: no se extrajo)
  const iS=Math.max(0,first);
  const sinop=new Array(n).fill(0), mecoff=new Array(n).fill(0), op=new Array(n).fill(0);
  runFlag(i=>tot[i]===0,7,sinop,iS,last); runFlag(i=>mf_mec[i]+ma_mec[i]===0,10,mecoff,iS,last);
  for(let i=iS;i<=last;i++) op[i]=(sinop[i]||mecoff[i])?0:1;
  return {src,n,T,t0,mf_man,mf_mec,ma_man,ma_mec,mf,ma,tot,rep,last,first,q,olaya:D.olaya,pintada:D.pintada,nivel:D.nivel,spObs:D.sitiopresa,sinop,mecoff,op,iS,P:src.params,fc:src.forecast_snapshot};
}
function interp(a,lim){const o=a.slice();let i=0;while(i<o.length){if(o[i]==null){let j=i;while(j<o.length&&o[j]==null)j++;if(i>0&&j<o.length&&j-i<=lim){for(let k=i;k<j;k++)o[k]=o[i-1]+(o[j]-o[i-1])*(k-i+1)/(j-i+1)}i=j}else i++}return o}
function runFlag(isZero,minLen,out,i0,i1){let i=i0;while(i<=i1){if(isZero(i)){let j=i;while(j<=i1&&isZero(j))j++;if(j-i>=minLen)for(let k=i;k<j;k++)out[k]=1;i=j}else i++}}

/* ---------- agregación semanal (semanas lunes-domingo) ---------- */
function weekly(arr,opArr,i0,i1){ // devuelve [{end,sum,op,n}]
  const m=new Map();
  for(let i=i0;i<=i1;i++){const t=S.T[i];const end=t+(6-dowM(t))*DAY;let w=m.get(end);if(!w){w={end,sum:0,op:1,n:0};m.set(end,w)}w.sum+=arr[i];w.n++;if(!opArr[i])w.op=0}
  return [...m.values()].sort((x,y)=>x.end-y.end);
}


/* ---------- charts helpers ---------- */
const charts={};
function mk(id,cfg){return mkR(id,cfg)}
function baseOpts(extra){
  const fg=css('--muted'),grid=css('--line');
  Chart.defaults.font.family=css('--f-body').replace(/"/g,'');Chart.defaults.color=fg;
  return Object.assign({responsive:true,maintainAspectRatio:false,animation:false,interaction:{mode:'index',intersect:false},
    plugins:{legend:{labels:{boxWidth:10,boxHeight:10,usePointStyle:false}},tooltip:{callbacks:{label:c=>c.dataset.label+': '+nf(c.parsed.y,c.parsed.y<10?2:0)}}},
    scales:{x:{grid:{color:grid,drawTicks:false},ticks:{maxRotation:0,autoSkipPadding:14}},y:{grid:{color:grid},beginAtZero:true,ticks:{callback:v=>nf(v,(Math.abs(v)<5&&!Number.isInteger(v))?2:0)}}}},extra||{});
}


function aggSeries(agg,fromIdx){
  const keys=['mf_man','mf_mec','ma_man','ma_mec'];const g=new Map();
  for(let i=fromIdx;i<=S.last;i++){const t=S.T[i];const d=new Date(t);let k;
    if(agg==='D')k=t;else if(agg==='W')k=t+(6-dowM(t))*DAY;else k=Date.UTC(d.getUTCFullYear(),d.getUTCMonth(),1);
    let o=g.get(k);if(!o){o={k,q:0,qn:0};keys.forEach(x=>o[x]=0);g.set(k,o)}
    keys.forEach(x=>o[x]+=S[x][i]);if(S.q[i]!=null){o.q+=S.q[i];o.qn++}}
  return [...g.values()].sort((a,b)=>a.k-b.k);
}
function renderHist(){
  const agg=[...document.querySelectorAll('#hist-agg button')].find(b=>b.getAttribute('aria-pressed')==='true').dataset.v;
  const fy=+document.getElementById('hist-from').value;
  const fromIdx=Math.max(S.first,Math.round((Date.UTC(fy,0,1)-S.t0)/DAY));
  const A=aggSeries(agg,fromIdx);
  const lab=A.map(o=>{const d=new Date(o.k);return agg==='M'?MES[d.getUTCMonth()]+' '+String(d.getUTCFullYear()).slice(2):iso(o.k)});
  const o=baseOpts();o.scales.x.stacked=true;o.scales.y.stacked=true;o.scales.y.title={display:true,text:agg==='D'?'m³ por día':agg==='W'?'m³ por semana':'m³ por mes'};
  o.scales.y2={position:'right',grid:{drawOnChartArea:false},beginAtZero:true,title:{display:true,text:'m³/s'}};
  const bar=agg==='D'?{barPercentage:1,categoryPercentage:1}:{};
  mk('ch-hist',{data:{labels:lab,datasets:[
    Object.assign({type:'bar',label:'Flotante mecanizado',data:A.map(x=>x.mf_mec),backgroundColor:css('--mf'),stack:'s'},bar),
    Object.assign({type:'bar',label:'Flotante manual',data:A.map(x=>x.mf_man),backgroundColor:css('--mf2'),stack:'s'},bar),
    Object.assign({type:'bar',label:'Macrófitas mecanizado',data:A.map(x=>x.ma_mec),backgroundColor:css('--ma'),stack:'s'},bar),
    Object.assign({type:'bar',label:'Macrófitas manual',data:A.map(x=>x.ma_man),backgroundColor:css('--ma2'),stack:'s'},bar),
    {type:'line',label:'Caudal Sitio Presa (m³/s)',data:A.map(x=>x.qn?x.q/x.qn:null),borderColor:css('--flow'),backgroundColor:css('--flow'),borderWidth:agg==='D'?1:2,pointRadius:0,tension:.25,yAxisID:'y2'}]},options:o});
  // KPIs y año
  const sum=(k,i0=S.first)=>{let s=0;for(let i=i0;i<=S.last;i++)s+=S[k][i];return s};
  const tmf=sum('mf'),tma=sum('ma');
  document.getElementById('hist-kpis').innerHTML=[
    ['Total extraído',tmf+tma,`${fmtD(S.T[S.first])} – ${fmtD(S.T[S.last])}`],
    ['Material flotante',tmf,`manual ${nf(sum('mf_man'))} · mecanizado ${nf(sum('mf_mec'))}`],
    ['Macrófitas',tma,`manual ${nf(sum('ma_man'))} · mecanizado ${nf(sum('ma_mec'))}`],
    ['Promedio diario activo',(()=>{let s=0,c=0;for(let i=S.iS;i<=S.last;i++)if(S.op[i]){s+=S.tot[i];c++}return s/c})(),'días con operación activa']
  ].map(([l,v,s])=>`<div class="panel c3 kpi"><span class="lab">${l}</span><span class="val">${nf(v)} <small>m³</small></span><span class="rng">${s}</span></div>`).join('');
  const Y=new Map();for(let i=S.first;i<=S.last;i++){const y=new Date(S.T[i]).getUTCFullYear();let o=Y.get(y);if(!o){o={y,mf_man:0,mf_mec:0,ma_man:0,ma_mec:0,dias:0,q:0,qn:0};Y.set(y,o)}['mf_man','mf_mec','ma_man','ma_mec'].forEach(k=>o[k]+=S[k][i]);o.dias+=S.rep[i];if(S.q[i]!=null){o.q+=S.q[i];o.qn++}}
  document.getElementById('tbl-year').innerHTML='<thead><tr><th>Año</th><th>Días</th><th>Flotante</th><th>Macrófitas</th><th>Total</th><th>Q medio</th></tr></thead><tbody>'+
   [...Y.values()].map(o=>`<tr><td>${o.y}</td><td class="num">${o.dias}</td><td class="num">${nf(o.mf_man+o.mf_mec)}</td><td class="num">${nf(o.ma_man+o.ma_mec)}</td><td class="num"><b>${nf(o.mf_man+o.mf_mec+o.ma_man+o.ma_mec)}</b></td><td class="num">${nf(o.q/o.qn)}</td></tr>`).join('')+'</tbody>';
  // acumulado (cada 7 días)
  const L=[],c1=[],c2=[];let a=0,b=0;for(let i=S.first;i<=S.last;i++){a+=S.mf[i];b+=S.ma[i];if((i-S.first)%7===0||i===S.last){L.push(iso(S.T[i]));c1.push(a);c2.push(b)}}
  const oc=baseOpts();oc.scales.y.stacked=true;
  mk('ch-cum',{type:'line',data:{labels:L,datasets:[{label:'Flotante',data:c1,borderColor:css('--mf'),backgroundColor:css('--mf')+'55',fill:'origin',pointRadius:0},{label:'Macrófitas',data:c2,borderColor:css('--ma'),backgroundColor:css('--ma')+'55',fill:'-1',pointRadius:0}]},options:oc});
}

function renderRel(){
  const C=S.src.composites, E=S.src.extra;
  const thr=[...document.querySelectorAll('#cmp-thr button')].find(b=>b.getAttribute('aria-pressed')==='true').dataset.v;
  const c=C[thr];
  const o=baseOpts();o.scales.y.beginAtZero=false;o.scales.y.suggestedMin=.5;o.scales.y.suggestedMax=1.8;o.scales.y.title={display:true,text:'veces el ritmo de las 4 semanas previas'};
  o.plugins.tooltip.callbacks.label=x=>x.dataset.label+': '+nf(x.parsed.y,2)+'×';
  mk('ch-comp',{type:'bar',data:{labels:C.ventanas.map(v=>'día '+v),datasets:[
    {label:'Material flotante',data:c.mf,backgroundColor:css('--mf')},{label:'Macrófitas',data:c.ma,backgroundColor:css('--ma')},
    {type:'line',label:'Sin cambio',data:C.ventanas.map(()=>1),borderColor:css('--muted'),borderDash:[4,4],pointRadius:0,borderWidth:1}]},options:o});
  document.getElementById('comp-note').textContent=`${c.n} crecientes con operación normal en las 4 semanas previas: ${c.eventos.join(', ')}. Media geométrica de la razón entre la extracción después del pico y antes de él.`;
  const x=[...document.querySelectorAll('#lag-x button')].find(b=>b.getAttribute('aria-pressed')==='true').dataset.v;
  const L=E.lagcorr; const ol=baseOpts();ol.scales.y.beginAtZero=false;ol.scales.y.suggestedMin=-.3;ol.scales.y.suggestedMax=.3;ol.scales.y.title={display:true,text:'ρ de Spearman'};
  ol.plugins.tooltip.callbacks.label=v=>v.dataset.label+': '+nf(v.parsed.y,2);
  mk('ch-lag',{type:'line',data:{labels:[0,1,2,3,4,5,6,7,8].map(l=>l+' sem'),datasets:[
    {label:'Material flotante',data:L.mf[x],borderColor:css('--mf'),backgroundColor:css('--mf'),pointRadius:3},
    {label:'Macrófitas',data:L.ma[x],borderColor:css('--ma'),backgroundColor:css('--ma'),pointRadius:3},
    {label:'Total',data:L.tot[x],borderColor:css('--muted'),backgroundColor:css('--muted'),borderDash:[5,4],pointRadius:2}]},options:ol});
  document.getElementById('lag-note').textContent=`${E.n_weeks} semanas completas con operación activa desde 2021. Con esta muestra, |ρ| < 0,11 no es significativo al 5 %.`;
  // estacionalidad
  const m=Array.from({length:12},()=>({mf:0,ma:0,q:0,n:0,qn:0}));const i21=Math.round((d0('2021-01-01')-S.t0)/DAY);
  for(let i=i21;i<=S.last;i++){if(!S.op[i])continue;const k=new Date(S.T[i]).getUTCMonth();m[k].mf+=S.mf[i];m[k].ma+=S.ma[i];m[k].n++}
  for(let i=i21;i<S.n;i++){if(S.q[i]==null)continue;const k=new Date(S.T[i]).getUTCMonth();m[k].q+=S.q[i];m[k].qn++}
  const os=baseOpts();os.scales.y.title={display:true,text:'m³ por día'};os.scales.y2={position:'right',grid:{drawOnChartArea:false},beginAtZero:true,title:{display:true,text:'m³/s'}};
  mk('ch-season',{data:{labels:MES,datasets:[
    {type:'bar',label:'Flotante',data:m.map(v=>v.mf/v.n),backgroundColor:css('--mf')},{type:'bar',label:'Macrófitas',data:m.map(v=>v.ma/v.n),backgroundColor:css('--ma')},
    {type:'line',label:'Caudal Sitio Presa',data:m.map(v=>v.q/v.qn),borderColor:css('--flow'),backgroundColor:css('--flow'),yAxisID:'y2',tension:.3,pointRadius:3}]},options:os});
  const c21=C['2100'];
  document.getElementById('findings').innerHTML=`
   <div class="fl"><b>El caudal explica poco de la variación semanal.</b> La correlación entre caudal y volumen extraído no supera |ρ| = 0,2. El volumen registrado depende sobre todo de cuántos equipos y cuadrillas trabajaron, y los paros mecanizados coinciden con temporadas de caudal alto (mar–abr 2022, feb–jun 2025).</div>
   <div class="mf"><b>Después de crecientes grandes se extrae más material flotante.</b> Tras picos de Sitio Presa sobre 2 100 m³/s, la extracción de flotante se mantiene entre ${nf(Math.min(...c21.mf),2)} y ${nf(Math.max(...c21.mf),2)} veces el ritmo previo durante unas 8 semanas. La señal es consistente pero se basa en ${c21.n} eventos, por lo que su incertidumbre es alta.</div>
   <div class="ma"><b>Las crecientes reducen la extracción de macrófitas.</b> Las macrófitas caen a ${nf(Math.min(...c21.ma),2)}–${nf(Math.max(...c21.ma),2)} veces su ritmo previo después de crecientes, y su correlación con el exceso de caudal es negativa durante 2 a 5 semanas (ρ ≈ −0,18). Es coherente con el lavado de las masas flotantes aguas abajo.</div>
   <div class="wn"><b>La persistencia es la mejor información disponible.</b> El ritmo de las últimas semanas, combinado con el promedio de largo plazo, predice mejor que el caudal solo. El caudal se usa como ajuste fino, sobre todo para macrófitas.</div>`;
}

function renderQuality(){
  const tot=S.n, repd=S.rep.reduce((a,b)=>a+b,0);
  const span=S.last-S.first+1, miss=span-S.rep.slice(S.first,S.last+1).reduce((a,b)=>a+b,0);
  let z=0,zop=0;for(let i=S.iS;i<=S.last;i++){if(S.tot[i]===0){z++;if(S.op[i])zop++}}
  let so=0,mo=0;for(let i=S.iS;i<=S.last;i++){so+=S.sinop[i];mo+=S.mecoff[i]&&!S.sinop[i]?1:0}
  document.getElementById('q-kpis').innerHTML=[
    ['Días reportados',repd,`de ${span} días calendario`],['Días sin reporte',miss,'se cuentan como 0 m³ (no se extrajo)'],
    ['Días sin operación',so,'7 o más días seguidos con total = 0'],['Días con mecanizado detenido',mo,'10 o más días sin extracción mecanizada']
  ].map(([l,v,s])=>`<div class="panel c3 kpi"><span class="lab">${l}</span><span class="val">${nf(v)}</span><span class="rng">${s}</span></div>`).join('');
  document.getElementById('q-steps').innerHTML=`<h3>Tratamiento aplicado</h3><ul>
   <li><b>Calendario continuo.</b> Se reconstruyó un día por fecha desde el primer registro. Los ${miss} días sin reporte (todos en julio–agosto de 2019) significan que no se extrajo: se cuentan como 0 m³ y se mantienen en el análisis, marcados como «sin reporte».</li>
   <li><b>Registro completo.</b> El análisis usa todo el registro, desde el 3 de julio de 2019. Los acumulados del archivo (versión del 30 de octubre) cuadran con los avances diarios en todas las fechas. Los avances diarios son la fuente de verdad; el acumulado se usa para verificar y para rellenar avances vacíos.</li>
   <li><b>Valores diarios vacíos.</b> Dos avances diarios nulos (30 ago 2019 y 8 sep 2020) se recalcularon como la diferencia de acumulados. Después de eso, la suma de avances diarios coincide con el último acumulado en las cuatro series.</li>
   <li><b>Macrófitas en kg.</b> La extracción manual en kg equivale a m³ con una densidad constante de 160 kg/m³ en todos los registros; se usa la columna en m³.</li>
   <li><b>Ceros con significado distinto.</b> Un cero aislado es un día sin extracción; una racha de 7 días o más con total cero es un periodo sin operación, y una racha de 10 días o más sin mecanizado es un paro de equipos. Esos periodos se excluyen al ajustar el modelo para no confundir falta de esfuerzo con falta de material.</li>
   <li><b>Caudal.</b> Promedio diario de los registros de 15 minutos de HydroForecast. Sitio Presa falta en ${nf(S.spObs.filter((v,i)=>v==null&&i<=S.last).length)} días; se completa con Q = 1,049·Q<sub>Olaya</sub> + 30 (correlación 0,99). Huecos de hasta 20 días se interpolan.</li></ul>`;
  const dw=S.P;const od=baseOpts();od.scales.y.beginAtZero=false;od.scales.y.suggestedMin=.6;od.scales.y.ticks={...(od.scales.y.ticks||{}),callback:v=>nf(v,1)};od.plugins.tooltip.callbacks.label=c=>c.dataset.label+': '+nf(c.parsed.y,2);
  mk('ch-dow',{type:'bar',data:{labels:DOWL,datasets:[{label:'Flotante',data:dw.mf_tot.dow,backgroundColor:css('--mf')},{label:'Macrófitas',data:dw.ma_tot.dow,backgroundColor:css('--ma')}]},options:od});
  // periodos
  const runs=(arr)=>{const r=[];let i=S.iS;while(i<=S.last){if(arr[i]){let j=i;while(j<=S.last&&arr[j])j++;r.push([i,j-1]);i=j}else i++}return r};
  const R=[...runs(S.sinop).map(r=>['Sin operación',...r]),...runs(S.mecoff).filter(r=>!(S.sinop[r[0]]&&S.sinop[r[1]])).map(r=>['Mecanizado detenido',...r])].sort((a,b)=>a[1]-b[1]);
  document.getElementById('tbl-periods').innerHTML='<thead><tr><th>Tipo</th><th>Desde</th><th>Hasta</th><th>Días</th><th>Q medio m³/s</th></tr></thead><tbody>'+
   R.map(([k,a,b])=>{let q=0,c=0;for(let i=a;i<=b;i++)if(S.q[i]!=null){q+=S.q[i];c++}return `<tr><td><span class="tag ${k==='Sin operación'?'bad':'warn'}">${k}</span></td><td>${fmtD(S.T[a])}</td><td>${fmtD(S.T[b])}</td><td class="num">${b-a+1}</td><td class="num">${nf(q/c)}</td></tr>`}).join('')+'</tbody>';
  const QA=S.src.qc_acum||[];
  document.getElementById('tbl-acum').innerHTML='<thead><tr><th>Serie</th><th>Avances vacíos</th><th>Suma de avances m³</th><th>Último acumulado m³</th><th>Desviación máx. m³</th><th>Quiebres</th><th>Fechas</th><th>Estado</th></tr></thead><tbody>'+
   QA.map(q=>{const ok=Math.abs(q.suma-q.acum)<0.5,cl=ok&&q.quiebres===0?'ok':ok?'warn':'bad';
     return `<tr><td>${q.serie}</td><td class="num">${q.nulos}</td><td class="num">${nf(q.suma,1)}</td><td class="num">${nf(q.acum,1)}</td><td class="num">${nf(q.max_desv,1)}</td><td class="num">${q.quiebres}</td><td style="white-space:normal;text-align:left;min-width:180px">${q.fechas.slice(0,3).map(f=>fmtD(d0(f))).join(', ')+(q.quiebres>3?' …':'')||'—'}</td><td><span class="tag ${cl}">${cl==='ok'?'Cuadra':cl==='warn'?'Cuadra al final, con quiebres':'No cuadra'}</span></td></tr>`}).join('')+'</tbody>';
  drawRegime();
}
function drawRegime(){
  const cv=document.getElementById('regime');const y0=new Date(S.T[S.first]).getUTCFullYear(),y1=new Date(S.T[S.last]).getUTCFullYear();
  const rows=y1-y0+1,cw=3,lw=44,rh=18,gap=4,W=lw+366*cw,H=rows*(rh+gap)+18,dpr=window.devicePixelRatio||1;
  cv.width=W*dpr;cv.height=H*dpr;cv.style.width=W+'px';cv.style.maxWidth='none';cv.style.height=H+'px';
  const g=cv.getContext('2d');g.scale(dpr,dpr);g.clearRect(0,0,W,H);
  const col={op:css('--ok'),mec:css('--warn'),sin:css('--bad'),nr:css('--line'),pre:css('--surface2')};
  g.font='11px '+css('--f-mono').split(',')[0].replace(/"/g,'');g.fillStyle=css('--muted');
  for(let y=y0;y<=y1;y++){g.fillText(String(y),0,(y-y0)*(rh+gap)+rh-5)}
  MES.forEach((m,k)=>{const x=lw+((Date.UTC(2021,k,1)-Date.UTC(2021,0,1))/DAY)*cw;g.fillText(m,x,H-4)});
  for(let i=S.first;i<=S.last;i++){const d=new Date(S.T[i]);const r=d.getUTCFullYear()-y0;const doy=(S.T[i]-Date.UTC(d.getUTCFullYear(),0,1))/DAY;
    let c=!S.rep[i]?col.nr:i<S.iS?col.pre:S.sinop[i]?col.sin:S.mecoff[i]?col.mec:col.op;
    g.fillStyle=c;g.globalAlpha=(c===col.op&&S.tot[i]===0)?.35:1;g.fillRect(lw+doy*cw,r*(rh+gap),cw,rh)}
  g.globalAlpha=1;
  document.getElementById('reg-legend').innerHTML=[[col.op,'Operación activa'],[col.op+'59','Operación activa, día con cero'],[col.mec,'Mecanizado detenido'],[col.sin,'Sin operación'],[col.nr,'Sin reporte (= 0 m³)'],[col.pre,'Antes del primer registro']].map(([c,l])=>`<span><i class="sw" style="background:${c}"></i>${l}</span>`).join('');
}


function renderReq(){
  const R=[
   ['Recibido','Esfuerzo de extracción diario','Recibido el 31-oct-2026 (producción diaria OT3_001, viajes por volqueta y por organización, corte 10-oct-2026). Falta: horas efectivas y personas por cuadrilla manual. Ver Operación.'],
   ['Alta','Plan semanal de descansos de EPM','Días sin extracción mecanizada ya programados para las próximas semanas. Es lo único que mejoró el pronóstico de forma significativa (−15 a −16 % de error en el total). Se ingresa en Pronóstico.'],
   ['Media','Causa de los días sin extracción con lista fija','Las observaciones permiten clasificar casi todos los días, pero en texto libre (100 días sin texto y 36 sin causa clara). Una lista fija evitaría la interpretación.'],
   ['Media','Volumen medido y composición por viaje','Hoy el volumen es viajes × capacidad nominal y la parte de flotante del mecanizado se estima (60/40 en volquetas mixtas). Medir algunas cargas y registrar la composición por viaje.'],
   ['Media','Inventario observado en la cola','La vegetación flotante ya se mide con Sentinel-2, Landsat y radar (pestaña Satélite). Falta lo que el satélite no ve: madera y residuos (dron o imágenes de 3 m) y el espesor de la mancha para pasar de hectáreas a m³.'],
   ['Recibido','Ubicación de la extracción y del depósito','Recibida el 1-nov-2026 (punto de extracción en la margen derecha, ~900 m aguas arriba de la barrera, y depósito). La barrera se ubicó en las imágenes. Falta: confirmar en campo el trazado de la barrera (hoy ±20 m) y si hay más de una.'],
   ['Media','Composición del material flotante','Fracción de troncos, ramas, residuos sólidos y plásticos. Los troncos llegan con crecientes; los residuos urbanos responden más a la lluvia local y a los primeros eventos de la temporada.'],
   ['Media','Caudal de afluentes cercanos a la cola','Caudal de los ríos San Andrés, Ituango y Espíritu Santo. HydroForecast no los mide: tiene pluviómetros (14 días en la API), Cauca aguas arriba (La Virginia, Bolombolo; 30 días) y lluvia pronosticada (WRF, GEFS, AIFS). La lluvia histórica (CHIRPS, IMERG y NASA POWER, 2019–2026) se evaluó y no mejoró el pronóstico: el caudal ya la integra. Ver Auditoría.'],
   ['Media','Operación del embalse','Nivel horario, caudal turbinado y vertido. Cambios de nivel desplazan la cola y concentran o dispersan el material.'],
   ['Baja','Variables para macrófitas','Temperatura del agua, nutrientes (fósforo y nitrógeno), transparencia y cobertura de buchón o lechuga de agua. Su crecimiento es biológico y el caudal solo explica el lavado.'],
   ['Baja','Viento en el embalse','Dirección y velocidad del viento, que empujan las masas flotantes hacia la cola o hacia la presa.']];
  document.getElementById('req-list').innerHTML=R.map(([p,t,d])=>`<li><span class="prio tag ${p==='Alta'?'bad':p==='Media'?'warn':p==='Recibido'?'ok':''}">${p}</span><b>${t}.</b> ${d}</li>`).join('');
}

/* ---------- carga de archivos ---------- */
function parseXlsx(buf,name){
  const wb=XLSX.read(buf,{type:'array',cellDates:true});
  const find=re=>wb.SheetNames.find(s=>re.test(s.normalize('NFD').replace(/[̀-ͯ]/g,'').toLowerCase()));
  const sMF=find(/flotante/),sMA=find(/macrofit/);
  if(!sMF||!sMA) throw new Error('No se encontraron las hojas «Material Flotante» y «Macrófitas».');
  const rows=s=>XLSX.utils.sheet_to_json(wb.Sheets[s],{header:1,raw:true}).slice(3).filter(r=>r[0]!=null&&r[0]!=='');
  const toT=v=>v instanceof Date?Date.UTC(v.getFullYear(),v.getMonth(),v.getDate()):typeof v==='number'?Math.round((v-25569))*DAY:d0(String(v));
  const num=v=>v==null||v===''||isNaN(+v)?null:+v;
  const mfR=rows(sMF).map(r=>({t:toT(r[0]),man:num(r[1]),manA:num(r[2]),mec:num(r[3]),mecA:num(r[4])}));
  const maR=rows(sMA).map(r=>({t:toT(r[0]),man:num(r[3]),manA:num(r[4]),mec:num(r[5]),mecA:num(r[6])}));
  const fix=R=>{for(let i=0;i<R.length;i++){for(const [d,a] of [['man','manA'],['mec','mecA']]){if(R[i][d]==null&&i>0&&R[i][a]!=null&&R[i-1][a]!=null)R[i][d]=Math.max(0,R[i][a]-R[i-1][a]);if(R[i][d]==null)R[i][d]=0}}return R};
  const nulls=R=>({man:R.filter(r=>r.man==null).length,mec:R.filter(r=>r.mec==null).length});
  const nMF0=nulls(mfR),nMA0=nulls(maR);
  fix(mfR);fix(maR);
  const chk=(serie,R,d,a,nn)=>{let cs=0,prev=0,mx=0,qb=0;const fz=[];for(const r of R){cs+=r[d]||0;const res=r[a]==null?prev:r[a]-cs;mx=Math.max(mx,Math.abs(res));if(Math.abs(res-prev)>0.01){qb++;if(fz.length<5)fz.push(new Date(r.t).toISOString().slice(0,10))}prev=res}
    const lastA=[...R].reverse().find(r=>r[a]!=null);return {serie,nulos:nn,suma:Math.round(cs*100)/100,acum:lastA?lastA[a]:0,max_desv:Math.round(mx*100)/100,quiebres:qb,fechas:fz}};
  const qcA=[chk('Flotante · manual',mfR,'man','manA',nMF0.man),chk('Flotante · mecanizado',mfR,'mec','mecA',nMF0.mec),chk('Macrófitas · manual',maR,'man','manA',nMA0.man),chk('Macrófitas · mecanizado',maR,'mec','mecA',nMA0.mec)];
  const src=JSON.parse(JSON.stringify(ORIG));const D=src.data;const t0=d0(D.start);
  const tmax=Math.max(...mfR.map(r=>r.t),...maR.map(r=>r.t));
  const n=Math.max(D.n,Math.round((tmax-t0)/DAY)+1);
  ['mf_man','mf_mec','ma_man','ma_mec'].forEach(k=>D[k]=new Array(n).fill(null));D.rep=new Array(n).fill(0);
  ['olaya','pintada','sitiopresa','nivel','olaya_max'].forEach(k=>{while(D[k].length<n)D[k].push(null)});
  for(const r of mfR){const i=Math.round((r.t-t0)/DAY);if(i<0)continue;D.mf_man[i]=r.man;D.mf_mec[i]=r.mec;D.rep[i]=1}
  for(const r of maR){const i=Math.round((r.t-t0)/DAY);if(i<0)continue;D.ma_man[i]=r.man;D.ma_mec[i]=r.mec;D.rep[i]=1}
  const kr=rows(sMA).map(r=>[num(r[1]),num(r[3])]).filter(x=>x[0]!=null&&x[1]>0).map(x=>x[0]/x[1]);
  D.n=n;src._xlsxName=name;src.qc_acum=qcA;src.kgm3=kr.length?[Math.min(...kr),Math.max(...kr)]:null;return {src,nMF:mfR.length,nMA:maR.length};
}
function applyJSON(txt){
  const j=JSON.parse(txt);const data=j.data||j;if(!Array.isArray(data)||!data.length)throw new Error('El JSON no tiene una lista «data».');
  const k=Object.keys(data[0]);const src=S.src;
  if(k.some(x=>/pred_mean/.test(x))){
    const g=(r,a)=>r[a]!=null?Math.round(r[a]):null;
    src.forecast_snapshot={generated_at:j.generated_at||new Date().toISOString(),source:'HydroForecast Ituango · JSON pegado',
      fecha:data.map(r=>String(r.timestamp).slice(0,10)),sp:data.map(r=>g(r,'QSitioPresa_pred_mean')??Math.round(1.0493*r.QOlaya_pred_mean+30.08)),
      ol:data.map(r=>g(r,'QOlaya_pred_mean')),ol_min:data.map(r=>g(r,'QOlaya_pred_min')??g(r,'QOlaya_pred_mean')),ol_max:data.map(r=>g(r,'QOlaya_pred_max')??g(r,'QOlaya_pred_mean')),pi:[],pi_min:[],pi_max:[]};
    return `Pronóstico cargado: ${data.length} días desde ${src.forecast_snapshot.fecha[0]}.`;
  }
  if(k.some(x=>/_obs$/.test(x))){
    const D=src.data,t0=d0(D.start);let c=0;
    for(const r of data){const i=Math.round((d0(String(r.timestamp).slice(0,10))-t0)/DAY);if(i<0)continue;
      while(D.olaya.length<=i){['olaya','pintada','sitiopresa','nivel','olaya_max','mf_man','mf_mec','ma_man','ma_mec'].forEach(x=>D[x].push(null));D.rep.push(0);D.n++}
      if(r.QOlaya_obs!=null)D.olaya[i]=Math.round(r.QOlaya_obs);if(r.QSitioPresa_obs!=null)D.sitiopresa[i]=Math.round(r.QSitioPresa_obs);if(r.QPintada_obs!=null)D.pintada[i]=Math.round(r.QPintada_obs);c++}
    return `Caudal observado actualizado en ${c} días.`;
  }
  throw new Error('No se reconoce el formato. Use quarterly_outlook o observed/daily.');
}


/* ================= v2: pronóstico, vistas nuevas, caudal en vivo, tema ================= */
function flowSeries(scen){ // caudal diario Sitio Presa observado + pronosticado
  const F=S.fc, map=new Map();
  for(let i=0;i<S.n;i++) if(S.q[i]!=null) map.set(S.T[i],S.q[i]);
  let endT=S.T[S.n-1];
  F.fecha.forEach((f,k)=>{const t=d0(f);let v=F.sp[k];
    if(scen==='low') v=(F.sp_min&&F.sp_min[k]!=null)?F.sp_min[k]:v*F.ol_min[k]/F.ol[k];
    if(scen==='high') v=(F.sp_max&&F.sp_max[k]!=null)?F.sp_max[k]:v*F.ol_max[k]/F.ol[k];
    if(!Number.isFinite(v)) return; if(!map.has(t)) map.set(t,v); if(t>endT) endT=t});
  return {map,endT};
}
function parosFactor(arr){ // razón (todas las semanas)/(semanas con operación) en las últimas N semanas completas
  const N=(S.P.factor_paros_ventana)||104;
  const W=weekly(arr,S.op,S.iS,S.last).filter(w=>w.n===7&&w.end<=S.T[S.last]).slice(-N);
  const all=W.reduce((a,w)=>a+w.sum,0)/Math.max(1,W.length), act=W.filter(w=>w.op===1), ma=act.reduce((a,w)=>a+w.sum,0)/Math.max(1,act.length);
  return ma>0?Math.min(1,all/ma):1;
}
function forecast(scen){
  const out={days:[],blocks:[]}; const lastT=S.T[S.last]; const {map,endT}=flowSeries(scen);
  const comps={mf_tot:S.mf,ma_tot:S.ma}, res={};
  for(const [y,arr] of Object.entries(comps)){
    const p=S.P[y]; const k=p.k??1;
    const W=weekly(arr,S.op,S.iS,S.last).filter(w=>w.n===7&&w.end<=lastT);
    const Wo=W.filter(w=>w.op===1);
    const L8=median(Wo.slice(-8).map(w=>w.sum));
    // v2.2 (flotante): nivel por media exponencial de semanas con operación completa (vida media p.ewma_hl semanas, igual que pandas ewm adjust=True)
    let EW=null; if(p.ewma_hl){const g=Math.pow(0.5,1/p.ewma_hl);let num=0,den=0,wt=1;for(let i=Wo.length-1;i>=0;i--){num+=wt*Wo[i].sum;den+=wt;wt*=g}EW=den?num/den:null}
    const LT=median(Wo.filter(w=>w.end>=d0(p.lt_desde||'2020-07-01')).map(w=>w.sum));
    const xw=new Map(); for(const [t,v] of map){const e=t+(6-dowM(t))*DAY;xw.set(e,(xw.get(e)||0)+Math.max(v-p.qc,0)/1000)}
    const days=[];
    for(let t=lastT+DAY;t<=endT;t+=DAY){
      const h=Math.ceil((t-lastT)/DAY/7); const we=t+(6-dowM(t))*DAY;
      let lin=p.b0; for(let l=0;l<7;l++) lin+=p.beta[l]*(xw.get(we-l*7*DAY)||0);
      const mult=p.usa_caudal===false?1:Math.min(1.5,Math.max(0.7,Math.sqrt(Math.exp(lin))));
      let fw;
      if(EW!=null&&p.a_h){const hh=Math.min(h,13)-1,a=p.a_h[hh],sh=p.shrink??0,w1=(p.mezcla&&p.mezcla.w1)||0,a8=p.a8_h?p.a8_h[hh]:0;
        fw=(w1*(a8*L8+(1-a8)*LT)+(1-w1)*((1-sh)*(a*EW+(1-a)*LT)+sh*LT))*mult}
      else{const ah=k*p.a1*Math.exp(-(h-1)/p.tau);fw=(ah*L8+(1-ah)*LT)*mult}
      days.push({t,h,f:fw/7*p.dow[dowM(t)],mult,fw});
    }
    res[y]={L8,LT,EW,k,days};
  }
  const nd=res.mf_tot.days.length;
  for(let i=0;i<nd;i++){const a=res.mf_tot.days[i],b=res.ma_tot.days[i];out.days.push({t:a.t,h:a.h,mf:a.f,ma:b.f,mmf:a.mult,mma:b.mult,q:map.get(a.t)})}
  const qk=(y,h,qq)=>S.P[y].q[qq][Math.min(h,13)-1], rk=(y,h)=>(S.P[y].rmean||S.P[y].q['0.5'])[Math.min(h,13)-1];
  const H=Math.ceil(nd/7);
  for(let h=1;h<=H;h++){
    const ds=out.days.filter(d=>d.h===h); if(!ds.length) continue;
    const b={h,t0:ds[0].t,t1:ds[ds.length-1].t,nd:ds.length,q:0,mmf:0,mma:0};
    let qn=0; ds.forEach(d=>{if(d.q!=null){b.q+=d.q;qn++}b.mmf+=d.mmf/ds.length;b.mma+=d.mma/ds.length}); b.q=qn?b.q/qn:null;
    for(const [c,y] of [['mf','mf_tot'],['ma','ma_tot']]){
      const raw=ds.reduce((s,d)=>s+d[c],0), sc=ds.length/7, wk=raw/sc; // escala semanal (bloque incompleto)
      const cal=r=>Math.max(0,((wk+50)*r-50)*sc);
      b[c+'_raw']=raw;
      ['0.1','0.25','0.5','0.75','0.9'].forEach(qq=>b[c+'_p'+Math.round(+qq*100)]=cal(qk(y,h,qq)));
      b[c]=b[c+'_p50']; b[c+'_e']=cal(rk(y,h));
    }
    b.tot=b.mf+b.ma; b.tot_e=b.mf_e+b.ma_e; ['p10','p25','p50','p75','p90'].forEach(x=>b['tot_'+x]=b['mf_'+x]+b['ma_'+x]);
    out.blocks.push(b);
  }
  // ajuste opcional por descanso programado de EPM (días sin extracción ya conocidos). Backtest 2022–2026: −13 a −15 % de error en el total
  const RP=restPlan(), L26=(S.src.esfuerzo&&S.src.esfuerzo.libres26)||6.7;
  out.blocks.forEach(b=>{const r=RP[Math.min(b.h,5)-1]; b.adj=1; b.rest=null;
    if(r==null||!(r>=0)) return; const rr=Math.min(b.nd,r*b.nd/7); b.rest=r; b.adj=Math.max(0,(b.nd-rr)/(L26*b.nd/7));
    Object.keys(b).forEach(k=>{if(/^(mf|ma|tot)(_|$)/.test(k)&&typeof b[k]==='number')b[k]*=b.adj})});
  out.res=res; out.lastT=lastT; out.endT=endT;
  out.fp={mf:parosFactor(S.mf),ma:parosFactor(S.ma)};
  // parada por caudal alto (seguridad de las lanchas): factor por días de la semana sobre el umbral, según el pronóstico de caudal
  const PC=S.P.parada_caudal;
  out.blocks.forEach(b=>{const ds=out.days.filter(d=>d.t>=b.t0&&d.t<=b.t1);const n=ds.filter(d=>d.q!=null&&d.q>(PC?PC.umbral:1e9)).length*7/Math.max(1,ds.length);
    const c=n<0.5?0:n<=3.5?1:2; b.d_alto=Math.round(n); b.ff_mf=PC?PC.mf[c]:1; b.ff_ma=PC?PC.ma[c]:1;
    b.mf_ep=b.mf_e*out.fp.mf*b.ff_mf; b.ma_ep=b.ma_e*out.fp.ma*b.ff_ma; b.tot_ep=b.mf_ep+b.ma_ep});
  let pk={v:-1,t:null}; for(const [t,v] of map){if(t>=lastT-56*DAY&&Number.isFinite(v)&&v>pk.v)pk={v,t}} out.qpk=pk;
  return out;
}

/* ---------- estado de caudal en vivo ---------- */
const LIVE={state:'fallback',when:null,src:null,err:null,obsDays:0};
const DEF_API='https://jdguarnizor-hydroforecast-ituango.hf.space';
function apiBase(){try{return localStorage.getItem('mfi-api')||DEF_API}catch(e){return DEF_API}}
async function fetchJSON(u,ms){const c=new AbortController();const to=setTimeout(()=>c.abort(),ms);try{const r=await fetch(u,{signal:c.signal,cache:'no-store'});if(!r.ok)throw new Error('HTTP '+r.status);return await r.json()}finally{clearTimeout(to)}}
function applyOutlook(q,label){
  const fin=v=>v!=null&&Number.isFinite(+v);
  const data=(q&&Array.isArray(q.data)?q.data:[]).filter(r=>r&&r.timestamp&&(fin(r.QSitioPresa_pred_mean)||fin(r.QOlaya_pred_mean)));
  if(data.length<7) throw new Error('respuesta sin datos válidos');
  const g=(r,a)=>fin(r[a])?Math.round(+r[a]):null;
  S.src.forecast_snapshot={generated_at:q.generated_at||new Date().toISOString(),source:label,
    fecha:data.map(r=>String(r.timestamp).slice(0,10)),
    sp:data.map(r=>g(r,'QSitioPresa_pred_mean')??Math.round(1.0493*+r.QOlaya_pred_mean+30.08)),
    sp_min:data.map(r=>g(r,'QSitioPresa_pred_min')),sp_max:data.map(r=>g(r,'QSitioPresa_pred_max')),
    ol:data.map(r=>g(r,'QOlaya_pred_mean')),ol_min:data.map(r=>g(r,'QOlaya_pred_min')??g(r,'QOlaya_pred_mean')),ol_max:data.map(r=>g(r,'QOlaya_pred_max')??g(r,'QOlaya_pred_mean')),pi:[],pi_min:[],pi_max:[]};
}
async function loadLive(base){
  base=(base||apiBase()).replace(/\/+$/,'');
  LIVE.state='loading';renderLive();
  try{
    const [q,o]=await Promise.all([fetchJSON(base+'/api/forecast/quarterly_outlook',12000),fetchJSON(base+'/api/observed/daily?days=90',12000).catch(()=>null)]);
    applyOutlook(q,'HydroForecast Ituango · '+base.replace(/^https?:\/\//,''));
    if(o&&Array.isArray(o.data)) LIVE.obsDays=mergeObserved(S.src,o.data);
    LIVE.state='live';LIVE.when=S.src.forecast_snapshot.generated_at;LIVE.src=base;LIVE.err=null;
    S=build(S.src);refreshAll();
    return true;
  }catch(e){
    LIVE.err=e.name==='AbortError'?'sin respuesta':e.message;
    try{ // respaldo: último pronóstico archivado a diario en el repositorio
      const q=await fetchJSON('datos/hf/ultimo.json',8000);
      applyOutlook(q,'Archivo diario del repositorio (HydroForecast)');
      try{const o=await fetchJSON('datos/hf/observado.json',8000);if(o&&Array.isArray(o.data))LIVE.obsDays=mergeObserved(S.src,o.data)}catch(_){}
      LIVE.state='archive';LIVE.when=S.src.forecast_snapshot.generated_at;LIVE.src='archivo';
      S=build(S.src);refreshAll();return false;
    }catch(_){LIVE.state='fallback';renderLive();return false}
  }
}
function mergeObserved(src,data){
  const D=src.data,t0=d0(D.start);let c=0;
  for(const r of data){const i=Math.round((d0(String(r.timestamp).slice(0,10))-t0)/DAY);if(i<0)continue;
    while(D.olaya.length<=i){['olaya','pintada','sitiopresa','nivel','olaya_max','mf_man','mf_mec','ma_man','ma_mec'].forEach(x=>D[x].push(null));D.rep.push(0);D.n++}
    const f=v=>v!=null&&Number.isFinite(+v)&&+v>0;
    if(f(r.QOlaya_obs))D.olaya[i]=Math.round(r.QOlaya_obs);if(f(r.QSitioPresa_obs))D.sitiopresa[i]=Math.round(r.QSitioPresa_obs);if(f(r.QPintada_obs))D.pintada[i]=Math.round(r.QPintada_obs);c++}
  return c;
}
function renderLive(){
  const dot=document.getElementById('live-dot'),txt=document.getElementById('live-txt'),pill=document.getElementById('live-pill');
  if(LIVE.state==='loading'){dot.className='dot warn';txt.textContent='Consultando caudal…';pill.title='Consultando HydroForecast'}
  else if(LIVE.state==='live'){dot.className='dot ok';txt.textContent='Caudal en vivo';pill.title='Pronóstico de HydroForecast generado '+LIVE.when.replace('T',' ').slice(0,16)}
  else if(LIVE.state==='archive'){dot.className='dot warn';txt.textContent='Caudal archivado';pill.title='HydroForecast no respondió'+(LIVE.err?' ('+LIVE.err+')':'')+'. Se usa el pronóstico archivado del '+LIVE.when.replace('T',' ').slice(0,16)}
  else {dot.className='dot bad';txt.textContent='Caudal de respaldo';pill.title='No se pudo consultar HydroForecast'+(LIVE.err?' ('+LIVE.err+')':'')+'. Se usa el respaldo incluido.'}
  renderMeta();
}
function renderMeta(){
  const el=document.getElementById('metaline'); if(!S) return;
  const age=Math.floor((Date.now()-S.T[S.last])/DAY);
  const fc=S.fc.generated_at.replace('T',' ').slice(0,16);
  el.innerHTML=`<span>Extracción hasta <b style="color:var(--fg2)">${fmtD(S.T[S.last])}</b>${age>7?` <span class="tag ${age>14?'bad':'warn'}">hace ${age} días</span>`:''}</span>`+
    `<span>· pronóstico de caudal ${LIVE.state==='live'?'en vivo':LIVE.state==='archive'?'archivado':'de respaldo'} <b style="color:var(--fg2)">${fc}</b></span>`+
    `<span>· ${nf(S.rep.reduce((a,b)=>a+b,0))} días reportados${S.src._repo?' · Excel del repositorio':S.src._xlsxName?' · Excel cargado en esta sesión':''}</span>`;
  document.getElementById('btn-live').disabled=LIVE.state==='loading';
}

/* ---------- vista pronóstico ---------- */
let FC=null;
function restPlan(){return [...document.querySelectorAll('#rest-plan input')].map(i=>i.value===''?null:Math.max(0,Math.min(7,+i.value)))}
function initRestPlan(){const box=document.getElementById('rest-plan');if(!box)return;let saved=[];try{saved=JSON.parse(localStorage.getItem('mfi-rest')||'[]')}catch(e){}
  box.querySelectorAll('input').forEach((i,k)=>{if(saved[k]!=null)i.value=saved[k];i.oninput=()=>{try{localStorage.setItem('mfi-rest',JSON.stringify(restPlan()))}catch(e){}renderForecast()}});
  document.getElementById('rest-clear').onclick=()=>{box.querySelectorAll('input').forEach(i=>i.value='');try{localStorage.removeItem('mfi-rest')}catch(e){}renderForecast()}}
function renderStatus(){renderLive()}
function renderForecast(){
  const scen=document.getElementById('fc-scen').value, comp=document.getElementById('fc-comp').value;
  FC=forecast(scen);
  const B=FC.blocks, R=FC.res;
  // aviso de vigencia
  const age=Math.floor((Date.now()-S.T[S.last])/DAY), bn=document.getElementById('stale-banner');
  const past=B.filter(b=>b.t1<Date.now()-DAY).length;
  if(age>7){bn.hidden=false;bn.innerHTML=`<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="flex-shrink:0;color:var(--warn);margin-top:1px"><path d="M12 9v4M12 17h.01"/><path d="M10.3 3.9L1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/></svg><div><b>El último reporte de extracción es del ${fmtD(S.T[S.last])} (hace ${age} días).</b> ${past?`Las semanas S1${past>1?'–S'+past:''} del pronóstico ya transcurrieron sin datos observados. `:''}Cargue el archivo actualizado en <a href="#actualizar" style="color:var(--accent)">Datos</a> para que el pronóstico parta de hoy.</div>`}
  else bn.hidden=true;
  // aviso de crecientes (respuesta histórica tras picos > umbral)
  const AV=S.P.aviso_creciente, fb=document.getElementById('flood-banner');
  if(AV&&FC.qpk.v>=AV.umbral){fb.hidden=false;fb.innerHTML=`<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="flex-shrink:0;color:var(--warn);margin-top:1px"><path d="M2 12c2.5-2.5 4.5-2.5 7 0s4.5 2.5 7 0 4.5-2.5 6-1M2 18c2.5-2.5 4.5-2.5 7 0s4.5 2.5 7 0 4.5-2.5 6-1"/></svg><div><b>Creciente ${FC.qpk.t>S.T[S.last]?'pronosticada':'reciente'}: Sitio Presa ${nf(FC.qpk.v)} m³/s el ${fmtD(FC.qpk.t)}.</b> Con caudal sobre ${nf(AV.umbral)} m³/s (oct-2021–2026) el mecanizado operó el ${nf(AV.opera*100)} % de los días (${nf(AV.opera_bajo*100)} % con menos de 1.000 m³/s) y el material flotante por día cayó a ~${nf(AV.mf_rel*100)} % de lo normal durante 2–3 semanas; después volvió a lo normal, sin volumen extra neto. Prepare la reanudación al bajar el caudal; el pronóstico semanal no incluye la parada.</div>`}
  else fb.hidden=true;
  renderAlertBanner('alert-banner');
  // tarjetas: desde la semana en curso (no desde el último reporte)
  const now=new Date(), today=Date.UTC(now.getUTCFullYear(),now.getUTCMonth(),now.getUTCDate());
  let i0=B.findIndex(b=>b.t1>=today); if(i0<0) i0=0;
  const fp=FC.fp, nAv=B.length-i0, n4=Math.min(4,nAv);
  const s=(k,n=n4)=>B.slice(i0,i0+n).reduce((a,b)=>a+b[k],0);
  const plan=B.slice(i0,i0+n4).some(b=>b.rest!=null);
  const sp=(key,n=n4)=>plan?s(key+'_e',n):s(key+'_ep',n);
  const from=i0?` desde hoy (S${B[i0].h})`:'';
  const card=(title,key,LT,color)=>{
    const v=s(key), e=s(key+'_e'), lo=s(key+'_p25'), hi=s(key+'_p75');
    const ref=LT!=null?LT*n4:null, ratio=ref?v/ref:1;
    const st=ratio>1.15?['warn','Por encima de lo normal']:ratio<0.85?['info','Por debajo de lo normal']:['ok','Normal'];
    const f=key==='tot'?null:fp[key];
    return `<div class="st ${st[0]} c4"><div class="row"><h2><i class="sw" style="background:${color}"></i>${title}</h2><span class="badge ${st[0]}">${st[1]}</span></div>
      <div class="big">${nf(v)} <small>m³</small></div>
      <div class="note">Próximas ${n4} semanas${from} · mediana · rango probable ${nf(lo)} – ${nf(hi)} m³</div>
      <p><b>${nf(sp(key))} m³</b> ${plan?'con el descanso programado ingresado':'con la frecuencia histórica de paros'+(f!=null?` (×${nf(f,2)})`:'')+(B.slice(i0,i0+n4).some(b=>b.d_alto)?' y la parada por caudal alto pronosticado':'')}${ref?` · ${ratio>=1?'+':''}${nf((ratio-1)*100)} % frente al nivel típico (${nf(ref)} m³)`:''}.${key!=='tot'?' <span class="muted">La división flotante/macrófitas del mecanizado es estimada en el registro; el total es la cifra más firme.</span>':''}</p></div>`};
  document.getElementById('fc-cards').innerHTML=
    card('Total','tot',(R.mf_tot.LT||0)+(R.ma_tot.LT||0),'var(--accent)')+card('Material flotante','mf',R.mf_tot.LT,'var(--mf)')+card('Macrófitas','ma',R.ma_tot.LT,'var(--ma)')+
    [[Math.min(8,nAv),`Próximas ${Math.min(8,nAv)} semanas${from}`],[nAv,`Resto del horizonte · ${nAv} semanas${from}`]].map(([k,lab])=>`<div class="panel c6 kpi"><span class="lab">${lab}</span>
      <span class="val">${nf(s('tot',k))} <small>m³ (mediana)</small></span>
      <span class="rng">esperado ${nf(s('tot_e',k))} m³ con operación normal · ${nf(sp('tot',k))} m³ con paros históricos y caudal pronosticado</span>
      <div class="split"><span><i class="sw" style="background:var(--mf)"></i>Flotante ${nf(s('mf',k))}</span><span><i class="sw" style="background:var(--ma)"></i>Macrófitas ${nf(s('ma',k))}</span></div></div>`).join('');
  // gráfico
  const hist=[]; for(let k=8;k>=1;k--){const i1=S.last-(k-1)*7,i0=i1-6;let a=0,b=0;for(let i=i0;i<=i1;i++){a+=S.mf[i];b+=S.ma[i]}let qq=0,c=0;for(let i=i0;i<=i1;i++)if(S.q[i]!=null){qq+=S.q[i];c++}hist.push({lab:fmtDs(S.T[i0])+'–'+fmtDs(S.T[i1]),mf:a,ma:b,q:c?qq/c:null})}
  const labels=[...hist.map(h=>h.lab),...B.map(b=>'S'+b.h+' · '+fmtDs(b.t0))];
  const nh=hist.length, pad=a=>[...new Array(nh).fill(null),...a];
  const mfc=css('--mf'),mac=css('--ma'),flc=css('--flow'),band=css('--band');
  const ds=[], showMF=comp!=='ma', showMA=comp!=='mf';
  if(showMF) ds.push({type:'bar',label:'Flotante extraído',data:[...hist.map(h=>h.mf),...new Array(B.length).fill(null)],backgroundColor:mfc,stack:'s',yAxisID:'y'});
  if(showMA) ds.push({type:'bar',label:'Macrófitas extraídas',data:[...hist.map(h=>h.ma),...new Array(B.length).fill(null)],backgroundColor:mac,stack:'s',yAxisID:'y'});
  if(showMF) ds.push({type:'bar',label:'Flotante pronosticado (P50)',data:pad(B.map(b=>b.mf)),backgroundColor:mfc+'66',borderColor:mfc,borderWidth:1,stack:'s',yAxisID:'y'});
  if(showMA) ds.push({type:'bar',label:'Macrófitas pronosticadas (P50)',data:pad(B.map(b=>b.ma)),backgroundColor:mac+'66',borderColor:mac,borderWidth:1,stack:'s',yAxisID:'y'});
  ds.push({type:'line',label:'P90',stack:'p90',data:pad(B.map(b=>b[comp+'_p90'])),borderColor:'transparent',backgroundColor:band,fill:'+1',pointRadius:0,yAxisID:'y',order:5});
  ds.push({type:'line',label:'P10',stack:'p10',data:pad(B.map(b=>b[comp+'_p10'])),borderColor:'transparent',backgroundColor:band,fill:false,pointRadius:0,yAxisID:'y',order:5});
  ds.push({type:'line',label:'Caudal Sitio Presa (m³/s)',stack:'q',data:[...hist.map(h=>h.q),...B.map(b=>b.q)],borderColor:flc,backgroundColor:flc,borderWidth:2,pointRadius:2,tension:.3,yAxisID:'y2',order:0});
  const o=baseOpts();
  o.scales.x.stacked=true;o.scales.y.stacked=true;o.scales.y.title={display:true,text:'m³ por semana'};
  o.scales.y2={position:'right',grid:{drawOnChartArea:false},beginAtZero:true,title:{display:true,text:'m³/s'},ticks:{callback:v=>nf(v)}};
  o.plugins.legend.labels.filter=it=>!['P90','P10'].includes(it.text);
  o.plugins.tooltip.callbacks.label=c=>c.parsed.y==null?null:c.dataset.label+': '+nf(c.parsed.y);
  mk('ch-fc',{data:{labels,datasets:ds},options:o});
  document.getElementById('fc-table').innerHTML='<thead><tr><th>Semana</th><th>Días</th><th>Q m³/s</th><th>Flotante</th><th>Macrófitas</th><th>Total P50</th><th>Esperado</th><th>Con paros</th><th>P10–P90</th></tr></thead><tbody>'+
   B.map(b=>`<tr${b.t1<today?' style="opacity:.55" title="Semana ya transcurrida, sin dato de extracción"':''}><td>S${b.h} · ${fmtDs(b.t0)} – ${fmtDs(b.t1)}</td><td class="num">${b.nd}${b.rest!=null?` <small>(${nf(b.rest)} desc.)</small>`:''}</td><td class="num">${nf(b.q)}</td><td class="num">${nf(b.mf)}</td><td class="num">${nf(b.ma)}</td><td class="num"><b>${nf(b.tot)}</b></td><td class="num">${nf(b.tot_e)}</td><td class="num">${b.rest!=null?nf(b.tot_e)+' <small>plan</small>':nf(b.tot_ep)+(b.d_alto?` <small title="días con caudal sobre ${nf(S.P.parada_caudal.umbral)} m³/s">(${b.d_alto} d alto)</small>`:'')}</td><td class="num">${nf(b.tot_p10)} – ${nf(b.tot_p90)}</td></tr>`).join('')+'</tbody>';
  const om=baseOpts(); om.scales.y.beginAtZero=false; om.scales.y.suggestedMin=.7; om.scales.y.suggestedMax=1.5;
  om.plugins.tooltip.callbacks.label=c=>c.dataset.label+': '+nf(c.parsed.y,2);
  mk('ch-mult',{type:'line',data:{labels:B.map(b=>'S'+b.h),datasets:[
    {label:'Flotante',data:B.map(b=>b.mmf),borderColor:mfc,backgroundColor:mfc,pointRadius:2,tension:.25},
    {label:'Macrófitas',data:B.map(b=>b.mma),borderColor:mac,backgroundColor:mac,pointRadius:2,tension:.25}]},options:om});
}

/* ---------- vista modelo ---------- */
function renderModel(){
  const P=S.P;
  document.getElementById('formula').textContent=
`Semana h (desde el último dato), modelo v2.3:
  L₈     = mediana de las últimas 8 semanas con operación
  EW     = media exponencial de semanas con operación (vida media 6 sem.)
  LT     = mediana de semanas con operación desde jul-2019
  nivel_P = a₈(h) · L₈ + (1 − a₈(h)) · LT            (persistencia)
  nivel_E = (1 − s) · [a(h) · EW + (1 − a(h)) · LT] + s · LT
  m      = clip( √exp(b₀ + Σₗ βₗ · x(semana−ℓ)) , 0,7 , 1,5 )
  f(h)   = [w · nivel_P + (1 − w) · nivel_E] · m
           Flotante: w = 0, s = 0,25.  Macrófitas: w = 0,5, s = 0,5
  P50    = f (valor central)
  E      = (f + 50) · r̄(h) − 50       ← valor esperado
  Pp     = (f + 50) · q_p(h) − 50,  p = 10, 25, 75, 90
  día    = semana / 7 · factor del día de la semana
  E_paros = E · (media de todas las semanas / media de semanas
            con operación, últimas 104 semanas) · k(días > 2.300 m³/s)
           k flotante 1 / 0,68 / 0,16 y macrófitas 1 / 0,74 / 0,52
           con 0, 1–3 y 4–7 días de caudal alto pronosticado
Total = Flotante + Macrófitas`;
  const r=(k,f)=>`<td class="num">${f(P.mf_tot[k])}</td><td class="num">${f(P.ma_tot[k])}</td>`;
  document.getElementById('tbl-params').innerHTML='<thead><tr><th>Parámetro</th><th>Flotante</th><th>Macrófitas</th></tr></thead><tbody>'+
   `<tr><td>k (peso de persistencia, actual)</td>${r('k',v=>nf(v??1,1))}</tr><tr><td>Umbral de caudal q<sub>c</sub> (m³/s)</td>${r('qc',v=>nf(v))}</tr><tr><td>a₁</td>${r('a1',v=>nf(v,2))}</tr><tr><td>τ (semanas)</td>${r('tau',v=>nf(v,1))}</tr><tr><td>b₀</td>${r('b0',v=>nf(v,3))}</tr>`+
   [0,1,2,3,4,5,6].map(l=>`<tr><td>β rezago ${l} sem</td>${r('beta',v=>nf(v[l],3))}</tr>`).join('')+
   `<tr><td>q₅₀(1) · r̄(1)</td><td class="num">${nf(P.mf_tot.q['0.5'][0],2)} · ${nf((P.mf_tot.rmean||[1])[0],2)}</td><td class="num">${nf(P.ma_tot.q['0.5'][0],2)} · ${nf((P.ma_tot.rmean||[1])[0],2)}</td></tr>`+
   `<tr><td>L₈ actual (m³/sem)</td><td class="num">${nf(FC.res.mf_tot.L8)}</td><td class="num">${nf(FC.res.ma_tot.L8)}</td></tr><tr><td>LT actual (m³/sem)</td><td class="num">${nf(FC.res.mf_tot.LT)}</td><td class="num">${nf(FC.res.ma_tot.LT)}</td></tr></tbody>`;
  const y=[...document.querySelectorAll('#sk-comp button')].find(b=>b.getAttribute('aria-pressed')==='true').dataset.v;
  const M=P[y].metricas;
  const o=baseOpts();o.scales.y.beginAtZero=false;o.scales.y.title={display:true,text:'RMSE semanal (m³)'};
  mk('ch-skill',{type:'line',data:{labels:M.map(m=>'h='+m.h),datasets:[
    {label:'Mediana histórica',data:M.map(m=>m.clim),borderColor:css('--muted'),backgroundColor:css('--muted'),borderDash:[5,4],pointRadius:2},
    {label:'Persistencia (8 semanas)',data:M.map(m=>m.pers),borderColor:css('--warn'),backgroundColor:css('--warn'),pointRadius:2},
    {label:'Modelo '+(S.P.version||'v2').split(' ')[0],data:M.map(m=>m.modelo),borderColor:css('--accent'),backgroundColor:css('--accent'),borderWidth:3,pointRadius:3}]},options:o});
  document.getElementById('tbl-skill').innerHTML='<thead><tr><th>h</th><th>MAE</th><th>vs mediana</th><th>vs pers.</th><th>Cob. 80%</th></tr></thead><tbody>'+
   M.filter(m=>[1,2,4,8,13].includes(m.h)).map(m=>`<tr><td>${m.h} sem</td><td class="num">${nf(m.mae)}</td><td class="num">${nf(m.skill_clim*100,1)} %</td><td class="num">${nf(m.skill_pers*100,1)} %</td><td class="num">${nf(m.cobertura80*100)} %</td></tr>`).join('')+'</tbody>';
  const m1=P.mf_tot.metricas[0],a1=P.ma_tot.metricas[0], rmf=P.mf_tot.rmse_total||{}, rma=P.ma_tot.rmse_total||{};
  document.getElementById('model-read').innerHTML=`<h3>Cómo leer el desempeño</h3>
   <p>En el backtest se pronosticó cada semana entre 2022 y 2026 usando solo la información disponible en la fecha de origen. A una semana, el error absoluto medio es de ${nf(m1.mae)} m³ en material flotante (promedio observado ${nf(m1.media_obs)} m³/semana) y ${nf(a1.mae)} m³ en macrófitas (promedio ${nf(a1.media_obs)} m³/semana).</p>
   <p>En todo el periodo, el RMSE semanal del material flotante es ${nf(rmf.v2)} m³ con el modelo v${(S.P.version||'2').split(' ')[0]}, frente a ${nf(rmf.clim)} m³ de la mediana histórica y ${nf(rmf.pers)} m³ de repetir las últimas semanas. En macrófitas: ${nf(rma.v2)}, ${nf(rma.clim)} y ${nf(rma.pers)} m³. La ventaja se concentra en las primeras 4 semanas; más allá, el pronóstico converge al nivel de largo plazo.</p>
   <p>Un error semanal cercano al 40 % del volumen es esperable mientras el registro mezcle llegada de material con esfuerzo de extracción. Para planear volúmenes use el valor esperado acumulado a 4 u 8 semanas, que es más confiable que una semana aislada. El intervalo P10–P90 cubrió el ${nf(P.mf_tot.cobertura80_fuera_muestra*100)} % (flotante) y el ${nf(P.ma_tot.cobertura80_fuera_muestra*100)} % (macrófitas) de los casos de 2024–2026 calibrando solo con 2022–2023.</p>
   <p>Se probaron y descartaron un modelo conceptual de inventario, regresiones de caudal sin persistencia, niveles de largo plazo móviles (26 a 104 semanas) y una corrección de sesgo móvil: ninguno mejoró fuera de la muestra. Detalle en <a href="#auditoria" style="color:var(--accent)">Auditoría</a>.</p>`;
}


/* ---------- rezagos caudal → material flotante ---------- */
function renderRezagos(){
  const R=S.src.rezagos; const box=document.getElementById('rez-panel'); if(!box) return; if(!R){box.hidden=true;return} box.hidden=false;
  const seg=document.getElementById('rez-per'); if(!seg.dataset.on){seg.dataset.on=1;seg.querySelectorAll('button').forEach(b=>b.onclick=()=>{seg.querySelectorAll('button').forEach(x=>x.setAttribute('aria-pressed',x===b));renderRezagos()})}
  const per=[...seg.querySelectorAll('button')].find(b=>b.getAttribute('aria-pressed')==='true').dataset.v, M=R.mensual[per];
  const o=baseOpts(); o.scales.y.min=-0.6; o.scales.y.max=0.7; o.scales.y.title={display:true,text:'correlación'}; o.scales.x.title={display:true,text:'meses de rezago (caudal antes)'};
  o.plugins.legend.labels.filter=it=>it.text!=='_';
  const n=per==='2019-2026'?80:54, L95=1.96/Math.sqrt(n);
  mk('ch-rez-mes',{type:'line',data:{labels:M.map(r=>r.L),datasets:[
    {label:'Cruda',data:M.map(r=>r.crudo),borderColor:css('--muted'),backgroundColor:css('--muted'),borderDash:[5,4],pointRadius:2},
    {label:'Preblanqueada',data:M.map(r=>r.preblanq),borderColor:css('--mf'),backgroundColor:css('--mf'),borderWidth:2.5,pointRadius:3},
    {label:'_',data:M.map(()=>L95),borderColor:css('--line'),borderDash:[2,3],pointRadius:0,borderWidth:1},
    {label:'_',data:M.map(()=>-L95),borderColor:css('--line'),borderDash:[2,3],pointRadius:0,borderWidth:1}]},options:o});
  const E=R.evento, o2=baseOpts(); o2.scales.y.title={display:true,text:'× nivel normal'}; o2.scales.x.title={display:true,text:'semana respecto al pico'};
  mk('ch-rez-ev',{type:'bar',data:{labels:E.semanas.map(s=>s.replace('s','')),datasets:[
    {label:'Tras creciente',data:E.evento,backgroundColor:css('--mf')},{label:'Fechas sin creciente',data:E.control,backgroundColor:css('--muted')+'99'}]},options:o2});
  document.getElementById('rez-tabla').innerHTML='<thead><tr><th>Caudal diario Sitio Presa (m³/s)</th><th>Días</th><th>Mecanizado operó</th><th>Parado por material o condiciones del río</th><th>Flotante por día vs normal (semanas con ese caudal máximo)</th></tr></thead><tbody>'+
    R.por_caudal.map(r=>`<tr><td>${r.clase}</td><td class="num">${nf(r.dias)}</td><td class="num">${nf(r.opera_mec*100)} %</td><td class="num">${nf(r.sin_material*100)} %</td><td class="num">${nf(r.mf_rel,2)}×</td></tr>`).join('')+'</tbody>';
  const bt=R.bt_lag, V=R.viaje;
  document.getElementById('rez-read').innerHTML=`<p><b>Horas (viaje del agua).</b> La Pintada → Olaya ${V['CaudalPintada->CaudalOlaya'].horas} h y Olaya → Sitio Presa ${V['CaudalOlaya->CaudalSitioPresa'].horas} h (cambios horarios); La Virginia, La Pintada y Bolombolo responden el mismo día en Olaya. El caudal llega en horas, pero en la extracción no aparece a esa escala.</p>
   <p><b>Días y semanas.</b> Con preblanqueo, la correlación diaria y semanal entre caudal y material flotante queda en ±0,1–0,2: no hay un rezago lineal útil. Lo que sí aparece es un umbral: por encima de ~2.300 m³/s el mecanizado opera el ${nf(R.por_caudal[4].opera_mec*100)} % de los días (${nf(R.por_caudal[0].opera_mec*100)} % con menos de 1.000 m³/s) y el flotante por día cae a ~${nf(R.por_caudal[4].mf_rel*100)} % de lo normal durante 2–3 semanas. Después vuelve a lo normal, sin volumen extra neto: la suma de las 8 semanas siguientes queda en la mediana +${nf(E.extra_8sem_mediana)} m³ sobre lo normal.</p>
   <p><b>Meses.</b> La anomalía de caudal se relaciona con el material flotante 5 a 8 meses después (cruda ρ 0,37–0,54; preblanqueada 0,16–0,27, en el límite). Coincide con lo anual: 2021–2022 muy húmedos (La Niña) y 2023 récord de flotante (128.403 m³); 2024 seco y 2024–2025 bajos. Como término del pronóstico baja el error total ${nf((1-bt.rmse/bt.rmse_base)*100,1)} %, pero en 2024 queda por debajo de la mediana histórica, así que se muestra como contexto y no entra al modelo.</p>
   <h3 style="margin-top:14px">Cómo se mejora la relación</h3>
   <p>La extracción está limitada por los equipos, no por el material: los viajes por volqueta no cambian con el caudal (ρ ≈ 0) y el volumen semanal lo explica el esfuerzo (volqueta-días, r = ${nf(R.regresion['esfuerzo (volqueta-días)'].r_val,2)} en 2025–2026). Por eso la correlación directa caudal–flotante es débil (ρ semanal ≈ −0,1). Separando los efectos del caudal mejora:</p>
   <div class="tbl"><table><thead><tr><th>Relación caudal → material flotante semanal</th><th>r 2021–2024</th><th>r 2025–2026 (validación)</th></tr></thead><tbody>
   ${[['Solo el caudal medio de la semana','solo caudal de la semana'],['Días de caudal alto en la semana (parada por seguridad)','caudal: parada (días >2.300 y 1.866–2.300)'],['Días altos + caudal de las 6 semanas previas','caudal: parada + llegada (media exp. 42 d)'],['Esfuerzo + caudal','esfuerzo + caudal (parada + llegada 56 d)']].map(([l,k])=>`<tr><td>${l}</td><td class="num">${nf(R.regresion[k].r_ent,2)}</td><td class="num">${nf(R.regresion[k].r_val,2)}</td></tr>`).join('')}</tbody></table></div>
   <p class="note">El caudal medio solo es inestable (0,21 frente a 0,73) porque en 2025–2026 lo domina la parada larga de abr–may 2025, con signo negativo: más caudal, menos extracción. Días altos + caudal previo se sostiene en ambos periodos (≈ 0,5).</p>
   <p>La llegada de material sí se ve en la <b>composición</b> de lo que cargan las volquetas: frente a su nivel de las 26 semanas previas, la fracción de flotante sube con el caudal de las 6–8 semanas anteriores (r = ${nf(R.composicion.r_ent,2)} en 2021–2024 y ${nf(R.composicion.r_val,2)} en 2025–mar 2026) y en la semana siguiente a una creciente pasa de ${nf(R.composicion.tras_creciente.base*100)} % a ~${nf((R.composicion.tras_creciente.base+R.composicion.tras_creciente.dif[3])*100)} %, y sigue alta unas 6 semanas: material acumulado mientras no se pudo extraer. Abr–sep 2026 queda fuera porque la división flotante/macrófitas del registro es fija (45,7 %).</p>
   <p><b>Incorporado al pronóstico:</b> el valor «con paros» ahora usa los días de caudal alto pronosticados (> 2.300 m³/s). Validado dejando fuera un año, en las ${R.parada.mf_tot.semanas} semanas con caudal alto el error baja de ${nf(R.parada.mf_tot.en_semanas_altas.constante)} a ${nf(R.parada.mf_tot.en_semanas_altas.por_caudal)} m³ en flotante y de ${nf(R.parada.ma_tot.en_semanas_altas.constante)} a ${nf(R.parada.ma_tot.en_semanas_altas.por_caudal)} m³ en macrófitas, sin empeorar ningún año. Depende de que HydroForecast anticipe bien la creciente.</p>
   <p class="note">Tras ~30 pruebas, los valores p son orientativos. Una revisión anterior reportó «2× en la segunda semana»: medido contra las 4 semanas previas, que ya venían deprimidas por el caudal alto; contra el nivel normal la segunda semana es 1,1×.</p>`;
}


function renderBateria(){
  const R=S.src.rezagos, box=document.getElementById('bat-panel'); if(!box) return; const B=R&&R.bateria; if(!B){box.hidden=true;return} box.hidden=false;
  const fam={}; B.pruebas.forEach(t=>{const f=fam[t.familia]||(fam[t.familia]={n:0,p05:0,q05:0});f.n++;if(t.p!=null&&t.p<0.05)f.p05++;if(t.q!=null&&t.q<0.05)f.q05++});
  document.getElementById('bat-resumen').innerHTML='<thead><tr><th>Familia</th><th>Pruebas</th><th>p < 0,05</th><th>Se sostienen tras corregir (q < 0,05)</th></tr></thead><tbody>'+Object.entries(fam).map(([k,f])=>`<tr><td>${esc(k)}</td><td class="num">${f.n}</td><td class="num">${f.p05}</td><td class="num"><b>${f.q05}</b></td></tr>`).join('')+`<tr><td><b>Total</b></td><td class="num">${B.pruebas.length}</td><td class="num">${B.pruebas.filter(t=>t.p!=null&&t.p<0.05).length}</td><td class="num"><b>${B.pruebas.filter(t=>t.q!=null&&t.q<0.05).length}</b></td></tr></tbody>`;
  document.getElementById('bat-read').innerHTML=B.lectura;
  document.getElementById('bat-todas').innerHTML='<thead><tr><th>#</th><th>Familia</th><th>Prueba</th><th>Estadístico</th><th>p</th><th>q (BH)</th></tr></thead><tbody>'+B.pruebas.map((t,i)=>`<tr${t.q!=null&&t.q<0.05?' style="font-weight:600"':''}><td class="num">${i+1}</td><td>${esc(t.familia)}</td><td>${esc(t.prueba)}</td><td class="num">${t.estadistico==null?'—':nf(t.estadistico,3)}</td><td class="num">${t.p==null?'—':nf(t.p,3)}</td><td class="num">${t.q==null?'—':nf(t.q,3)}</td></tr>`).join('')+'</tbody>';
}

/* ---------- pronóstico real de HydroForecast vs observado (sombra) ---------- */
let HFH=null;
async function loadHFHist(){
  if(HFH) return HFH;
  const base=(LIVE.src&&LIVE.src!=='archivo'?LIVE.src:DEF_API).replace(/\/+$/,'');
  const [h,o]=await Promise.all([fetchJSON(base+'/api/forecast/history?station=olaya&n=20&spacing_hours=72&lookback_days=60',20000),fetchJSON(base+'/api/observed/daily?days=150',15000)]);
  const sp=r=>Number.isFinite(+r.QSitioPresa_pred_mean)?+r.QSitioPresa_pred_mean:(Number.isFinite(+r.QOlaya_pred_mean)?1.0493*r.QOlaya_pred_mean+30.08:null);
  const runs=(h.past_forecasts||[]).map(f=>{const q=f.quarterly_outlook_90d||[];return {t0:d0(String(q[0]?.timestamp).slice(0,10)),pts:q.map(r=>({t:d0(String(r.timestamp).slice(0,10)),v:sp(r)})).filter(x=>x.v!=null)}}).filter(r=>r.pts.length>7);
  const obs=new Map((o.data||[]).map(r=>[d0(String(r.timestamp).slice(0,10)),Number.isFinite(+r.QSitioPresa_obs)?+r.QSitioPresa_obs:(Number.isFinite(+r.QOlaya_obs)?1.0493*r.QOlaya_obs+30.08:null)]).filter(x=>x[1]!=null));
  HFH={runs,obs,base};return HFH;
}
async function renderHFSkill(){
  const note=document.getElementById('hf-note');
  let H; try{H=await loadHFHist()}catch(e){note.textContent='No se pudo consultar el historial de pronósticos de HydroForecast ('+(e.message||e)+').';return}
  const {runs,obs}=H; if(!runs.length){note.textContent='HydroForecast no devolvió pronósticos pasados.';return}
  const sel=document.getElementById('hf-sel');
  if(sel.options.length===1){runs.forEach((r,i)=>sel.insertAdjacentHTML('beforeend',`<option value="${i}">Emitido ${fmtD(r.t0)}</option>`));sel.onchange=renderHFSkill}
  const v=sel.value, show=v==='all'?runs:[runs[+v]];
  const ot=[...obs.keys()].sort((a,b)=>a-b), t0=Math.min(...runs.map(r=>r.t0))-7*DAY;
  const ds=[{type:'line',label:'Caudal observado (sombra)',data:ot.filter(t=>t>=t0).map(t=>({x:t,y:obs.get(t)})),borderColor:css('--muted'),backgroundColor:css('--muted')+'40',fill:'origin',pointRadius:0,borderWidth:1.5,order:9}];
  show.forEach((r,i)=>ds.push({type:'line',label:i===show.length-1?(v==='all'?'Pronósticos emitidos (90 días)':'Pronóstico '+fmtD(r.t0)):'_',data:r.pts.map(p=>({x:p.t,y:p.v})),borderColor:css('--accent')+(v==='all'?(i===show.length-1?'':'55'):''),borderWidth:v==='all'&&i<show.length-1?1:2,pointRadius:0,fill:false,order:1}));
  ds.push({type:'line',label:'Umbral macrófitas 1 000 m³/s',data:[{x:t0,y:1000},{x:Math.max(...runs.map(r=>r.pts.at(-1).t)),y:1000}],borderColor:css('--ma'),borderDash:[5,4],borderWidth:1,pointRadius:0,fill:false});
  ds.push({type:'line',label:'Umbral flotante 1 500 m³/s',data:[{x:t0,y:1500},{x:Math.max(...runs.map(r=>r.pts.at(-1).t)),y:1500}],borderColor:css('--mf'),borderDash:[5,4],borderWidth:1,pointRadius:0,fill:false});
  const o=baseOpts();o.scales.x={type:'linear',grid:{color:css('--line')},ticks:{callback:x=>fmtDs(x),maxTicksLimit:10}};o.scales.y.title={display:true,text:'m³/s'};
  o.plugins.legend.labels.filter=it=>it.text!=='_';o.plugins.tooltip.callbacks.title=it=>fmtD(it[0].parsed.x);o.interaction={mode:'nearest',intersect:false};
  o.plugins.tooltip.callbacks.label=c=>c.dataset.label==='_'?null:c.dataset.label+': '+nf(c.parsed.y);
  mk('ch-hf',{data:{datasets:ds},options:o});
  // calidad por semana de anticipación vs persistencia
  const W=[];for(const r of runs){const per=obs.get(r.t0-DAY)??obs.get(r.t0);r.pts.forEach((p,k)=>{const ob=obs.get(p.t);if(ob==null||per==null)return;const w=Math.ceil((k+1)/7);(W[w]=W[w]||[]).push([p.v,ob,per])})}
  const rows=W.map((a,w)=>a&&a.length>=10?{w,n:a.length,mae:a.reduce((s,x)=>s+Math.abs(x[0]-x[1]),0)/a.length,bias:a.reduce((s,x)=>s+(x[0]-x[1]),0)/a.length,pers:a.reduce((s,x)=>s+Math.abs(x[2]-x[1]),0)/a.length,mo:a.reduce((s,x)=>s+x[1],0)/a.length}:null).filter(Boolean);
  document.getElementById('tbl-hf').innerHTML='<thead><tr><th>Semana</th><th>Casos</th><th>Error pron.</th><th>Sesgo</th><th>Error persist.</th><th>Q obs. medio</th></tr></thead><tbody>'+
    rows.map(r=>`<tr><td>${r.w}</td><td class="num">${r.n}</td><td class="num"${r.mae<r.pers?' style="color:var(--ok)"':''}>${nf(r.mae)}</td><td class="num">${Math.abs(r.bias)<0.5?'0':(r.bias>0?'+':'')+nf(r.bias)}</td><td class="num">${nf(r.pers)}</td><td class="num">${nf(r.mo)}</td></tr>`).join('')+'</tbody>';
  // impacto en el multiplicador del modelo de extracción: pronóstico real vs observado
  const imp={};for(const [y,lab] of [['mf_tot','flotante'],['ma_tot','macrófitas']]){const p=S.P[y];let n=0,dsum=0,dmax=0,cnt=0;
    for(const r of runs){const pm=new Map(r.pts.map(x=>[x.t,x.v]));
      const xw=(src,w)=>{let s_=0;for(let d=0;d<7;d++){const t=r.t0+((w-1)*7+d)*DAY;const val=w<=0?obs.get(t):src.get(t);if(val!=null)s_+=Math.max(val-p.qc,0)/1000}return s_};
      for(let h=1;h<=13;h++){if(!obs.has(r.t0+(h*7-1)*DAY))break;const m=src=>{let lin=p.b0;for(let l=0;l<7;l++)lin+=p.beta[l]*xw(src,h-l);return Math.min(1.5,Math.max(0.7,Math.sqrt(Math.exp(lin))))};
        const d=Math.abs(m(pm)/m(obs)-1);n++;dsum+=d;dmax=Math.max(dmax,d);if(d>0.001)cnt++}}
    imp[lab]={n,media:n?dsum/n*100:0,max:dmax*100,cnt}}
  const big=[...obs.values()].filter(x=>x>1000).length, pbig=runs.reduce((s,r)=>s+r.pts.filter(x=>x.v>1000).length,0), npts=runs.reduce((s,r)=>s+r.pts.length,0);
  const better=rows.filter(r=>r.mae<r.pers).map(r=>r.w);
  note.textContent=`${runs.length} pronósticos de 90 días emitidos entre ${fmtD(runs[0].t0)} y ${fmtD(runs.at(-1).t0)} (la API guarda 60 días), comparados con el caudal observado en Sitio Presa. Fuente: ${H.base.replace(/^https?:\/\//,'')}.`;
  document.getElementById('hf-read').innerHTML=`<h3>Lectura</h3><ul>
    <li>El pronóstico supera a repetir el caudal actual en las semanas ${better.length?better.join(', '):'—'}${rows.length?`; su sesgo medio va de ${nf(Math.min(...rows.map(r=>r.bias)))} a ${nf(Math.round(Math.max(...rows.map(r=>r.bias)))||0)} m³/s`:''}.</li>
    <li>Impacto en el modelo de extracción (multiplicador con pronóstico real frente a caudal observado): flotante ${nf(imp.flotante.media,2)} % de diferencia media (${imp.flotante.cnt} de ${imp.flotante.n} casos con diferencia); macrófitas ${nf(imp['macrófitas'].media,2)} % (${imp['macrófitas'].cnt} de ${imp['macrófitas'].n}).</li>
    <li>${big?`El caudal observado superó 1 000 m³/s en ${big} días del periodo.`:'En este periodo el caudal observado no superó 1 000 m³/s: los umbrales del modelo no se activan y el pronóstico real no cambia la extracción pronosticada.'} El pronóstico superó 1 000 m³/s en ${pbig} de ${npts} días pronosticados.</li>
    <li>La evaluación se actualiza sola; tendrá peso cuando el periodo incluya crecientes. El repositorio archiva cada pronóstico dos veces al día para ampliar esta ventana.</li></ul>`;
}

/* ---------- vista auditoría ---------- */
const esc=t=>String(t).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function integrityChecks(){
  const out=[], QA=S.src.qc_acum||[], i0=S.first, i1=S.last;
  const ser=[['mf_man','Flotante manual'],['mf_mec','Flotante mecanizado'],['ma_man','Macrófitas manual'],['ma_mec','Macrófitas mecanizado']];
  const span=i1-i0+1, rep=S.rep.slice(i0,i1+1).reduce((a,b)=>a+b,0);
  out.push(['ok','Estructura del archivo',`${nf(rep)} días reportados entre ${fmtD(S.T[i0])} y ${fmtD(S.T[i1])}, con las mismas fechas en ambas hojas.`]);
  const brk=QA.filter(q=>q.quiebres>0||Math.abs(q.suma-q.acum)>=0.5);
  out.push([brk.length?'warn':'ok','Acumulados vs avances diarios',brk.length?`${brk.length} serie(s) con quiebres: ${brk.map(q=>q.serie+' ('+q.quiebres+')').join(', ')}. Detalle en Calidad del dato.`:'Las 4 series cuadran en todas las fechas (0 quiebres).']);
  let neg=0; ser.forEach(([k])=>{for(let i=i0;i<=i1;i++)if(S[k][i]<0)neg++});
  out.push([neg?'bad':'ok','Valores negativos',neg?`${neg} valores negativos.`:'Ninguno.']);
  const kg=S.src.kgm3; if(kg) out.push([Math.abs(kg[0]-kg[1])<0.01?'ok':'warn','Conversión kg → m³ (macrófitas manual)',Math.abs(kg[0]-kg[1])<0.01?`Constante en ${nf(kg[0])} kg/m³.`:`Varía entre ${nf(kg[0],1)} y ${nf(kg[1],1)} kg/m³.`]);
  const nul=QA.reduce((a,q)=>a+q.nulos,0);
  out.push([nul?'warn':'ok','Avances diarios vacíos',nul?`${nul} celda(s) vacía(s), rellenadas con la diferencia de acumulados.`:'Ninguno.']);
  out.push(['ok','Días sin reporte',`${nf(span-rep)} días: se cuentan como 0 m³ (no se extrajo) y permanecen en el análisis.`]);
  const ext=[]; ser.forEach(([k,lab])=>{const v=[];for(let i=i0;i<=i1;i++)if(S[k][i]>0)v.push(S[k][i]);v.sort((a,b)=>a-b);const p99=v[Math.floor(v.length*0.99)]||0;
    for(let i=i0;i<=i1;i++)if(p99>0&&S[k][i]>3*p99)ext.push(`${lab} ${fmtD(S.T[i])} (${nf(S[k][i])} m³)`)});
  out.push([ext.length?'warn':'ok','Valores extremos (> 3 × percentil 99)',ext.length?`${ext.length}: ${ext.join('; ')}. Confirmar si corresponden a un día o a varios (como el ajuste de dic-2019).`:'Ninguno.']);
  return out;
}
function renderAudit(){
  const A=S.src.audit; if(!A) return;
  const li=arr=>arr.map(([s,t,d])=>`<li><span><span class="tag ${s}">${s==='ok'?'Correcto':s==='warn'?'Atención':'Crítico'}</span></span><div><div class="t">${t}</div><div class="d">${d}</div></div></li>`).join('');
  const plat=[...(A.plataforma||[])];
  plat.push(['ok','Fuentes externas','La página no depende de CDN ni de fuentes externas: librerías y datos van incluidos. Solo consulta la API de HydroForecast para el caudal, con respaldo si falla.']);
  plat.push([LIVE.state==='live'?'ok':'warn','Caudal en esta sesión',LIVE.state==='live'?`Pronóstico en vivo de ${LIVE.src.replace(/^https?:\/\//,'')}, generado ${LIVE.when.replace('T',' ').slice(0,16)}.`:`No se pudo consultar HydroForecast${LIVE.err?' ('+LIVE.err+')':''}; se usa el respaldo del ${S.fc.generated_at.slice(0,10)}.`]);
  const INT=integrityChecks();
  document.getElementById('aud-int').innerHTML=li(INT);
  document.getElementById('aud-q').innerHTML=li(A.caudal);
  document.getElementById('aud-plat').innerHTML=li(plat);
  document.getElementById('aud-mod').innerHTML=li(A.modelo);
  const age=Math.floor((Date.now()-S.T[S.last])/DAY);
  document.getElementById('aud-vig').innerHTML=li([[age>14?'bad':age>7?'warn':'ok','Datos de extracción',`Último reporte: ${fmtD(S.T[S.last])} (hace ${age} días).${age>7?' Las primeras semanas del pronóstico ya transcurrieron sin datos observados.':''}`],
    [LIVE.state==='live'?'ok':'warn','Pronóstico de caudal'+(LIVE.state==='archive'?' (archivado)':''),`Generado ${S.fc.generated_at.replace('T',' ').slice(0,16)} · ${S.fc.fecha.length} días.`],['ok','Parámetros del modelo',`Versión ${S.P.version||'2.0'}; recalibrar cada trimestre.`]]);
  document.getElementById('aud-rec').innerHTML=A.recomendaciones.map(r=>`<li>${r}</li>`).join('');
  const all=[...INT,...A.caudal,...plat,...A.modelo];
  if(A.experimento){const E=A.experimento;document.getElementById('aud-exp').innerHTML='<thead><tr><th>Modelo</th>'+E.cols.map(c=>`<th>${c}</th>`).join('')+'</tr></thead><tbody>'+E.rows.map(r=>`<tr${r[2]?' style="font-weight:600"':''}><td>${r[0]}</td>${r[1].map(v=>`<td class="num">${nf(v)}</td>`).join('')}</tr>`).join('')+'</tbody>';document.getElementById('aud-exp-note').textContent=E.nota}
  const cnt=k=>all.filter(x=>x[0]===k).length;
  document.getElementById('aud-lede').textContent=`Revisión independiente del ${fmtD(d0(A.fecha))}: integridad del Excel, calidad de los caudales, validez estadística del modelo y funcionamiento de la plataforma. Cada punto indica si está correcto, requiere atención o es crítico.`;
  const v=A.v1v2;
  document.getElementById('aud-score').innerHTML=[
    ['ok','Correctos',cnt('ok'),'puntos verificados sin observaciones'],['warn','Atención',cnt('warn'),'limitaciones conocidas y documentadas'],['bad','Críticos',cnt('bad')+(age>14?1:0),'requieren acción'],
    ['info','Error v1 → actual (flotante)',`${nf(v.mf_tot.rmse.v1)} → ${nf(v.mf_tot.rmse.v2)}`,'RMSE semanal 2022–2026, m³']
  ].map(([s,l,n,d])=>`<div class="st ${s} c3"><h2>${l}</h2><div class="big">${n}</div><div class="note">${d}</div></div>`).join('');
  const y=[...document.querySelectorAll('#aud-comp button')].find(b=>b.getAttribute('aria-pressed')==='true').dataset.v;
  const yrs=Object.keys(v[y].anual);
  const o=baseOpts();o.scales.y.beginAtZero=false;o.scales.y.title={display:true,text:'% de mejora'};o.scales.y.ticks={callback:x=>nf(x)+' %'};
  o.plugins.tooltip.callbacks.label=c=>c.dataset.label+': '+nf(c.parsed.y,1)+' %';
  mk('ch-aud',{type:'bar',data:{labels:yrs,datasets:[
    {label:'v1 (anterior)',data:yrs.map(k=>v[y].anual[k].v1*100),backgroundColor:css('--muted')+'aa'},
    {label:v.etiqueta_v2||'v2 (actual)',data:yrs.map(k=>v[y].anual[k].v2*100),backgroundColor:css('--accent')}]},options:o});
}

/* ---------- vista satélite ---------- */
let SAT=null, SAT_P=null;
function loadSat(){if(SAT)return Promise.resolve(SAT);if(SAT_P)return SAT_P;SAT_P=fetchJSON('datos/satelite/app/serie.json',10000).then(j=>(SAT=j)).catch(e=>{SAT_P=null;throw e});return SAT_P}
async function renderSat(){
  const msg=document.getElementById('sat-msg');
  let J; try{J=await loadSat();msg.hidden=true}catch(e){msg.hidden=false;msg.innerHTML='<div>Los datos satelitales están en el repositorio y solo se cargan en la versión publicada (astrococo.github.io/flotante-ituango).</div>';return}
  const S_=J.serie.map(r=>({...r,T:d0(r.f),src:'Sentinel-2'})), A=J.area_ha, LS=(J.landsat||[]).map(r=>({...r,T:d0(r.f),src:'Landsat '+r.p})), S1=(J.s1||[]).map(r=>({...r,T:d0(r.f),src:'Sentinel-1 (radar)'}));
  const MG=(J.margen||[]).map(r=>({...r,T:d0(r.f)}));
  const ALL=[...S_,...LS,...S1].sort((a,b)=>a.T-b.T), last=ALL[ALL.length-1], OPT=[...S_,...LS].sort((a,b)=>a.T-b.T);
  const mo=new Date(last.T).getUTCMonth(), same=ALL.filter(r=>new Date(r.T).getUTCMonth()===mo).map(r=>r.t), medMo=median(same);
  const pr=same.filter(v=>v<=last.t).length/same.length;
  document.getElementById('sat-kpis').innerHTML=[
    ['info','Última escena útil',`${nf(last.t,1)} <small>ha</small>`,`${fmtD(last.T)} · ${last.src} · ${nf(last.t/A.total*100)} % del núcleo de ${nf(A.total)} ha`],
    (()=>{const lo=OPT[OPT.length-1], g=MG.length?MG[MG.length-1]:null;
      if(!g)return ['ok','Aguas arriba · aguas abajo',`${nf(lo.a,1)} · ${nf(lo.b,1)} <small>ha</small>`,`última escena óptica (${fmtD(lo.T)})`];
      const d=g.ad+g.bd, tot=d+g.ai+g.bi;
      return ['ok','Margen derecha (donde se extrae)',`${nf(tot?d/tot*100:0)} <small>%</small>`,`del área de la última escena óptica (${fmtD(g.T)}, ${nf(lo.t,1)} ha) · aguas arriba ${nf(lo.a,1)} ha, aguas abajo ${nf(lo.b,1)} ha`]})(),
    [last.t>medMo*1.5?'warn':'ok',`Frente a lo típico de ${MES[mo]}`,`${nf(last.t/medMo*100)} <small>%</small>`,`de la mediana de ${MES[mo]} (${nf(medMo,1)} ha, ${same.length} escenas); percentil ${nf(pr*100)} entre las escenas de ${MES[mo]}`],
    ['info','Escenas útiles',`${nf(J.n_utiles+LS.length+S1.length)}`,`${nf(J.n_utiles)} Sentinel-2 + ${nf(LS.length)} Landsat (≥ ${nf(J.metodo.minimo_despejado*100)} % despejado) + ${nf(S1.length)} radar Sentinel-1`]
  ].map(([c,l,v,d])=>`<div class="st ${c} c3"><h2>${l}</h2><div class="big">${v}</div><div class="note">${d}</div></div>`).join('');
  const mode=[...document.querySelectorAll('#sat-lado button')].find(b=>b.getAttribute('aria-pressed')==='true').dataset.v;
  const o=baseOpts();o.scales.x={type:'linear',grid:{color:css('--line')},ticks:{callback:v=>{const d=new Date(v);return MES[d.getUTCMonth()]+' '+String(d.getUTCFullYear()).slice(2)},maxTicksLimit:10},min:ALL[0].T-30*DAY,max:ALL[ALL.length-1].T+30*DAY};
  o.scales.y.title={display:true,text:'hectáreas'};o.plugins.tooltip.callbacks.title=it=>fmtD(it[0].parsed.x);o.plugins.tooltip.callbacks.label=c=>c.dataset.label+': '+nf(c.parsed.y,1)+' ha';o.interaction={mode:'nearest',intersect:false};
  const pt=(k)=>S_.map(r=>({x:r.T,y:r[k]})), ptL=(k)=>LS.map(r=>({x:r.T,y:r[k]}));
  const ds=mode==='t'?[{type:'line',label:'Vegetación flotante (total)',data:pt('t'),borderColor:css('--ma'),backgroundColor:css('--ma'),pointRadius:3,borderWidth:1,tension:0},
    {type:'line',label:'Umbral NDVI 0,2–0,4 (sensibilidad)',data:S_.map(r=>({x:r.T,y:r.t20})),borderColor:'transparent',backgroundColor:css('--ma')+'33',pointRadius:0,fill:'+1'},{type:'line',label:'_',data:S_.map(r=>({x:r.T,y:r.t40})),borderColor:'transparent',pointRadius:0,fill:false},{type:'scatter',label:'Landsat 8/9 (30 m)',data:ptL('t'),borderColor:css('--accent'),backgroundColor:css('--accent'),pointStyle:'triangle',pointRadius:4},{type:'scatter',label:'Sentinel-1 radar (sin nubes)',data:S1.map(r=>({x:r.T,y:r.t})),borderColor:css('--muted'),backgroundColor:css('--muted')+'99',pointStyle:'rect',pointRadius:3}]
   :[{type:'line',label:'Aguas arriba (sur)',data:pt('a'),borderColor:css('--mf'),backgroundColor:css('--mf'),pointRadius:3,borderWidth:1},{type:'line',label:'Aguas abajo (norte)',data:pt('b'),borderColor:css('--ma'),backgroundColor:css('--ma'),pointRadius:3,borderWidth:1},{type:'scatter',label:'Landsat aguas arriba',data:ptL('a'),borderColor:css('--mf'),backgroundColor:css('--mf'),pointStyle:'triangle',pointRadius:4},{type:'scatter',label:'Landsat aguas abajo',data:ptL('b'),borderColor:css('--ma'),backgroundColor:css('--ma'),pointStyle:'triangle',pointRadius:4},{type:'scatter',label:'Radar aguas abajo',data:S1.map(r=>({x:r.T,y:r.b})),borderColor:css('--ma'),backgroundColor:css('--ma')+'55',pointStyle:'rect',pointRadius:3},...(S1.some(r=>r.a!=null)?[{type:'scatter',label:'Radar aguas arriba',data:S1.filter(r=>r.a!=null).map(r=>({x:r.T,y:r.a})),borderColor:css('--mf'),backgroundColor:css('--mf')+'55',pointStyle:'rect',pointRadius:3}]:[])];
  if(mode==='mg'){ds.length=0;ds.push(
    {type:'line',label:'Margen derecha (oriental)',data:MG.map(r=>({x:r.T,y:r.ad+r.bd})),borderColor:css('--mf'),backgroundColor:css('--mf'),pointRadius:3,borderWidth:1},
    {type:'line',label:'Margen izquierda (occidental)',data:MG.map(r=>({x:r.T,y:r.ai+r.bi})),borderColor:css('--muted'),backgroundColor:css('--muted'),pointRadius:3,borderWidth:1})}
  o.plugins.legend.labels.filter=it=>it.text!=='_';
  o.onClick=(ev,els,ch)=>{if(!els.length)return;const e=els[0],d=ch.data.datasets[e.datasetIndex],pt=d.data[e.index];if(!pt)return;const f=new Date(pt.x).toISOString().slice(0,10);if(window.__visorGo)window.__visorGo(f,/radar|Radar/.test(d.label))};
  mk('ch-sat',{data:{datasets:ds},options:o});
  document.getElementById('sat-note').textContent=`Círculos: Sentinel-2 (${J.n_utiles} escenas). Triángulos: Landsat 8/9 (${LS.length} escenas, NDVI ≥ 0,40; frente a Sentinel-2 en ${J.landsat_validacion?.n||31} fechas cercanas: ρ = 0,82, sesgo −0,6 ha). Cuadros: radar Sentinel-1 (${S1.length} escenas, ${J.s1_validacion?.umbral||'VH ≥ −14 dB'}; frente a Sentinel-2 en ${J.s1_validacion?.n||90} fechas: ρ = ${nf(J.s1_validacion?.rho??0.75,2)}, error medio ${nf(J.s1_validacion?.mae_ha??11.3,1)} ha; ve a través de las nubes). ${J.s1_validacion?.usa_arriba?'Aguas arriba también se muestra (ρ = '+nf(J.s1_validacion.rho_arriba,2)+').':'Aguas arriba el radar no concuerda lo suficiente y no se muestra por lado.'} Las ópticas solo con al menos ${nf(J.metodo.minimo_despejado*100)} % del núcleo despejado. La franja muestra el rango con umbrales de NDVI entre 0,2 y 0,4: la forma de la serie no cambia (correlación ≥ 0,95). Hay meses sin escenas útiles por nubosidad.`;
  if(mode==='mg')document.getElementById('sat-note').textContent=`Área de vegetación flotante a cada lado del eje del cauce (aguas arriba + aguas abajo), Sentinel-2 y Landsat 8/9, ${MG.length} escenas con al menos 70 % despejado. La margen derecha (oriental) es hacia donde se extrae el material. Cada margen se estima con su propia fracción despejada, así que la suma puede diferir unas hectáreas del total.`;
  const m=Array.from({length:12},(_,k)=>ALL.filter(r=>new Date(r.T).getUTCMonth()===k).map(r=>r.t));
  const om=baseOpts();om.scales.y.title={display:true,text:'hectáreas (mediana)'};om.plugins.tooltip.callbacks.label=c=>`${nf(c.parsed.y,1)} ha · ${m[c.dataIndex].length} escenas`;
  mk('ch-sat-mes',{type:'bar',data:{labels:MES,datasets:[{label:'Mediana',data:m.map(a=>a.length?median(a):null),backgroundColor:css('--ma')}]},options:om,
    plugins:[{id:'n',afterDatasetsDraw(ch){const g=ch.ctx;g.save();g.fillStyle=css('--muted');g.font='11px '+css('--f-mono').split(',')[0];g.textAlign='center';ch.getDatasetMeta(0).data.forEach((b,i)=>{g.fillText(m[i].length,b.x,b.y-4)});g.restore()}}]});
  const sel=document.getElementById('sat-anio');
  if(!sel.options.length){J.mapas.forEach(y=>sel.insertAdjacentHTML('beforeend',`<option value="${y}">${y}</option>`));sel.value=J.mapas[J.mapas.length-1];sel.onchange=()=>{document.getElementById('sat-mapa').src=`datos/satelite/app/frecuencia_${sel.value}.png`}}
  document.getElementById('sat-mapa').src=`datos/satelite/app/frecuencia_${sel.value}.png`;
  document.getElementById('sat-ql').src='datos/satelite/app/ultima_escena.jpg';
  document.getElementById('sat-ql-note').textContent=`Sentinel-2, ${fmtD(d0(J.ultima_vista))}, color real, 10 m. Actualizado ${J.generado} UTC.`;
  renderVisor(J);
  renderCorredor(); renderVolumen(J,ALL); renderRetenido();
  renderAlertas();renderAlertBanner('sat-alert');
  document.getElementById('sat-metodo').innerHTML=`<h3>Método</h3><ul>
   <li><b>Imágenes:</b> ${J.metodo.sensor}, desde 2019; nubes y sombras excluidas con la clasificación de escena (SCL).</li>
   <li><b>Zona de agua:</b> píxeles con agua (MNDWI &gt; 0) en al menos la mitad de las escenas despejadas, a 2,5 km de la barrera: ${nf(A.total)} ha. El índice de agua del SCL no sirve aquí porque confunde el agua turbia del Cauca con suelo.</li>
   <li><b>Vegetación flotante:</b> NDVI ≥ 0,30 dentro de la zona de agua. Se verificó visualmente en escenas con mucha y poca cobertura.</li>
   <li><b>Otros sensores:</b> Landsat 8/9 (30 m, NDVI ≥ 0,40) y radar Sentinel-1 corregido por terreno (${J.s1_validacion?.umbral||'VH ≥ −14 dB'}) se calibraron contra Sentinel-2 en fechas cercanas (ρ = 0,82 y ${nf(J.s1_validacion?.rho??0.75,2)}${J.s1_validacion?.clasificador?`; un clasificador de VV, VH y textura entrenado píxel a píxel con Sentinel-2 se probó dejando un año fuera y fue peor (ρ = ${nf(J.s1_validacion.clasificador.rho,2)}), así que se mantiene el umbral`:''}). Con los tres, todos los meses desde 2019 tienen al menos una medición.</li>
   <li><b>Lo que no se puede medir:</b> madera y residuos no verdes. El índice de residuos flotantes (FDI) del agua turbia (mediana 0,048) se confunde con el del material, así que con 10 m de resolución no se separan.</li></ul>
   <h3>Qué muestra y cómo se validó</h3><ul>
   <li><b>Dos procesos distintos.</b> Al sur de la barrera (aguas arriba, agua turbia de río) se ve lo que la barrera retiene; al norte (aguas abajo, agua quieta del embalse) crecen las macrófitas. La revisión visual de 15 escenas en color real confirma las masas verdes en el lado que reporta cada serie.</li>
   <li><b>Margen derecha (oriental), hacia donde se extrae:</b> se dividió la zona por el eje del cauce. Desde 2024 la margen derecha concentra la mayor parte del material (69–79 % aguas abajo y 57–78 % aguas arriba en escenas con más de 3 ha), lo que concuerda con la operación. Ninguna subzona (margen, franja de 100 m junto a la orilla, 600 m alrededor de la barrera) anticipa la extracción mejor que la propia extracción reciente (correlación parcial ≤ 0,08, no significativa).</li>
   <li><b>Aguas arriba concuerda con la extracción de macrófitas:</b> ρ = +0,24 con lo extraído las 2 semanas previas y +0,24 con las 2 siguientes, quitando la estacionalidad (190 escenas ópticas, p &lt; 0,01; zonas separadas por la línea de la barrera).</li>
   <li><b>Aguas abajo va en sentido contrario:</b> ρ = −0,21 con lo extraído las 2 semanas previas y −0,31 a escala mensual. Por eso el <b>total mezcla ambos efectos</b> y casi no se relaciona con la extracción (ρ mensual −0,20, no significativo): use la vista «Aguas arriba y abajo».</li>
   <li>Más área con caudal alto (ρ mensual = +0,39, n = 87) y con nivel alto del embalse (+0,17 a +0,39 según sensor). La estacionalidad es clara: poca área de enero a febrero y más de marzo a julio.</li>
   <li><b>Corredor de 30 km:</b> se midió la vegetación en 6 tramos, 15 km aguas arriba y abajo (283 fechas). Lo que se ve aguas arriba no anticipa la extracción: al usarlo en el pronóstico el error sube en todos los tramos.</li>
   <li>La madera y los residuos (material flotante) no se ven: su relación con el área es débil (ρ ≈ +0,2). El satélite no mejora el pronóstico semanal (diferencias de −2 a +4 m³/semana, no significativas); se usa como indicador de estado.</li>
   <li>Los valores más altos (22 may y 11 jun 2019: 116 y 153 ha) coinciden con la crisis del buchón de 2019: en abril la Fiscalía pidió su retiro urgente y el 1 de junio se rompió una barrera de contención (Blu Radio, 3 jun 2019).</li></ul>`;
}


function exportCSV(){
  if(!FC) return; const B=FC.blocks, q=v=>v==null?'':String(Math.round(v));
  const rows=[['semana','desde','hasta','dias','descanso_programado','caudal_m3s','flotante_p50','macrofitas_p50','total_p50','total_esperado','total_p10','total_p90']].concat(
    B.map(b=>['S'+b.h,new Date(b.t0).toISOString().slice(0,10),new Date(b.t1).toISOString().slice(0,10),b.nd,b.rest??'',q(b.q),q(b.mf),q(b.ma),q(b.tot),q(b.tot_e),q(b.tot_p10),q(b.tot_p90)]));
  const blob=new Blob(['\ufeff'+rows.map(r=>r.join(';')).join('\n')],{type:'text/csv;charset=utf-8'});
  const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='pronostico_flotante_'+new Date().toISOString().slice(0,10)+'.csv';document.body.appendChild(a);a.click();setTimeout(()=>{URL.revokeObjectURL(a.href);a.remove()},500);
}
/* ---------- vista operación (esfuerzo) ---------- */
function renderOps(){
  const E=S.src.esfuerzo; if(!E) return;
  const CAT=[['opero','Operó','--accent'],['programada','Descanso programado','--muted'],['operativa','Labores operativas (barreras, piscinas, equipos, vías)','--mf'],['disponibilidad','Sin material en el puerto o mancha lejos','--ma'],['externa','Externa (aislamiento, orden público, contingencias)','--bad'],['sin_dato','Sin explicación registrada','--line2']];
  const n=E.semanas.length, T=E.semanas.map(d0), last8=[...Array(8)].map((_,k)=>n-8+k);
  const sum=(a,ix)=>ix.reduce((s,i)=>s+a[i],0), op8=sum(E.dias.opero,last8)/8, m8=sum(E.mec,last8)/Math.max(1,sum(E.dias.opero,last8));
  const yrs=E.anual.filter(a=>a.anio>=2021&&a.anio<=2025), opH=median(yrs.map(a=>a.opero));
  document.getElementById('ops-kpis').innerHTML=[
    ['info','Días operados por semana',`${nf(op8,1)}`,`últimas 8 semanas hasta ${fmtD(T[n-1])} · típico 2021–2025: ${nf(opH,1)}`],
    ['info','m³ por día operado',`${nf(m8)} <small>m³</small>`,`mecanizado, últimas 8 semanas · casi constante entre años (${nf(Math.min(...yrs.map(a=>a.m3dia)))}–${nf(Math.max(...yrs.map(a=>a.m3dia)))})`],
    ['ok','Lo que explica la extracción',`${nf(E.r2.volq*100)} %`,`de la variación semanal del mecanizado la explican los días y volquetas en operación (${nf(E.r2.dias*100)} % solo los días)`],
    ['warn','Caudal alto',`${nf(E.caudal[4].opera*100)} %`,`de los días se opera con caudal > ${nf(+E.caudal[4].rango.split('–')[0])} m³/s, frente a ${nf(E.caudal[2].opera*100)} % con caudal medio`]
  ].map(([c,l,v,d])=>`<div class="st ${c} c3"><h2>${l}</h2><div class="big">${v}</div><div class="note">${d}</div></div>`).join('');
  const o=baseOpts(); o.scales.x={stacked:true,grid:{display:false},ticks:{maxTicksLimit:12,callback:(v,i)=>{const d=new Date(T[i]);return MES[d.getUTCMonth()]+' '+String(d.getUTCFullYear()).slice(2)}}};
  o.scales.y={stacked:true,max:7,grid:{color:css('--line')},title:{display:true,text:'días de la semana'}};
  o.plugins.tooltip.callbacks.title=it=>'Semana al '+fmtD(T[it[0].dataIndex]); o.plugins.tooltip.callbacks.label=c=>`${c.dataset.label}: ${c.parsed.y} d`;
  o.interaction={mode:'index',intersect:false};
  mk('ch-ops',{type:'bar',data:{labels:E.semanas,datasets:CAT.map(([k,l,v])=>({label:l,data:E.dias[k],backgroundColor:css(v),borderWidth:0,barPercentage:1,categoryPercentage:1}))},options:o});
  const yr=E.anual;
  document.getElementById('ops-anual').innerHTML='<thead><tr><th>Año</th><th>Días operados / sem</th><th>Descanso programado</th><th>Labores operativas</th><th>Sin material</th><th>m³ por día operado</th><th>Volquetas por día</th><th>Hora de inicio</th><th>Parte asignada a flotante</th><th>Manual m³/sem</th></tr></thead><tbody>'+
    yr.map(a=>`<tr><td>${a.anio}${a.dias<300?' <small>(parcial)</small>':''}</td><td class="num">${nf(a.opero,1)}</td><td class="num">${nf(a.prog,1)}</td><td class="num">${nf(a.oper,1)}</td><td class="num">${nf(a.disp,1)}</td><td class="num">${nf(a.m3dia)}</td><td class="num">${nf(a.volq,0)}</td><td class="num">${a.hora?Math.floor(a.hora)+':'+String(Math.round(a.hora%1*60)).padStart(2,'0'):'—'}</td><td class="num">${nf(a.mf_share*100)} %</td><td class="num">${nf(a.man_sem)}</td></tr>`).join('')+'</tbody>';
  document.getElementById('ops-caudal').innerHTML='<thead><tr><th>Caudal Sitio Presa (m³/s)</th><th>Días</th><th>Opera</th><th>Descanso</th><th>Labores operativas</th><th>Sin material en puerto</th><th>m³ por día operado</th></tr></thead><tbody>'+
    E.caudal.map(c=>`<tr><td>${c.rango} <small>(mediana ${nf(c.q50)})</small></td><td class="num">${nf(c.n)}</td><td class="num"><b>${nf(c.opera*100)} %</b></td><td class="num">${nf(c.prog*100)} %</td><td class="num">${nf(c.oper*100)} %</td><td class="num">${nf(c.disp*100,1)} %</td><td class="num">${nf(c.m3dia)}</td></tr>`).join('')+'</tbody>';
  const bt=E.backtest, pc=(a,b)=>nf((b/a-1)*100);
  document.getElementById('ops-bt').innerHTML='<thead><tr><th>Serie · horizonte</th><th>Modelo actual</th><th>Con descanso programado conocido</th><th>Con calendario (festivos y fines de semana)</th><th>Con caudal observado (perfecto)</th><th>Sabiendo todos los días operados</th></tr></thead><tbody>'+
    [['Total · semanas 1–4',0],['Total · semanas 5–13',1]].map(([l,k])=>`<tr><td>${l}</td><td class="num">${nf(bt.base.tot[k])}</td><td class="num"><b>${nf(bt.prog.tot[k])}</b> (${pc(bt.base.tot[k],bt.prog.tot[k])} %)</td><td class="num">${nf(bt.calendario.tot[k])} (${pc(bt.base.tot[k],bt.calendario.tot[k])} %)</td><td class="num">${nf(bt.caudal_oraculo.tot[k])} (${pc(bt.base.tot[k],bt.caudal_oraculo.tot[k])} %)</td><td class="num">${nf(bt.oraculo_dias.tot[k])} (${pc(bt.base.tot[k],bt.oraculo_dias.tot[k])} %)</td></tr>`).join('')+
    [['Flotante · semanas 1–4','mf',0],['Macrófitas · semanas 1–4','ma',0]].map(([l,c,k])=>`<tr><td>${l}</td><td class="num">${nf(bt.base[c][k])}</td><td class="num"><b>${nf(bt.prog[c][k])}</b> (${pc(bt.base[c][k],bt.prog[c][k])} %)</td><td class="num">—</td><td class="num">—</td><td class="num">—</td></tr>`).join('')+'</tbody>';
}


/* ---------- visor satelital interactivo (Leaflet, se carga solo al abrir Satélite) ---------- */
let LF_P=null, VIS=null, MAP=null, VL={};
function loadLeaflet(){if(window.L)return Promise.resolve();if(LF_P)return LF_P;LF_P=new Promise((ok,ko)=>{
  const c=document.createElement('link');c.rel='stylesheet';c.href='vendor/leaflet/leaflet.css';document.head.appendChild(c);
  const s=document.createElement('script');s.src='vendor/leaflet/leaflet.js';s.onload=ok;s.onerror=()=>{LF_P=null;ko(new Error('no se pudo cargar el mapa'))};document.head.appendChild(s)});return LF_P}
async function renderVisor(J){
  const box=document.getElementById('visor');if(!box)return;
  try{await loadLeaflet();if(!VIS)VIS=await fetchJSON('datos/satelite/visor/visor.json',10000)}catch(e){box.innerHTML='<p class="note">El visor no está disponible: '+esc(e.message)+'</p>';return}
  const sel=document.getElementById('vis-fecha'), sen=document.getElementById('vis-sensor');
  const lista=()=>sen.value==='s1'?VIS.s1.slice().reverse().map(f=>({f})):VIS.s2.slice().reverse();
  const area=f=>{const r=(sen.value==='s1'?(J.s1||[]):J.serie).find(x=>x.f===f);return r?` · ${nf(r.t,1)} ha`:''};
  const fill=()=>{const keep=sel.value;sel.innerHTML=lista().map(r=>`<option value="${r.f}">${fmtD(d0(r.f))}${area(r.f)}</option>`).join('');if([...sel.options].some(o=>o.value===keep))sel.value=keep};
  if(!MAP){
    MAP=L.map('visor',{zoomControl:true,attributionControl:true});const cen=L.latLng((VIS.linea[0][0]+VIS.linea[1][0])/2,(VIS.linea[0][1]+VIS.linea[1][1])/2);MAP.fitBounds(cen.toBounds(1800));setTimeout(()=>{MAP.invalidateSize();MAP.fitBounds(cen.toBounds(1800))},200);
    const esri=L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',{maxZoom:19,attribution:'Imagen base © Esri, Maxar, Earthstar Geographics'});
    const osm=L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'© OpenStreetMap'});
    esri.addTo(MAP);
    VL.zona=L.imageOverlay('datos/satelite/visor/zona.png',VIS.bounds,{opacity:1,interactive:false}).addTo(MAP);
    VL.barrera=L.polyline(VIS.linea,{color:'#ef4444',weight:4}).bindTooltip('Barrera (identificada en Sentinel-2)').addTo(MAP);
    VL.punto=L.circleMarker(VIS.punto,{radius:4,color:'#f59e0b',weight:2,fillOpacity:.6}).bindTooltip('Punto informado (orilla occidental)').addTo(MAP);
    const PU=VIS.puerto||[6.893912,-75.82926],DE=VIS.deposito||[6.8955,-75.827299];
    VL.puerto=L.circleMarker(PU,{radius:7,color:'#fff',weight:2,fillColor:'#0ea5e9',fillOpacity:1}).bindTooltip('Punto de extracción (margen derecha)').addTo(MAP);
    VL.radio=L.circle(PU,{radius:500,color:'#0ea5e9',weight:1,dashArray:'4 4',fill:false}).addTo(MAP);
    VL.deposito=L.circleMarker(DE,{radius:6,color:'#fff',weight:2,fillColor:'#a855f7',fillOpacity:1}).bindTooltip('Depósito').addTo(MAP);
    L.control.layers({'Alta resolución (Esri)':esri,'Mapa (OpenStreetMap)':osm},{},{collapsed:true}).addTo(MAP);
    L.control.scale({imperial:false}).addTo(MAP);
    sen.onchange=()=>{fill();sel.selectedIndex=0;show()};sel.onchange=show;
    document.getElementById('vis-prev').onclick=()=>{if(sel.selectedIndex<sel.options.length-1){sel.selectedIndex++;show()}};
    document.getElementById('vis-next').onclick=()=>{if(sel.selectedIndex>0){sel.selectedIndex--;show()}};
    document.querySelectorAll('#vis-capas input').forEach(i=>i.onchange=show);
    document.getElementById('vis-op').oninput=show;
  }
  fill();show();
  function show(){
    const f=sel.value,isS1=sen.value==='s1',on=id=>document.getElementById(id).checked,op=+document.getElementById('vis-op').value/100;
    ['img','veg'].forEach(k=>{if(VL[k]){MAP.removeLayer(VL[k]);VL[k]=null}});
    if(on('vc-img')){const u=isS1?`datos/satelite/visor/s1_${f}.jpg`:`datos/satelite/series/ql_${f}.jpg`;if(isS1||(VIS.s2.find(r=>r.f===f)||{}).ql)VL.img=L.imageOverlay(u,VIS.bounds,{opacity:op}).addTo(MAP)}
    if(on('vc-veg')&&!isS1)VL.veg=L.imageOverlay(`datos/satelite/visor/veg_${f}.png`,VIS.bounds,{opacity:1}).addTo(MAP);
    on('vc-zona')?VL.zona.addTo(MAP):MAP.removeLayer(VL.zona); on('vc-bar')?(VL.barrera.addTo(MAP),VL.punto.addTo(MAP)):(MAP.removeLayer(VL.barrera),MAP.removeLayer(VL.punto));
    document.getElementById('vis-info').textContent=isS1?`Radar Sentinel-1 (VH, ${fmtD(d0(f))}): claro = más retrodispersión (vegetación, orillas); oscuro = agua lisa. Ve a través de las nubes.`:`Sentinel-2 ${fmtD(d0(f))}, color real 10 m. Verde: vegetación flotante detectada (NDVI ≥ 0,30); blanco: nube o sombra. Borde azul: zona de agua analizada.`;
  }
  window.__visorGo=(f,s1)=>{sen.value=s1?'s1':'s2';fill();if([...sel.options].some(o=>o.value===f)){sel.value=f;show();box.scrollIntoView({behavior:'smooth',block:'center'})}};
}


/* ---------- corredor del río (30 km aguas arriba, 15 km aguas abajo) ---------- */
let COR=null;
async function renderCorredor(){
  const box=document.getElementById('cor-tabla');if(!box)return;
  try{if(!COR)COR=await fetchJSON('datos/satelite/corredor/serie.json',10000)}catch(e){box.innerHTML='<tbody><tr><td>El análisis del corredor aún no está disponible.</td></tr></tbody>';return}
  const tr=COR.tramos, lab=t=>{const [a,b]=t.split('..').map(Number);return b<=0?`${nf(Math.abs(b),1)}–${nf(Math.abs(a),1)} km aguas arriba`:`${nf(a,1)}–${nf(b,1)} km aguas abajo`};
  const last=t=>{for(let i=COR.serie.length-1;i>=0;i--){if(COR.serie[i][t]!=null)return COR.serie[i]}return null};
  const med=t=>median(COR.serie.map(r=>r[t]).filter(v=>v!=null));
  box.innerHTML='<thead><tr><th>Tramo</th><th>Agua (ha)</th><th>Última escena despejada</th><th>Vegetación (ha)</th><th>% del agua</th><th>Mediana histórica (ha)</th></tr></thead><tbody>'+
    tr.map(t=>{const r=last(t);return `<tr><td>${lab(t)}</td><td class="num">${nf(COR.agua_ha[t])}</td><td>${r?fmtD(d0(r.f)):'—'}</td><td class="num"><b>${r?nf(r[t],1):'—'}</b></td><td class="num">${r?nf(r[t]/COR.agua_ha[t]*100):'—'} %</td><td class="num">${nf(med(t),1)}</td></tr>`}).join('')+'</tbody>';
  const cols=['#7c3aed','#2563eb','#0891b2','#10b981','#84cc16','#f59e0b','#f97316','#ef4444'];
  const o=baseOpts();o.scales.x={type:'linear',grid:{color:css('--line')},ticks:{callback:v=>{const d=new Date(v);return MES[d.getUTCMonth()]+' '+String(d.getUTCFullYear()).slice(2)},maxTicksLimit:10}};
  o.scales.y.title={display:true,text:'hectáreas'};o.plugins.tooltip.callbacks.title=it=>fmtD(it[0].parsed.x);o.plugins.tooltip.callbacks.label=c=>c.dataset.label+': '+nf(c.parsed.y,1)+' ha';
  mk('ch-cor',{type:'line',data:{datasets:tr.map((t,i)=>({label:lab(t),data:COR.serie.filter(r=>r[t]!=null).map(r=>({x:d0(r.f),y:r[t]})),borderColor:cols[i],backgroundColor:cols[i],pointRadius:1.5,borderWidth:1,tension:0,hidden:!t.startsWith('-')}))},options:o});
  document.getElementById('cor-nota').textContent=`Sentinel-2 a 20 m, ${COR.serie.length} fechas con algún tramo despejado (≥ 60 %). Se actualiza todos los días con las imágenes nuevas (última revisión ${COR.generado} UTC). Haga clic en la leyenda para mostrar u ocultar tramos; por defecto se ven los de aguas arriba.`;
}




/* ---------- mancha retenida en la barrera (óptico + radar) ---------- */
let RET=null;
async function renderRetenido(){
  const box=document.getElementById('ret-panel'); if(!box) return;
  try{if(!RET)RET=await fetchJSON('datos/satelite/retenido/serie.json',15000)}catch(e){box.hidden=true;return}
  if(!RET||!Object.keys(RET.optico||{}).length){box.hidden=true;return} box.hidden=false;
  const seg=document.getElementById('ret-var'); if(!seg.dataset.on){seg.dataset.on=1;seg.querySelectorAll('button').forEach(b=>b.onclick=()=>{seg.querySelectorAll('button').forEach(x=>x.setAttribute('aria-pressed',x===b));renderRetenido()})}
  const v=[...seg.querySelectorAll('button')].find(b=>b.getAttribute('aria-pressed')==='true').dataset.v;
  const pts=src=>Object.entries(RET[src]||{}).filter(([f,o])=>o[v]!=null).map(([f,o])=>({x:d0(f),y:o[v]})).sort((a,b)=>a.x-b.x);
  const O=pts('optico'), R=pts('radar'), all=[...O,...R].sort((a,b)=>a.x-b.x);
  const qs=[]; for(let i=S.first;i<S.n;i++){if(S.q[i]!=null&&S.T[i]>=d0('2019-01-01'))qs.push({x:S.T[i],y:S.q[i]})}
  const o=baseOpts(); o.scales.x={type:'linear',grid:{color:css('--line')},ticks:{callback:x=>{const d=new Date(x);return MES[d.getUTCMonth()]+' '+String(d.getUTCFullYear()).slice(2)},maxTicksLimit:10}};
  o.scales.x.min=d0('2019-01-01');o.scales.y.title={display:true,text:v==='ret'?'hectáreas':'% de la franja'}; o.scales.y2={position:'right',grid:{display:false},title:{display:true,text:'Sitio Presa m³/s'}};
  o.plugins.tooltip.callbacks.title=it=>fmtD(it[0].parsed.x);
  mk('ch-ret',{type:'line',data:{datasets:[
    {label:'Óptico (Sentinel-2)',data:O,borderColor:css('--ma'),backgroundColor:css('--ma'),showLine:false,pointRadius:2.5},
    {label:'Radar (Sentinel-1)',data:R,borderColor:css('--mf'),backgroundColor:css('--mf'),showLine:false,pointRadius:2.5,pointStyle:'rect'},
    {label:'Caudal Sitio Presa',data:qs,yAxisID:'y2',borderColor:css('--flow2'),backgroundColor:css('--flow2'),pointRadius:0,borderWidth:1}]},options:o});
  const vals=all.map(p=>p.y).sort((a,b)=>a-b), pct=p=>vals[Math.min(vals.length-1,Math.floor(p*vals.length))], last=all[all.length-1];
  const lastO=O[O.length-1], lastR=R[R.length-1], rank=last?vals.filter(x=>x<=last.y).length/vals.length:0;
  const u=v==='ret'?' ha':' %';
  document.getElementById('ret-cards').innerHTML=[
    [rank>=0.9?'warn':'info',v==='ret'?'Mancha retenida (0–2,5 km aguas arriba)':'Ocupación de la barrera (franja de 100 m)',last?`${nf(last.y,1)}<small>${u}</small>`:'—',last?`${fmtD(last.x)} · ${R.includes(last)?'radar':'óptico'} · percentil ${nf(rank*100)}${v==='bar'&&rank>=0.9?' · <b>≥ P90: vigilar la barrera</b>':''} · mediana ${nf(pct(0.5),1)}${u}, P90 ${nf(pct(0.9),1)}${u}`:''],
    ['info','Mediciones',`${nf(O.length)} + ${nf(R.length)}`,`ópticas + radar desde 2019 · última óptica ${lastO?fmtD(lastO.x):'—'}, último radar ${lastR?fmtD(lastR.x):'—'}`]
  ].map(([s,t,b,n])=>`<div class="st ${s} c6"><h2>${t}</h2><div class="big">${b}</div><div class="note">${n}</div></div>`).join('');
  const lab=t=>{const [a,b]=t.split('..').map(Number);return b<=0?`${nf(Math.abs(b),1)}–${nf(Math.abs(a),1)} km aguas arriba`:`${nf(a,1)}–${nf(b,1)} km aguas abajo`};
  const ult=k=>{let best=null;for(const src of ['optico','radar'])for(const [f,o] of Object.entries(RET[src]||{}))if(o[k]!=null&&(!best||f>best.f))best={f,v:o[k],src};return best};
  const med=k=>median([...Object.values(RET.optico||{}),...Object.values(RET.radar||{})].map(o=>o[k]).filter(x=>x!=null));
  document.getElementById('ret-tabla').innerHTML='<thead><tr><th>Tramo</th><th>Agua (ha)</th><th>Última medición</th><th>Vegetación (ha)</th><th>Mediana histórica (ha)</th></tr></thead><tbody>'+
    RET.tramos.map(t=>{const k='t'+t.replace('..','_');const u_=ult(k);return `<tr><td>${lab(t)}</td><td class="num">${nf(RET.agua_ha[k]??null)}</td><td>${u_?fmtD(d0(u_.f))+' · '+(u_.src==='radar'?'radar':'óptico'):'—'}</td><td class="num"><b>${u_?nf(u_.v,1):'—'}</b></td><td class="num">${nf(med(k),1)}</td></tr>`}).join('')+'</tbody>';
  const SA=S.src.rezagos&&S.src.rezagos.satelite, rr=document.getElementById('ret-read');
  if(SA&&rr){const b0=SA.balance['0'],bc=SA.balance['738'],bd=SA.balance_abajo['738'],B=SA.bar;
    rr.innerHTML=`<p><b>Cómo leer este panel.</b> Cada punto es una medición: verde = óptico (Sentinel-2), naranja = radar (Sentinel-1). «Mancha retenida» son las hectáreas de vegetación flotante en los 2,5 km de río justo antes de la barrera; «Ocupación» es qué parte de la franja de 100 m pegada a la barrera está cubierta. La tabla da cada tramo del corredor, de 30 km aguas arriba a 30 km aguas abajo. Para pasar hectáreas a m³ se multiplica por ${nf(VOLK.central)} (cuenta completa arriba, en «Cómo salen las cuentas»).</p><p><b>Lectura.</b> La mancha retenida suele ser pequeña y <b>no crece cuando sube el caudal</b>. Justo aguas abajo de la barrera sí aparece más vegetación con caudal alto: indicio de que parte del material pasa la barrera. Lo seguro es que en crecientes se extrae menos; el balance por tipo de semana está en el resumen de arriba.</p><details><summary class="note" style="cursor:pointer">Detalle técnico</summary><p><b>Qué muestra.</b> La mancha retenida aguas arriba de la barrera <b>no crece con el caudal</b> (ρ ≈ 0 en 205 semanas con medición, óptica o de radar). En cambio, la vegetación en los <b>2,5 km aguas abajo</b> sí aumenta con el caudal (ρ = 0,47, q = 0,02, confirmado solo con óptico, ρ = 0,38): en crecientes parte del material <b>pasa la barrera</b>.</p>
<p><b>Balance semanal</b> (llegada = extraído + cambio de la mancha × m³/ha, ${nf(b0.n)} semanas, valor central ${nf(VOLK.central)} m³/ha): solo con lo extraído la relación con el caudal es r = ${nf(b0.r_q,2)} (p = ${nf(b0.p_q,3)}); sumando la mancha retenida, r = ${nf(bc.r_q,2)}; sumando además lo que pasa aguas abajo, r = ${nf(bd.r,2)} (p = ${nf(bd.p,2)}). Es decir, en crecientes lo que llega no disminuye: baja lo que se alcanza a extraer, y la diferencia queda retenida o, sobre todo, sobrepasa la barrera. El rango de m³/ha es amplio (bajo–alto ${nf(VOLK.bajo)}–${nf(VOLK.alto)}), así que el balance es indicativo.</p>
<p><b>Riesgo para la barrera.</b> La ocupación de la franja de 100 m se compara con su historia (mediana y P90 en la tarjeta de arriba, opción «Ocupación de la barrera»); una ocupación ≥ P90 se marca en ámbar. Solo ${nf(B.n_q_alto)} mediciones coinciden con caudal > 2.300 m³/s (${nf(B.p_alto_q_alto*100)} % de ellas ≥ P90 frente a ${nf(B.p_alto_q_bajo*100)} % con caudal menor): son pocas para concluir. La mancha retenida no mejora el pronóstico de extracción, por eso se usa como monitoreo y no entra al modelo.</p></details>`}
  const C=RET.calibracion_radar||{}, ce=C.elegido?C[C.elegido]:null;
  document.getElementById('ret-nota').innerHTML=`Mancha retenida: vegetación flotante en el agua de los 2,5 km aguas arriba de la línea de la barrera. Ocupación: % de la franja de 0–100 m frente a la barrera cubierta. Óptico: NDVI ≥ 0,30 a 20 m, solo con ≥ 60 % de la zona despejada. Radar: VH ≥ ${C.elegido?'−'+C.elegido.slice(2):'−14'} dB, ve a través de nubes, útil en crecientes${ce?`; frente al óptico (±3 días, ${ce.n} pares): ρ = ${nf(ce.rho,2)}, sesgo ${nf(ce.sesgo_ha,1)} ha, error medio ${nf(ce.mae_ha,1)} ha`:''}. Zona de agua erosionada 20 m para no contar orillas. Sentinel-2 pasa cada 5 días y Sentinel-1 cada 12 (6 desde 2025): no es una medición diaria. Madera y residuos no se distinguen de la vegetación en el radar ni se ven en el óptico. Actualización diaria automática (${RET.generado} UTC).`;
}

/* ---------- volumen estimado a partir del área satelital ---------- */
// Biomasa fresca por m² de jacinto de agua (Eichhornia crassipes): mínimo 3,8, mediana 11,8 y máximo 40,8 kg/m² (PeerJ 2023, 12 meses, llanura del Brahmaputra).
// Densidad aparente del proyecto: 160 kg/m³ (conversión de la hoja de viajes manual). m³/ha = kg/m² × 10.000 / 160.
const VOLK={bajo:3.8*1e4/160,central:11.8*1e4/160,alto:40.8*1e4/160};
async function renderVolumen(J,ALL){
  const box=document.getElementById('vol-cards');if(!box)return;
  try{if(!COR)COR=await fetchJSON('datos/satelite/corredor/serie.json',10000)}catch(e){}
  const rng=ha=>`${nf(ha*VOLK.central)} <small>m³</small>`, rtxt=ha=>`${nf(ha*VOLK.bajo)}–${nf(ha*VOLK.alto)} m³`;
  // ritmo de extracción de las últimas 8 semanas
  let e8=0;for(let i=S.last-55;i<=S.last;i++)e8+=(S.mf[i]||0)+(S.ma[i]||0);const eDia=e8/56;
  const last=ALL[ALL.length-1], cards=[];
  cards.push(['info','Zona del puerto (núcleo de '+nf(J.area_ha.total)+' ha)',last.t,`${fmtD(last.T)} · ${last.src} · ${nf(last.t,1)} ha · rango ${rtxt(last.t)} · ≈ ${nf(last.t*VOLK.central/Math.max(eDia,1))} días de extracción al ritmo de las últimas 8 semanas (${nf(eDia)} m³/día)`]);
  if(COR&&COR.serie){const up=COR.tramos.filter(t=>t.split('..').map(Number)[1]<=0);let ha=0,fs=[];
    up.forEach(t=>{for(let i=COR.serie.length-1;i>=0;i--){const r=COR.serie[i];if(r[t]!=null){ha+=r[t];fs.push(r.f);break}}});
    const f0=fs.sort()[0],f1=fs[fs.length-1];
    cards.push(['info','Corredor 0–30 km aguas arriba',ha,`${nf(ha,1)} ha · última escena despejada de cada tramo (${fmtD(d0(f0))} a ${fmtD(d0(f1))}) · rango ${rtxt(ha)} · material en camino al puerto`]);}
  box.innerHTML=cards.map(([s,t,ha,d])=>`<div class="st ${s} c6"><h2>${t}</h2><div class="big">${rng(ha)}</div><div class="note">${d}</div></div>`).join('');
  // serie mensual: inventario de la zona del puerto frente a la extracción del mes
  const mk_=t=>{const d=new Date(t);return Date.UTC(d.getUTCFullYear(),d.getUTCMonth(),1)};
  const A=new Map();ALL.forEach(r=>{const k=mk_(r.T);const o=A.get(k)||{s:0,n:0};o.s+=r.t;o.n++;A.set(k,o)});
  const E=new Map();for(let i=S.first;i<=S.last;i++){const k=mk_(S.T[i]);E.set(k,(E.get(k)||0)+(S.mf[i]||0)+(S.ma[i]||0))}
  const partial=mk_(S.T[S.last]+DAY)===mk_(S.T[S.last])?mk_(S.T[S.last]):null; // mes con extracción incompleta
  const ks=[...A.keys()].filter(k=>E.has(k)&&k!==partial&&k>=Date.UTC(2020,0,1)).sort((a,b)=>a-b);
  const rows=ks.map(k=>({k,ha:A.get(k).s/A.get(k).n,n:A.get(k).n,e:E.get(k)}));
  const o=baseOpts();o.scales.x={type:'linear',grid:{color:css('--line')},ticks:{callback:v=>{const d=new Date(v);return MES[d.getUTCMonth()]+' '+String(d.getUTCFullYear()).slice(2)},maxTicksLimit:10}};
  o.scales.y.title={display:true,text:'m³'};o.plugins.legend.labels.filter=l=>l.text!=='_bajo';o.plugins.tooltip.filter=c=>c.dataset.label!=='_bajo';o.plugins.tooltip.callbacks.title=it=>{const d=new Date(it[0].parsed.x);return MES[d.getUTCMonth()]+' '+d.getUTCFullYear()};o.plugins.tooltip.callbacks.label=c=>c.dataset.label+': '+nf(c.parsed.y)+' m³';
  mk('ch-vol',{type:'line',data:{datasets:[
    {label:'Rango del inventario (bajo–alto)',data:rows.map(r=>({x:r.k,y:r.ha*VOLK.alto})),borderColor:'transparent',backgroundColor:css('--accent')+'22',pointRadius:0,fill:'+1'},
    {label:'_bajo',data:rows.map(r=>({x:r.k,y:r.ha*VOLK.bajo})),borderColor:'transparent',pointRadius:0,fill:false},
    {label:'Inventario estimado (central), promedio del mes',data:rows.map(r=>({x:r.k,y:r.ha*VOLK.central})),borderColor:css('--accent'),backgroundColor:css('--accent'),pointRadius:1.5,borderWidth:2},
    {label:'Extracción del mes',data:rows.map(r=>({x:r.k,y:r.e})),borderColor:css('--mf'),backgroundColor:css('--mf'),pointRadius:1.5,borderWidth:2}]},options:o});
  // generación = extracción + Δinventario (últimos 12 meses completos)
  const T=[];for(let i=1;i<rows.length;i++){const a=rows[i-1],b=rows[i];const dh=b.ha-a.ha;T.push({k:b.k,e:b.e,dh,g:b.e+dh*VOLK.central,gl:b.e+dh*(dh>=0?VOLK.bajo:VOLK.alto),gh:b.e+dh*(dh>=0?VOLK.alto:VOLK.bajo),n:b.n})}
  const T12=T.slice(-12);
  document.getElementById('vol-tabla').innerHTML='<thead><tr><th>Mes</th><th>Extracción (m³)</th><th>Δ área (ha)</th><th>Generado, central (m³)</th><th>Rango (m³)</th><th>Escenas</th></tr></thead><tbody>'+
    T12.map(r=>{const d=new Date(r.k);return `<tr><td>${MES[d.getUTCMonth()]} ${d.getUTCFullYear()}</td><td class="num">${nf(r.e)}</td><td class="num">${nf(r.dh,1)}</td><td class="num"><b>${nf(Math.max(0,r.g))}</b></td><td class="num">${nf(Math.max(0,r.gl))}–${nf(Math.max(0,r.gh))}</td><td class="num">${r.n}</td></tr>`}).join('')+
    (T12.length?`<tr><td><b>12 meses</b></td><td class="num"><b>${nf(T12.reduce((s,r)=>s+r.e,0))}</b></td><td class="num">${nf(T12.reduce((s,r)=>s+r.dh,0),1)}</td><td class="num"><b>${nf(Math.max(0,T12.reduce((s,r)=>s+r.g,0)))}</b></td><td></td><td></td></tr>`:'')+'</tbody>';
  document.getElementById('vol-nota').innerHTML=`Volumen = área con vegetación flotante × biomasa fresca por m² ÷ densidad aparente. Biomasa de jacinto de agua: 3,8 (bajo), 11,8 (central) y 40,8 kg/m² (alto), mínimo, mediana y máximo mensual medidos en un año completo (PeerJ, 2023); densidad 160 kg/m³, la misma de la hoja de viajes manual. Equivale a ${nf(VOLK.bajo)}, ${nf(VOLK.central)} y ${nf(VOLK.alto)} m³ por hectárea. <b>Es un orden de magnitud, no una medición:</b> no se ha medido la biomasa por m² en Ituango; con fechas de paro sin extracción el área no creció de forma consistente, así que el factor no se pudo calibrar con los datos propios. Solo cuenta vegetación verde: madera y residuos no se ven. Para cerrar la incertidumbre: pesar el material de 3–5 cuadros de 1 m² en la mancha frente al puerto y medir su volumen suelto.`;
}

/* ---------- alertas satelitales y material frente al puerto ---------- */
let ALR=null;
async function loadAlertas(){if(ALR)return ALR;try{ALR=await fetchJSON('datos/satelite/alertas.json',8000)}catch(e){ALR={activas:[],posibles_pasos_barrera:[]}}return ALR}
async function renderAlertBanner(id){
  const el=document.getElementById(id);if(!el)return;const A=await loadAlertas();const a=A.activas||[];
  if(!a.length){el.hidden=true;return}
  el.hidden=false;el.innerHTML=`<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="flex-shrink:0;color:var(--warn);margin-top:1px"><path d="M12 9v4M12 17h.01"/><path d="M10.3 3.9L1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/></svg><div><b>Alerta satelital${a.length>1?'s ('+a.length+')':''}.</b> ${a.map(x=>esc(x.texto)).join(' ')} <a href="#satelite">Ver en Satélite</a></div>`;
}
async function renderAlertas(){
  const box=document.getElementById('alr-lista');if(!box)return;const A=await loadAlertas();
  box.innerHTML=(A.activas||[]).length?A.activas.map(a=>`<li><span class="tag ${a.nivel==='alta'?'bad':'warn'}">${a.nivel}</span> ${esc(a.texto)}</li>`).join(''):`<li><span class="tag ok">sin alertas</span> Ninguna regla se activó con las imágenes de los últimos 10 días (revisión ${esc(A.generado||'—')} UTC).</li>`;
  const P=A.posibles_pasos_barrera||[];
  document.getElementById('alr-barrera').innerHTML='<thead><tr><th>Entre</th><th>Aguas arriba (ha)</th><th>Aguas abajo (ha)</th><th>Sensores</th></tr></thead><tbody>'+
    P.map(e=>`<tr><td><a href="#satelite" onclick="window.__visorGo&&window.__visorGo('${e.hasta}',${/radar/.test(e.sensores.split('→')[1])});return false">${fmtD(d0(e.desde))} – ${fmtD(d0(e.hasta))}</a></td><td class="num">${nf(e.arriba[0],1)} → ${nf(e.arriba[1],1)}</td><td class="num">${nf(e.abajo[0],1)} → ${nf(e.abajo[1],1)}</td><td>${esc(e.sensores)}</td></tr>`).join('')+'</tbody>';
  // material frente al puerto (corredor diario)
  try{if(!COR)COR=await fetchJSON('datos/satelite/corredor/serie.json',10000)}catch(e){}
  const k=document.getElementById('alr-puerto');if(!k)return;
  if(!COR||!COR.serie.some(r=>r.p500!=null)){k.innerHTML='<div class="st info c12"><h2>Material frente al puerto</h2><div class="note">Se calcula en la próxima corrida diaria del corredor.</div></div>';return}
  const card=(key,tit,desc)=>{const h=COR.serie.filter(r=>r[key]!=null),v=h.map(r=>r[key]).sort((a,b)=>a-b),q=p=>v[Math.min(v.length-1,Math.floor(p*v.length))],last=h[h.length-1],pr=v.filter(x=>x<=last[key]).length/v.length;
    return `<div class="st ${pr>=0.9?'warn':pr<=0.1?'info':'ok'} c6"><h2>${tit}</h2><div class="big">${nf(last[key],1)} <small>ha</small></div><div class="note">${desc} · ${fmtD(d0(last.f))} · percentil ${nf(pr*100)} (mediana ${nf(q(0.5),1)} ha, P90 ${nf(q(0.9),1)} ha, ${v.length} escenas)</div></div>`};
  k.innerHTML=card('bp','Entre el puerto y la barrera','vegetación en el agua de los ~900 m entre el punto de extracción y la barrera')+card('p500','A 500 m del punto de extracción','vegetación en el agua a ≤ 500 m del puerto');
}

/* ---------- vista datos ---------- */
function renderUpdate(){
  const s=S.src;
  document.getElementById('api-url').value=apiBase();
  document.getElementById('src-info').innerHTML=`<p>Extracción: ${s._xlsxName?('<b>'+esc(s._xlsxName)+'</b> ('+(s._repo?'leído del repositorio al abrir':'cargado en esta sesión')+')'):'<b>'+(s.xlsx_name||'DatosExtracción.xlsx')+'</b> (incluido)'}, ${fmtD(S.T[S.first])} a ${fmtD(S.T[S.last])}.</p>
   <p>Caudal observado: promedios diarios de HydroForecast Ituango (Olaya, La Pintada, Sitio Presa y nivel) hasta ${fmtD(S.T[S.n-1])}${LIVE.obsDays?`; ${LIVE.obsDays} días actualizados en vivo`:''}.</p>
   <p>Pronóstico de caudal: ${S.fc.source}, generado ${S.fc.generated_at.replace('T',' ').slice(0,16)}, ${S.fc.fecha.length} días. Estado: <span class="tag ${LIVE.state==='live'?'ok':'warn'}">${LIVE.state==='live'?'en vivo':LIVE.state==='archive'?'archivo diario del repositorio':'respaldo incluido'}</span></p>`;
}

/* ---------- navegación ---------- */

/* ================= barra de rango para gráficos de tiempo ================= */
const RNG={};
const RNG_IDS=new Set(['ch-fc','ch-mult','ch-hist','ch-cum','ch-ops','ch-hf','ch-ret','ch-vol','ch-sat','ch-cor']);
const RNG_P=[['Todo',0],['5 años',1826],['2 años',730],['1 año',365],['6 meses',182],['3 meses',91]];
function rngParse(l){if(typeof l!=='string')return null;if(/^\d{4}-\d{2}-\d{2}/.test(l))return d0(l);const m=l.match(/^([a-z]{3}) (\d{2})$/);if(m){const k=MES.indexOf(m[1]);if(k>=0)return Date.UTC(2000+(+m[2]),k,1)}return null}
function rngDomain(cfg){
  const x=(cfg.options&&cfg.options.scales&&cfg.options.scales.x)||{};
  if(x.type==='linear'){let lo=Infinity,hi=-Infinity;(cfg.data.datasets||[]).forEach(d=>(d.data||[]).forEach(p=>{if(p&&typeof p.x==='number'&&isFinite(p.x)){if(p.x<lo)lo=p.x;if(p.x>hi)hi=p.x}}));
    if(x.min!=null)lo=x.min; if(x.max!=null)hi=x.max; return lo<hi?{lin:true,lo,hi}:null}
  const L=cfg.data.labels||[]; if(L.length<4)return null; const T=L.map(rngParse);
  if(T.some(t=>t==null)){const I=L.map((_,i)=>i);return {lin:false,idx:true,L,T:I,lo:0,hi:I.length-1}} // etiquetas sin fecha: rango por posición
  return {lin:false,T,lo:T[0],hi:T[T.length-1],day:(T[T.length-1]-T[0])/Math.max(1,T.length-1)<25*DAY};
}
function rngBounds(D,st){ // fechas visibles [a,b] según el estado
  let a=D.lo,b=D.hi; if(!st)return [a,b];
  if(st.p){a=Math.max(D.lo,D.hi-st.p*DAY)}else{if(st.a!=null)a=Math.max(D.lo,Math.min(st.a,D.hi));if(st.b!=null)b=Math.min(D.hi,Math.max(st.b,D.lo))}
  if(b<=a){a=D.lo;b=D.hi} return [a,b];
}
function rngSet(x,D,a,b){
  if(D.lin){x.min=a;x.max=b;return}
  let i0=D.T.findIndex(t=>t>=a); if(i0<0)i0=0; let i1=D.T.length-1; while(i1>0&&D.T[i1]>b)i1--; if(i1<=i0){i0=0;i1=D.T.length-1}
  x.min=i0; x.max=i1;
}
function rngFmt(t,D){if(D.idx)return String(D.L[t]);const d=new Date(t);return (D.lin||D.day?d.getUTCDate()+' ':'')+MES[d.getUTCMonth()]+' '+d.getUTCFullYear()}
function rngPrep(id,cfg){ // antes de crear el gráfico: aplica el rango guardado
  if(!RNG_IDS.has(id))return null; const D=rngDomain(cfg); if(!D)return null;
  cfg.options.scales.x=cfg.options.scales.x||{}; const [a,b]=rngBounds(D,RNG[id]); rngSet(cfg.options.scales.x,D,a,b); return D;
}
function rngUI(id,ch,D){
  const cv=document.getElementById(id), box=cv&&cv.parentElement; if(!box)return;
  let bar=box.nextElementSibling; if(!bar||!bar.classList.contains('rngbar')||bar.dataset.for!==id){
    bar=document.createElement('div');bar.className='rngbar';bar.dataset.for=id;
    bar.innerHTML=`<div class="rngp" role="group" aria-label="Periodo visible"></div><div class="rngs"><div class="rngtrack"><i></i></div><input type="range" class="r0" min="0" max="1000" step="1" aria-label="Inicio del periodo visible"><input type="range" class="r1" min="0" max="1000" step="1" aria-label="Fin del periodo visible"></div><span class="rngt"></span>`;
    box.after(bar);
  }
  const span=D.idx?0:(D.hi-D.lo)/DAY, pre=RNG_P.filter(([,d])=>d===0||d<span*0.95);
  const pbox=bar.querySelector('.rngp'), st=RNG[id]||{};
  pbox.innerHTML=pre.map(([l,d])=>`<button type="button" data-d="${d}" aria-pressed="${(d===0&&!st.p&&st.a==null&&st.b==null)||(d&&st.p===d)?'true':'false'}">${l}</button>`).join('');
  const r0=bar.querySelector('.r0'), r1=bar.querySelector('.r1'), lab=bar.querySelector('.rngt'), fill=bar.querySelector('.rngtrack i');
  const N=D.lin?1000:D.T.length-1; r0.max=r1.max=N;
  const toV=t=>D.lin?Math.round((t-D.lo)/(D.hi-D.lo)*N):Math.max(0,D.T.findIndex(x=>x>=t));
  const toT=v=>D.lin?D.lo+(D.hi-D.lo)*v/N:D.T[Math.max(0,Math.min(N,v))];
  const sync=()=>{const [a,b]=rngBounds(D,RNG[id]);r0.value=toV(a);r1.value=D.lin?toV(b):(()=>{let i=N;while(i>0&&D.T[i]>b)i--;return i})();
    fill.style.left=(r0.value/N*100)+'%';fill.style.right=(100-r1.value/N*100)+'%';lab.textContent=rngFmt(a,D)+' – '+rngFmt(b,D)};
  const apply=()=>{const [a,b]=rngBounds(D,RNG[id]);rngSet(ch.options.scales.x,D,a,b);ch.update('none');sync();
    pbox.querySelectorAll('button').forEach(x=>{const d=+x.dataset.d,s=RNG[id]||{};x.setAttribute('aria-pressed',String((d===0&&!s.p&&s.a==null&&s.b==null)||(d>0&&s.p===d)))})};
  let raf=0; const onSlide=e=>{let v0=+r0.value,v1=+r1.value; if(v0>v1-1){if(e.target===r0)v0=r0.value=Math.max(0,v1-1);else v1=r1.value=Math.min(N,v0+1)}
    RNG[id]={a:v0<=0?null:toT(v0),b:v1>=N?null:toT(v1)}; cancelAnimationFrame(raf); raf=requestAnimationFrame(apply)};
  r0.oninput=r1.oninput=onSlide;
  pbox.onclick=e=>{const btn=e.target.closest('button');if(!btn)return;const d=+btn.dataset.d;RNG[id]=d?{p:d}:{};apply()};
  sync();
}
function mkR(id,cfg){if(charts[id])charts[id].destroy();const D=rngPrep(id,cfg);charts[id]=new Chart(document.getElementById(id),cfg);if(D)rngUI(id,charts[id],D);return charts[id]}

/* ================= resumen ejecutivo por pestaña ================= */
const pc_=(v,d=0)=>(v>=0?'+':'−')+nf(Math.abs(v)*100,d)+' %';
function exBox(id,o){
  const el=document.getElementById(id); if(!el)return;
  const calc=o.calc?`<details class="exc"${o.open===false?'':' open'}><summary>${o.calcTitle||'Cómo salen las cuentas'}</summary>${o.calc}</details>`:'';
  el.innerHTML=`<div class="exh"><span class="exk">En pocas palabras</span>${o.when?`<span class="exw">${o.when}</span>`:''}</div>${o.lead?`<p class="exlead">${o.lead}</p>`:''}<ul class="exl">${o.items.map(x=>`<li>${x}</li>`).join('')}</ul>${calc}${o.foot?`<p class="note exf">${o.foot}</p>`:''}`;
  el.hidden=false;
}
const calcT=(head,rows,cls)=>`<div class="tbl"><table class="calc${cls?' '+cls:''}"><thead><tr>${head.map(h=>`<th>${h}</th>`).join('')}</tr></thead><tbody>${rows.map(r=>`<tr${r.cls?` class="${r.cls}"`:''}>${(r.c||r).map((c,i)=>`<td${i?' class="num"':''}>${c}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;

function exPronostico(){
  if(!FC)return; const B=FC.blocks, P=S.P; if(!B.length)return;
  const now=new Date(), today=Date.UTC(now.getUTCFullYear(),now.getUTCMonth(),now.getUTCDate());
  let i0=B.findIndex(b=>b.t1>=today); if(i0<0)i0=0; const n4=Math.min(4,B.length-i0), W=B.slice(i0,i0+n4);
  const s=k=>W.reduce((a,b)=>a+b[k],0), plan=W.some(b=>b.rest!=null);
  const LT=(FC.res.mf_tot.LT||0)+(FC.res.ma_tot.LT||0), ref=LT*n4, v=s('tot'), ratio=ref?v/ref:1;
  const qs=W.map(b=>b.q).filter(x=>x!=null), dA=W.reduce((a,b)=>a+(b.d_alto||0),0), U=P.parada_caudal?P.parada_caudal.umbral:2300;
  const b=W[0], hh=Math.min(b.h,13)-1;
  const comp=(y,c)=>{const p=P[y], d=FC.res[y].days.find(x=>x.h===b.h), lvl=d?d.fw/d.mult:null, r=FC.res[y];
    let f=null; if(p.a_h&&r.EW!=null){const a=p.a_h[hh],sh=p.shrink??0,w1=(p.mezcla&&p.mezcla.w1)||0,a8=p.a8_h?p.a8_h[hh]:0;const wL8=w1*a8,wEW=(1-w1)*(1-sh)*a,wLT=1-wL8-wEW;
      f=[[wL8,'últimas 8 semanas',r.L8],[wEW,'promedio reciente',r.EW],[wLT,'mediana desde 2019',r.LT]].filter(x=>x[0]>0.005)}
    const adj=b.adj||1;
    return {lvl,f,m:b['m'+c],p50:b[c]/adj,adj,p50a:b[c],e:b[c+'_e'],fp:FC.fp[c],ff:b['ff_'+c],ep:b[c+'_ep'],rb:(p.rmean||p.q['0.5'])[hh]}};
  const F=comp('mf_tot','mf'), M=comp('ma_tot','ma');
  const fx=(x,d=0)=>nf(x,d), lvF=x=>x.f?x.f.map(([w,l,v])=>`${nf(w*100)} % × ${nf(v)}`).join(' + '):'—';
  const rows=[
    {c:['<b>1. Nivel típico reciente</b><br><span class="muted">Promedio de semanas con operación completa, mezclando lo reciente con lo de largo plazo</span>',`${lvF(F)}<br>= <b>${fx(F.lvl)}</b>`,`${lvF(M)}<br>= <b>${fx(M.lvl)}</b>`,`<b>${fx(F.lvl+M.lvl)}</b>`]},
    {c:['<b>2. Ajuste por caudal</b><br><span class="muted">Multiplicador según el caudal pronosticado (entre 0,7 y 1,5)</span>',`× ${fx(F.m,2)}`,`× ${fx(M.m,2)}`,'']},
    {c:[`<b>3. Pronóstico central (P50)</b><br><span class="muted">Nivel × ajuste${b.nd<7?`, ${b.nd} días de la semana`:''}; se reparte por día de la semana</span>`,`≈ <b>${fx(F.p50)}</b>`,`≈ <b>${fx(M.p50)}</b>`,`<b>${fx(F.p50+M.p50)}</b>`],cls:'sum'}];
  if(plan)rows.push({c:[`<b>4. Con el descanso programado ingresado</b> (${nf(b.rest)} días)`,`× ${fx(F.adj,2)} = ${fx(F.p50a)}`,`× ${fx(M.adj,2)} = ${fx(M.p50a)}`,`<b>${fx(F.p50a+M.p50a)}</b>`],cls:'sum'});
  else rows.push(
    {c:['<b>4. Valor medio esperado</b><br><span class="muted">Las semanas altas pesan más que las bajas: (P50 + 50) × r̄ − 50</span>',`r̄ = ${fx(F.rb,3)} → ${fx(F.e)}`,`r̄ = ${fx(M.rb,3)} → ${fx(M.e)}`,`${fx(F.e+M.e)}`]},
    {c:['<b>5. Paros habituales</b><br><span class="muted">Promedio de todas las semanas ÷ promedio de semanas sin paros (últimos 2 años)</span>',`× ${fx(F.fp,3)}`,`× ${fx(M.fp,3)}`,'']},
    {c:[`<b>6. Caudal alto pronosticado</b><br><span class="muted">${b.d_alto?`${b.d_alto} días sobre ${nf(U)} m³/s: se detiene la extracción por seguridad`:`ningún día sobre ${nf(U)} m³/s`}</span>`,`× ${fx(F.ff,3)}`,`× ${fx(M.ff,3)}`,'']},
    {c:['<b>7. Con paros y caudal</b> = 4 × 5 × 6',`<b>${fx(F.ep)}</b>`,`<b>${fx(M.ep)}</b>`,`<b>${fx(F.ep+M.ep)}</b>`],cls:'sum'});
  const sp=plan?s('tot_e'):s('tot_ep');
  exBox('ex-pronostico',{when:`Semanas S${W[0].h}–S${W[W.length-1].h} · ${fmtDs(W[0].t0)} a ${fmtD(W[W.length-1].t1)}`,
    items:[
      `En las próximas <b>${n4} semanas</b> se esperan <b>${nf(v)} m³</b> de material (valor central). Lo más probable es que quede entre <b>${nf(s('tot_p25'))} y ${nf(s('tot_p75'))} m³</b>.`,
      `Eso es <b>${pc_(ratio-1)}</b> frente a ${n4} semanas típicas (${nf(ref)} m³), calculadas con la mediana de semanas con operación desde 2019.`,
      plan?`Con el descanso programado que ingresó: <b>${nf(sp)} m³</b>.`:`Si se repiten los paros habituales${dA?' y se detiene la extracción en los días de caudal alto':''}: <b>${nf(sp)} m³</b>. Esta es la cifra prudente para planear.`,
      qs.length?`Caudal pronosticado en Sitio Presa: entre <b>${nf(Math.min(...qs))} y ${nf(Math.max(...qs))} m³/s</b> (promedio semanal). Días por encima de ${nf(U)} m³/s, el límite de seguridad para las lanchas: <b>${dA}</b>.`:'Sin pronóstico de caudal para estas semanas.',
      `Material flotante: ${nf(s('mf'))} m³ · macrófitas: ${nf(s('ma'))} m³. La división entre ambos del mecanizado es estimada en el registro; el total es la cifra más firme.`],
    calcTitle:`Cómo sale la semana S${b.h} (${fmtDs(b.t0)} – ${fmtDs(b.t1)}), en m³`,
    open:false,calc:calcT(['Paso','Flotante','Macrófitas','Total'],rows)+`<p class="note">El paso 3 difiere unas decenas de m³ de multiplicar 1 × 2 porque el ajuste por caudal cambia día a día y cada día de la semana pesa distinto (los fines de semana se extrae menos). El rango probable (P25–P75) y la franja del gráfico (P10–P90) salen de los errores reales del modelo en 2022–2026 para cada horizonte. El caudal pronosticado viene de HydroForecast (${LIVE.state==='live'?'en vivo':LIVE.state==='archive'?'archivo diario':'respaldo'}, emitido ${S.fc.generated_at.replace('T',' ').slice(0,16)}).</p>`});
}

function exHistorico(){
  const sum=(a,i0,i1)=>{let s=0;for(let i=Math.max(i0,S.first);i<=i1;i++)s+=a[i];return s};
  const L=S.last, tmf=sum(S.mf,S.first,L), tma=sum(S.ma,S.first,L), tot=tmf+tma;
  const y1=sum(S.tot,L-364,L), y0=sum(S.tot,L-729,L-365);
  let so=0,c=0; for(let i=S.iS;i<=L;i++)if(S.op[i]){so+=S.tot[i];c++}
  const mec=sum(S.mf_mec,S.first,L)+sum(S.ma_mec,S.first,L);
  const Y=new Map(); for(let i=S.first;i<=L;i++){const y=new Date(S.T[i]).getUTCFullYear();Y.set(y,(Y.get(y)||0)+S.tot[i])}
  const fy=new Date(S.T[S.first]).getUTCFullYear(), ly=new Date(S.T[L]).getUTCFullYear();
  const full=[...Y.entries()].filter(([y])=>y>fy&&y<ly).sort((a,b)=>b[1]-a[1]);
  exBox('ex-historico',{when:`${fmtD(S.T[S.first])} – ${fmtD(S.T[L])}`,
    items:[
      `Desde ${fmtD(S.T[S.first])} se han extraído <b>${nf(tot)} m³</b>: ${nf(tmf)} m³ de material flotante (${nf(tmf/tot*100)} %) y ${nf(tma)} m³ de macrófitas (${nf(tma/tot*100)} %).`,
      `Últimos 12 meses: <b>${nf(y1)} m³</b>, ${pc_(y1/y0-1)} frente a los 12 meses anteriores (${nf(y0)} m³).`,
      full.length?`Año completo con más extracción: <b>${full[0][0]}</b> (${nf(full[0][1])} m³); con menos: <b>${full[full.length-1][0]}</b> (${nf(full[full.length-1][1])} m³).`:'',
      `En un día con operación se extraen en promedio <b>${nf(so/c)} m³</b>. El ${nf(mec/tot*100)} % del volumen total es mecanizado.`].filter(Boolean),
    calc:calcT(['Cifra','Cuenta','Resultado'],[
      ['Total extraído','flotante + macrófitas',`${nf(tmf)} + ${nf(tma)} = <b>${nf(tot)}</b> m³`],
      ['Últimos 12 meses',`suma diaria ${fmtDs(S.T[L-364])} ${new Date(S.T[L-364]).getUTCFullYear()} – ${fmtD(S.T[L])}`,`<b>${nf(y1)}</b> m³`],
      ['12 meses anteriores',`suma diaria ${fmtDs(S.T[L-729])} ${new Date(S.T[L-729]).getUTCFullYear()} – ${fmtD(S.T[L-365])}`,`<b>${nf(y0)}</b> m³`],
      ['Cambio',`${nf(y1)} ÷ ${nf(y0)} − 1`,`<b>${pc_(y1/y0-1)}</b>`],
      ['Promedio por día con operación',`${nf(so)} m³ ÷ ${nf(c)} días`,`<b>${nf(so/c)}</b> m³/día`]]),open:false,
    foot:'Un día sin reporte cuenta como 0 m³. 2019 y el año en curso están incompletos; por eso no entran en la comparación de años.'});
}

function exRelacion(){
  const R=S.src.rezagos; if(!R)return; const pq=R.por_caudal, lo=pq[0], hi=pq[pq.length-1], PC=S.P.parada_caudal, par=R.parada, ev=R.evento;
  const LTf=FC?FC.res.mf_tot.LT:null, LTa=FC?FC.res.ma_tot.LT:null;
  const red=(a,b)=>nf((1-b/a)*100);
  exBox('ex-relacion',{
    items:[
      `<b>El caudal no cambia cuánto se saca en un día de trabajo; cambia cuántos días se puede trabajar.</b> Con caudal bajo (${lo.clase} m³/s) el mecanizado operó el <b>${nf(lo.opera_mec*100)} %</b> de los días; con más de ${nf(PC.umbral)} m³/s, solo el <b>${nf(hi.opera_mec*100)} %</b>.`,
      `Con más de ${nf(PC.umbral)} m³/s, por la seguridad del personal de las lanchas, el material flotante extraído por día cae a cerca del <b>${nf(hi.mf_rel*100)} %</b> de lo normal (${nf(hi.dias)} días con ese caudal desde oct-2021).`,
      `Pasada la creciente no se recupera más de lo normal: en las 8 semanas siguientes a ${ev.n} crecientes, el volumen adicional fue de <b>${ev.extra_8sem_mediana>=0?'+':''}${nf(ev.extra_8sem_mediana)} m³</b> (mediana), es decir, prácticamente nada.`,
      `¿Y el material que no se alcanza a sacar? El satélite muestra más vegetación justo aguas abajo de la barrera cuando sube el caudal: es un indicio de que parte pasa la barrera, todavía con mucha incertidumbre (detalle en <a href="#satelite">Satélite</a>).`,
      `Por eso el pronóstico descuenta los días de caudal alto pronosticado. En ${par.mf_tot.semanas} semanas de caudal alto el error bajó <b>${red(par.mf_tot.en_semanas_altas.constante,par.mf_tot.en_semanas_altas.por_caudal)} %</b> en flotante (de ${nf(par.mf_tot.en_semanas_altas.constante)} a ${nf(par.mf_tot.en_semanas_altas.por_caudal)} m³) y <b>${red(par.ma_tot.en_semanas_altas.constante,par.ma_tot.en_semanas_altas.por_caudal)} %</b> en macrófitas (de ${nf(par.ma_tot.en_semanas_altas.constante)} a ${nf(par.ma_tot.en_semanas_altas.por_caudal)} m³).`],
    calcTitle:`Cuánto se descuenta por caudal alto (días de la semana sobre ${nf(PC.umbral)} m³/s)`,
    calc:calcT(['Días de caudal alto en la semana','Flotante','Macrófitas'],[
      ['Ninguno',`× ${nf(PC.mf[0],3)}${LTf?` → ${nf(LTf)} m³`:''}`,`× ${nf(PC.ma[0],3)}${LTa?` → ${nf(LTa)} m³`:''}`],
      ['1 a 3',`× ${nf(PC.mf[1],3)}${LTf?` → ${nf(LTf)} × ${nf(PC.mf[1],3)} = <b>${nf(LTf*PC.mf[1])}</b> m³`:''}`,`× ${nf(PC.ma[1],3)}${LTa?` → ${nf(LTa)} × ${nf(PC.ma[1],3)} = <b>${nf(LTa*PC.ma[1])}</b> m³`:''}`],
      ['4 a 7',`× ${nf(PC.mf[2],3)}${LTf?` → ${nf(LTf)} × ${nf(PC.mf[2],3)} = <b>${nf(LTf*PC.mf[2])}</b> m³`:''}`,`× ${nf(PC.ma[2],3)}${LTa?` → ${nf(LTa)} × ${nf(PC.ma[2],3)} = <b>${nf(LTa*PC.ma[2])}</b> m³`:''}`]])+
      `<p class="note">Ejemplo con una semana típica (mediana de semanas con operación desde 2019: ${nf(LTf)} m³ de flotante y ${nf(LTa)} m³ de macrófitas). Los factores son la razón entre lo extraído y lo pronosticado en las semanas de 2022–2026 con ese número de días de caudal alto. Mejora del error = 1 − error con factor ÷ error sin factor.</p>`});
}

function exOperacion(){
  const E=S.src.esfuerzo; if(!E)return; const n=E.semanas.length, ix=[...Array(8)].map((_,k)=>n-8+k), sm=(a)=>ix.reduce((s,i)=>s+a[i],0);
  const d8=sm(E.dias.opero), mec8=sm(E.mec), op8=d8/8, m8=mec8/Math.max(1,d8);
  const yrs=E.anual.filter(a=>a.anio>=2021&&a.anio<=2025), opH=median(yrs.map(a=>a.opero)), bt=E.backtest;
  const lo=Math.min(...yrs.map(a=>a.m3dia)), hi=Math.max(...yrs.map(a=>a.m3dia));
  exBox('ex-operacion',{when:`Hoja de viajes hasta ${fmtD(d0(E.corte))}`,
    items:[
      `<b>El volumen depende de cuántos días se opera, no de cuánto se saca por día.</b> En 2021–2025 un día operado rindió entre ${nf(lo)} y ${nf(hi)} m³ mecanizados, mientras los días operados por semana fueron de ${nf(Math.min(...yrs.map(a=>a.opero)),1)} a ${nf(Math.max(...yrs.map(a=>a.opero)),1)} según el año.`,
      `Últimas 8 semanas: <b>${nf(op8,1)} días operados por semana</b> (típico 2021–2025: ${nf(opH,1)}) y <b>${nf(m8)} m³ por día operado</b>.`,
      `Los días y las volquetas en operación explican el <b>${nf(E.r2.volq*100)} %</b> de las subidas y bajadas semanales del mecanizado.`,
      `Lo único que mejoró el pronóstico de forma clara es conocer el descanso programado: el error del total a 1–4 semanas baja de ${nf(bt.base.tot[0])} a ${nf(bt.prog.tot[0])} m³/semana (<b>${pc_(bt.prog.tot[0]/bt.base.tot[0]-1)}</b>). Se ingresa en Pronóstico.`,
      `El caudal alto reduce los días que se puede operar (detalle en <a href="#relacion">Caudal y material</a>).`],
    calc:calcT(['Cifra','Cuenta','Resultado'],[
      ['Días operados por semana',`${nf(d8)} días en 8 semanas ÷ 8`,`<b>${nf(op8,1)}</b>`],
      ['m³ por día operado (mecanizado)',`${nf(mec8)} m³ ÷ ${nf(d8)} días`,`<b>${nf(m8)}</b> m³`],
      ['Mecanizado por semana',`${nf(op8,1)} días × ${nf(m8)} m³`,`<b>${nf(mec8/8)}</b> m³`],
      ['Mejora con el descanso programado',`${nf(bt.prog.tot[0])} ÷ ${nf(bt.base.tot[0])} − 1`,`<b>${pc_(bt.prog.tot[0]/bt.base.tot[0]-1)}</b>`]]),open:false,
    foot:'El volumen del registro es viajes × capacidad nominal de cada volqueta: mide sobre todo el esfuerzo, no el material que llega.'});
}

function exCalidad(){
  const repd=S.rep.reduce((a,b)=>a+b,0), span=S.last-S.first+1, miss=span-S.rep.slice(S.first,S.last+1).reduce((a,b)=>a+b,0);
  let z=0,so=0,mo=0,m0=null,m1=null; for(let i=S.iS;i<=S.last;i++){if(S.tot[i]===0)z++;so+=S.sinop[i];mo+=S.mecoff[i]&&!S.sinop[i]?1:0}
  for(let i=S.first;i<=S.last;i++)if(!S.rep[i]){if(m0==null)m0=i;m1=i}
  exBox('ex-calidad',{
    items:[
      `De <b>${nf(span)} días</b> calendario (${fmtD(S.T[S.first])} – ${fmtD(S.T[S.last])}), <b>${nf(repd)}</b> tienen reporte. Los ${nf(miss)} días sin reporte${m0!=null?` (${fmtD(S.T[m0])} a ${fmtD(S.T[m1])})`:''} se cuentan como 0 m³: no se extrajo.`,
      `Hay <b>${nf(z)} días con extracción total en cero</b>. Un cero aislado es un día sin trabajo, no un día sin material.`,
      `Para ajustar el modelo se excluyen <b>${nf(so+mo)} días</b> (${nf((so+mo)/span*100)} % del periodo): ${nf(so)} en periodos sin operación (7 días o más en cero) y ${nf(mo)} con el mecanizado detenido (10 días o más sin mecanizado). Así un paro no se confunde con falta de material.`,
      'Los acumulados del archivo se comparan fila por fila con los avances diarios (tabla «Validación de acumulados»).'],
    calc:calcT(['Cifra','Cuenta','Resultado'],[
      ['Días calendario','del primer al último reporte',`<b>${nf(span)}</b>`],
      ['Días sin reporte',`${nf(span)} − ${nf(repd)}`,`<b>${nf(miss)}</b>`],
      ['Días excluidos del ajuste',`${nf(so)} + ${nf(mo)}`,`<b>${nf(so+mo)}</b> (${nf((so+mo)/span*100)} %)`]]),open:false});
}

function exModelo(){
  const P=S.P, f=P.mf_tot, a=P.ma_tot, rf=f.rmse_total||{}, ra=a.rmse_total||{}, A=S.src.audit&&S.src.audit.v1v2;
  const yrs=y=>A?Object.entries(A[y].anual):[], pos=y=>yrs(y).filter(([,v])=>v.v2>0.0005).length, cero=y=>yrs(y).filter(([,v])=>Math.abs(v.v2)<=0.0005).length, ny=yrs('mf_tot').length;
  const m1=f.metricas[0], a1=a.metricas[0];
  exBox('ex-modelo',{
    items:[
      `En 2022–2026, pronosticando cada semana solo con la información de ese momento, el modelo se equivoca en promedio <b>±${nf(rf.v2)} m³/semana</b> en material flotante. Repetir la mediana histórica se habría equivocado ±${nf(rf.clim)}: <b>${nf((1-rf.v2/rf.clim)*100)} % menos error</b>.`,
      `En macrófitas: <b>±${nf(ra.v2)}</b> frente a ±${nf(ra.clim)} m³/semana (<b>${nf((1-ra.v2/ra.clim)*100)} % menos error</b>).`,
      A?`Año por año (${ny} años), el modelo supera a la mediana histórica en ${pos('mf_tot')} y la iguala en ${cero('mf_tot')} en flotante; en macrófitas la supera en ${pos('ma_tot')}${cero('ma_tot')?` y la iguala en ${cero('ma_tot')}`:''}.`:'',
      `A una semana, el error típico es ${nf(m1.mae)} m³ en flotante (semana media: ${nf(m1.media_obs)} m³) y ${nf(a1.mae)} m³ en macrófitas (semana media: ${nf(a1.media_obs)} m³). Para planear, use la suma de 4 u 8 semanas: es más confiable que una semana aislada.`,
      `El rango P10–P90 contuvo el valor real en el ${nf(f.cobertura80_fuera_muestra*100)} % (flotante) y el ${nf(a.cobertura80_fuera_muestra*100)} % (macrófitas) de las semanas de 2024–2026; lo esperado es 80 %.`].filter(Boolean),
    calc:calcT(['Cifra','Cuenta','Flotante','Macrófitas'],[
      ['Error típico del modelo','raíz del promedio de (pronóstico − real)²',`${nf(rf.v2)}`,`${nf(ra.v2)}`],
      ['Error de la mediana histórica','misma cuenta, pronosticando siempre la mediana',`${nf(rf.clim)}`,`${nf(ra.clim)}`],
      ['Reducción del error','1 − modelo ÷ mediana',`<b>${nf((1-rf.v2/rf.clim)*100)} %</b>`,`<b>${nf((1-ra.v2/ra.clim)*100)} %</b>`]]),open:false});
}

function exAuditoria(){
  const A=S.src.audit; if(!A)return; const secs=[['integridad','Archivo de extracción'],['caudal','Caudales'],['modelo','Modelo'],['plataforma','Plataforma'],['vigencia','Vigencia']];
  const all=secs.flatMap(([k])=>A[k]||[]), c=s=>all.filter(x=>x[0]===s).length, warn=secs.flatMap(([k,l])=>(A[k]||[]).filter(x=>x[0]==='warn'||x[0]==='bad').map(x=>`${l}: ${x[1]}`));
  exBox('ex-auditoria',{when:`Revisión del ${A.fecha}`,
    items:[`Se revisaron <b>${all.length} puntos</b>: <b>${c('ok')} en orden</b>, ${c('warn')+c('bad')} con advertencia y ${c('info')} informativos.`,
      `Lo que queda por resolver:<ul class="exsub">${warn.map(w=>`<li>${esc(w)}</li>`).join('')}</ul>`,
      `${(A.recomendaciones||[]).length} recomendaciones al final de la página, en orden de prioridad.`]});
}

function exDatos(){
  const age=Math.floor((Date.now()-S.T[S.last])/DAY);
  exBox('ex-actualizar',{items:[
    `Extracción: registro hasta el <b>${fmtD(S.T[S.last])}</b> (hace ${age} días)${S.src._repo?', leído del Excel del repositorio':S.src._xlsxName?', del Excel cargado en esta sesión':''}. Para actualizar, reemplace <code>datos/DatosExtraccion.xlsx</code> en GitHub.`,
    `Caudal: pronóstico de HydroForecast <b>${LIVE.state==='live'?'en vivo':LIVE.state==='archive'?'del archivo diario':'de respaldo'}</b>, emitido ${S.fc.generated_at.replace('T',' ').slice(0,16)}. Se consulta al abrir la página; si no responde, se usa la copia que GitHub guarda 4 veces al día.`,
    'Satélite: se procesa a diario en GitHub con las imágenes nuevas de Sentinel-2 y Sentinel-1 (una medición cada 3–5 días, según nubes y pasadas).',
    'Todo se calcula en su navegador; los archivos que cargue aquí no se envían a ningún servidor.']});
}

function exRequisitos(){
  const li=[...document.querySelectorAll('#req-list li')], pend=li.filter(x=>!/Recibido/.test(x.querySelector('.prio')?.textContent||''));
  exBox('ex-requisitos',{items:[
    `${pend.length} datos pendientes y ${li.length-pend.length} ya recibidos. Lo que más ayudaría, en orden:`,
    `<ol class="exsub">${pend.slice(0,3).map(x=>`<li>${x.querySelector('b')?.innerHTML||''}</li>`).join('')}</ol>`,
    'Con el plan de descansos se comprobó una mejora del pronóstico (−15 % de error en el total); los demás se piden para explicar mejor lo que llega a la barrera.']});
}

async function exSatelite(){
  let J=null; try{J=await loadSat()}catch(e){return}
  try{if(!RET)RET=await fetchJSON('datos/satelite/retenido/serie.json',15000)}catch(e){}
  const R=S.src.rezagos, T=R&&R.satelite&&R.satelite.tabla, K=VOLK.central;
  const S_=J.serie.map(r=>({t:r.t,T:d0(r.f),src:'Sentinel-2'})), LS=(J.landsat||[]).map(r=>({t:r.t,T:d0(r.f),src:'Landsat'})), S1=(J.s1||[]).map(r=>({t:r.t,T:d0(r.f),src:'radar'}));
  const ALL=[...S_,...LS,...S1].sort((a,b)=>a.T-b.T), last=ALL[ALL.length-1];
  let e8=0; for(let i=S.last-55;i<=S.last;i++)e8+=(S.mf[i]||0)+(S.ma[i]||0); const eDia=e8/56;
  const ult=k=>{let best=null;if(RET)for(const src of ['optico','radar'])for(const [f,o] of Object.entries(RET[src]||{}))if(o[k]!=null&&(!best||f>best.f))best={f,v:o[k],src};return best};
  const hist=k=>RET?[...Object.values(RET.optico||{}),...Object.values(RET.radar||{})].map(o=>o[k]).filter(x=>x!=null).sort((a,b)=>a-b):[];
  const pq=(a,p)=>a.length?a[Math.min(a.length-1,Math.floor(p*a.length))]:null;
  const ret=ult('ret'), bar=ult('bar'), hb=hist('bar'), hr=hist('ret');
  const g=T?T.grupos:null, d=T?T.dif_alta_vs_resto:null;
  const items=[
    `<b>Qué mide.</b> El satélite ve la vegetación flotante verde (buchón, lechuga de agua y material vegetal) sobre el agua. No ve madera ni basura, y mide cada 3–5 días, no a diario: el óptico (Sentinel-2) no ve con nubes y el radar (Sentinel-1) sí.`,
    `<b>Hoy.</b> En la zona de 2,5 km alrededor de la barrera (${nf(J.area_ha.total)} ha de agua) se ven <b>${nf(last.t,1)} ha</b> (${fmtD(last.T)}, ${last.src}), unos <b>${nf(last.t*K)} m³</b>: equivalen a <b>${nf(last.t*K/Math.max(eDia,1))} días</b> de extracción al ritmo de las últimas 8 semanas (${nf(eDia)} m³/día).`+
      (ret?` Retenidos contra la barrera (los 2,5 km aguas arriba): <b>${nf(ret.v,1)} ha</b> ≈ ${nf(ret.v*K)} m³ (${fmtD(d0(ret.f))}).`:'')+
      (bar?` La franja de 100 m frente a la barrera está ocupada al <b>${nf(bar.v)} %</b>${hb.length?` (lo normal es ${nf(pq(hb,.5))} %; se vigila desde ${nf(pq(hb,.9))} %)`:''}.`:''),
    `<b>Sirve para vigilar, no para pronosticar.</b> En 2019–2026, cuánta vegetación se ve no anticipa cuánto se extraerá las semanas siguientes. Por eso no entra al pronóstico; sirve para ver qué viene río abajo y el estado de la barrera.`];
  if(g)items.push(`<b>Qué pasa en las crecientes.</b> Lo único seguro es que se extrae menos: <b>${nf(Math.abs(d.E.dif))} m³ menos por semana</b> (entre ${nf(Math.abs(d.E.ic90[1]))} y ${nf(Math.abs(d.E.ic90[0]))}). Frente a la barrera no se ve acumulación en promedio; justo aguas abajo de la barrera sí aparece más vegetación, señal de que parte del material pasa. Esta segunda parte es un indicio, con mucha incertidumbre.`);
  const calc1=calcT(['Paso','Cuenta','Resultado'],[
    ['Hectáreas a metros cuadrados','1 ha = 10.000 m²','10.000 m²'],
    ['Peso del material por m²','11,8 kg/m² (valor central publicado para buchón; rango 3,8 a 40,8)','118.000 kg por ha'],
    ['Peso a volumen','118.000 kg ÷ 160 kg/m³ (densidad usada en la hoja de viajes)',`<b>${nf(K)} m³ por ha</b>`],
    ['Rango posible','3,8 a 40,8 kg/m² con la misma cuenta',`${nf(VOLK.bajo)} a ${nf(VOLK.alto)} m³ por ha`],
    ['Ejemplo de hoy',`${nf(last.t,1)} ha × ${nf(K)} m³/ha`,`<b>${nf(last.t*K)} m³</b> (rango ${nf(last.t*VOLK.bajo)} a ${nf(last.t*VOLK.alto)})`]]);
  let calc2='';
  const sg=v=>(v>=0?'+':'−')+nf(Math.abs(v)), seg_=x=>(x.ic90[0]>0||x.ic90[1]<0)?`<b>Sí</b>: entre ${sg(x.ic90[0])} y ${sg(x.ic90[1])} m³`:`No: entre ${sg(x.ic90[0])} y ${sg(x.ic90[1])} m³ (incluye el cero)`;
  if(g){const row=(k,l)=>{const x=g[k];return [`${l}<br><span class="muted">${nf(x.n)} semanas · caudal medio ${nf(x.q)} m³/s</span>`,nf(x.E),(x.acu>=0?'+':'−')+nf(Math.abs(x.acu)),(x.pasa>=0?'+':'−')+nf(Math.abs(x.pasa)),`<b>${nf(x.lleg)}</b>`]};
    calc2=`<h4>Balance semanal: lo que llega = lo extraído + lo que se acumula frente a la barrera + lo que aparece aguas abajo</h4>`+
      calcT(['Tipo de semana','Extraído (m³)','Cambio frente a la barrera (m³)','Cambio 0–2,5 km aguas abajo (m³)','Llegada estimada (m³)'],[
        row('baja','Caudal bajo (menos de 1.500 m³/s)'),row('media','Caudal medio (1.500 m³/s o más, sin días sobre 2.300)'),{c:row('alta','Creciente (al menos 1 día sobre 2.300 m³/s)'),cls:'sum'}])+
      calcT(['Creciente frente al resto','Diferencia por semana','¿Es seguro?'],[
        ['Extraído',sg(d.E.dif)+' m³',seg_(d.E)],['Acumulado frente a la barrera',sg(d.acu.dif)+' m³',seg_(d.acu)],['Aparece aguas abajo',sg(d.pasa.dif)+' m³',seg_(d.pasa)],['Llegada total',sg(d.lleg.dif)+' m³',seg_(d.lleg)]],'calc2')+
      `<p class="note">Cómo se lee: en una semana de creciente se extraen ${nf(g.alta.E)} m³ frente a ${nf(g.baja.E)} en una de caudal bajo. Cada cambio de hectáreas entre el inicio y el fin de la semana se pasa a m³ con ${nf(K)} m³/ha (si la mancha crece 1 ha, suma ${nf(K)} m³). «¿Es seguro?» usa un intervalo del 90 %: si incluye el cero, la diferencia no está demostrada. ${nf(T.n)} semanas entre ${fmtD(d0(T.desde))} y ${fmtD(d0(T.hasta))} con medición satelital a menos de 21 días de distancia. La vegetación aguas abajo también crece y se mueve por sí sola, por eso esa columna es la más incierta.</p>`}
  exBox('ex-satelite',{when:`Imágenes hasta ${fmtD(last.T)}`,items,calcTitle:'Cómo salen las cuentas',calc:`<h4>De hectáreas a metros cúbicos</h4>`+calc1+calc2,
    foot:'El paso de hectáreas a m³ no está calibrado en campo: pesar y medir el material de 3 a 5 cuadros de 1 m² en una fecha con imagen despejada fijaría esta cifra.'});
}

function renderExec(v){try{
  if(v==='pronostico')exPronostico();else if(v==='historico')exHistorico();else if(v==='relacion')exRelacion();else if(v==='operacion')exOperacion();
  else if(v==='calidad')exCalidad();else if(v==='modelo')exModelo();else if(v==='satelite')exSatelite();else if(v==='auditoria')exAuditoria();
  else if(v==='actualizar')exDatos();else if(v==='requisitos')exRequisitos();
}catch(e){console.warn('resumen',v,e)}}

const VIEWS=['pronostico','historico','relacion','operacion','calidad','modelo','satelite','auditoria','actualizar','requisitos'];
function show(){
  const h=(location.hash||'#pronostico').slice(1);const v=VIEWS.includes(h)?h:'pronostico';
  VIEWS.forEach(x=>document.getElementById('v-'+x).hidden=x!==v);
  document.querySelectorAll('#tabs a').forEach(a=>a.setAttribute('aria-current',a.getAttribute('href')==='#'+v?'page':'false'));
  document.querySelector('#tabs a[aria-current="page"]')?.scrollIntoView({block:'nearest',inline:'center'});
  renderView(v);
}
function renderView(v){
  if(v==='pronostico')renderForecast();else if(v==='historico')renderHist();else if(v==='relacion')renderRel();
  if(v==='relacion'){const n=document.getElementById('rel-note');n.hidden=!S.src._xlsxName||S.src._same;n.textContent=`Análisis de crecientes y correlaciones calculados con el archivo base (hasta ${fmtD(S.T[ORIGLAST])}). El histórico, la calidad y el pronóstico sí usan el archivo cargado.`}
  if(v==='calidad')renderQuality();else if(v==='modelo'){if(!FC)FC=forecast('mean');renderModel();renderHFSkill();renderRezagos();renderBateria()}else if(v==='auditoria')renderAudit();else if(v==='satelite')renderSat();else if(v==='operacion')renderOps();
  else if(v==='actualizar')renderUpdate();else if(v==='requisitos')renderReq();
  renderExec(v);
}
function seg(id,cb){document.getElementById(id).addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;
  [...e.currentTarget.querySelectorAll('button')].forEach(x=>x.setAttribute('aria-pressed',x===b?'true':'false'));cb()})}
function refreshAll(){renderLive();FC=forecast('mean');show()}
function adoptParsed(r,name,repo){
  r.src.forecast_snapshot=S.src.forecast_snapshot;r.src.esfuerzo=S.src.esfuerzo;r.src.audit=S.src.audit;r.src.rezagos=S.src.rezagos;
  const D0=S.src.data;['olaya','pintada','sitiopresa','nivel','olaya_max'].forEach(k=>{r.src.data[k]=D0[k].slice();while(r.src.data[k].length<r.src.data.n)r.src.data[k].push(null)});
  r.src._xlsxName=name;r.src._repo=!!repo;S=build(r.src);refreshAll();
}
async function loadRepoExcel(){
  try{const res=await fetch('datos/DatosExtraccion.xlsx',{cache:'no-cache'});if(!res.ok)return false;
    const buf=new Uint8Array(await res.arrayBuffer());
    if(ORIG.xlsx_sha&&crypto.subtle){const h=[...new Uint8Array(await crypto.subtle.digest('SHA-256',buf))].map(b=>b.toString(16).padStart(2,'0')).join('');
      if(h===ORIG.xlsx_sha){S.src._xlsxName='datos/DatosExtraccion.xlsx';S.src._repo=true;S.src._same=true;renderLive();return true}}
    await loadXlsx();const r=parseXlsx(buf,'datos/DatosExtraccion.xlsx');adoptParsed(r,'datos/DatosExtraccion.xlsx',true);return true}
  catch(e){console.warn('Excel del repositorio no disponible:',e.message);return false}
}
let XLSX_P=null;
function loadXlsx(){if(window.XLSX)return Promise.resolve();if(XLSX_P)return XLSX_P;XLSX_P=new Promise((ok,ko)=>{const s=document.createElement('script');s.src='vendor/xlsx.full.min.js';s.onload=ok;s.onerror=()=>{XLSX_P=null;ko(new Error('no se pudo cargar el lector de Excel'))};document.head.appendChild(s)});return XLSX_P}
function setTheme(t){document.documentElement.setAttribute('data-theme',t);try{localStorage.setItem('mfi-theme',t)}catch(e){}document.getElementById('theme-txt').textContent=t==='dark'?'Claro':'Oscuro'}
let ORIGLAST=0;
function init(){
  S=build(ORIG);ORIGLAST=S.last;
  setTheme(document.documentElement.getAttribute('data-theme')||'dark');
  document.getElementById('theme-btn').onclick=()=>setTheme(document.documentElement.getAttribute('data-theme')==='dark'?'light':'dark');
  const ys=new Date(S.T[S.first]).getUTCFullYear(),ye=new Date(S.T[S.last]).getUTCFullYear();
  const sel=document.getElementById('hist-from');sel.innerHTML='';for(let y=ys;y<=ye;y++)sel.insertAdjacentHTML('beforeend',`<option value="${y}">${y}</option>`);sel.value=String(Math.max(ys,2021));
  sel.onchange=renderHist;
  initRestPlan();document.getElementById('btn-csv').onclick=exportCSV;document.getElementById('btn-print').onclick=()=>window.print();
  document.getElementById('fc-scen').onchange=renderForecast;document.getElementById('fc-comp').onchange=renderForecast;
  seg('hist-agg',renderHist);seg('cmp-thr',renderRel);seg('lag-x',renderRel);seg('sk-comp',renderModel);seg('aud-comp',renderAudit);seg('sat-lado',renderSat);
  document.getElementById('up-xlsx').onchange=async e=>{const f=e.target.files[0];if(!f)return;const m=document.getElementById('up-msg');
    try{m.className='msg';m.textContent='Leyendo archivo…';await loadXlsx();const r=parseXlsx(new Uint8Array(await f.arrayBuffer()),f.name);adoptParsed(r,f.name,false);location.hash='#actualizar';
      m.className='msg ok';m.textContent=`Archivo cargado: ${r.nMF} filas de material flotante y ${r.nMA} de macrófitas. Último dato: ${fmtD(S.T[S.last])}. El pronóstico ya usa estos datos.`}
    catch(err){m.className='msg err';m.textContent='No se pudo leer el archivo: '+err.message}};
  document.getElementById('btn-json').onclick=()=>{const m=document.getElementById('json-msg');try{const msg=applyJSON(document.getElementById('paste-json').value);S=build(S.src);refreshAll();m.className='msg ok';m.textContent=msg}catch(err){m.className='msg err';m.textContent='No se pudo usar el JSON: '+err.message}};
  document.getElementById('btn-reset').onclick=()=>{LIVE.state='fallback';LIVE.err='restaurado';S=build(JSON.parse(JSON.stringify(ORIG)));refreshAll();const m=document.getElementById('json-msg');m.className='msg ok';m.textContent='Se restauraron los datos incluidos.'};
  const doApi=async()=>{const u=document.getElementById('api-url').value.trim()||DEF_API;try{localStorage.setItem('mfi-api',u)}catch(e){}const m=document.getElementById('json-msg');m.className='msg';m.textContent='Consultando '+u+'…';
    const ok=await loadLive(u);m.className='msg '+(ok?'ok':'err');m.textContent=ok?`Caudal actualizado desde ${u}.`:`No se pudo consultar ${u} (${LIVE.err}). Se mantiene el caudal anterior.`};
  document.getElementById('btn-api').onclick=doApi;
  document.getElementById('btn-live').onclick=()=>loadLive();
  window.addEventListener('hashchange',show);
  const rerender=()=>{const h=(location.hash||'#pronostico').slice(1);renderView(VIEWS.includes(h)?h:'pronostico')};
  new MutationObserver(rerender).observe(document.documentElement,{attributes:true,attributeFilter:['data-theme']});
  document.querySelectorAll('canvas').forEach(c=>{const h=c.closest('.panel')?.querySelector('h3');c.setAttribute('role','img');c.setAttribute('aria-label',(h?h.textContent:'Gráfico')+'. Los valores están en la tabla o el texto de esta sección.')});
  refreshAll();
  S.src._xlsxName='datos/DatosExtraccion.xlsx';S.src._repo=true;S.src._same=true;renderLive();
  loadLive();
  fetch('datos/app/extra.json?v=eccfebc520',{cache:'no-cache'}).then(r=>r.json()).then(x=>{Object.assign(ORIG,x);Object.assign(S.src,x);const h=(location.hash||'#pronostico').slice(1);if(VIEWS.includes(h))renderView(h)}).catch(()=>{});
}
fetch('datos/app/base.json?v=aa4039a8b3',{cache:'no-cache'}).then(r=>{if(!r.ok)throw new Error('HTTP '+r.status);return r.json()}).then(j=>{ORIG=j;init()})
  .catch(e=>{const m=document.getElementById('load-msg');if(m){m.hidden=false;m.textContent='No se pudieron cargar los datos ('+e.message+'). Recargue la página.'}});
if('serviceWorker' in navigator&&location.protocol==='https:')window.addEventListener('load',()=>navigator.serviceWorker.register('sw.js').catch(()=>{}));
})();
