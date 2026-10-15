"""Hugging Face generation and OpenAI judging, with verified token-price bounds."""
import datetime as dt
import os
import urllib.parse

import benchmark as b

HF_MODELS = 'https://router.huggingface.co/v1/models'
HF_CHAT = 'https://router.huggingface.co/v1/chat/completions'
OPENAI_CHAT = 'https://api.openai.com/v1/chat/completions'
FEATHERLESS_MODELS = 'https://api.featherless.ai/v1/models/'
HF_PROVIDERS = {'featherless-ai', 'nscale', 'deepinfra', 'together', 'fireworks-ai',
                'groq', 'cerebras', 'novita', 'hf-inference', 'scaleway', 'ovhcloud',
                'publicai', 'nebius', 'sambanova', 'friendli'}
# Avoid the Qwen route with three unresolved HTTP 504s; no paid fallback/retry.
HF_PROVIDER_OVERRIDES = {'Qwen/Qwen3.5-9B': 'together'}
# Published GPT-5 mini standard rates: USD per token, cached-input discounts ignored.
JUDGE_ROUTE = {'service': 'openai', 'api_url': OPENAI_CHAT, 'model': 'gpt-5-mini',
               'providers': ['OpenAI'], 'prompt': '0.00000025', 'completion': '0.000002',
               'source_url': 'https://developers.openai.com/api/docs/models/gpt-5-mini',
               'price_basis': 'published_standard_token_rates'}


def quote(entry):
    candidates = []
    for provider in entry.get('providers', []):
        preferred = HF_PROVIDER_OVERRIDES.get(entry['id'])
        if preferred and provider.get('provider') != preferred:
            continue
        if provider.get('status') != 'live' or provider.get('provider') not in HF_PROVIDERS:
            continue
        pricing = provider.get('pricing', {})
        try:
            prompt = b.dec(pricing.get('input')) / 1_000_000
            completion = b.dec(pricing.get('output')) / 1_000_000
            if any(b.dec(v) for k, v in pricing.items() if k not in ('input', 'output') and v is not None):
                continue
        except b.SetupError:
            continue
        candidates.append({'service': 'huggingface', 'api_url': HF_CHAT,
                           'model': entry['id'] + ':' + provider['provider'],
                           'providers': [provider['provider']], 'prompt': str(prompt),
                           'completion': str(completion), 'checked_at': b.now(),
                           'source_url': HF_MODELS, 'price_basis': 'USD_per_million_tokens'})
    if not candidates:
        raise b.SetupError('Aktiv rute mangler verificerbar tokenpris; ikke kørt inden for budgettet')
    return min(candidates, key=lambda row: b.dec(row['prompt']) + b.dec(row['completion']))


def featherless_quote(identity, api=b.request_json):
    # Public read only: never forward HF/OpenAI credentials to this host.
    url = FEATHERLESS_MODELS + urllib.parse.quote(identity, safe='/')
    detail = api(url)
    if detail.get('id') != identity or detail.get('status') != 'active':
        raise b.SetupError('Featherless-modelidentitet eller aktiv status er ikke verificeret')
    pricing = detail.get('pricing', {})
    prompt, completion = b.dec(pricing.get('prompt')), b.dec(pricing.get('completion'))
    for key, value in pricing.items():
        if key in ('prompt', 'completion', 'input', 'output'):
            continue
        if b.dec(value) != 0:
            raise b.SetupError('Featherless har ekstra prisfelter uden et verificeret loft')
    rates = []
    for key, rate in (('input', prompt), ('output', completion)):
        display = b.dec(pricing[key]) / 1_000_000 if key in pricing else rate
        high, low = max(display, rate), min(display, rate)
        # The per-million display may be rounded; always reserve the higher quote.
        if high and (not low or high > low * b.dec('1.01')):
            raise b.SetupError('Featherless-prisens enheder er inkonsistente')
        rates.append(high)
    prompt, completion = rates
    return {'service': 'huggingface', 'api_url': HF_CHAT,
            'model': identity + ':featherless-ai', 'providers': ['featherless-ai'],
            'prompt': str(prompt), 'completion': str(completion), 'checked_at': b.now(),
            'source_url': url, 'price_basis': 'provider_published_USD_per_token',
            'provider_pricing': pricing,
            'billing_source_url': 'https://huggingface.co/docs/inference-providers/pricing'}


def refresh(path, api=b.request_json, snapshot=None):
    catalog = b.read_json(path)
    if snapshot is None:
        rows = api(HF_MODELS, key=os.environ.get('HF_TOKEN')).get('data', [])
        source_time = b.now()
    else:
        fresh({'checked_at': snapshot['checked_at']})
        rows = snapshot['models']
        source_time = snapshot['checked_at']
    if not isinstance(rows, list) or not rows:
        raise b.SetupError('Hugging Face returnerede intet model-/priskatalog')
    current = {row['id']: row for row in rows}
    models = catalog['models']
    identities = {m.get('hf_id') for m in models}
    for identity, entry in current.items():
        nominal = b.infer_size(identity)
        if identity not in identities and nominal and nominal <= 9:
            models.append({'id': 'hf:' + identity, 'hf_id': identity, 'name': identity.split('/')[-1],
                           'family': identity.split('/')[0], 'parameters_b': nominal,
                           'eligibility': 'candidate', 'license_status': 'unverified'})
    seen, retained = set(), []
    for model in models:
        model.pop('route', None)
        model.pop('reason', None)
        model['availability'] = 'unavailable'
        identity = model.get('hf_id')
        if not identity:
            retained.append(model)
            continue
        try:
            info = api('https://huggingface.co/api/models/' + urllib.parse.quote(identity, safe='/')
                       + '?expand[]=inferenceProviderMapping&expand[]=safetensors&expand[]=cardData&expand[]=sha&expand[]=gated&expand[]=private')
            # Canonical names change (e.g. Meta-Llama -> Llama); keep public sample IDs stable.
            canonical = info.get('id', identity)
            if canonical in seen:
                continue
            seen.add(canonical)
            model['hf_id'] = canonical
            model['source_url'] = 'https://huggingface.co/' + canonical
            b.verify_hf(model, lambda url: info)
            live = {provider: detail for provider, detail in info.get('inferenceProviderMapping', {}).items()
                    if detail.get('status') == 'live' and detail.get('task') == 'conversational'
                    and provider in HF_PROVIDERS}
            entry = current.get(canonical) or current.get(identity)
            if not entry and not live:
                model['reason'] = 'Ingen aktiv conversational-rute hos de valgte Hugging Face-udbydere'
                retained.append(model)
                continue
            try:
                try:
                    model['route'] = quote(entry or {'id': canonical})
                    model['route']['checked_at'] = source_time
                except b.SetupError:
                    if 'featherless-ai' not in live or canonical in HF_PROVIDER_OVERRIDES:
                        raise
                    model['route'] = featherless_quote(canonical, api)
                model['availability'] = 'available'
            except b.SetupError as exc:
                model['availability'] = 'unpriced'
                model['reason'] = str(exc)
                model['live_providers'] = sorted(live)
        except b.SetupError as exc:
            model['reason'] = str(exc)
            # Never retain an old verification if the current check fails.
            model['eligibility'] = 'excluded' if (model.get('parameters_b') or 0) > 10 else 'candidate'
        retained.append(model)
    models = retained
    catalog.update(models=models, checked_at=b.now(), status='checked', service='huggingface',
                   max_parameters_b=10, max_nominal_parameters_b=9,
                   scope='Hugging Face: officielle små modeller og aktuelle routermodeller. Aktiv adgang og verificerbar pris vises separat.')
    sources = catalog.setdefault('sources', [])
    if not any(source.get('url') == HF_MODELS for source in sources):
        sources.append({'name': 'Hugging Face router: aktive udbydere og priser', 'url': HF_MODELS})
    for name, url in (
        ('Featherless: offentlige modelspecifikke tokenpriser', 'https://featherless.ai/docs/api-reference-models'),
        ('Hugging Face: viderefakturering af udbyderpriser', 'https://huggingface.co/docs/inference-providers/pricing')):
        if not any(source.get('url') == url for source in sources):
            sources.append({'name': name, 'url': url})
    b.write_json(path, catalog)
    print(f'Hugging Face: {sum(m["availability"] == "available" for m in models)} prisverificerede modeller; '
          f'{sum(m["availability"] == "unpriced" for m in models)} aktive ruter uden verificeret pris')
    return catalog


def fresh(route):
    try:
        checked = dt.datetime.fromisoformat(route['checked_at'])
        age = dt.datetime.now(dt.timezone.utc) - checked
    except (KeyError, ValueError, TypeError):
        raise b.SetupError('HF-prisens tidsstempel mangler') from None
    if age.total_seconds() < -300 or age.total_seconds() > 3600:
        raise b.SetupError('HF-prisen er for gammel; opdatér kataloget før betalt kørsel')


def generation_payload(model, messages, route):
    fresh(route)
    return {'model': route['model'], 'messages': messages, 'max_tokens': 1536,
            'temperature': 0.8, 'stream': False}


def judge_payload(messages):
    schema = {'type': 'object', 'additionalProperties': False,
              'properties': {
                  **{key: {'type': 'integer', 'enum': [1, 2, 3, 4, 5]} for key in b.SCORES},
                  'explanation': {'type': 'string'},
                  'examples': {'type': 'array', 'minItems': 1, 'maxItems': 3,
                               'items': {'type': 'string'}}},
              'required': [*b.SCORES, 'explanation', 'examples']}
    return {'model': 'gpt-5-mini', 'messages': messages, 'max_completion_tokens': 2048,
            'reasoning_effort': 'minimal',
            'response_format': {'type': 'json_schema', 'json_schema': {
                'name': 'danish_writing_evaluation', 'strict': True, 'schema': schema}}}


def cost_from_tokens(usage, route):
    prompt, completion = usage.get('prompt_tokens'), usage.get('completion_tokens')
    if type(prompt) is not int or type(completion) is not int or prompt < 0 or completion < 0:
        return None
    # completion_tokens includes reasoning tokens. Cache discounts only reduce billing.
    return str(b.dec(prompt) * b.dec(route['prompt']) + b.dec(completion) * b.dec(route['completion']))
