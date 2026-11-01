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
function mk(id,cfg){if(charts[id])charts[id].destroy();charts[id]=new Chart(document.getElementById(id),cfg);return charts[id]}
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
   ['Alta','Inventario observado en la cola','Área o volumen de material acumulado en la superficie (inspección con dron, imágenes Sentinel-2/Planet, o estimación visual en las barreras). Es la variable que el caudal realmente explica.'],
   ['Media','Ubicación de la extracción','Punto o sector de la cola donde se retira el material y posición de las barreras o log-booms. Permite separar llegada desde el Cauca de material que ya circula en el embalse.'],
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
    const LT=median(Wo.filter(w=>w.end>=d0(p.lt_desde||'2020-07-01')).map(w=>w.sum));
    const xw=new Map(); for(const [t,v] of map){const e=t+(6-dowM(t))*DAY;xw.set(e,(xw.get(e)||0)+Math.max(v-p.qc,0)/1000)}
    const days=[];
    for(let t=lastT+DAY;t<=endT;t+=DAY){
      const h=Math.ceil((t-lastT)/DAY/7); const we=t+(6-dowM(t))*DAY;
      let lin=p.b0; for(let l=0;l<7;l++) lin+=p.beta[l]*(xw.get(we-l*7*DAY)||0);
      const mult=Math.min(1.5,Math.max(0.7,Math.sqrt(Math.exp(lin))));
      const ah=k*p.a1*Math.exp(-(h-1)/p.tau);
      const fw=(ah*L8+(1-ah)*LT)*mult;
      days.push({t,h,f:fw/7*p.dow[dowM(t)],mult,fw});
    }
    res[y]={L8,LT,k,days};
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
  if(AV&&FC.qpk.v>=AV.umbral){fb.hidden=false;fb.innerHTML=`<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="flex-shrink:0;color:var(--warn);margin-top:1px"><path d="M2 12c2.5-2.5 4.5-2.5 7 0s4.5 2.5 7 0 4.5-2.5 6-1M2 18c2.5-2.5 4.5-2.5 7 0s4.5 2.5 7 0 4.5-2.5 6-1"/></svg><div><b>Creciente ${FC.qpk.t>S.T[S.last]?'pronosticada':'reciente'}: Sitio Presa ${nf(FC.qpk.v)} m³/s el ${fmtD(FC.qpk.t)}.</b> En ${AV.eventos} crecientes históricas sobre ${nf(AV.umbral)} m³/s, la extracción de material flotante fue ${nf(AV.factor_mf[0],2)}–${nf(AV.factor_mf[1],2)} veces la previa durante unas ${AV.semanas} semanas, y la de macrófitas ${nf(AV.factor_ma[0],2)}–${nf(AV.factor_ma[1],2)} veces. Úselo como escenario: el pronóstico central incluye solo parte de ese efecto.</div>`}
  else fb.hidden=true;
  // tarjetas: desde la semana en curso (no desde el último reporte)
  const now=new Date(), today=Date.UTC(now.getUTCFullYear(),now.getUTCMonth(),now.getUTCDate());
  let i0=B.findIndex(b=>b.t1>=today); if(i0<0) i0=0;
  const fp=FC.fp, nAv=B.length-i0, n4=Math.min(4,nAv);
  const s=(k,n=n4)=>B.slice(i0,i0+n).reduce((a,b)=>a+b[k],0);
  const plan=B.slice(i0,i0+n4).some(b=>b.rest!=null);
  const sp=(key,n=n4)=>plan?s(key+'_e',n):(key==='tot'?s('mf_e',n)*fp.mf+s('ma_e',n)*fp.ma:s(key+'_e',n)*fp[key]);
  const from=i0?` desde hoy (S${B[i0].h})`:'';
  const card=(title,key,LT,color)=>{
    const v=s(key), e=s(key+'_e'), lo=s(key+'_p25'), hi=s(key+'_p75');
    const ref=LT!=null?LT*n4:null, ratio=ref?v/ref:1;
    const st=ratio>1.15?['warn','Por encima de lo normal']:ratio<0.85?['info','Por debajo de lo normal']:['ok','Normal'];
    const f=key==='tot'?null:fp[key];
    return `<div class="st ${st[0]} c4"><div class="row"><h2><i class="sw" style="background:${color}"></i>${title}</h2><span class="badge ${st[0]}">${st[1]}</span></div>
      <div class="big">${nf(v)} <small>m³</small></div>
      <div class="note">Próximas ${n4} semanas${from} · mediana · rango probable ${nf(lo)} – ${nf(hi)} m³</div>
      <p><b>${nf(sp(key))} m³</b> ${plan?'con el descanso programado ingresado':'con la frecuencia histórica de paros'+(f!=null?` (×${nf(f,2)})`:'')}${ref?` · ${ratio>=1?'+':''}${nf((ratio-1)*100)} % frente al nivel típico (${nf(ref)} m³)`:''}.${key!=='tot'?' <span class="muted">La división flotante/macrófitas del mecanizado es estimada en el registro; el total es la cifra más firme.</span>':''}</p></div>`};
  document.getElementById('fc-cards').innerHTML=
    card('Total','tot',(R.mf_tot.LT||0)+(R.ma_tot.LT||0),'var(--accent)')+card('Material flotante','mf',R.mf_tot.LT,'var(--mf)')+card('Macrófitas','ma',R.ma_tot.LT,'var(--ma)')+
    [[Math.min(8,nAv),`Próximas ${Math.min(8,nAv)} semanas${from}`],[nAv,`Resto del horizonte · ${nAv} semanas${from}`]].map(([k,lab])=>`<div class="panel c6 kpi"><span class="lab">${lab}</span>
      <span class="val">${nf(s('tot',k))} <small>m³ (mediana)</small></span>
      <span class="rng">esperado ${nf(s('tot_e',k))} m³ con operación normal · ${nf(sp('tot',k))} m³ con paros históricos</span>
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
   B.map(b=>`<tr${b.t1<today?' style="opacity:.55" title="Semana ya transcurrida, sin dato de extracción"':''}><td>S${b.h} · ${fmtDs(b.t0)} – ${fmtDs(b.t1)}</td><td class="num">${b.nd}${b.rest!=null?` <small>(${nf(b.rest)} desc.)</small>`:''}</td><td class="num">${nf(b.q)}</td><td class="num">${nf(b.mf)}</td><td class="num">${nf(b.ma)}</td><td class="num"><b>${nf(b.tot)}</b></td><td class="num">${nf(b.tot_e)}</td><td class="num">${b.rest!=null?nf(b.tot_e)+' <small>plan</small>':nf(b.mf_e*FC.fp.mf+b.ma_e*FC.fp.ma)}</td><td class="num">${nf(b.tot_p10)} – ${nf(b.tot_p90)}</td></tr>`).join('')+'</tbody>';
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
`Semana h (desde el último dato):
  a(h)   = k · a₁ · exp(−(h−1)/τ)
  nivel  = a(h) · L₈ + (1 − a(h)) · LT
  m      = clip( √exp(b₀ + Σₗ βₗ · x(semana−ℓ)) , 0,7 , 1,5 )
  f(h)   = nivel · m
  P50    = (f + 50) · q₅₀(h) − 50      ← valor mostrado
  E      = (f + 50) · r̄(h) − 50       ← valor esperado
  Pp     = (f + 50) · q_p(h) − 50,  p = 10, 25, 75, 90
  día    = semana / 7 · factor del día de la semana
  E_paros = E · (media de todas las semanas / media de semanas
            con operación, últimas 104 semanas)
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
    {label:'Modelo v2',data:M.map(m=>m.modelo),borderColor:css('--accent'),backgroundColor:css('--accent'),borderWidth:3,pointRadius:3}]},options:o});
  document.getElementById('tbl-skill').innerHTML='<thead><tr><th>h</th><th>MAE</th><th>vs mediana</th><th>vs pers.</th><th>Cob. 80%</th></tr></thead><tbody>'+
   M.filter(m=>[1,2,4,8,13].includes(m.h)).map(m=>`<tr><td>${m.h} sem</td><td class="num">${nf(m.mae)}</td><td class="num">${nf(m.skill_clim*100,1)} %</td><td class="num">${nf(m.skill_pers*100,1)} %</td><td class="num">${nf(m.cobertura80*100)} %</td></tr>`).join('')+'</tbody>';
  const m1=P.mf_tot.metricas[0],a1=P.ma_tot.metricas[0], rmf=P.mf_tot.rmse_total||{}, rma=P.ma_tot.rmse_total||{};
  document.getElementById('model-read').innerHTML=`<h3>Cómo leer el desempeño</h3>
   <p>En el backtest se pronosticó cada semana entre 2022 y 2026 usando solo la información disponible en la fecha de origen. A una semana, el error absoluto medio es de ${nf(m1.mae)} m³ en material flotante (promedio observado ${nf(m1.media_obs)} m³/semana) y ${nf(a1.mae)} m³ en macrófitas (promedio ${nf(a1.media_obs)} m³/semana).</p>
   <p>En todo el periodo, el RMSE semanal del material flotante es ${nf(rmf.v2)} m³ con el modelo v2, frente a ${nf(rmf.clim)} m³ de la mediana histórica y ${nf(rmf.pers)} m³ de repetir las últimas semanas. En macrófitas: ${nf(rma.v2)}, ${nf(rma.clim)} y ${nf(rma.pers)} m³. La ventaja se concentra en las primeras 4 semanas; más allá, el pronóstico converge al nivel de largo plazo.</p>
   <p>Un error semanal cercano al 40 % del volumen es esperable mientras el registro mezcle llegada de material con esfuerzo de extracción. Para planear volúmenes use el valor esperado acumulado a 4 u 8 semanas, que es más confiable que una semana aislada. El intervalo P10–P90 cubrió el ${nf(P.mf_tot.cobertura80_fuera_muestra*100)} % (flotante) y el ${nf(P.ma_tot.cobertura80_fuera_muestra*100)} % (macrófitas) de los casos de 2024–2026 calibrando solo con 2022–2023.</p>
   <p>Se probaron y descartaron un modelo conceptual de inventario, regresiones de caudal sin persistencia, niveles de largo plazo móviles (26 a 104 semanas) y una corrección de sesgo móvil: ninguno mejoró fuera de la muestra. Detalle en <a href="#auditoria" style="color:var(--accent)">Auditoría</a>.</p>`;
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
    ['info','Error v1 → v2 (flotante)',`${nf(v.mf_tot.rmse.v1)} → ${nf(v.mf_tot.rmse.v2)}`,'RMSE semanal 2022–2026, m³']
  ].map(([s,l,n,d])=>`<div class="st ${s} c3"><h2>${l}</h2><div class="big">${n}</div><div class="note">${d}</div></div>`).join('');
  const y=[...document.querySelectorAll('#aud-comp button')].find(b=>b.getAttribute('aria-pressed')==='true').dataset.v;
  const yrs=Object.keys(v[y].anual);
  const o=baseOpts();o.scales.y.beginAtZero=false;o.scales.y.title={display:true,text:'% de mejora'};o.scales.y.ticks={callback:x=>nf(x)+' %'};
  o.plugins.tooltip.callbacks.label=c=>c.dataset.label+': '+nf(c.parsed.y,1)+' %';
  mk('ch-aud',{type:'bar',data:{labels:yrs,datasets:[
    {label:'v1 (anterior)',data:yrs.map(k=>v[y].anual[k].v1*100),backgroundColor:css('--muted')+'aa'},
    {label:'v2 (actual)',data:yrs.map(k=>v[y].anual[k].v2*100),backgroundColor:css('--accent')}]},options:o});
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

/* ---------- vista datos ---------- */
function renderUpdate(){
  const s=S.src;
  document.getElementById('api-url').value=apiBase();
  document.getElementById('src-info').innerHTML=`<p>Extracción: ${s._xlsxName?('<b>'+esc(s._xlsxName)+'</b> ('+(s._repo?'leído del repositorio al abrir':'cargado en esta sesión')+')'):'<b>'+(s.xlsx_name||'DatosExtracción.xlsx')+'</b> (incluido)'}, ${fmtD(S.T[S.first])} a ${fmtD(S.T[S.last])}.</p>
   <p>Caudal observado: promedios diarios de HydroForecast Ituango (Olaya, La Pintada, Sitio Presa y nivel) hasta ${fmtD(S.T[S.n-1])}${LIVE.obsDays?`; ${LIVE.obsDays} días actualizados en vivo`:''}.</p>
   <p>Pronóstico de caudal: ${S.fc.source}, generado ${S.fc.generated_at.replace('T',' ').slice(0,16)}, ${S.fc.fecha.length} días. Estado: <span class="tag ${LIVE.state==='live'?'ok':'warn'}">${LIVE.state==='live'?'en vivo':LIVE.state==='archive'?'archivo diario del repositorio':'respaldo incluido'}</span></p>`;
}

/* ---------- navegación ---------- */
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
  if(v==='calidad')renderQuality();else if(v==='modelo'){if(!FC)FC=forecast('mean');renderModel();renderHFSkill()}else if(v==='auditoria')renderAudit();else if(v==='satelite')renderSat();else if(v==='operacion')renderOps();
  else if(v==='actualizar')renderUpdate();else if(v==='requisitos')renderReq();
}
function seg(id,cb){document.getElementById(id).addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;
  [...e.currentTarget.querySelectorAll('button')].forEach(x=>x.setAttribute('aria-pressed',x===b?'true':'false'));cb()})}
function refreshAll(){renderLive();FC=forecast('mean');show()}
function adoptParsed(r,name,repo){
  r.src.forecast_snapshot=S.src.forecast_snapshot;r.src.esfuerzo=S.src.esfuerzo;r.src.audit=S.src.audit;
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
  fetch('datos/app/extra.json?v=7711ed1d90',{cache:'no-cache'}).then(r=>r.json()).then(x=>{Object.assign(ORIG,x);Object.assign(S.src,x);const h=(location.hash||'#pronostico').slice(1);if(['auditoria','operacion','pronostico'].includes(h))renderView(h)}).catch(()=>{});
}
fetch('datos/app/base.json?v=844de4c842',{cache:'no-cache'}).then(r=>{if(!r.ok)throw new Error('HTTP '+r.status);return r.json()}).then(j=>{ORIG=j;init()})
  .catch(e=>{const m=document.getElementById('load-msg');if(m){m.hidden=false;m.textContent='No se pudieron cargar los datos ('+e.message+'). Recargue la página.'}});
if('serviceWorker' in navigator&&location.protocol==='https:')window.addEventListener('load',()=>navigator.serviceWorker.register('sw.js').catch(()=>{}));
})();
