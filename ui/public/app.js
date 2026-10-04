import {CaseClient, escapeHTML as esc, label, payloadFor, controlsHTML, deviceView, messageFor} from './model.js';
const $=id=>document.getElementById(id);
async function call(tool,args) {
  const response=await fetch(`/api/${tool}`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(args),signal:AbortSignal.timeout(100000)});
  const data=await response.json();
  if (!response.ok || data.error) throw new Error(data.error || 'The workflow could not be reached.');
  return data;
}
// Browsers with disabled storage still work for this session.
const memory=new Map();
const storage={getItem(key){try{return localStorage.getItem(key);}catch{return memory.get(key);}},setItem(key,value){memory.set(key,value);try{localStorage.setItem(key,value);}catch{}},removeItem(key){memory.delete(key);try{localStorage.removeItem(key);}catch{}}};
const client=new CaseClient(call,storage);
let busy=false, online=false, lastRender='', serialDraft='', attestedDraft=false, draftRun=null, explanationKey='', explanation=null, explanationError='', explanationLoading=false;
const stamp=time=>new Date(time).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit',second:'2-digit'});
const field=(title,value,kind='')=>value ? `<div class="evidence-row ${kind}"><strong>${title}</strong>${esc(typeof value==='string'?value:JSON.stringify(value))}</div>`:'';

function render(force=false) {
  const s=client.snapshot, events=client.events;
  const nextExplanationKey=s?`${s.run_id}:${s.state}`:'';
  if(nextExplanationKey!==explanationKey){explanationKey=nextExplanationKey;explanation=null;explanationError='';explanationLoading=false;}
  const signature=JSON.stringify([s,events,busy,online,explanation,explanationError,explanationLoading]);
  if(!force && signature===lastRender)return;
  lastRender=signature;
  const serial=document.querySelector('[name=serial]'), attested=document.querySelector('[name=attested]');
  if(draftRun!==s?.run_id){serialDraft='';attestedDraft=false;draftRun=s?.run_id;}
  if(document.querySelector('#verification-form')?.dataset.run===s?.run_id){
    if(serial)serialDraft=serial.value;
    if(attested)attestedDraft=attested.checked;
  }
  $('connection').textContent=busy?'Contacting workflow…':online?'MCP connected':s?'Connection needs attention':'Local workflow';
  $('connection').parentElement.classList.toggle('offline',!online);
  $('working').hidden=!busy;
  $('status').innerHTML=`<span class="badge ${s?.state==='VERIFYING' || s?.state==='INSUFFICIENT_EVIDENCE'?'warning':''}">${esc(s?.state || 'READY TO CHECK')}</span><p class="status-note">${s?`${esc(s.run_id)} · ${s.terminal?'Case ended':'In progress'}`:'No case started'}</p>`;
  $('stepper').innerHTML=events.length?events.map((e,i)=>`<li class="${i===events.length-1?'current':''}" ${i===events.length-1?'aria-current="step"':''}><span class="step-number">${i===events.length-1?'•':'✓'}</span><span>${esc(label(e.to))}</span></li>`).join(''):'<li class="empty">Your recorded steps will appear here.</li>';
  const messages=$('messages'); const wasNearBottom=messages.scrollHeight-messages.scrollTop-messages.clientHeight<50;
  messages.innerHTML=events.length?events.map(e=>`<article class="chat-item"><div class="chat-meta"><span>RECALLGUARD · ${esc(label(e.to).toUpperCase())}</span><time datetime="${esc(e.at)}">${esc(stamp(e.at))}</time></div><div class="chat-bubble">${esc(messageFor(e))}</div></article>`).join(''):`<div class="welcome"><div class="orb" aria-hidden="true">✦</div><h2>Let’s check your kitchen.</h2><p>I’ll look for recall evidence, help verify your product, and ask before taking action.</p></div>`;
  if(wasNearBottom)messages.scrollTop=messages.scrollHeight;
  $('controls').innerHTML=s?controlsHTML(s,busy||!online):`<div class="start-card"><p>Insignia Kitchen Air Fryer · NS-AF5DSS2</p><button id="start" class="primary" ${busy?'disabled':''}>Check my air fryer <span>→</span></button></div>`;
  const serialNew=document.querySelector('[name=serial]'),attestedNew=document.querySelector('[name=attested]');
  if(document.querySelector('#verification-form'))document.querySelector('#verification-form').dataset.run=s.run_id;
  if(serialNew)serialNew.value=serialDraft;
  if(attestedNew)attestedNew.checked=attestedDraft;
  $('start')?.addEventListener('click',()=>start('kitchen-air-fryer'));
  $('verification-form')?.addEventListener('submit',e=>{e.preventDefault();const f=new FormData(e.currentTarget);run(()=>client.act('submit_verification',{serial:String(f.get('serial')||'').trim()||null,user_attested:f.get('attested')==='on'}));});
  $('insufficient')?.addEventListener('click',()=>run(()=>client.act('submit_verification',{user_attested:false})));
  $('approve')?.addEventListener('click',()=>run(()=>client.act('approve_action')));
  $('deny')?.addEventListener('click',()=>run(()=>client.act('deny_action')));
  const review=payloadFor(events,'MATCH_REVIEW'), ready=payloadFor(events,'EVIDENCE_READY'), confirmed=payloadFor(events,'MATCH_CONFIRMED');
  const primary=review.primary || payloadFor(events,'SIGNAL_DETECTED').candidates?.[0];
  const number=ready.recall_number || primary?.recall_number;
  const isVacuum=s?.product_key==='bedroom-vacuum';
  $('product-kind').textContent=isVacuum?'DEMO CONTROL':'KITCHEN';
  $('product-brand').textContent=isVacuum?'DYSON':'INSIGNIA';
  $('product-name').textContent=isVacuum?'Bedroom Vacuum':'Kitchen Air Fryer';
  $('product-model').textContent=isVacuum?'SV22':'NS-AF5DSS2';
  document.querySelector('.appliance').hidden=isVacuum;
  const evidenceBody=number?`<span class="badge ${confirmed.basis?'':'warning'}">${confirmed.basis?'CONFIRMED':esc(primary.confidence)} · CPSC #${esc(number)}</span><p class="recall-title">${esc(ready.title||primary.title)}</p>${field('MATCHED / EVIDENCE',confirmed.evidence||review.evidence_hint,'matched')}${confirmed.basis?field('CONFIRMATION BASIS',confirmed.basis,'matched'):field('MISSING EVIDENCE',review.evidence_needed?.join(', '),'missing')}${field('HAZARD',ready.hazard)}${field('REMEDY',Object.hasOwn(ready,'remedy')?(ready.remedy ?? 'Not included in the lifecycle payload. See the CPSC recall notice.'):null)}${!ready.hazard?'<p class="fine">Detailed hazard and remedy have not been returned by the lifecycle yet.</p>':''}<a class="source-link" href="https://www.cpsc.gov/Recalls?search_combined_fields=${encodeURIComponent(number)}" target="_blank" rel="noopener noreferrer">Search CPSC for #${esc(number)} ↗</a>`:s?.state==='NO_MATCH'?field('RESULT',payloadFor(events,'NO_MATCH').note):'<p class="empty">Recall evidence appears here after the check. No match has been assumed.</p>';
  const explainable=!!s && ['VERIFYING','MATCH_CONFIRMED','EVIDENCE_READY','AWAITING_APPROVAL','ACTION_EXECUTED','REMEDY_STARTED','TRACKING','INSUFFICIENT_EVIDENCE','NO_MATCH','ACTION_DECLINED'].includes(s.state);
  $('evidence').innerHTML=`${evidenceBody}${explainable?`<section class="bedrock-explainer"><div class="eyebrow">OPTIONAL · AMAZON BEDROCK</div><p>Get a plain language explanation of the recall evidence. On request, the CPSC recall facts and workflow confirmation basis are sent to AWS Bedrock. Serial numbers and device IDs are excluded.</p><button id="explain-evidence" class="secondary" ${explanationLoading?'disabled':''}>${explanationLoading?'Explaining…':'Explain this evidence'}</button>${explanation?`<div class="ai-answer"><strong>AI explanation · informational only</strong><p>${esc(explanation)}</p></div>`:''}${explanationError?`<p class="ai-error" role="status">${esc(explanationError)}</p>`:''}</section>`:''}`;
  const device=deviceView(events);
  $('device').innerHTML=`<div class="device-readout"><span class="power-icon" aria-hidden="true">⏻</span><div><div class="device-state ${device.state?'':'unknown'}">${device.from?`${esc(device.from)} <span class="muted">→</span> `:''}${esc(device.state||'Not reported')}</div><div class="device-detail">${device.state?'Last backend-reported reading':'Waiting for a device reading'}</div></div></div>${device.verified?'<p class="verified">✓ Read-back verified by the workflow</p>':`<p class="fine">${s?.terminal?'No device action recorded in this case.':'No device action recorded yet.'}</p>`}<p class="fine">Local simulation · no real hardware</p>`;
  const remedy=payloadFor(events,'REMEDY_STARTED');
  $('remedy').innerHTML=remedy.case_id?`<h3>${esc(remedy.case_id)}</h3><span class="badge">${s.state==='TRACKING'?'TRACKING':'DRAFT CREATED'}</span><p>Draft only. Review and send it yourself.</p><details><summary class="source-link">Read remedy draft</summary><pre>${esc(remedy.remedy_draft)}</pre></details>`:'<h3>No remedy started</h3><p>A draft is created only after you approve the proposed action.</p>';
  const open=new Set([...$('events').querySelectorAll('details[open]')].map(d=>d.dataset.seq));
  $('event-count').textContent=`${events.length} event${events.length===1?'':'s'}`;
  $('events').innerHTML=events.length?events.map(e=>`<details data-seq="${e.seq}" ${open.has(String(e.seq))?'open':''}><summary><span>${String(e.seq).padStart(2,'0')}</span><b>${esc(e.from)} → ${esc(e.to)}</b><time>${esc(stamp(e.at))}</time><span>＋</span></summary><pre>${esc(JSON.stringify(e,null,2))}</pre></details>`).join(''):'<p class="empty">No events yet. Every recorded transition will appear here with its original timestamp and payload.</p>';
  for(const id of ['refresh','new-check','no-match'])$(id).disabled=busy;
}
async function explainEvidence(){
  if(explanationLoading||!client.snapshot)return;
  const runId=client.snapshot.run_id,state=client.snapshot.state;
  explanationLoading=true;explanationError='';render();
  try{const result=await call('explain_evidence',{run_id:runId});if(client.snapshot?.run_id===runId&&client.snapshot?.state===state)explanation=result.explanation;}
  catch(error){if(client.snapshot?.run_id===runId&&client.snapshot?.state===state)explanationError=error.message;}
  finally{explanationLoading=false;render();}
}
async function run(fn) {
  if(busy)return;
  busy=true; $('error').hidden=true; render();
  try{await fn();online=!!client.snapshot;}
  catch(error){online=false;$('error').textContent=error.message;$('error').hidden=false;}
  finally{busy=false;render();}
}
function start(product) {serialDraft='';attestedDraft=false;run(()=>client.start(product));}
$('refresh').onclick=()=>run(()=>client.refresh(true));
$('new-check').onclick=()=>start('kitchen-air-fryer');
document.addEventListener('click',event=>{if(event.target.closest?.('#explain-evidence')){event.preventDefault();explainEvidence();}});
$('no-match').onclick=()=>start('bedroom-vacuum');
render();
await run(()=>client.restore());
// Sequential polling prevents stale responses from overtaking user actions.
async function poll(){if(!busy && client.snapshot && !document.hidden){busy=true;try{await client.refresh();online=true;$('error').hidden=true;}catch(error){online=false;$('error').textContent=error.message;$('error').hidden=false;}finally{busy=false;render();}}setTimeout(poll,3500);}
setTimeout(poll,3500);
