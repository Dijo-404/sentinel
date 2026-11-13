"""Deterministic validation of the pinned baseline's JSON values and bytes."""
from datetime import datetime
from hashlib import sha256
from importlib.resources import files
import json
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

VERSION = 'sentinel.task-contracts.v1'
BASELINE_HASH = '0c728513e8b4ec0f34bcef63faa0207160d45cc7f20f872c1d9136ca7e252ffa'
Violation = dict[str, str]
_FORMATS = FormatChecker()


@_FORMATS.checks('date-time', raises=ValueError)
def _utc_timestamp(value: Any) -> bool:
    if not isinstance(value, str):
        return True
    return value.endswith('Z') and datetime.fromisoformat(value[:-1] + '+00:00') is not None


def _data(name: str) -> bytes:
    return files('sentinel_contract_checks').joinpath('data', name).read_bytes()


def _json_values(value: Any, path: str = '$') -> None:
    """All baseline numbers are integers; booleans remain a separate JSON type."""
    if type(value) in (bool, int) or value is None:
        return
    if isinstance(value, str):
        value.encode('utf-8')  # Lone surrogates are not UTF-8 wire strings.
    elif type(value) is list:
        for index, item in enumerate(value):
            _json_values(item, f'{path}/{index}')
    elif type(value) is dict:
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError(f'{path}: object keys must be strings')
            key.encode('utf-8')
            _json_values(item, f'{path}/{key}')
    else:
        raise ValueError(f'{path}: expected a JSON value with integer numbers')


def load_json(raw: str | bytes) -> Any:
    """Parse without duplicate keys, NaN, Infinity, floats or surrogate strings."""
    def object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate JSON object key')
            result[key] = value
        return result

    def invalid_number(_: str) -> None:
        raise ValueError('Only integer JSON numbers are supported')

    if isinstance(raw, bytes):
        raw = raw.decode('utf-8')
    value = json.loads(raw, object_pairs_hook=object_pairs,
                       parse_constant=invalid_number, parse_float=invalid_number)
    _json_values(value)
    return value


def snapshot() -> dict[str, Any]:
    return load_json(_data('schemas.json'))


_SCHEMA = snapshot()
Draft202012Validator.check_schema(_SCHEMA)


def _timestamp_order(value: str) -> tuple[str, str]:
    # Schema already validated UTC calendar values; preserve arbitrary fractional precision.
    fraction = value[20:-1].rstrip('0') if value[19:20] == '.' else ''
    return value[:19], fraction


def _violation(path: str, code: str, message: str) -> Violation:
    return {'path': path, 'code': code, 'message': message}


def _serialize(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False).encode('utf-8')


def validate(type_name: str, value: Any) -> list[Violation]:
    """Check shape and embedded consistency; no identity/freshness authority is inferred."""
    if type_name not in _SCHEMA['$defs']:
        return [_violation('$', 'UNKNOWN_TYPE', 'Unknown baseline wire type')]
    try:
        _json_values(value)
    except (ValueError, UnicodeError):
        return [_violation('$', 'INVALID_JSON_VALUE', 'Expected UTF-8 JSON with integer numbers')]
    schema = {'$ref': f'#/$defs/{type_name}', '$defs': _SCHEMA['$defs']}
    validator = Draft202012Validator(schema, format_checker=_FORMATS)
    errors = list(validator.iter_errors(value))
    if errors:
        # Do not echo untrusted values: provider payloads and identifiers may be private.
        return [_violation('$' + ''.join(f'/{p}' for p in e.absolute_path),
                           'SCHEMA_VIOLATION', f'Failed {e.validator} constraint')
                for e in errors]
    violations: list[Violation] = []

    def consistency(node: Any, path: str) -> None:
        if type_name == 'RunInput' and path == '$/parameters':
            return  # Extensible scalar map keys do not identify typed records.
        if isinstance(node, list):
            for index, child in enumerate(node):
                consistency(child, f'{path}/{index}')
        elif isinstance(node, dict):
            if 'payload' in node and ('action_digest' in node or 'approval' in node):
                expected = sha256(_serialize(node['payload'])).hexdigest()
                if 'action_digest' in node and node['action_digest'] != expected:
                    violations.append(_violation(path + '/action_digest', 'DIGEST_MISMATCH', 'Digest differs from exact action payload'))
                approval = node.get('approval')
                if approval and any(approval[k] != v for k, v in (
                    ('action_digest', expected),
                    ('case_revision', node['payload']['case_revision']),
                    ('policy_version', node['payload']['policy_version']),
                )):
                    violations.append(_violation(path + '/approval', 'APPROVAL_MISMATCH', 'Approval differs from bound action'))
            observed = node.get('observed_at', node.get('assessed_at'))
            if observed and 'expires_at' in node:
                if _timestamp_order(node['expires_at']) <= _timestamp_order(observed):
                    violations.append(_violation(path + '/expires_at', 'INVALID_EXPIRY', 'Expiry must follow observation'))
            for key, child in node.items():
                consistency(child, f'{path}/{key}')

    consistency(value, '$')
    return violations


def canonical_action(payload: Any) -> bytes:
    violations = validate('Action', payload)
    if violations:
        raise ValueError('Invalid action: ' + violations[0]['code'])
    return _serialize(payload)


def action_digest(payload: Any) -> str:
    return sha256(canonical_action(payload)).hexdigest()


def verify_evidence(evidence: Any, original_payload: bytes) -> list[Violation]:
    """The supplied original payload is the exact serialized typed facts object."""
    violations = validate('Evidence', evidence)
    if violations:
        return violations
    if sha256(original_payload).hexdigest() != evidence['digest']:
        return [_violation('$/digest', 'EVIDENCE_DIGEST_MISMATCH', 'Original byte digest differs')]
    try:
        facts = load_json(original_payload)
    except (ValueError, UnicodeError):
        return [_violation('$/facts', 'INVALID_EVIDENCE_BYTES', 'Original payload is invalid JSON')]
    if _serialize(facts) != _serialize(evidence['facts']):
        return [_violation('$/facts', 'EVIDENCE_FACTS_MISMATCH', 'Original payload differs from typed facts')]
    return []


def check_retries(records: Any) -> list[Violation]:
    """Compare a local captured retry sequence; this is not an idempotency store.

    `scope` is an explicit synthetic capture label, never authenticated identity.
    Records describe retries of the same endpoint/resource within that label.
    """
    if not isinstance(records, list):
        return [_violation('$', 'INVALID_RETRY_CAPTURE', 'Expected an array of captured requests')]
    seen: dict[tuple[str, str, str], bytes] = {}
    violations = []
    for index, record in enumerate(records):
        path = f'$/{index}'
        if (not isinstance(record, dict) or set(record) != {'scope', 'key', 'type', 'value'}
                or any(not isinstance(record[k], str) or not record[k] for k in ('scope', 'key', 'type'))):
            violations.append(_violation(path, 'INVALID_RETRY_CAPTURE', 'Expected scope, key, type and value'))
            continue
        errors = validate(record['type'], record['value'])
        if errors:
            violations.extend(dict(v, path=path + v['path'][1:]) for v in errors)
            continue
        key = (record['scope'], record['type'], record['key'])
        payload = _serialize(record['value'])
        if key in seen and seen[key] != payload:
            violations.append(_violation(path, 'PAYLOAD_CONFLICT', 'Same scoped key has different payload; peer must reject with 409'))
        seen[key] = payload
    return violations


def compare_schemas(before: dict, after: dict) -> dict:
    """Conservative reader/writer compatibility; financial action fields stay exact.

    Only new optional properties on nonfinancial records and new type definitions
    are accepted. Every other semantic change requires a versioned review.
    """
    changes = []
    financial = {'Action', 'ActionBase', 'RefundAction', 'StatusAction', 'DisputeAction',
                 'RecheckAction', 'SyncAction', 'EscalateAction', 'RefundRequest',
                 'ReservationRequest', 'ProposalRequest', 'Command', 'ActionRecord',
                 'Approval', 'DecisionRequest'}

    def difference(old: Any, new: Any, path: list[str]) -> None:
        if _serialize(old) == _serialize(new):
            return
        if isinstance(old, dict) and isinstance(new, dict):
            for key in sorted(old.keys() | new.keys()):
                at = path + [key]
                if key not in new:
                    changes.append({'path': '/'.join(at), 'kind': 'BREAKING'})
                elif key not in old:
                    definition = path[1] if len(path) >= 2 and path[0] == '$defs' else None
                    optional = (len(path) == 3 and path[2] == 'properties'
                                and definition not in financial
                                and key not in after['$defs'][definition].get('required', []))
                    kind = 'COMPATIBLE_OPTIONAL' if optional or path == ['$defs'] else 'BREAKING'
                    changes.append({'path': '/'.join(at), 'kind': kind})
                else:
                    difference(old[key], new[key], at)
        else:
            changes.append({'path': '/'.join(path), 'kind': 'BREAKING'})

    for schema in (before, after):
        if not isinstance(schema, dict) or not isinstance(schema.get('$defs'), dict):
            raise ValueError('Expected a snapshot with $defs')
        Draft202012Validator.check_schema(schema)
    difference(before, after, [])
    status = ('BREAKING' if any(c['kind'] == 'BREAKING' for c in changes)
              else 'COMPATIBLE_OPTIONAL' if changes else 'IDENTICAL')
    return {'status': status, 'changes': changes}


def fixture_report() -> dict:
    checks = []
    fixtures = load_json(_data('fixtures.json'))
    for fixture in fixtures:
        result = not validate(fixture['type'], fixture['value'])
        passed = result == fixture['valid']
        checks.append({'name': fixture['name'], 'status': 'PASS' if passed else 'FAIL',
                       'reason_code': 'EXPECTED_RESULT' if passed else 'UNEXPECTED_RESULT'})
    for vector in load_json(_data('canonical-vectors.json')):
        passed = (canonical_action(vector['payload']) == vector['canonical_utf8'].encode()
                  and action_digest(vector['payload']) == vector['sha256'])
        checks.append({'name': vector['name'], 'status': 'PASS' if passed else 'FAIL',
                       'reason_code': 'CANONICAL_MATCH' if passed else 'CANONICAL_MISMATCH'})
    for fixture in load_json(_data('invalid-json.json')):
        try:
            load_json(fixture['raw'])
            passed = False
        except (ValueError, UnicodeError):
            passed = True
        checks.append({'name': 'invalid-json-' + fixture['name'], 'status': 'PASS' if passed else 'FAIL', 'reason_code': 'STRICT_JSON'})
    for name, expected in (('compat-optional', 'COMPATIBLE_OPTIONAL'), ('compat-breaking', 'BREAKING')):
        result = compare_schemas(load_json(_data('compat-before.json')), load_json(_data(name + '.json')))
        passed = result['status'] == expected
        checks.append({'name': name, 'status': 'PASS' if passed else 'FAIL', 'reason_code': 'COMPATIBILITY'})
    for name, expected in (('retries-valid', False), ('retries-conflict', True)):
        passed = bool(check_retries(load_json(_data(name + '.json')))) == expected
        checks.append({'name': name, 'status': 'PASS' if passed else 'FAIL', 'reason_code': 'RETRY_CAPTURE'})
    passed = sha256(_data('baseline.md')).hexdigest() == BASELINE_HASH
    checks.append({'name': 'pinned-baseline', 'status': 'PASS' if passed else 'FAIL', 'reason_code': 'BASELINE_HASH'})
    return {'contract_version': VERSION, 'run_id': 'contract-checks-self-test', 'mode': 'fixture',
            'status': 'PASS' if all(c['status'] == 'PASS' for c in checks) else 'FAIL',
            'checks': checks, 'output_artifacts': []}
