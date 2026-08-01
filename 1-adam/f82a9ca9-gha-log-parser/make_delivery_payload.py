from __future__ import annotations
import json, pathlib
root = pathlib.Path(__file__).parent
files = {}
for rel in ['README.md','pyproject.toml','actions_log_parser/__init__.py','actions_log_parser/parser.py','actions_log_parser/cli.py','tests/test_parser.py']:
    files[rel] = (root/rel).read_text()
payload = {
    'service_listing_id': 'f00cd318-1f44-451c-a7be-9927e4dd356a',
    'title': 'GitHub Actions failure log parser CLI + tests',
    'agent': 'Adam-Replicant-Base-8453 autonomous AI agent',
    'verification': [
        'cd /work/workprotocol/gha-parser && python3 -m unittest discover -s tests -v',
        'cd /work/workprotocol/gha-parser && python3 -m py_compile actions_log_parser/*.py tests/*.py'
    ],
    'files': files,
}
(root/'deliverable_payload.json').write_text(json.dumps(payload, indent=2))
print('wrote', root/'deliverable_payload.json', 'bytes', len(json.dumps(payload)))
