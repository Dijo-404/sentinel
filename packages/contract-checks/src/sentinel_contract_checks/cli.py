"""Filesystem and standard-stream adapters for the contract-checks.v1 CLI."""
import argparse
import json
from pathlib import Path
import sys

from jsonschema.exceptions import SchemaError

from .checks import (
    action_digest, canonical_action, check_retries, compare_schemas,
    fixture_report, load_json, validate, verify_evidence,
)


def _read(path: str):
    return load_json(sys.stdin.buffer.read() if path == '-' else Path(path).read_bytes())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('check', help='validate bundled synthetic fixtures and canonical vectors')
    val = sub.add_parser('validate', help='validate a named baseline type; - reads stdin')
    val.add_argument('type')
    val.add_argument('file')
    val.add_argument('--evidence-bytes', help='verify original UTF-8 typed facts bytes for Evidence')
    digest = sub.add_parser('digest', help='validate any of the six actions and compute canonical bytes/digest')
    digest.add_argument('file')
    diff = sub.add_parser('compare', help='classify schema snapshot compatibility conservatively')
    diff.add_argument('before')
    diff.add_argument('after')
    replay = sub.add_parser('retries', help='check a synthetic scoped request capture for payload conflicts')
    replay.add_argument('file')
    args = parser.parse_args(argv)
    try:
        if args.command == 'check':
            output = fixture_report()
            success = output['status'] == 'PASS'
        elif args.command == 'digest':
            value = _read(args.file)
            output = {'canonical_utf8': canonical_action(value).decode(), 'sha256': action_digest(value)}
            success = True
        elif args.command == 'compare':
            output = compare_schemas(_read(args.before), _read(args.after))
            success = output['status'] != 'BREAKING'
        else:
            value = _read(args.file)
            if args.command == 'retries':
                violations = check_retries(value)
            elif args.evidence_bytes:
                if args.type != 'Evidence':
                    raise ValueError('--evidence-bytes requires Evidence')
                violations = verify_evidence(value, Path(args.evidence_bytes).read_bytes())
            else:
                violations = validate(args.type, value)
            output = {'valid': not violations, 'violations': violations}
            success = not violations
    except (ValueError, UnicodeError, OSError, SchemaError, RecursionError):
        output = {'valid': False, 'violations': [{'path': '$', 'code': 'INVALID_INPUT',
                   'message': 'Unreadable or invalid input; no fixture fallback was used'}]}
        success = False
    print(json.dumps(output, ensure_ascii=False, allow_nan=False))
    return 0 if success else 1
