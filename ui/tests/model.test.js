import test from 'node:test';
import assert from 'node:assert/strict';
import {canApprove,controlsHTML,approvalArgs,deviceView,mergeEvents,identity,CaseClient,messageFor} from '../public/model.js';
const pending={action_id:'server-chosen-action-42',description:'Turn OFF the simulated device and draft remedy.'};
const snapshot=state=>({run_id:'WF-0001',state,terminal:['NO_MATCH','INSUFFICIENT_EVIDENCE','ACTION_DECLINED','TRACKING'].includes(state),pending_action:pending});
const event=(seq,to,payload={})=>({seq,from:'IDLE',to,at:`2026-09-27T12:00:0${seq}Z`,payload});
test('approval requires exact awaiting state, nonterminal case, and a complete pending action',()=>{
  assert.equal(canApprove(snapshot('AWAITING_APPROVAL')),true);
  for(const state of ['IDLE','SIGNAL_DETECTED','MATCH_REVIEW','VERIFYING','MATCH_CONFIRMED','EVIDENCE_READY','ACTION_EXECUTED','REMEDY_STARTED','TRACKING','NO_MATCH','INSUFFICIENT_EVIDENCE','ACTION_DECLINED']){
    assert.equal(canApprove(snapshot(state)),false,state);
    assert.doesNotMatch(controlsHTML(snapshot(state)),/id="approve"/,state);
  }
  assert.equal(canApprove({...snapshot('AWAITING_APPROVAL'),terminal:true}),false);
  assert.equal(canApprove({...snapshot('AWAITING_APPROVAL'),pending_action:null}),false);
});
test('every terminal state renders its actual outcome despite a stale pending action',()=>{
  for(const state of ['TRACKING','NO_MATCH','INSUFFICIENT_EVIDENCE','ACTION_DECLINED']){
    const html=controlsHTML(snapshot(state));assert.match(html,new RegExp(state));assert.doesNotMatch(html,/id="approve"|id="deny"|verification-form/);
  }
});
test('verification attestation is never prechecked and absent on other states',()=>{
  const html=controlsHTML(snapshot('VERIFYING'));assert.match(html,/name="attested"/);assert.doesNotMatch(html,/<input[^>]*\schecked[\s=>]/);
  assert.doesNotMatch(controlsHTML(snapshot('TRACKING')),/name="attested"/);
});
test('approval sends backend ID unchanged; stale/terminal approval throws',()=>{
  assert.deepEqual(approvalArgs(snapshot('AWAITING_APPROVAL')),{run_id:'WF-0001',action_id:pending.action_id});
  assert.throws(()=>approvalArgs(snapshot('TRACKING')));
  assert.match(controlsHTML(snapshot('AWAITING_APPROVAL'),true),/id="approve" disabled/);
});
test('untrusted descriptions are escaped in controls',()=>{
  assert.match(controlsHTML({...snapshot('AWAITING_APPROVAL'),pending_action:{...pending,description:'<img src=x onerror=alert(1)>'}}),/&lt;img/);
});
test('device never fabricates an ON reading or verification',()=>{
  assert.deepEqual(deviceView([event(0,'INSUFFICIENT_EVIDENCE')]),{state:null,from:null,verified:false,simulated:false});
  assert.equal(deviceView([event(0,'EVIDENCE_READY',{planned_action:{from:'OFF',to:'OFF',simulated:true}})]).state,'OFF');
  assert.deepEqual(deviceView([event(0,'ACTION_EXECUTED',{device_transition:{old_state:'ON',new_state:'OFF',verified:true,simulated:true}})]),{state:'OFF',from:'ON',verified:true,simulated:true});
});
test('event merging preserves seq zero and deduplicates overlapping polling responses',()=>{
  assert.deepEqual(mergeEvents([event(0,'SIGNAL_DETECTED'),event(1,'MATCH_REVIEW')],[event(1,'MATCH_REVIEW'),event(2,'VERIFYING')]).map(e=>e.seq),[0,1,2]);
});
test('conversation distinguishes attestation from serial corroboration',()=>{
  assert.match(messageFor(event(3,'MATCH_CONFIRMED',{basis:'user attestation of the rating label'})),/user attestation/);
});
function storage(initial){const m=new Map(Object.entries(initial||{}));return{getItem:k=>m.get(k),setItem:(k,v)=>m.set(k,v),removeItem:k=>m.delete(k)};}
test('restore calls get_case and full get_events(-1); polling uses last observed seq',async()=>{
  const events=[event(0,'SIGNAL_DETECTED'),event(1,'MATCH_REVIEW'),event(2,'VERIFYING')];const calls=[];
  const client=new CaseClient(async(tool,args)=>{calls.push([tool,args]);return tool==='get_case'?{...snapshot('VERIFYING'),event_count:3}:{state:'VERIFYING',events:args.after_seq===-1?events:[]};},storage({'recallguard.case':JSON.stringify({run_id:'WF-0001',identity:identity(events)})}));
  await client.restore();assert.equal(client.events.length,3);assert.deepEqual(calls[1],['get_events',{run_id:'WF-0001',after_seq:-1}]);
  await client.refresh();assert.equal(calls.at(-1)[1].after_seq,2);
});
test('backend restart with recycled ID invalidates saved case instead of restoring another run',async()=>{
  const client=new CaseClient(async(tool)=>tool==='get_case'?{...snapshot('VERIFYING'),event_count:1}:{state:'VERIFYING',events:[event(0,'VERIFYING')]},storage({'recallguard.case':JSON.stringify({run_id:'WF-0001',identity:'old-event'})}));
  await assert.rejects(()=>client.restore(),/reused/);assert.equal(client.snapshot,null);
});
test('failed mutation never advances local workflow or invents events',async()=>{
  const events=[event(0,'AWAITING_APPROVAL')];
  const client=new CaseClient(async(tool)=>{if(tool==='get_case')return{...snapshot('AWAITING_APPROVAL'),event_count:1};if(tool==='get_events')return{state:'AWAITING_APPROVAL',events};throw Error('Connection lost');},storage());
  client.snapshot=snapshot('AWAITING_APPROVAL');client.events=events;
  await assert.rejects(()=>client.act('approve_action'),/Connection lost/);assert.equal(client.snapshot.state,'AWAITING_APPROVAL');assert.equal(client.events.length,1);
});
test('action rereads current case and passes exact current ID, deny uses only run_id',async()=>{
  const events=[event(0,'AWAITING_APPROVAL')];const calls=[];
  const client=new CaseClient(async(tool,args)=>{calls.push([tool,args]);return tool==='get_events'?{state:'AWAITING_APPROVAL',events:args.after_seq===-1?events:[]}:{...snapshot('AWAITING_APPROVAL'),event_count:1};},storage());
  client.snapshot=snapshot('AWAITING_APPROVAL');await client.act('approve_action');await client.act('deny_action');
  assert.deepEqual(calls.find(c=>c[0]==='approve_action')[1],{run_id:'WF-0001',action_id:pending.action_id});assert.deepEqual(calls.find(c=>c[0]==='deny_action')[1],{run_id:'WF-0001'});
});
test('a changed approval ID requires a fresh human review, not an automatic substituted approval',async()=>{
  const events=[event(0,'AWAITING_APPROVAL')];let acted=false;
  const client=new CaseClient(async(tool)=>{
    if(tool==='get_case')return{...snapshot('AWAITING_APPROVAL'),pending_action:{...pending,action_id:'changed'},event_count:1};
    if(tool==='get_events')return{state:'AWAITING_APPROVAL',events};acted=true;
  },storage());
  client.snapshot=snapshot('AWAITING_APPROVAL');await assert.rejects(()=>client.act('approve_action'),/changed/);assert.equal(acted,false);
});
test('expired saved runs are cleared with an actionable restart message',async()=>{
  const saved=storage({'recallguard.case':JSON.stringify({run_id:'WF-0001',identity:'old'})});
  const client=new CaseClient(async()=>{throw Error("unknown run 'WF-0001'");},saved);
  await assert.rejects(()=>client.restore(),/Start a new check/);
  assert.equal(client.snapshot,null);assert.equal(saved.getItem('recallguard.case'),undefined);
});
