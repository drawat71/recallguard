export const escapeHTML = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export const label = state => (state || '').toLowerCase().replaceAll('_', ' ');
export const payloadFor = (events, state) => events.findLast(e => e.to === state)?.payload || {};
export const canApprove = snapshot => snapshot?.state === 'AWAITING_APPROVAL' && snapshot.terminal === false && !!snapshot.pending_action?.action_id && !!snapshot.pending_action?.description;
export const identity = events => events[0] ? JSON.stringify([events[0].seq, events[0].at, events[0].to]) : null;
export function mergeEvents(existing, incoming) {
  return [...new Map([...existing, ...incoming].map(e => [e.seq, e])).values()].sort((a,b) => a.seq-b.seq);
}
export function approvalArgs(snapshot) {
  if (!canApprove(snapshot)) throw new Error('No action is awaiting approval.');
  return {run_id:snapshot.run_id, action_id:snapshot.pending_action.action_id};
}
export function deviceView(events) {
  const action = payloadFor(events, 'ACTION_EXECUTED').device_transition;
  const plan = payloadFor(events, 'EVIDENCE_READY').planned_action;
  return action ? {state:action.new_state, from:action.old_state, verified:action.verified === true, simulated:action.simulated === true}
    : {state:plan?.from ?? null, from:null, verified:false, simulated:plan?.simulated === true};
}
export function messageFor(event) {
  const p = event.payload;
  switch(event.to) {
    case 'SIGNAL_DETECTED': return `A recall signal needs a closer look. Verdict: ${p.verdict}.`;
    case 'MATCH_REVIEW': return p.evidence_hint;
    case 'VERIFYING': return `Please provide the ${p.needed}. In this text demo, enter the serial and confirm the label below.`;
    case 'MATCH_CONFIRMED': return `Match confirmed. Evidence basis: ${p.basis}.`;
    case 'EVIDENCE_READY': return 'The evidence is ready for your review. No device action has been taken in this case.';
    case 'AWAITING_APPROVAL': return p.prompt;
    case 'ACTION_EXECUTED': {const d=p.device_transition; return `Simulated device: ${d.old_state} → ${d.new_state}. ${d.verified ? 'Read-back verified.' : 'Read-back not verified.'}`;}
    case 'REMEDY_STARTED': return `Remedy draft created: ${p.case_id}. You review and send it.`;
    case 'TRACKING': return `${p.case_id}: ${p.note}`;
    case 'INSUFFICIENT_EVIDENCE': return `I don’t have enough evidence to act. ${p.reason} No device action was taken.`;
    case 'NO_MATCH': return p.note;
    case 'ACTION_DECLINED': return 'You declined the action. No device action or remedy was started in this case.';
    default: return `Workflow reported ${label(event.to)}.`;
  }
}
export function controlsHTML(snapshot, blocked=false) {
  const disabled=blocked?'disabled':'';
  if (snapshot?.state === 'VERIFYING' && !snapshot.terminal) return `<form id="verification-form"><div class="form-heading"><span class="eyebrow">YOUR TURN</span><h3>Check the rating label</h3></div><label for="serial">Serial number <span class="muted">(if available)</span></label><input id="serial" name="serial" placeholder="Enter the serial from your label" autocomplete="off" ${disabled}><label class="attestation"><input type="checkbox" name="attested" ${disabled}><span>I checked the physical rating label and confirm it matches the recalled model.</span></label><p class="fine">Attestation is recorded as your confirmation. It is not CPSC serial verification.</p><button class="primary" type="submit" ${disabled}>Submit evidence <span>→</span></button><button class="text-button" id="insufficient" type="button" ${disabled}>I can’t verify the label</button></form>`;
  if (canApprove(snapshot)) return `<section class="approval"><span class="eyebrow">YOUR PERMISSION IS REQUIRED</span><h3>Ready when you are.</h3><p>${escapeHTML(snapshot.pending_action.description)}</p><p class="fine">This approves the named simulated device action and remedy draft. Nothing is sent to the manufacturer.</p><div class="button-row"><button class="primary" id="approve" ${disabled}>Approve action <span>→</span></button><button class="secondary" id="deny" ${disabled}>Deny action</button></div></section>`;
  const endings = {INSUFFICIENT_EVIDENCE:['Evidence is incomplete. Action stopped.','No device action was taken. Start a new check when you can verify the label.'],NO_MATCH:['No matching recall found.','This check has ended. No consequential action was taken.'],ACTION_DECLINED:['Your decision. Action declined.','The workflow has ended without taking the proposed action.'],TRACKING:['Action verified. Remedy in tracking.','Your draft is ready to review. Tracking is local; no manufacturer request has been sent.']};
  const ending=endings[snapshot?.state];
  return ending ? `<section class="outcome ${snapshot.state === 'TRACKING' ? 'success' : ''}"><span class="eyebrow">${escapeHTML(snapshot.state)}</span><h3>${ending[0]}</h3><p>${ending[1]}</p></section>` : '';
}

export class CaseClient {
  constructor(call, storage) {this.call=call; this.storage=storage; this.snapshot=null; this.events=[]; this.fingerprint=null;}
  async restore() {
    const saved=JSON.parse(this.storage.getItem('recallguard.case') || 'null');
    if (!saved) return;
    this.snapshot={run_id:saved.run_id}; this.fingerprint=saved.identity;
    await this.refresh(true);
  }
  async refresh(full=false, attempts=0) {
    if (!this.snapshot) return;
    const run_id=this.snapshot.run_id;
    let snapshot;
    try { snapshot=await this.call('get_case',{run_id}); }
    catch(error) {
      if (/unknown run /.test(error.message)) {
        this.forget();
        throw new Error('This case is no longer available. The backend may have restarted. Start a new check.');
      }
      throw error;
    }
    const feed=await this.call('get_events',{run_id,after_seq:full?-1:(this.events.at(-1)?.seq ?? -1)});
    if (full && this.fingerprint && identity(feed.events)!==this.fingerprint) {
      this.forget(); throw new Error('The backend restarted and this run ID was reused. Start a new check.');
    }
    const events=full?feed.events:mergeEvents(this.events,feed.events);
    // A concurrent transition between reads must not pair old controls with new events.
    if (snapshot.state!==feed.state || snapshot.event_count!==events.length) {
      if (attempts>=2) throw new Error('Case changed during refresh. Refresh again before taking action.');
      return this.refresh(true, attempts+1);
    }
    this.snapshot=snapshot; this.events=events; this.fingerprint=identity(events);
    this.storage.setItem('recallguard.case',JSON.stringify({run_id,identity:this.fingerprint}));
  }
  async start(product_key) {
    const result=await this.call('start_case',{product_key});
    this.snapshot={run_id:result.run_id}; this.events=[]; this.fingerprint=identity(result.events);
    this.storage.setItem('recallguard.case',JSON.stringify({run_id:result.run_id,identity:this.fingerprint}));
    await this.refresh(true);
  }
  async act(tool,args={}) {
    const approved=tool==='approve_action'?approvalArgs(this.snapshot):null;
    await this.refresh(true);
    if (approved && JSON.stringify(approved)!==JSON.stringify(approvalArgs(this.snapshot))) throw new Error('The pending action changed. Review it before approving.');
    const values=approved || {run_id:this.snapshot.run_id,...args};
    await this.call(tool, values);
    await this.refresh();
  }
  forget() {this.storage.removeItem('recallguard.case');this.snapshot=null;this.events=[];this.fingerprint=null;}
}
