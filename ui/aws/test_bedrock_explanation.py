import json
import os
import unittest
from unittest.mock import Mock, patch

from ui.aws.bedrock_explanation import (
    BedrockExplanationError,
    explain,
    facts_from_events,
    validate_facts,
)

class BedrockExplanationTests(unittest.TestCase):
    def setUp(self):
        self.facts = {
            'verdict': 'LIKELY',
            'recall_number': '24159',
            'recall_title': 'Recall title',
            'evidence': 'Model appears in CPSC description; serial missing.',
            'hazard': 'Overheating hazard.',
        }

    def test_bounded_converse_request_uses_only_caller_facts(self):
        fake = Mock()
        fake.converse.return_value = {'output': {'message': {'content': [{'text': 'A likely model match needs label verification.'}]}}}
        result = explain(self.facts, client=fake, model_id='test-model')
        self.assertEqual(result, 'A likely model match needs label verification.')
        kwargs = fake.converse.call_args.kwargs
        self.assertEqual(kwargs['modelId'], 'test-model')
        self.assertEqual(kwargs['inferenceConfig'], {'maxTokens': 180, 'temperature': 0.2})
        prompt = kwargs['messages'][0]['content'][0]['text'].split('\n', 1)[1]
        self.assertEqual(json.loads(prompt), self.facts)
        self.assertNotIn('serial', json.loads(prompt))
        self.assertIn('not a decision maker', kwargs['system'][0]['text'])

    def test_facts_are_curated_from_lifecycle_events_and_serial_is_excluded(self):
        events = [
            {'to': 'SIGNAL_DETECTED', 'payload': {'verdict': 'LIKELY', 'candidates': [{'recall_number': '24159', 'title': 'Recall title', 'confidence': 'LIKELY'}]}},
            {'to': 'MATCH_REVIEW', 'payload': {'primary': {'recall_number': '24159', 'title': 'Recall title', 'confidence': 'LIKELY'}, 'evidence_hint': 'Model NS-AF5DSS2 matches; serial is missing.'}},
            {'to': 'MATCH_CONFIRMED', 'payload': {'recall_number': '24159', 'basis': 'user attestation of the rating label', 'evidence': 'Model matches recall #24159.'}},
            {'to': 'EVIDENCE_READY', 'payload': {'recall_number': '24159', 'title': 'Recall title', 'hazard': 'Overheating', 'remedy': None, 'serial': 'SHOULD_NOT_PASS'}},
        ]
        facts = facts_from_events(events)
        self.assertEqual(facts['verdict'], 'CONFIRMED')
        self.assertEqual(facts['confidence'], 'LIKELY')
        self.assertEqual(facts['confirmation_basis'], 'user attestation of the rating label')
        self.assertNotIn('serial', json.dumps(facts))
        self.assertNotIn('SHOULD_NOT_PASS', json.dumps(facts))

    def test_rejects_arbitrary_or_oversized_facts(self):
        with self.assertRaises(BedrockExplanationError): validate_facts({'serial': 'private'})
        with self.assertRaises(BedrockExplanationError): validate_facts({'evidence': 'x' * 1801})

    def test_missing_model_configuration_never_calls_client(self):
        fake = Mock()
        with patch.dict(os.environ, {'RECALLGUARD_BEDROCK_MODEL_ID': ''}):
            with self.assertRaisesRegex(BedrockExplanationError, 'not configured'):
                explain(self.facts, client=fake)
        fake.converse.assert_not_called()

    def test_aws_errors_are_safe_and_do_not_change_fact_payload(self):
        fake = Mock()
        fake.converse.side_effect = RuntimeError('sensitive local AWS error detail')
        with self.assertRaisesRegex(BedrockExplanationError, 'temporarily unavailable') as caught:
            explain(self.facts, client=fake, model_id='test-model')
        self.assertNotIn('sensitive local', str(caught.exception))

if __name__ == '__main__': unittest.main()
