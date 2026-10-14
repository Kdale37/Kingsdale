# Tjenestevalg og kilder

Den oprindelige undersøgelse er fra 9. oktober 2026. Senere opdateringer står nedenfor; aktuelle målinger og budget findes i `data/results.json`.

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

## Opdatering 13. oktober 2026: Hugging Face + direkte OpenAI

Brugeren har valgt Hugging Face til fortællingerne og direkte OpenAI GPT-5 mini som dommer. OpenRouter er en valgfri ældre backend. En offentlig katalogforespørgsel gennem GitHub bekræfter Hugging Face-adgang med den tilføjede HF-token; OpenAI-nøglen var tom i workflowets miljø og skal være et repository secret med præcis navnet `OPENAI_API_KEY`. Ingen betalte kald er udført ved denne kontrol.

Katalogstatus og budgetmæssig køreklarhed er forskellige. Mange modeller har `live` i modelkortets `inferenceProviderMapping`, men mangler priser i `https://router.huggingface.co/v1/models`, især dynamiske Featherless-ruter. De mærkes `unpriced`; runneren opfinder ingen rate og kører dem ikke inden for et ubekræftet budget. Modeller med publicerede input-/outputpriser køres med en konkret `model:provider`-rute. Priserne er USD pr. million tokens og konverteres før budgetreservation. Modelkortets kanoniske identitet bruges til at finde ruten; gamle Llama-aliaser deduplikeres.

Direkte GPT-5 mini bruger `max_completion_tokens=2048`, `reasoning_effort=minimal` og JSON-output, uden temperatur. Konservativt forbrug beregnes ud fra rapporterede input- og outputtokens (inklusive reasoning) × de publicerede standardrater. Cache-rabatter ignoreres; fakturaer er ikke verificeret. Både HF og OpenAI debiteres samme budget, og timeouts beholder reservationen.

## Opdatering 14. oktober 2026

Den læsende provider-kontrol bestod med begge repository secrets og adgang til GPT-5 mini. GitHub Pages er aktiveret, og første publicering er gennemført. Den tidligere HF-fejl med HTTP 402 og dens reservation forbliver i regnskabet ved genoptagelse.

[Hugging Faces prisvejledning](https://huggingface.co/docs/inference-providers/pricing) beskriver central afregning af routede kald. [Featherless' prisside](https://featherless.ai/pricing) dokumenterer abonnementer, men er ikke tilstrækkelig dokumentation for hver models input-/outputrate gennem HF. Aktive ruter uden modeltilknyttet tokenpris forbliver derfor `unpriced`; abonnementspriser omregnes ikke til opdigtede tokenpriser.

[AutoGLM-Phone-9B-Multilingual](https://huggingface.co/zai-org/AutoGLM-Phone-9B-Multilingual) viser kun 934.400 parametre i safetensors-metadata, mens modelkortet beskriver samme arkitektur som GLM-4.1V-9B-Thinking. Denne uoverensstemmelse kan ikke dokumentere den samlede vægtstørrelse. Runneren kræver nu manuel verificering, hvis metadata angiver under halvdelen af den nominelle størrelse. Det er et konservativt konsistenstjek; det beregner ikke et alternativt faktisk parameterantal. Modellen bevares som kandidat uden betalt kørsel.
