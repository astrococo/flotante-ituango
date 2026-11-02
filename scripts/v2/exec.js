
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
