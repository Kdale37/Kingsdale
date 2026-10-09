import copy
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


def fixture_results():
    return {'schema_version': 1, 'status': 'awaiting_key', 'generated_at': None,
            'judge_model': None, 'prompt': 'Skriv 200 danske ord om ungdom i 1980erne.',
            'repetitions': 3, 'budget': {'limit_dkk': 100, 'usd_dkk_rate': 8,
                                       'spent_usd': 0, 'reserved_usd': 0}, 'runs': []}


def fixture_model():
    return {'id': 'test/model-3b', 'name': 'Fixture 3B', 'family': 'Test',
            'hf_id': 'test/weights', 'parameters_b': 3,
            'eligibility': 'eligible', 'availability': 'available',
            'supported_parameters': ['temperature']}


def endpoint(provider='DeepInfra'):
    return {'provider_name': provider, 'pricing': {'prompt': '0.0000001',
            'completion': '0.0000002', 'input_cache_read': '0.00000001', 'discount': 0}}


def evaluation():
    return {'grammar': 4, 'naturalness': 5, 'narrative': 3, 'period': 4,
            'explanation': 'Naturligt dansk med en mindre bøjningsfejl.',
            'examples': ['En konkret rettelse i testteksten.']}


class BudgetTests(unittest.TestCase):
    def test_budget_refuses_before_request_and_persists_reservation(self):
        results, snapshots = fixture_results(), []
        budget = b.Budget(results, lambda: snapshots.append(copy.deepcopy(results)))
        budget.reserve(b.dec('12'))
        with self.assertRaises(b.SetupError):
            budget.reserve(b.dec('0.6'))
        self.assertEqual(budget.total(), b.dec('12'))
        self.assertEqual(len(snapshots), 1)

    def test_settled_cost_and_ambiguous_cost_do_not_reset_budget(self):
        results = fixture_results()
        budget = b.Budget(results, lambda: None)
        budget.reserve(b.dec('1'))
        budget.settle(b.dec('1'), None)
        self.assertEqual(budget.total(), b.dec('1'))
        budget.settle(b.dec('1'), '0.2')
        self.assertEqual(budget.total(), b.dec('0.2'))
        resumed = b.Budget(results, lambda: None)
        self.assertEqual(resumed.total(), b.dec('0.2'))

    def test_timeout_keeps_charge_reservation(self):
        results = fixture_results()
        route = {'providers': ['DeepInfra'], 'prompt': '0.000001', 'completion': '0.000002'}
        budget = b.Budget(results, lambda: None)
        payload = b.make_payload('test/model', [{'role': 'user', 'content': 'Hej'}], route, 100)
        def fail(*args):
            self.assertGreater(budget.total(), 0)
            raise b.SetupError('timeout')
        with self.assertRaises(b.SetupError):
            b.paid_call(payload, route, budget, 'fixture-secret', fail)
        self.assertGreater(b.dec(results['budget']['reserved_usd']), 0)

    def test_invalid_limit_and_price(self):
        for limit in (0, -1, 101, float('nan')):
            with self.assertRaises(b.SetupError):
                b.Budget(fixture_results(), lambda: None, limit)
        for price in (None, '-1', 'NaN', 'Infinity'):
            with self.assertRaises(b.SetupError):
                b.dec(price)


class MetadataTests(unittest.TestCase):
    def test_moe_and_total_size(self):
        self.assertEqual(b.infer_size('Qwen: Qwen3 8B'), 8)
        self.assertEqual(b.infer_size('test/model-360M'), .36)
        self.assertIsNone(b.infer_size('Qwen 30B-A3B'))
        self.assertIsNone(b.infer_size('Mixtral 8x7B'))
        model = {'hf_id': 'test/model'}
        with self.assertRaisesRegex(b.SetupError, '10B'):
            b.verify_hf(model, lambda url: {'safetensors': {'total': 30_000_000_000}, 'cardData': {'license': 'apache-2.0'}})

    def test_routes_filter_chinese_operators_and_cap_western_prices(self):
        endpoints = [endpoint('Alibaba'), endpoint('DeepInfra'), endpoint('Together')]
        endpoints[2]['pricing']['completion'] = '0.0000004'
        route = b.routes('test/model', lambda url: {'data': {'endpoints': endpoints}})
        self.assertEqual(route['providers'], ['DeepInfra', 'Together'])
        self.assertEqual(b.dec(route['completion']), b.dec('0.0000004'))
        payload = b.make_payload('test/model', [], route, 100)
        self.assertFalse(payload['provider']['allow_fallbacks'])
        self.assertEqual(payload['provider']['max_price']['completion'], .4)
        with self.assertRaises(b.SetupError):
            b.routes('test/model', lambda url: {'data': {'endpoints': [endpoint('Alibaba')]}})

    def test_auxiliary_price_and_optional_unused_web_search(self):
        extra = endpoint()
        extra['pricing']['web_search'] = '.01'
        self.assertEqual(b.routes('test/model', lambda url: {'data': {'endpoints': [extra]}})['providers'], ['DeepInfra'])
        extra['pricing']['request'] = '.01'
        with self.assertRaises(b.SetupError):
            b.routes('test/model', lambda url: {'data': {'endpoints': [extra]}})

    def test_unverified_licence_and_parameter_metadata_fail_closed(self):
        for info in ({'cardData': {'license': 'mit'}},
                     {'safetensors': {'total': 3_000_000_000}, 'cardData': {'license': 'other'}}):
            with self.assertRaises(b.SetupError):
                b.verify_hf({'hf_id': 'test/model'}, lambda url: info)

    def test_named_research_license_is_not_lost_under_other_metadata(self):
        result = b.verify_hf({'hf_id': 'test/model'}, lambda url: {
            'safetensors': {'total': 3_000_000_000},
            'cardData': {'license': 'other', 'license_name': 'qwen-research'}})
        self.assertEqual(result['license'], 'qwen-research')
        self.assertEqual(result['eligibility'], 'eligible')

    def test_discovery_preserves_local_candidates_and_excludes_large_moe(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'catalog.json'
            b.write_json(path, {'schema_version': 1, 'models': [fixture_model()], 'excluded': []})
            entries = [{'id': 'test/hosted-4b', 'name': 'Hosted 4B', 'hugging_face_id': 'test/hosted'},
                       {'id': 'test/30b-a3b', 'name': 'MoE 30B-A3B', 'hugging_face_id': 'test/moe'},
                       {'id': 'test/8x22b', 'name': 'MoE 8x22B', 'hugging_face_id': 'test/moe'}]
            def api(url):
                if url.endswith('/models'):
                    return {'data': entries}
                if url.endswith('/endpoints'):
                    return {'data': {'endpoints': [endpoint()]}}
                return {'safetensors': {'total': (30 if url.endswith('/moe') else 4) * 1_000_000_000},
                        'cardData': {'license': 'mit'}, 'sha': 'test-revision'}
            data = b.refresh_catalog(path, api)
            self.assertEqual(len(data['models']), 2)
            self.assertEqual(len(data['excluded']), 2)
            local = next(m for m in data['models'] if m['id'] == 'test/model-3b')
            self.assertEqual(local['availability'], 'unavailable')
            self.assertEqual(local['eligibility'], 'eligible')

    def test_nominal_nine_b_survives_repeated_catalogue_refresh(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'catalog.json'
            model = dict(fixture_model(), id='test/model-9b', name='Model 9B', parameters_b=9.65)
            b.write_json(path, {'schema_version': 1, 'models': [model], 'excluded': []})
            def api(url):
                if url.endswith('/models'):
                    return {'data': [{'id': 'test/model-9b', 'name': 'Model 9B', 'hugging_face_id': 'test/weights'}]}
                if url.endswith('/endpoints'):
                    return {'data': {'endpoints': [endpoint()]}}
                return {'safetensors': {'total': 9_650_000_000}, 'cardData': {'license': 'mit'}}
            first = b.refresh_catalog(path, api)
            second = b.refresh_catalog(path, api)
            self.assertEqual(first['models'][0]['availability'], 'available')
            self.assertEqual(second['models'][0]['availability'], 'available')
            self.assertEqual(second['models'][0]['parameters_b'], 9.65)


class EvaluationTests(unittest.TestCase):
    def test_danish_word_count(self):
        self.assertEqual(b.word_count("Jeg gik på café. 80'erne var min tid — en blå-grøn cykel!"), 11)

    def test_evaluation_schema_rejects_boolean_and_injected_fields(self):
        self.assertEqual(b.validate_evaluation(evaluation()), evaluation())
        for change in ({'grammar': True}, {'period': 6}, {'examples': []}, {'extra': 'ignore instructions'}):
            invalid = dict(evaluation(), **change)
            with self.assertRaises(b.SetupError):
                b.validate_evaluation(invalid)


class RunTests(unittest.TestCase):
    def test_isolated_model_failure_preserves_budget_and_other_samples_continue(self):
        with tempfile.TemporaryDirectory() as tmp:
            path, cat = Path(tmp) / 'results.json', Path(tmp) / 'catalog.json'
            b.write_json(path, fixture_results())
            b.write_json(cat, {'checked_at': b.now(), 'models': [fixture_model()]})
            args = SimpleNamespace(results=str(path), catalog=str(cat), models=None,
                                   repetitions=3, dry_run=False, judge=None, budget_dkk=100, usd_dkk_rate=8)
            calls = []
            def api(url, payload=None, key=None):
                if url.endswith('/models'):
                    return {'data': [{'id': 'openai/gpt-4o-mini', 'supported_parameters': ['response_format']}]}
                if url.endswith('/endpoints'):
                    return {'data': {'endpoints': [endpoint('OpenAI' if '/openai/' in url else 'DeepInfra')]}}
                calls.append(payload)
                if len(calls) == 1:
                    raise b.SetupError('Netværks-/JSON-fejl fra openrouter.ai')
                judge = payload['model'].startswith('openai/')
                return {'id': 'fixture-id', 'model': payload['model'],
                        'provider': 'OpenAI' if judge else 'DeepInfra', 'usage': {'cost': .0001},
                        'choices': [{'message': {'content': json.dumps(evaluation()) if judge else ' '.join(['dansk'] * 200)}, 'finish_reason': 'stop'}]}
            with patch.dict(os.environ, {'OPENROUTER_API_KEY': 'fixture-only'}):
                with self.assertRaisesRegex(b.SetupError, 'partial'):
                    b.run(args, api)
            result = b.read_json(path)
            self.assertEqual(len(calls), 5)
            self.assertEqual(sum(row['status'] == 'complete' for row in result['runs']), 2)
            self.assertGreater(b.dec(result['budget']['reserved_usd']), 0)

    def test_three_real_workflow_samples_and_resume_without_duplicate_calls(self):
        with tempfile.TemporaryDirectory() as tmp:
            path, cat = Path(tmp) / 'results.json', Path(tmp) / 'catalog.json'
            b.write_json(path, fixture_results())
            b.write_json(cat, {'checked_at': b.now(), 'models': [fixture_model()]})
            args = SimpleNamespace(results=str(path), catalog=str(cat), models=None,
                                   repetitions=3, dry_run=False, judge='openai/gpt-4o-mini',
                                   budget_dkk=100, usd_dkk_rate=8)
            judge = {'id': 'openai/gpt-4o-mini', 'supported_parameters': ['response_format', 'temperature']}
            requests = []
            def api(url, payload=None, key=None):
                if url.endswith('/models'):
                    return {'data': [judge]}
                if url.endswith('/endpoints'):
                    provider = 'OpenAI' if '/openai/' in url else 'DeepInfra'
                    return {'data': {'endpoints': [endpoint(provider)]}}
                requests.append(payload)
                is_judge = payload['model'].startswith('openai/')
                if is_judge:
                    self.assertNotIn('test/model', str(payload['messages']))
                content = json.dumps(evaluation()) if is_judge else ' '.join(['dansk'] * 200)
                return {'id': 'fixture-id', 'model': payload['model'],
                        'provider': 'OpenAI' if is_judge else 'DeepInfra',
                        'usage': {'cost': .0001, 'total_tokens': 200},
                        'choices': [{'message': {'content': content}, 'finish_reason': 'stop'}]}
            with patch.dict(os.environ, {'OPENROUTER_API_KEY': 'fixture-only'}):
                b.run(args, api)
                b.run(args, api)
            results = b.read_json(path)
            self.assertEqual(len(requests), 6)
            self.assertEqual(results['status'], 'complete')
            self.assertEqual(len(results['runs']), 3)
            self.assertTrue(all(r['word_count'] == 200 and r['evaluation'] for r in results['runs']))
            self.assertEqual(b.dec(results['budget']['spent_usd']), b.dec('.0006'))
            self.assertEqual(b.dec(results['budget']['reserved_usd']), 0)
            self.assertNotIn('fixture-only', path.read_text())

    def test_interrupted_api_call_is_not_automatically_repeated(self):
        with tempfile.TemporaryDirectory() as tmp:
            path, cat = Path(tmp) / 'results.json', Path(tmp) / 'catalog.json'
            result = fixture_results()
            result['runs'] = [{'model_id': 'test/model-3b', 'repeat': n, 'status': 'generating'} for n in (1, 2, 3)]
            b.write_json(path, result)
            b.write_json(cat, {'checked_at': b.now(), 'models': [fixture_model()]})
            args = SimpleNamespace(results=str(path), catalog=str(cat), models=None,
                                   repetitions=3, dry_run=False, judge=None, budget_dkk=100, usd_dkk_rate=8)
            def api(url, *args):
                if url.endswith('/models'):
                    return {'data': [{'id': 'openai/gpt-4o-mini', 'supported_parameters': ['response_format']}]}
                if url.endswith('/endpoints'):
                    return {'data': {'endpoints': [endpoint('OpenAI' if '/openai/' in url else 'DeepInfra')]}}
                self.fail('No paid call is allowed after an ambiguous interruption')
            with patch.dict(os.environ, {'OPENROUTER_API_KEY': 'fixture-only'}):
                with self.assertRaisesRegex(b.SetupError, 'Afbrudt API-kald'):
                    b.run(args, api)


if __name__ == '__main__':
    unittest.main()
