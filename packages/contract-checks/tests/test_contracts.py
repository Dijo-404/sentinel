import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest

from sentinel_contract_checks import (
    canonical_action, action_digest, validate, load_json, compare_schemas,
    check_retries, verify_evidence, snapshot, fixture_report,
)

DATA = Path(__file__).parents[1] / 'src/sentinel_contract_checks/data'
ACTION = {
    'action': 'REQUEST_REFUND', 'case_id': 'case-demo-42', 'case_revision': 1,
    'transaction_ref': 'TXN-B', 'amount_minor': 150000, 'currency': 'INR',
    'destination': 'ORIGINAL_PAYMENT_ROUTE',
    'evidence_ids': ['evidence-payment-b', 'evidence-order'],
    'policy_version': 'demo-policy-v1',
}
DIGEST = 'd5ce68ac9b173525d7ed0989eeb374cbb41b0a551f4457f8406d85342e1a8993'


class Contracts(unittest.TestCase):
    def test_canonical_baseline_vector(self):
        expected = b'{"action":"REQUEST_REFUND","amount_minor":150000,"case_id":"case-demo-42","case_revision":1,"currency":"INR","destination":"ORIGINAL_PAYMENT_ROUTE","evidence_ids":["evidence-payment-b","evidence-order"],"policy_version":"demo-policy-v1","transaction_ref":"TXN-B"}'
        self.assertEqual(canonical_action(ACTION), expected)
        self.assertEqual(action_digest(ACTION), DIGEST)

    def test_all_six_actions_have_exact_schemas(self):
        base = {k: ACTION[k] for k in ('case_id', 'case_revision', 'evidence_ids', 'policy_version')}
        variants = [
            ACTION,
            dict(base, action='STATUS_UPDATE', message_code='WAITING'),
            dict(base, action='OPEN_DISPUTE', transaction_ref='TXN-B', reason_code='FAILED'),
            dict(base, action='SCHEDULE_RECHECK', available_at='2026-11-13T12:00:00Z', reason_code='WAIT'),
            dict(base, action='SYNC_ORDER', transaction_ref='TXN-B', order_reference='DEMO-ORDER-42'),
            dict(base, action='ESCALATE', reason_code='FRAUD', owner_queue='FRAUD'),
        ]
        for action in variants:
            with self.subTest(action=action['action']):
                self.assertEqual(validate('Action', action), [])
                self.assertTrue(validate('Action', dict(action, unauthorized=True)))
                for key in action:
                    bad = dict(action)
                    del bad[key]
                    self.assertTrue(validate('Action', bad), key)

    def test_invalid_money_and_revision_do_not_coerce(self):
        for field in ('amount_minor', 'case_revision'):
            for bad in (True, False, 1.0, 1.5, '1', None, 0, -1, float('nan'), float('inf')):
                with self.subTest(field=field, value=bad):
                    self.assertTrue(validate('Action', dict(ACTION, **{field: bad})))
                    with self.assertRaises(ValueError):
                        canonical_action(dict(ACTION, **{field: bad}))

    def test_string_bytes_and_evidence_order_are_preserved(self):
        value = dict(ACTION, case_id='தமிழ்-e\u0301')
        raw = canonical_action(value)
        self.assertIn('தமிழ்'.encode(), raw)
        self.assertIn('e\u0301'.encode(), raw)
        self.assertNotEqual(action_digest(value), action_digest(dict(value, case_id='தமிழ்-é')))
        self.assertNotEqual(DIGEST, action_digest(dict(ACTION, evidence_ids=list(reversed(ACTION['evidence_ids'])))))

    def test_nested_payload_digest_conflict(self):
        value = {'operation_key': 'op', 'payload': ACTION, 'action_digest': DIGEST, 'approval_id': 'a'}
        self.assertFalse(validate('ReservationRequest', value))
        value['payload'] = dict(ACTION, amount_minor=1)
        self.assertIn('DIGEST_MISMATCH', {v['code'] for v in validate('ReservationRequest', value)})

    def test_policy_approval_matches_action_binding(self):
        approval = {'approval_id': 'a', 'action_digest': DIGEST, 'case_revision': 1, 'policy_version': 'demo-policy-v1', 'decision': 'APPROVE', 'reviewer_id': 'synthetic-supervisor', 'expires_at': '2026-11-13T13:00:00Z'}
        value = {'payload': ACTION, 'evidence': [], 'approval': approval}
        self.assertFalse(validate('PolicyRequest', value))
        for field, bad in [('action_digest', 'a' * 64), ('case_revision', 2), ('policy_version', 'different')]:
            changed = copy.deepcopy(value)
            changed['approval'][field] = bad
            self.assertTrue(validate('PolicyRequest', changed))

    def test_self_check_includes_negative_parse_compatibility_and_retries(self):
        names = {c['name'] for c in fixture_report()['checks']}
        self.assertIn('invalid-json-float-money', names)
        self.assertIn('compat-optional', names)
        self.assertIn('compat-breaking', names)
        self.assertIn('retries-conflict', names)

    def test_unknown_state_and_version_reject(self):
        self.assertTrue(validate('Case', {'contract_version': 'v2', 'case_id': 'c', 'revision': 1, 'status': 'DONE', 'language': 'en', 'intent': 'x', 'evidence_ids': []}))
        self.assertTrue(validate('ActionRecord', {'action_id': 'a', 'provider_ref': 'p', 'payload': ACTION, 'action_digest': DIGEST, 'status': 'REFUNDED'}))

    def test_proposal_presence_iff_model_proposal(self):
        value = {'outcome': 'NEEDS_INPUT', 'reason_codes': [], 'original_text': 'x', 'language': 'en'}
        self.assertFalse(validate('ModelResult', value))
        self.assertTrue(validate('ModelResult', dict(value, proposal=ACTION)))
        value['outcome'] = 'PROPOSAL'
        self.assertTrue(validate('ModelResult', value))
        self.assertFalse(validate('ModelResult', dict(value, proposal=ACTION)))

    def test_resolved_result_requires_assessment(self):
        value = {'event_key': 'e', 'expected_revision': 1, 'status': 'VERIFIED_RESOLVED', 'evidence_ids': [], 'reason_code': 'VERIFIED'}
        self.assertTrue(validate('CaseResult', value))
        self.assertFalse(validate('CaseResult', dict(value, assessment_id='assessment')))

    def test_strict_json_loader(self):
        for raw in ('{"a":1,"a":2}', '{"a":NaN}', '{"a":Infinity}', '{"a":-Infinity}', '{broken', '"\\ud800"'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                load_json(raw)

    def test_byte_inputs_must_be_utf8(self):
        facts = {'kind': 'CREDIT', 'credit': {'provider_ref': 'r', 'confirmed': True, 'observed_at': '2026-11-13T12:00:00Z'}}
        for encoding in ('utf-16', 'utf-32'):
            raw = json.dumps(facts).encode(encoding)
            with self.subTest(encoding=encoding):
                with self.assertRaises(ValueError):
                    load_json(raw)
                evidence = {'evidence_id': 'e', 'case_id': 'c', 'source': 'simulator', 'subject_ref': 's', 'observed_at': '2026-11-13T12:00:00Z', 'expires_at': '2026-11-13T13:00:00Z', 'digest': hashlib.sha256(raw).hexdigest(), 'verification_status': 'VERIFIED', 'facts': facts}
                self.assertTrue(verify_evidence(evidence, raw))
                result = subprocess.run([sys.executable, '-m', 'sentinel_contract_checks', 'validate', 'Credit', '-'], input=json.dumps(facts['credit']).encode(encoding), capture_output=True)
                self.assertEqual(result.returncode, 1)
                self.assertEqual(json.loads(result.stdout)['violations'][0]['code'], 'INVALID_INPUT')

    def test_evidence_digest_uses_original_bytes(self):
        facts = {'kind': 'CREDIT', 'credit': {'provider_ref': 'r', 'confirmed': True, 'observed_at': '2026-11-13T12:00:00Z'}}
        raw = json.dumps(facts, indent=2).encode()
        evidence = {'evidence_id': 'e', 'case_id': 'c', 'source': 'simulator', 'subject_ref': 's', 'observed_at': '2026-11-13T12:00:00Z', 'expires_at': '2026-11-13T13:00:00Z', 'digest': hashlib.sha256(raw).hexdigest(), 'verification_status': 'VERIFIED', 'facts': facts}
        self.assertFalse(verify_evidence(evidence, raw))
        self.assertTrue(verify_evidence(evidence, json.dumps(facts, separators=(',', ':')).encode()))
        wrong = json.dumps(dict(facts, credit=dict(facts['credit'], confirmed=False))).encode()
        evidence['digest'] = hashlib.sha256(wrong).hexdigest()
        self.assertTrue(verify_evidence(evidence, wrong))

    def test_original_evidence_rejects_bool_integer_confusion(self):
        facts = {'kind': 'CREDIT', 'credit': {'provider_ref': 'r', 'confirmed': True, 'observed_at': '2026-11-13T12:00:00Z'}}
        raw = b'{"kind":"CREDIT","credit":{"provider_ref":"r","confirmed":1,"observed_at":"2026-11-13T12:00:00Z"}}'
        evidence = {'evidence_id': 'e', 'case_id': 'c', 'source': 'simulator', 'subject_ref': 's', 'observed_at': '2026-11-13T12:00:00Z', 'expires_at': '2026-11-13T13:00:00Z', 'digest': hashlib.sha256(raw).hexdigest(), 'verification_status': 'VERIFIED', 'facts': facts}
        self.assertTrue(verify_evidence(evidence, raw))

    def test_bad_timestamps_and_expiry_order(self):
        for stamp in ('2026-11-13T12:00:00+00:00', '2026-02-30T12:00:00Z', 'tomorrow'):
            self.assertTrue(validate('Credit', {'provider_ref': 'r', 'confirmed': True, 'observed_at': stamp}))

    def test_free_form_run_parameters_are_not_typed_records(self):
        for parameters in ({'payload': 'hello', 'action_digest': 'anything'}, {'observed_at': 1, 'expires_at': 2}, {'payload': True, 'approval': 'text'}):
            value = {'contract_version': 'sentinel.task-contracts.v1', 'run_id': 'synthetic-run', 'mode': 'fixture', 'input_artifacts': [], 'parameters': parameters}
            with self.subTest(parameters=parameters):
                self.assertFalse(validate('RunInput', value))

    def test_scoped_retry_conflicts(self):
        records = [{'scope': 'synthetic-tenant/case', 'key': 'op', 'type': 'ReservationRequest', 'value': {'operation_key': 'op', 'payload': ACTION, 'action_digest': DIGEST, 'approval_id': 'a'}}]
        self.assertFalse(check_retries(records * 2))
        changed = copy.deepcopy(records[0])
        changed['value']['approval_id'] = 'different'
        self.assertIn('PAYLOAD_CONFLICT', {v['code'] for v in check_retries(records + [changed])})
        changed['scope'] = 'another-tenant/case'
        self.assertFalse(check_retries(records + [changed]))

    def test_compatible_optional_and_breaking_schema_changes(self):
        before = snapshot()
        added = copy.deepcopy(before)
        added['$defs']['Case']['properties']['display_hint'] = {'type': 'string'}
        self.assertEqual(compare_schemas(before, added)['status'], 'COMPATIBLE_OPTIONAL')
        added['$defs']['Case']['required'].append('display_hint')
        self.assertEqual(compare_schemas(before, added)['status'], 'BREAKING')
        for mutate in (
            lambda s: s['$defs']['RefundAction']['properties'].pop('amount_minor'),
            lambda s: s['$defs']['CaseState']['enum'].append('DONE'),
            lambda s: s['$defs']['RefundAction']['properties']['amount_minor'].update(minimum=2),
            lambda s: s.update(**{'x-contract-version': 'v2'}),
        ):
            changed = copy.deepcopy(before)
            mutate(changed)
            self.assertEqual(compare_schemas(before, changed)['status'], 'BREAKING')
        self.assertEqual(compare_schemas(before, before)['status'], 'IDENTICAL')

    def test_schema_boolean_to_integer_is_breaking(self):
        before = snapshot()
        after = copy.deepcopy(before)
        after['$defs']['Ack']['properties']['accepted']['const'] = 1
        self.assertEqual(compare_schemas(before, after)['status'], 'BREAKING')

    def test_rfc3339_submicrosecond_expiry_preserves_precision(self):
        value = {'assessment_id': 'v', 'case_id': 'c', 'case_revision': 1, 'action_id': 'a', 'assessed_at': '2026-11-13T12:00:00.0000001Z', 'expires_at': '2026-11-13T12:00:00.0000002Z', 'status': 'WAITING', 'evidence': [], 'reason_codes': []}
        self.assertFalse(validate('VerificationResult', value))

    def test_verification_expiry_must_follow_assessment(self):
        value = {'assessment_id': 'v', 'case_id': 'c', 'case_revision': 1, 'action_id': 'a', 'assessed_at': '2026-11-13T12:00:00Z', 'expires_at': '2026-11-13T11:00:00Z', 'status': 'WAITING', 'evidence': [], 'reason_codes': []}
        self.assertTrue(validate('VerificationResult', value))

    def test_compare_rejects_non_snapshot_json(self):
        for bad in (True, False, [], 'schema', {}):
            with self.subTest(bad=bad), self.assertRaises((ValueError, TypeError)):
                compare_schemas(bad, snapshot())

    def test_cli_failures_are_structured_and_nonzero(self):
        for command, content in [
            (['digest', '-'], '{"amount_minor":1.0}'),
            (['validate', 'Credit', '-'], '{"confirmed":true,"confirmed":false}'),
            (['retries', '-'], '[{}]'),
            (['digest', '/does-not-exist'], None),
        ]:
            result = subprocess.run([sys.executable, '-m', 'sentinel_contract_checks', *command], input=content, text=True, capture_output=True)
            self.assertEqual(result.returncode, 1)
            self.assertTrue(json.loads(result.stdout)['violations'])
            self.assertNotIn('Traceback', result.stderr)

    def test_fixtures_cover_each_declared_record(self):
        fixtures = load_json((DATA / 'fixtures.json').read_text())
        covered = {case['type'] for case in fixtures if case['valid']}
        required = {name for name, schema in snapshot()['$defs'].items() if schema.get('type') == 'object'}
        self.assertFalse(required - covered)
        for case in fixtures:
            with self.subTest(case=case['name']):
                self.assertEqual(not validate(case['type'], case['value']), case['valid'])
        report = fixture_report()
        self.assertFalse(validate('RunReport', report))
        self.assertEqual(report['status'], 'PASS')

    def test_cli_compatibility_and_retry_examples(self):
        cases = [
            (['compare', str(DATA / 'compat-before.json'), str(DATA / 'compat-optional.json')], 0, 'COMPATIBLE_OPTIONAL'),
            (['compare', str(DATA / 'compat-before.json'), str(DATA / 'compat-breaking.json')], 1, 'BREAKING'),
            (['retries', str(DATA / 'retries-valid.json')], 0, None),
            (['retries', str(DATA / 'retries-conflict.json')], 1, None),
        ]
        for command, code, status in cases:
            result = subprocess.run([sys.executable, '-m', 'sentinel_contract_checks', *command], capture_output=True, text=True)
            self.assertEqual(result.returncode, code, result.stderr)
            output = json.loads(result.stdout)
            if status:
                self.assertEqual(output['status'], status)

    def test_cli_reports_structured_errors(self):
        result = subprocess.run([sys.executable, '-m', 'sentinel_contract_checks', 'check'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['status'], 'PASS')
        result = subprocess.run([sys.executable, '-m', 'sentinel_contract_checks', 'validate', 'UnknownType', '-'], input='{}', capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stdout)['violations'][0]['code'], 'UNKNOWN_TYPE')


if __name__ == '__main__':
    unittest.main()
