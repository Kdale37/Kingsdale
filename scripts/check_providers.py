"""Read-only service checks and public HF routing/price snapshot. Never prints keys."""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import benchmark as b


def main():
    if not os.environ.get('HF_TOKEN'):
        raise b.SetupError('HF_TOKEN is missing from repository secrets')
    catalog = b.read_json(b.ROOT / 'data/catalog.json')
    identities = {m['hf_id'] for m in catalog['models'] if m.get('hf_id')}
    models = b.request_json('https://router.huggingface.co/v1/models', key=os.environ['HF_TOKEN'])
    rows = models.get('data')
    if not isinstance(rows, list) or not rows:
        raise b.SetupError('Hugging Face returned no model catalogue')
    selected = [m for m in rows if m.get('id', '').split(':')[0] in identities]
    if not selected:
        raise b.SetupError('No candidate weight identities matched the HF router catalogue')
    snapshot = {'schema_version': 1, 'checked_at': b.now(), 'source': 'https://router.huggingface.co/v1/models',
                'judge_access': None, 'models': selected}
    b.write_json(b.ROOT / 'data/hf-pricing-snapshot.json', snapshot)
    if not os.environ.get('OPENAI_API_KEY'):
        raise b.SetupError('OPENAI_API_KEY is missing from repository secrets')
    judge = b.request_json('https://api.openai.com/v1/models/gpt-5-mini', key=os.environ['OPENAI_API_KEY'])
    if judge.get('id') != 'gpt-5-mini':
        raise b.SetupError('GPT-5 mini model access could not be verified')
    snapshot['judge_access'] = 'gpt-5-mini'
    b.write_json(b.ROOT / 'data/hf-pricing-snapshot.json', snapshot)
    b.write_json(b.ROOT / 'data/provider-preflight.json', {'status': 'passed', 'checked_at': b.now(),
                 'hf_catalog_entries': len(selected), 'judge_access': 'gpt-5-mini', 'paid_calls': 0})
    print(f'Both service keys accepted for read-only checks; {len(selected)} candidate catalogue entries saved. No paid calls.')


if __name__ == '__main__':
    try:
        main()
    except b.SetupError as exc:
        b.write_json(b.ROOT / 'data/provider-preflight.json', {'status': 'blocked', 'checked_at': b.now(),
                     'error': str(exc), 'paid_calls': 0})
        sys.exit(str(exc))
