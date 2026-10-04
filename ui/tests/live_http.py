"""Current-contract test: UI adapter -> real MCP HTTP -> live CPSC workflow.
Run with both servers running. Creates local simulated cases; sends nothing externally.
"""
import json
import urllib.request
import urllib.error

BASE = 'http://127.0.0.1:3000/api/'

def call(tool, **args):
    request = urllib.request.Request(BASE + tool, data=json.dumps(args).encode(), headers={'Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(request, timeout=100) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        return json.load(error)


def start():
    result = call('start_case', product_key='kitchen-air-fryer')
    assert result.get('state') == 'VERIFYING', result
    return result['run_id']


def main():
    run = start()
    insufficient = call('submit_verification', run_id=run, user_attested=False)
    assert insufficient['state'] == 'INSUFFICIENT_EVIDENCE' and insufficient['terminal']
    assert 'error' in call('approve_action', run_id=run, action_id='disable_kitchen-air-fryer')
    assert all(e['to'] != 'ACTION_EXECUTED' for e in insufficient['events'])
    print('LIVE insufficient evidence: PASS')

    no_match = call('start_case', product_key='bedroom-vacuum')
    assert no_match['state'] == 'NO_MATCH' and no_match['terminal']
    feed = call('get_events', run_id=no_match['run_id'], after_seq=-1)
    assert len(feed['events']) == 1 and feed['events'][0]['seq'] == 0
    print('LIVE no-match, including sequence zero: PASS')

    run = start()
    ready = call('submit_verification', run_id=run, serial='DEMO-SN88412', user_attested=True)
    assert ready['state'] == 'AWAITING_APPROVAL'
    denied = call('deny_action', run_id=run)
    assert denied['state'] == 'ACTION_DECLINED'
    assert all(e['to'] != 'ACTION_EXECUTED' for e in denied['events'])
    print('LIVE deny: PASS')

    run = start()
    ready = call('submit_verification', run_id=run, serial='DEMO-SN88412', user_attested=True)
    assert ready['state'] == 'AWAITING_APPROVAL'
    assert 'error' in call('approve_action', run_id=run, action_id='wrong-action')
    result = call('approve_action', run_id=run, action_id=ready['pending_action']['action_id'])
    expected = ['SIGNAL_DETECTED','MATCH_REVIEW','VERIFYING','MATCH_CONFIRMED','EVIDENCE_READY','AWAITING_APPROVAL','ACTION_EXECUTED','REMEDY_STARTED','TRACKING']
    assert result['state'] == 'TRACKING' and result['terminal']
    assert [e['to'] for e in result['events']] == expected
    transition = result['events'][6]['payload']['device_transition']
    assert transition['new_state'] == 'OFF' and transition['verified'] and transition['simulated']
    print(f"LIVE happy path: {transition['old_state']} -> OFF -> verified: PASS")
    restored = call('get_case', run_id=run)
    feed = call('get_events', run_id=run, after_seq=-1)
    assert restored['state'] == 'TRACKING' and len(feed['events']) == 9
    assert [e['seq'] for e in call('get_events', run_id=run, after_seq=5)['events']] == [6,7,8]
    assert call('get_events', run_id=run, after_seq=8)['events'] == []
    assert all(set(e) == {'seq','from','to','at','payload'} for e in feed['events'])
    assert 'error' in call('approve_action', run_id=run, action_id=ready['pending_action']['action_id'])
    assert 'error' in call('get_case', run_id='missing')
    assert 'error' in call('set_device_state', device_id='kitchen-air-fryer-plug', state='ON')
    print('LIVE restore, incremental feed, guards, adapter allowlist: PASS')

if __name__ == '__main__': main()
