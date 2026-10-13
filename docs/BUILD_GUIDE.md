# Byggevejledning: Dansk Modelbench

Denne opgave bygges af **GPT-6.1-sol med lav ræsonnementsindsats**. Læs vejledningen og følg trinnene i rækkefølge. Brug checkoutet `/workspace/Kingsdale`; opret ikke et worktree.

## Formål og afgrænsning

Lav en dansk, offentlig GitHub Pages-side, der sammenligner små modeller med åbne vægte på en cirka 200 ord lang fortælling om at være ung i Danmark i 1980'erne. Modeller markedsført op til cirka 9B er kandidater; tillad højst 10B faktiske **samlede** parametre for embeddings, billeddele og afrunding. Store MoE-modeller udelades på totalstørrelse. Download og tilladt finjustering skal verificeres før kørsel. Modeller med særlige licenser er tilladt, men må ikke kaldes OSI-open-source uden belæg. Kinesiske modeludviklere er tilladt; den fælles API og valgte inferenceoperatører skal være vestlige.

Der findes ikke en endelig liste over alle community-finetunes. Vis derfor dato, afgrænsning, kandidater, tilgængelige modeller og udeladelser. Kald ikke en foreløbig liste udtømmende. Katalogopdateringen skal finde alle relevante små modeller i Hugging Faces aktuelle katalog og beholde kendte lokale kandidater, også når de ikke kan køres dér. Små MoE-aktivtal må ikke forveksles med totalstørrelse. Kataloget viser både nominel grænse 9B og faktisk grænse 10B.

## Trin 1: Statisk hjemmeside

Byg `index.html`, `styles.css`, `app.js` og `.nojekyll` uden framework, byggetrin, CDN, analyseværktøjer eller eksterne skrifttyper. Sprog: dansk. Design: varm papirbaggrund, mørk marineblå, afdæmpet orange, tydelig typografi, små referencer til kassettebånd/1980'erne. Den skal fungere både på mobil og desktop, med tastatur og skærmlæser. Brug relative URL'er, så `/Kingsdale/` virker på GitHub Pages.

Siden skal indeholde:

1. Titel, kort forklaring, status og tidspunkt for seneste måling.
2. Nøgletal: verificerede målte modeller, komplette fortællinger, faktisk forbrug, budget.
3. Rangliste med søgning, familie/størrelsesfilter og sortering; gennemsnit af **sprogscore**, fortælling, tidsmiljø, antal komplette prøver og spredning. Vis ikke rangering før målinger findes.
4. En fortællingslæser med model, prøve, ordtal, dommerens score og konkrete begrundelser. Bevar hele originalteksten. Vis også fejl/skippede prøver særskilt.
5. Katalog med størrelse, modelkort/download, licensstatus og tilgængelighed. Lokale kandidater uden API er synlige.
6. Metode: identisk prompt, tre prøver, blind dommer, grammatisk korrekthed og naturligt dansk (primær sprogscore), fortællekvalitet og tidsmiljø (sekundære mål), 180–220 ord, begrænsninger og kilder. Undgå at præsentere én prompt eller maskinvurdering som bevis på samlet danskkompetence.

Initialt findes **ingen rigtige målinger**. Vis et nyttigt, ærligt tomt stadie, kandidatlisten og metoden. Opfind ingen resultater, historier, priser eller placeringer. Der må ikke være en browserfunktion, der kræver API-nøgle; GitHub Pages har ingen server. Kørsel sker i Python/GitHub Actions, og kun resultater bliver offentlige.

## Trin 2: Dataaftale

Læs `data/catalog.json` og `data/results.json` med `fetch` og håndtér fejl synligt. Alle eksterne tekster skal sættes med `textContent`, aldrig rå `innerHTML`. Tillad kun HTTPS i modelkort/kildelinks. UI må ikke indeholde nøgler, rå API-fejl eller interne driftsinstruktioner.

Katalog: `{schema_version, checked_at, status, max_parameters_b, models, excluded, sources}`. Model: `{id, name, family, parameters_b, hf_id, license, license_status, availability, eligibility, source_url}`. Manglende felter vises som "Ikke verificeret". `availability` er `available`, `unpriced`, `unavailable` eller `unverified`; `eligibility` er `eligible`, `candidate` eller `excluded`.

Resultater: `{schema_version, status, generated_at, judge_model, prompt, repetitions, budget, runs}`. Budget: `{limit_dkk, usd_dkk_rate, spent_usd, reserved_usd}`. En prøve: `{id, model_id, repeat, status, story, word_count, finish_reason, generation, evaluation, error}`. `generation` indeholder kun offentlige metadata (model/provider, tokens, USD, tidspunkt). `evaluation`: `{grammar, naturalness, narrative, period, explanation, examples}` med fire heltal 1–5. `explanation` er dansk tekst; `examples` er en liste af konkrete danske kommentarer. Status `complete` kræver en gyldig dommervurdering; kun komplette prøver tæller i ranglisten. Sprogscore = gennemsnit af grammar og naturalness. Saml modelscore ved lige vægt pr. prøve. Vis antal og standardafvigelse og markér mindre end tre prøver som foreløbigt. Ordgrænse er et separat, objektivt mål.

## Trin 3: Validering

Kontrollér med en lokal HTTP-server fra repositoryroden, at data kan hentes, tomt stadie fungerer og ingen konsolfejl opstår. Test igen med syntetiske målinger **kun i testfixtures**, aldrig i offentlig data. Kontrollér navigation, filtre, tekstvisning, XSS-beskyttelse og projektsti. Test i browser, hvis værktøjet er tilgængeligt; rapportér præcist, hvad der faktisk blev testet.

## Arbejdsdeling

Den mindre model implementerer **kun** frontendfilerne og eventuelle frontendtests. Hovedagenten skriver katalog, benchmarkrunner, Python-tests, dokumentation og GitHub Actions. Redigér ikke hinandens filer. Send hovedagenten en kort liste over filer, antagelser og testresultater. Ingen commits, pushes eller eksterne publikationer fra underagenten.

## Tjenester efter 13. oktober 2026

Standardbackend: Hugging Face-generering (`HF_TOKEN`) og direkte OpenAI GPT-5 mini-vurdering (`OPENAI_API_KEY`), med samme budget. `unpriced` betyder aktiv rute, men ingen verificerbar tokenpris; vis det særskilt fra en manglende rute. `budget.cost_basis=quoted_token_upper_bound` betyder rapporterede tokens gange publicerede rater uden cache-rabat; vis beregnet omkostning og reservationer, aldrig en påstået verificeret faktura. Begge nøgler er GitHub repository secrets og må ikke vises i frontend.
