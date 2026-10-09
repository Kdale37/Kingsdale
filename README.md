# Dansk Modelbench

En dansk GitHub Pages-side med et benchmark af små modeller med åbne vægte: tre fortællinger pr. model om at være ung i Danmark i 1980'erne, vurderet anonymt af en billig dommermodel.

**Status:** Siden og benchmarkværktøjet er implementeret. Katalog, størrelser, licensmetadata og aktuelle hosted ruter er undersøgt. Der er endnu **ingen betalte målinger**, ingen opdigtede tekster og ingen rangering. Kinesiske udviklere, herunder Qwen og DeepSeek, er med i undersøgelsen.

## Lokal udvikling

Ingen installation eller frontendbygning er nødvendig. Python 3.11+ og Node 20+ bruges til runner og tests.

```bash
cd /workspace/Kingsdale
python3 -m http.server 8000 --bind 0.0.0.0
```

Brug det eksisterende checkout; cloudopgaver er allerede isolerede, og et ekstra worktree er ikke nødvendigt. Alle sidestier er relative, så GitHub Pages-projektstien `/Kingsdale/` fungerer. API-kald sker aldrig fra besøgendes browser.

## Kør målingerne

Opret/fundér en konto hos [OpenRouter](https://openrouter.ai/), og bind `OPENROUTER_API_KEY` gennem sikre miljøindstillinger. Gem ikke nøglen i chat, kode, repository, logs eller kommandolinjeargumenter. En proxybundet nøgle bruges gennem HTTPS til `openrouter.ai`.

```bash
python3 scripts/benchmark.py catalog
python3 scripts/benchmark.py run --dry-run
python3 scripts/benchmark.py run --budget-dkk 100 --usd-dkk-rate 8
python3 scripts/benchmark.py validate
```

Budgettet er højst 100 DKK **for dette resultatsæt**. Kursen 8 DKK/USD er en konservativ kalkulationskurs, ikke en dagskurs. Køb af kreditter, moms og betalingsgebyrer er særskilte fra tokenforbruget: hold også disse inden for det samlede loft. Sæt en højere kalkulationskurs eller et lavere scriptbudget, hvis de kræver ekstra margin, og sæt gerne et kreditloft på OpenRouter-nøglen.

Runneren genbruger komplette prøver og gemmer data efter hvert trin. Kendt forbrug og budgetreservationer nulstilles ikke ved genkørsel. En reservation skrives **før** hvert API-kald og bevares ved timeout eller manglende omkostningsdata. Priser og udbydere kontrolleres igen før kørsel; routing begrænses til tilladte operatører og verificerede maksimumspriser. En isoleret model-/JSON-fejl stopper den berørte prøve; andre modeller kan fortsætte inden for budgettet. Autorisations-, routing- eller regnskabsfejl stopper hele kørslen. En ufærdig kørsel bevarer checkpoints og returnerer en fejlstatus. Ingen automatiske betalte retries. Kontrollér OpenRouters forbrugsoversigt før manuel genoptagelse af et afbrudt kald; nulstil ikke forbrugsregnskabet.

Brug enten cloudmiljøet eller GitHub Actions til en betalt kørsel, ikke to forskellige kopier af samme budget. Fil-lås og Actions-concurrency forhindrer samtidige kørsler i samme miljø, men synkroniserer ikke forskellige maskiner.

## GitHub Pages og Actions

`.github/workflows/pages.yml` tester og publicerer ved push til `master`, manuel dispatch og afsluttet benchmarkworkflow. Pages skal bruge **GitHub Actions** som buildkilde. Kun frontend og `data/catalog.json`/`data/results.json` bliver sendt til Pages.

For målinger på GitHub: tilføj `OPENROUTER_API_KEY` i repositoryets **Settings → Secrets and variables → Actions**, og vælg **Actions → Benchmark Danish prose → Run workflow** på `master`. Det er en anden binding end en nøgle i Codex-miljøet. Der er ingen automatisk betalingsplan eller betalte kald på almindelige pushes. Workflowet opdaterer kataloget, kører/genoptager prøverne, gemmer JSON-artifacts også ved fejl og committer data/checkpoints til `master`. Pages udgiver efterfølgende resultaterne. Hvis et workflow afbrydes før sluttrinnene, kontrollér API-forbruget før en ny betalt kørsel.

## Afgrænsning

- Nominelt op til cirka 9B, højst **10B faktiske samlede parametre**, så embeddings/billeddele i nominelle 9B-modeller kan medtages. MoE tælles på alle vægte. Faktisk størrelse kommer fra Hugging Faces `safetensors.total`.
- Kendte officielle små modelfamilier plus opdagelse i OpenRouters aktuelle katalog. Modeller uden en egnet hosted rute forbliver synlige lokale kandidater. “Alle små modeller” er ikke opnået alene med OpenRouter; der findes heller ingen endelig liste over alle community-finetunes.
- Downloadidentitet og kendt licensmetadata kontrolleres før kørsel. Llama/Gemma og andre særlige licenser må være med, men er ikke automatisk OSI-open-source. Ukendte `other`-licenser kræver særskilt gennemgang. Gatekeeping kan kræve accept af lokale downloadvilkår.
- QLoRA på en NVIDIA-GPU med 16–24 GB VRAM, korte sekvenser, batch 1 og checkpointing er et forventeligt udgangspunkt, **ikke en verificeret GPU-test**. Nye arkitekturer kan kræve nye Transformers/PEFT-versioner. 4-bit vægte alene bruger cirka 0,5 GB pr. milliard parametre; træningshukommelse og billeddele kommer oveni. Download normalt officielle vægte til adaptertræning, ikke kun en GGUF til inference.
- OpenRouter og eksplicit tilladte vestlige inferenceoperatører. **Kinesiske modeludviklere er tilladt.** Operatørens hovedkontor er ikke en garanti for datacenterets land. Kataloget forklarer modeller, der mangler en tilladt rute.

## Vurdering

Samme danske prompt og tre uafhængige tekster på 180–220 ord; ingen manuel redigering eller valg af den bedste tekst. Primær sprogscore er gennemsnittet af grammatik og naturligt dansk, hver 1–5. Fortælling og tidsmiljø får separate karakterer. Ranglisten viser gennemsnit, prøveantal og standardafvigelse; mindre end tre komplette prøver er foreløbigt. Ordgrænsen måles særskilt med ord inklusive interne bindestreger/apostroffer. Uvurderede tekster kan læses, men bliver ikke rangeret.

Dommeren ser teksten uden modelnavnet og behandler den som ubetroet tekst. Foretrukken dommer er `openai/gpt-5-mini`; fallback er `openai/gpt-4.1-mini` eller `openai/gpt-4o-mini`, hvis JSON, priser og tilladt rute verificeres. Der skiftes ikke dommer midt i et datasæt. Interne Luna-agentnavne antages ikke at være offentlige API-ID'er.

Sampling og offentlige udbyder-/modelmetadata gemmes. Temperatur 0,8 for historier og 0 for dommeren, når understøttet. Reasoning forsøges slået fra ved generation; GPT-5 mini bruger minimal reasoning ved vurdering. Uunderstøttede indstillinger bliver en dokumenteret fejl. Ingen garanti for bit-for-bit determinisme eller identisk lokal quantisering. Én prompt og én maskindommer er en smal undersøgelse; tre prøver understøtter ikke sikker statistisk generalisering.

## Tests

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
node --test tests/frontend.test.cjs
python3 scripts/benchmark.py validate
```

Hvis Python Playwright og Chromium er tilgængelige: `python3 tests/browser_check.py`. Den afprøver mobil/desktop, projektsti, filtrering, tekster, fejlede dommere og XSS med data, der kun indsprøjtes i browseren. Ingen testresultater skrives i offentlige JSON-filer.

[Byggevejledning til den mindre model](docs/BUILD_GUIDE.md) · [Tjenester, priser og modeldækning](docs/RESEARCH.md)
