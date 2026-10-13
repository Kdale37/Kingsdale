# Dansk Modelbench

En dansk GitHub Pages-side med et benchmark af små modeller med åbne vægte: tre fortællinger pr. model om at være ung i Danmark i 1980'erne, vurderet anonymt af en billig dommermodel.

**Status:** Siden og benchmarkværktøjet er implementeret og testet. `data/results.json` angiver den aktuelle kørselsstatus; kun komplette vurderede prøver rangeres. Kinesiske udviklere, herunder Qwen og DeepSeek, er med i undersøgelsen.

## Lokal udvikling

Ingen installation eller frontendbygning er nødvendig. Python 3.11+ og Node 20+ bruges til runner og tests.

```bash
cd /workspace/Kingsdale
python3 -m http.server 8000 --bind 0.0.0.0
```

Brug det eksisterende checkout; cloudopgaver er allerede isolerede, og et ekstra worktree er ikke nødvendigt. Alle sidestier er relative, så GitHub Pages-projektstien `/Kingsdale/` fungerer. API-kald sker aldrig fra besøgendes browser.

## Kør målingerne

Brug [Hugging Face Inference Providers](https://huggingface.co/docs/inference-providers/index) til fortællinger og [OpenAI API](https://platform.openai.com/) til GPT-5 mini som dommer. Tilføj `HF_TOKEN` og `OPENAI_API_KEY` som **repository secrets** på GitHub. HF-tokenen skal have rettigheden “Make calls to Inference Providers”. Begge konti skal have API-kreditter. Gem ikke nøglen i chat, kode, repository, logs eller kommandolinjeargumenter. HF-tokenen sendes kun til `router.huggingface.co`; OpenAI-nøglen kun til `api.openai.com`. De overføres ikke automatisk til Codex-miljøet. Ved lokal kørsel skal tilsvarende sikre miljøbindinger være til stede; `BENCHMARK_JUDGE_KEY` accepteres også som lokal OpenAI-binding.

```bash
python3 scripts/benchmark.py catalog
python3 scripts/benchmark.py run --dry-run
python3 scripts/benchmark.py run --budget-dkk 100 --usd-dkk-rate 8
python3 scripts/benchmark.py validate
```

Budgettet er højst 100 DKK **for dette resultatsæt**. Kursen 8 DKK/USD er en konservativ kalkulationskurs, ikke en dagskurs. Køb af kreditter, moms og betalingsgebyrer er særskilte fra tokenforbruget: hold også disse inden for det samlede loft. Sæt en højere kalkulationskurs eller et lavere scriptbudget, hvis de kræver ekstra margin, og brug også tjenesternes kontobudgetter.

Runneren genbruger komplette prøver og gemmer data efter hvert trin. Kendt forbrug og budgetreservationer nulstilles ikke ved genkørsel. En reservation skrives **før** hvert API-kald og bevares ved timeout eller manglende omkostningsdata. Hugging Face-priser kontrolleres i routerkataloget, og en konkret udbyder vælges med modellen `model:provider`. Priser over en time gamle afvises. Aktive ruter uden verificerbar tokenpris vises som `unpriced` og køres ikke. GPT-5 mini bruger de publicerede standardrater 0,25 USD/M input og 2 USD/M output. Rapporterede tokenantal × disse rater bruges som et konservativt beregnet forbrug; cache-rabatter ignoreres. Det er ikke en fakturakontrol. Begge tjenester bruger samme vedvarende budget. En isoleret model-/JSON-fejl stopper den berørte prøve; andre modeller kan fortsætte inden for budgettet. Autorisations-, routing- eller regnskabsfejl stopper hele kørslen. En ufærdig kørsel bevarer checkpoints og returnerer en fejlstatus. Ingen automatiske betalte retries. Kontrollér begge tjenesters forbrugsoversigter før manuel genoptagelse af et afbrudt kald; nulstil ikke forbrugsregnskabet.

Brug enten cloudmiljøet eller GitHub Actions til en betalt kørsel, ikke to forskellige kopier af samme budget. Fil-lås og Actions-concurrency forhindrer samtidige kørsler i samme miljø, men synkroniserer ikke forskellige maskiner.

## GitHub Pages og Actions

`.github/workflows/pages.yml` tester og publicerer ved push til `master`, manuel dispatch og afsluttet benchmarkworkflow. Pages skal bruge **GitHub Actions** som buildkilde. Kun frontend og `data/catalog.json`/`data/results.json` bliver sendt til Pages.

For målinger på GitHub: tilføj `HF_TOKEN` og `OPENAI_API_KEY` i repositoryets **Settings → Secrets and variables → Actions**, og vælg **Actions → Benchmark Danish prose → Run workflow** på `master`. Disse GitHub-bindinger er adskilt fra Codex-miljøet. Workflowet er ikke knyttet til et GitHub Environment og bruger derfor repository secrets. Der er ingen automatisk betalingsplan eller betalte kald på almindelige pushes. Workflowet opdaterer kataloget, kører/genoptager prisverificerede prøver, gemmer JSON-artifacts også ved fejl og committer data/checkpoints til `master`. Pages udgiver efterfølgende resultaterne. Hvis et workflow afbrydes før sluttrinnene, kontrollér API-forbruget før en ny betalt kørsel.

## Afgrænsning

- Nominelt op til cirka 9B, højst **10B faktiske samlede parametre**, så embeddings/billeddele i nominelle 9B-modeller kan medtages. MoE tælles på alle vægte. Faktisk størrelse kommer fra Hugging Faces `safetensors.total`.
- Kendte officielle små modelfamilier plus opdagelse i Hugging Faces aktuelle routerkatalog. Modeller uden en egnet hosted rute forbliver synlige lokale kandidater. “Alle små modeller” er ikke opnået alene med Hugging Face; der findes heller ingen endelig liste over alle community-finetunes.
- Downloadidentitet og kendt licensmetadata kontrolleres før kørsel. Llama/Gemma og andre særlige licenser må være med, men er ikke automatisk OSI-open-source. Ukendte `other`-licenser kræver særskilt gennemgang. Gatekeeping kan kræve accept af lokale downloadvilkår.
- QLoRA på en NVIDIA-GPU med 16–24 GB VRAM, korte sekvenser, batch 1 og checkpointing er et forventeligt udgangspunkt, **ikke en verificeret GPU-test**. Nye arkitekturer kan kræve nye Transformers/PEFT-versioner. 4-bit vægte alene bruger cirka 0,5 GB pr. milliard parametre; træningshukommelse og billeddele kommer oveni. Download normalt officielle vægte til adaptertræning, ikke kun en GGUF til inference.
- Hugging Face som fælles API og eksplicit valgte inferenceoperatører; OpenAI API som dommer. **Kinesiske modeludviklere er tilladt.** Operatørens hovedkontor er ikke en garanti for datacenterets land. Kataloget forklarer modeller, der mangler en tilladt rute.

## Vurdering

Samme danske prompt og tre uafhængige tekster på 180–220 ord; ingen manuel redigering eller valg af den bedste tekst. Primær sprogscore er gennemsnittet af grammatik og naturligt dansk, hver 1–5. Fortælling og tidsmiljø får separate karakterer. Ranglisten viser gennemsnit, prøveantal og standardafvigelse; mindre end tre komplette prøver er foreløbigt. Ordgrænsen måles særskilt med ord inklusive interne bindestreger/apostroffer. Uvurderede tekster kan læses, men bliver ikke rangeret.

Dommeren ser teksten uden modelnavnet og behandler den som ubetroet tekst. Dommeren er `gpt-5-mini` gennem den direkte OpenAI API. Der skiftes ikke automatisk til andre dommere. JSON-format og minimal reasoning bruges med `max_completion_tokens`, uden en temperatur som modellen ikke understøtter. Der skiftes ikke dommer midt i et datasæt. Interne Luna-agentnavne antages ikke at være offentlige API-ID'er.

Sampling og offentlige udbyder-/modelmetadata gemmes. Temperatur 0,8 for historier og 0 for dommeren, når understøttet. Generationsparametrene er fælles standardparametre i Hugging Face-routeren; der tvinges ikke udbyderspecifikke reasoning-indstillinger. GPT-5 mini bruger minimal reasoning ved vurdering. Uunderstøttede indstillinger bliver en dokumenteret fejl. Ingen garanti for bit-for-bit determinisme eller identisk lokal quantisering. Én prompt og én maskindommer er en smal undersøgelse; tre prøver understøtter ikke sikker statistisk generalisering.

## Tests

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
node --test tests/frontend.test.cjs
python3 scripts/benchmark.py validate
```

Hvis Python Playwright og Chromium er tilgængelige: `python3 tests/browser_check.py`. Den afprøver mobil/desktop, projektsti, filtrering, tekster, fejlede dommere og XSS med data, der kun indsprøjtes i browseren. Ingen testresultater skrives i offentlige JSON-filer.

[Byggevejledning til den mindre model](docs/BUILD_GUIDE.md) · [Tjenester, priser og modeldækning](docs/RESEARCH.md)

Den tidligere OpenRouter-backend bevares til eksplicit brug med `--backend openrouter`; standarden `huggingface` kræver kun HF- og OpenAI-nøglerne. Hvis en forudsætning er rettet, kan `--retry-failed` bruges eksplicit efter kontrol af faktiske omkostninger. Den bevarer tidligere forsøg og hele forbrugsregnskabet. Feltet `models` i workflowet kan afgrænse en pilot; tomt felt kører alle prisverificerede modeller.

Workflowets `generation_only` (CLI `--generation-only`) kan kontrollere HF-generering og gemme tekster, mens dommernøglen rettes. Det kræver kun HF-tokenen og bruger samme budget. Teksterne vises som afventende uden karakterer; en normal efterfølgende kørsel genbruger dem og betaler kun for dommervurderingen.
