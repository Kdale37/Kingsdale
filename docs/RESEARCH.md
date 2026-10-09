# Tjenestevalg og kilder

Undersøgt 9. oktober 2026. Katalog- og priskontrol er udført; der er endnu ingen betalte modelkald.

## Primære kilder, som er hentet

- [OpenRouters modelkatalog](https://openrouter.ai/api/v1/models): model-ID, vægtidentitet, priser og parametre.
- [Providerkatalog](https://openrouter.ai/api/v1/providers): DeepInfra, Together, OpenAI og Cloudflare angives som US; Mistral som FR. Datacenterland er ikke garanteret.
- [Qwen3.5-9B endpoints](https://openrouter.ai/api/v1/models/qwen/qwen3.5-9b/endpoints): DeepInfra og Together giver en vestlig rute til en kinesisk udviklet model.
- [GPT-5 mini endpoints](https://openrouter.ai/api/v1/models/openai/gpt-5-mini/endpoints): almindelig OpenAI/Azure-pris 0,25 USD/M input og 2 USD/M output; OpenAI flex kan være billigere. Priser kontrolleres igen før kørsel.
- [Qwen3.5-9B vægtmetadata](https://huggingface.co/api/models/Qwen/Qwen3.5-9B): cirka 9,65B faktiske parametre, licens og revision. Derfor afrundingsgrænsen 10B for nominelle 9B-modeller.
- Officielle repositories for [Qwen3.5](https://github.com/QwenLM/Qwen3.5), [Qwen3](https://github.com/QwenLM/Qwen3), [SmolLM](https://github.com/huggingface/smollm) og [Mistral inference](https://github.com/mistralai/mistral-inference) er læst. Bibliotekslicens er ikke vægtlicens; modelkort kontrolleres separat.
- [LFM Open License v1.0](https://huggingface.co/LiquidAI/LFM2.5-2.6B/blob/main/LICENSE) og [Qwen research-licensen](https://huggingface.co/Qwen/Qwen2.5-3B-Instruct/blob/main/LICENSE) er læst. De tillader tilpasning under særlige vilkår: LFM har en erhvervsomsætningsgrænse, Qwen research kræver separat tilladelse til kommerciel brug. Det personlige benchmark kan medtage dem, men de betegnes ikke ubetinget open-source.

## Hvorfor OpenRouter

Én OpenAI-kompatibel API med offentligt katalog, providerdata og routingkontrol passer til en lille sammenligning. Små modellers teksttokenpriser er lave. Gratis aliasruter tælles ikke dobbelt; en vægtrelease, der kun har en gratis rute, bevares som kandidat. Rate limits kan gøre sådanne kørsler ufærdige.

DeepInfra, Together og Fireworks kan være billigere direkte for modeller, de selv hoster. Ingen direkte tjeneste er her dokumenteret som både billigere samlet og med fuld dækning af alle kandidater. Der er ikke oprettet konti eller købt kreditter hos dem. Hugging Face har langt flere downloadbare modeller, men det er ikke en garanti for serverless hosted inference.

OpenRouter er valgt for fælles adgang, **ikke som bevist billigst**. Top-up-gebyrer, moms og valutakonvertering skal vurderes ved køb. Runneren afviser ruter med ukendte/ekstra request- eller multimodalgebyrer. Cache-rabatter og priser for websearch, som ikke aktiveres, ændrer ikke det konservative tekstbudget.

## Dækning

`data/catalog.json` er den daterede undersøgelse af hele OpenRouter-kataloget og kendte lokale kandidater. API-klare modeller kræver identificerbare vægte, størrelses-/licensmetadata og en tilladt rute med verificerbar pris. LoRA på en faktisk GPU er ikke afprøvet.

**Kinesiske udviklere er med:** Qwen, DeepSeek, Yi, Tencent og ByteDance. Qwen3.5-9B har en passende vestlig endpoint-rute. Andre mangler sådan en rute og bliver vist som lokale kandidater; ingen må fremstå målt uden en fuldført kørsel.

Ukendte licenser, gamle/uklare modelkort og manglende vægtmetadata godkendes ikke automatisk. Store MoE-modeller udelades på totalstørrelse. Community-finetunes uden entydig downloadidentitet dokumenteres som udeladelser.

Fuld måling af alle downloadbare modeller kræver flere hosted endpoints eller GPUkørsel med et særskilt overslag. Det er ikke etableret her. Siden gør derfor ikke en udtømmende påstand om alle små modeller på internettet.
