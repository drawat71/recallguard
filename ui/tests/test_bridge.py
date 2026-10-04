import unittest
from ui.bridge import validate, validate_explanation_request, CONTRACT

class ContractTests(unittest.TestCase):
    def test_only_six_tools(self):
        self.assertEqual(len(CONTRACT), 6)
        for tool in ('set_device_state', 'set_state', 'start_remedy', 'get_inventory'):
            with self.assertRaises(ValueError): validate(tool, {})

    def test_explanation_accepts_only_run_id_and_does_not_extend_mcp_contract(self):
        validate_explanation_request({'run_id': 'WF-0001'})
        self.assertEqual(len(CONTRACT), 6)
        for args in ({}, {'run_id': 'WF-0001', 'serial': 'private'}, {'run_id': ''}, {'run_id': 1}):
            with self.assertRaises(ValueError): validate_explanation_request(args)

    def test_frozen_arguments(self):
        validate('get_events', {'run_id': 'WF-0001', 'after_seq': -1})
        validate('deny_action', {'run_id': 'WF-0001'})
        validate('submit_verification', {'run_id': 'WF-0001', 'serial': None, 'user_attested': False})
        for tool, args in [('approve_action', {'run_id': 'WF-0001'}), ('deny_action', {'run_id': 'WF-0001', 'action_id': 'a'}), ('get_events', {'run_id': 'WF-0001', 'after_seq': True}), ('submit_verification', {'run_id': 'WF-0001', 'user_attested': 'yes'})]:
            with self.assertRaises(ValueError): validate(tool, args)

if __name__ == '__main__': unittest.main()
