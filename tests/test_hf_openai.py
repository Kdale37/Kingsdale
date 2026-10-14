import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import benchmark as b
import hf_openai as hf


def entry(identity='test/model-3B'):
    return {'id': identity, 'providers': [
        {'provider': 'deepinfra', 'status': 'live', 'pricing': {'input': .1, 'output': .2}},
        {'provider': 'featherless-ai', 'status': 'live'}]}


class ProviderTests(unittest.TestCase):
    def test_qwen_uses_verified_alternate_route_without_fallback(self):
        model = entry('Qwen/Qwen3.5-9B')
        with self.assertRaises(b.SetupError):
            hf.quote(model)
        model['providers'].append({'provider': 'together', 'status': 'live',
                                   'pricing': {'input': .17, 'output': .25}})
        self.assertEqual(hf.quote(model)['model'], 'Qwen/Qwen3.5-9B:together')
        model['providers'][-1]['status'] = 'offline'
        with self.assertRaises(b.SetupError):
            hf.quote(model)

    def test_generation_only_checks_hf_without_spending_on_a_missing_judge(self):
        with tempfile.TemporaryDirectory() as tmp:
            cat, results = Path(tmp) / 'catalog.json', Path(tmp) / 'results.json'
            b.write_json(cat, {'checked_at': b.now(), 'models': [
                {'id': 'model', 'availability': 'available', 'eligibility': 'eligible', 'route': hf.quote(entry())}]})
            b.write_json(results, {'repetitions': 3, 'prompt': 'Skriv 200 ord på dansk.',
                                 'judge_model': None, 'runs': [], 'budget': {'spent_usd': 0, 'reserved_usd': 0}})
            args = SimpleNamespace(catalog=str(cat), results=str(results), models=None, backend='huggingface',
                                   budget_dkk=100, usd_dkk_rate=8, repetitions=3, dry_run=False,
                                   judge=None, generation_only=True)
            calls = []
            def api(url, payload=None, key=None):
                self.assertEqual(url, hf.HF_CHAT)
                calls.append(payload)
                return {'usage': {'prompt_tokens': 100, 'completion_tokens': 200},
                        'choices': [{'finish_reason': 'stop', 'message': {'content': ' '.join(['dansk'] * 200)}}]}
            with patch.dict(os.environ, {'HF_TOKEN': 'fixture-only'}):
                b.run(args, api)
            value = b.read_json(results)
            self.assertEqual(len(calls), 3)
            self.assertEqual(value['status'], 'awaiting_judge')
            self.assertTrue(all(row['status'] == 'generated' and row.get('evaluation') is None for row in value['runs']))
            self.assertGreater(b.dec(value['budget']['spent_usd']), 0)

    def test_quotes_convert_million_token_rates_and_refuse_missing_prices(self):
        route = hf.quote(entry())
        self.assertEqual(b.dec(route['prompt']), b.dec('.0000001'))
        self.assertEqual(route['model'], 'test/model-3B:deepinfra')
        self.assertEqual(route['providers'], ['deepinfra'])
        with self.assertRaises(b.SetupError):
            hf.quote({'id': 'test/model', 'providers': [{'provider': 'featherless-ai', 'status': 'live'}]})
        with self.assertRaises(b.SetupError):
            hf.quote({'id': 'test/model', 'providers': [{'provider': 'z-ai', 'status': 'live', 'pricing': {'input': .1, 'output': .1}}]})

    def test_openai_uses_direct_compatible_parameters_and_reasoning_token_budget(self):
        payload = hf.judge_payload([{'role': 'user', 'content': 'Hej'}])
        self.assertEqual(payload['model'], 'gpt-5-mini')
        self.assertEqual(payload['max_completion_tokens'], 2048)
        self.assertEqual(payload['reasoning_effort'], 'minimal')
        self.assertNotIn('temperature', payload)
        self.assertNotIn('max_tokens', payload)
        self.assertGreater(b.price_bound(payload, hf.JUDGE_ROUTE), 0)
        self.assertEqual(b.dec(hf.cost_from_tokens({'prompt_tokens': 100, 'completion_tokens': 50}, hf.JUDGE_ROUTE)), b.dec('.000125'))
        self.assertIsNone(hf.cost_from_tokens({'prompt_tokens': True, 'completion_tokens': 50}, hf.JUDGE_ROUTE))

    def test_stale_hf_prices_are_rejected_before_calls(self):
        route = hf.quote(entry())
        route['checked_at'] = '2020-01-01T00:00:00+00:00'
        with self.assertRaises(b.SetupError):
            hf.generation_payload({}, [], route)

    def test_canonical_aliases_are_deduplicated_and_unpriced_routes_stay_visible(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'catalog.json'
            b.write_json(path, {'models': [{'id': 'old-id', 'hf_id': 'test/old-model-3B'},
                                           {'id': 'unpriced', 'hf_id': 'test/unpriced-3B'}], 'sources': []})
            def api(url, **kwargs):
                if url == hf.HF_MODELS:
                    return {'data': [entry('test/model-3B')]}
                identity = 'test/unpriced-3B' if 'unpriced' in url else 'test/model-3B'
                return {'id': identity, 'safetensors': {'total': 3_000_000_000},
                        'cardData': {'license': 'mit'}, 'sha': 'revision',
                        'inferenceProviderMapping': {'featherless-ai': {'status': 'live', 'task': 'conversational'}}}
            result = hf.refresh(path, api)
            self.assertEqual(len(result['models']), 2)
            self.assertEqual(result['models'][0]['id'], 'old-id')
            self.assertEqual(result['models'][0]['availability'], 'available')
            self.assertEqual(result['models'][1]['availability'], 'unpriced')

    def test_direct_hf_and_openai_complete_three_samples_with_separate_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            cat, results = Path(tmp) / 'catalog.json', Path(tmp) / 'results.json'
            b.write_json(cat, {'schema_version': 1, 'checked_at': b.now(), 'models': [
                {'id': 'model', 'hf_id': 'test/model-3B', 'availability': 'available',
                 'eligibility': 'eligible', 'route': hf.quote(entry())}]})
            b.write_json(results, {'schema_version': 1, 'repetitions': 3, 'prompt': 'Skriv 200 ord på dansk.',
                                 'judge_model': None, 'runs': [], 'budget': {'spent_usd': 0, 'reserved_usd': 0}})
            args = SimpleNamespace(catalog=str(cat), results=str(results), models=None,
                                   backend='huggingface', budget_dkk=100, usd_dkk_rate=8,
                                   repetitions=3, dry_run=False, judge=None)
            calls = []
            def api(url, payload=None, key=None):
                calls.append((url, payload))
                judging = url == hf.OPENAI_CHAT
                self.assertEqual(key, 'judge-fixture' if judging else 'generation-fixture')
                self.assertNotIn('provider', payload)
                if judging:
                    self.assertNotIn('test/model', str(payload['messages']))
                    self.assertEqual(payload['response_format']['type'], 'json_schema')
                    schema = payload['response_format']['json_schema']
                    self.assertTrue(schema['strict'])
                    self.assertEqual(schema['schema']['properties']['examples']['items']['type'], 'string')
                evaluation = {'grammar': 4, 'naturalness': 4, 'narrative': 3, 'period': 4,
                              'explanation': 'Klar dansk tekst.', 'examples': ['En konkret kommentar.']}
                return {'model': payload['model'], 'id': 'fixture-id',
                        'usage': {'prompt_tokens': 100, 'completion_tokens': 100, 'total_tokens': 200},
                        'choices': [{'finish_reason': 'stop', 'message': {
                            'content': json.dumps(evaluation) if judging else ' '.join(['dansk'] * 200)}}]}
            with patch.dict(os.environ, {'HF_TOKEN': 'generation-fixture', 'OPENAI_API_KEY': 'judge-fixture'}):
                b.run(args, api)
                b.run(args, api)
            value = b.read_json(results)
            self.assertEqual(len(calls), 6)
            self.assertEqual(value['status'], 'complete')
            self.assertEqual(value['judge_model'], 'gpt-5-mini')
            for row in value['runs']:
                self.assertEqual(json.loads(row['judge_response']), row['evaluation'])
            self.assertEqual(value['budget']['cost_basis'], 'quoted_token_upper_bound')
            self.assertEqual(b.dec(value['budget']['reserved_usd']), 0)
            self.assertNotIn('judge-fixture', results.read_text())
            self.assertNotIn('generation-fixture', results.read_text())

    def test_retry_judge_after_quota_fix_reuses_story_and_retains_cost_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            cat, results = Path(tmp) / 'catalog.json', Path(tmp) / 'results.json'
            b.write_json(cat, {'checked_at': b.now(), 'models': [
                {'id': 'model', 'availability': 'available', 'eligibility': 'eligible', 'route': hf.quote(entry())}]})
            b.write_json(results, {'repetitions': 3, 'prompt': 'Skriv 200 danske ord.',
                                 'judge_model': None, 'runs': [], 'budget': {'spent_usd': 0, 'reserved_usd': 0}})
            args = SimpleNamespace(catalog=str(cat), results=str(results), models=None, backend='huggingface',
                                   budget_dkk=100, usd_dkk_rate=8, repetitions=3, dry_run=False, judge=None)
            generations, judges = [], []
            def api(url, payload=None, key=None):
                judging = url == hf.OPENAI_CHAT
                (judges if judging else generations).append(payload)
                if judging and len(judges) == 1:
                    raise b.SetupError('HTTP 429 fra api.openai.com')
                evaluation = {'grammar': 4, 'naturalness': 4, 'narrative': 3, 'period': 4,
                              'explanation': 'Klar tekst.', 'examples': ['Konkret kommentar.']}
                return {'usage': {'prompt_tokens': 100, 'completion_tokens': 100},
                        'choices': [{'finish_reason': 'stop', 'message': {
                            'content': json.dumps(evaluation) if judging else ' '.join(['dansk'] * 200)}}]}
            with patch.dict(os.environ, {'HF_TOKEN': 'fixture', 'OPENAI_API_KEY': 'fixture'}):
                with self.assertRaises(b.SetupError):
                    b.run(args, api)
                reservation = b.dec(b.read_json(results)['budget']['reserved_usd'])
                self.assertEqual(len(generations), 1)
                args.retry_failed = True
                b.run(args, api)
            value = b.read_json(results)
            self.assertEqual(len(generations), 3)
            self.assertEqual(len(judges), 4)
            self.assertEqual(b.dec(value['budget']['reserved_usd']), reservation)
            failed = next(row for row in value['runs'] if row.get('attempt_history'))
            self.assertEqual(failed['attempt_history'][0]['status'], 'judge_failed')
            self.assertEqual(value['status'], 'complete')


if __name__ == '__main__':
    unittest.main()
