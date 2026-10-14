'use strict';
const Bench = (() => {
  const finite = value => typeof value === 'number' && Number.isFinite(value);
  const scoreKeys = ['grammar', 'naturalness', 'narrative', 'period'];
  const validRun = run => run && run.status === 'complete' && typeof run.story === 'string' && run.story.trim().length > 0 && scoreKeys.every(key => Number.isInteger(run.evaluation?.[key]) && run.evaluation[key] >= 1 && run.evaluation[key] <= 5);
  const language = run => (run.evaluation.grammar + run.evaluation.naturalness) / 2;
  const average = values => values.reduce((a, b) => a + b, 0) / values.length;
  function aggregate(models, runs) {
    return models.filter(model => model.eligibility === 'eligible').map(model => {
      const samples = runs.filter(run => run.model_id === model.id && validRun(run));
      if (!samples.length) return null;
      const values = samples.map(language), mean = average(values);
      return {model, count: samples.length, uniqueStories: new Set(samples.map(run => run.story)).size, language: mean, narrative: average(samples.map(run => run.evaluation.narrative)), period: average(samples.map(run => run.evaluation.period)), deviation: Math.sqrt(average(values.map(value => (value - mean) ** 2)))};
    }).filter(Boolean);
  }
  function safeURL(value) { try { const url = new URL(value); return url.protocol === 'https:' ? url.href : null; } catch { return null; } }
  return {finite, validRun, language, aggregate, safeURL};
})();
if (typeof module !== 'undefined') module.exports = Bench;
if (typeof document !== 'undefined') {
  const $ = id => document.getElementById(id);
  const set = (id, value) => { $(id).textContent = value; };
  const element = (tag, text, className) => { const node = document.createElement(tag); if (text !== undefined) node.textContent = text; if (className) node.className = className; return node; };
  const format = value => Bench.finite(value) ? value.toLocaleString('da-DK', {maximumFractionDigits: 2}) : 'Ikke verificeret';
  const date = value => { const parsed = new Date(value); return value && !Number.isNaN(parsed.getTime()) ? parsed.toLocaleString('da-DK', {dateStyle:'medium', timeStyle:'short', timeZone:'UTC'}) + ' UTC' : 'Ikke verificeret'; };
  const labels = {available:'Tilgængelig via API', unpriced:'Aktiv API-rute · pris afventer verificering', unavailable:'Ikke tilgængelig via API', unverified:'Ikke verificeret', eligible:'Verificeret kandidat', candidate:'Afventer verificering', excluded:'Udeladt', verified_metadata:'Metadata verificeret', verified:'Verificeret'};
  let catalog = {models:[], excluded:[], sources:[]}, results = {runs:[]}, ranked = [], complete = [], readable = [];
  const numeric = value => (typeof value === 'number' || typeof value === 'string' && value.trim() !== '') && Number.isFinite(Number(value)) ? Number(value) : null;
  function link(parent, name, href) { const safe = Bench.safeURL(href); if (!safe) return; const anchor = element('a', name); anchor.href = safe; anchor.rel = 'noopener noreferrer'; parent.append(anchor); }
  function renderRanking() {
    const query = $('search').value.trim().toLocaleLowerCase('da'), family = $('family').value, size = $('size').value, sort = $('sort').value;
    const rows = ranked.filter(row => (!query || `${row.model.name} ${row.model.family}`.toLocaleLowerCase('da').includes(query)) && (!family || row.model.family === family) && (!size || Bench.finite(row.model.parameters_b) && (size === 'small' ? row.model.parameters_b <= 3 : row.model.parameters_b > 3 && row.model.parameters_b <= 10)));
    rows.sort((a,b) => sort === 'name' ? String(a.model.name).localeCompare(String(b.model.name), 'da') : b[sort] - a[sort] || String(a.model.name).localeCompare(String(b.model.name), 'da'));
    $('rankings').replaceChildren();
    rows.forEach(row => { const tr = element('tr'), name = element('td'); name.append(element('strong', row.model.name || row.model.id)); if (row.count < 3) name.append(element('span','Foreløbigt','badge')); if (row.uniqueStories < row.count) name.append(element('span',`${row.uniqueStories} unik tekst · ${row.count} prøver · gentagne tekster`,'badge')); tr.append(name); [row.language,row.narrative,row.period].forEach(value => tr.append(element('td',format(value)))); tr.append(element('td',String(row.count)),element('td',format(row.deviation))); $('rankings').append(tr); });
    $('ranking-table').hidden = rows.length === 0; $('ranking-empty').hidden = rows.length > 0;
    set('ranking-empty', ranked.length ? 'Ingen målte modeller matcher dine filtre.' : 'Ingen placeringer endnu. De første verificerede målinger vil blive vist her.');
  }
  function renderStory() {
    const run = readable.find(item => item.id === $('run-select').value);
    $('story-panel').hidden = !run; $('reader-empty').hidden = !!run;
    if (!run) return;
    const model = catalog.models.find(item => item.id === run.model_id);
    set('story-title',model?.name || run.model_id); set('story-meta',`PRØVE ${run.repeat ?? 'Ikke verificeret'} · ${format(run.word_count)} ORD`); set('story-text',run.story);
    $('scores').replaceChildren();
    if (!Bench.validRun(run)) { set('explanation','Denne fortælling har ingen gyldig dommervurdering og tæller ikke i ranglisten.'); $('examples').replaceChildren(); set('word-status',`Ordantal: ${format(run.word_count)} · vurdering afventer eller fejlede.`); return; }
    [['Sprogscore',Bench.language(run)],['Grammatik',run.evaluation.grammar],['Naturligt dansk',run.evaluation.naturalness],['Fortælling',run.evaluation.narrative],['Tidsmiljø',run.evaluation.period]].forEach(([name,value]) => $('scores').append(element('dt',name),element('dd',`${format(value)} / 5`)));
    set('explanation',typeof run.evaluation.explanation === 'string' ? run.evaluation.explanation : 'Ingen offentlig begrundelse.'); $('examples').replaceChildren();
    if (Array.isArray(run.evaluation.examples)) run.evaluation.examples.filter(value => typeof value === 'string').forEach(value => $('examples').append(element('li',value)));
    set('word-status',Bench.finite(run.word_count) ? (run.word_count >= 180 && run.word_count <= 220 ? 'Ordgrænse: inden for 180–220 ord.' : 'Ordgrænse: uden for 180–220 ord.') : 'Ordantal: ikke verificeret.');
  }
  function render() {
    complete = results.runs.filter(Bench.validRun); readable = results.runs.filter(run => typeof run.story === 'string' && run.story.trim()); ranked = Bench.aggregate(catalog.models, results.runs);
    set('status',results.status === 'awaiting_judge' ? 'Fortællinger klar · afventer dommervurdering' : results.status === 'budget_exhausted' ? 'Måling stoppet ved budgetgrænsen' : results.status === 'partial' ? 'Delvis måling · nogle prøver mangler' : complete.length ? 'Målinger tilgængelige · se afgrænsningen nedenfor' : 'Afventer første måling'); set('updated',`Seneste måling: ${results.generated_at ? date(results.generated_at) : 'ingen målinger endnu'}`);
    set('model-count',String(ranked.length)); set('story-count',String(complete.length));
    const budget = results.budget || {}, spent = numeric(budget.spent_usd), rate = numeric(budget.usd_dkk_rate), reserved = numeric(budget.reserved_usd), limit = numeric(budget.limit_dkk);
    set('spent',spent !== null && rate !== null ? `${format(spent * rate)} kr.` : 'Ikke verificeret'); set('budget',limit !== null ? `${format(limit)} kr.` : 'Ikke verificeret');
    const quoted = budget.cost_basis === 'quoted_token_upper_bound';
    set('spent-label',quoted ? 'Beregnet forbrug · estimeret DKK' : 'Registreret forbrug · estimeret DKK');
    set('budget-note',`Reservationer til ikke afklaret forbrug: ${reserved !== null && rate !== null ? format(reserved * rate) + ' kr. (estimat)' : 'Ikke verificeret'}. ${rate !== null ? 'Omregning: ' + format(rate) + ' DKK/USD, planlægningskurs; ikke live valutakurs.' : 'Omregningskurs ikke verificeret.'} ${budget.accounting_status === 'not_started' ? 'Målingen er ikke startet.' : reserved > 0 ? 'Endeligt forbrug er endnu ikke afklaret; reservationer er adskilt fra registreret forbrug.' : 'Kun registreret forbrug er vist.'} ${quoted ? 'Forbruget er et beregnet øvre skøn ud fra rapporterede tokens og kontrollerede offentliggjorte tokenpriser. Cache-rabatter er ikke medregnet; beløbet er ikke verificeret mod en faktura.' : 'Omkostningsgrundlag: ikke verificeret mod en faktura her.'}`);
    [...new Set(catalog.models.map(model => model.family).filter(value => typeof value === 'string' && value))].sort().forEach(value => { const option = element('option',value); option.value = value; $('family').append(option); });
    renderRanking(); $('run-select').replaceChildren(); $('run-select').disabled = !readable.length;
    if (!readable.length) $('run-select').append(element('option','Ingen fortællinger endnu'));
    readable.forEach(run => { const model = catalog.models.find(item => item.id === run.model_id); const option = element('option',`${model?.name || run.model_id} · prøve ${run.repeat ?? '?'}`); option.value = run.id; $('run-select').append(option); }); renderStory();
    const failed = results.runs.filter(run => !Bench.validRun(run)); set('failure-count',`(${failed.length})`); $('failure-list').replaceChildren();
    if (!failed.length) $('failure-list').append(element('li','Ingen fejl eller skippede prøver registreret.'));
    failed.forEach(run => { const model = catalog.models.find(item => item.id === run.model_id); const status = {generated:'Afventer vurdering',generation_failed:'Generering fejlet',judge_failed:'Dommer fejlet',failed:'Fejlet',skipped:'Skippet',incomplete:'Ufuldstændig',pending:'Afventer'}[run.status] || 'Ikke komplet'; $('failure-list').append(element('li',`${model?.name || run.model_id || 'Ukendt model'} · prøve ${run.repeat ?? '?'}: ${status}. Ingen gyldig komplet vurdering til ranglisten.`)); });
    set('catalog-meta',`Katalog kontrolleret: ${date(catalog.checked_at)} · ${catalog.models.length} modeller · markedsført højst ${format(catalog.max_nominal_parameters_b)} mia. · faktisk højst ${format(catalog.max_parameters_b)} mia. samlede parametre${typeof catalog.scope === 'string' ? ' · ' + catalog.scope : ''}`);
    $('catalog-list').replaceChildren();
    catalog.models.forEach(model => { const card = element('article',undefined,'model-card'); card.append(element('h3',model.name || model.id || 'Ikke verificeret'),element('span',labels[model.eligibility] || 'Ikke verificeret','badge')); const dl = element('dl'); [['Familie',model.family],[model.eligibility === 'eligible' ? 'Faktiske parametre' : 'Oplyst størrelse',Bench.finite(model.parameters_b) ? `${format(model.parameters_b)} mia.` : null],['Licens',model.license],['Licensstatus',labels[model.license_status] || model.license_status],['Adgang',labels[model.availability]]].forEach(([name,value]) => dl.append(element('dt',name),element('dd',typeof value === 'string' && value ? value : 'Ikke verificeret'))); card.append(dl); if (model.availability === 'unpriced') card.append(element('p','Ruten er aktiv, men modellen kan ikke køres inden for budgettet, før tokenprisen er verificeret.','small muted')); if (typeof model.reason === 'string' && model.reason) card.append(element('p',model.reason,'small muted')); if (model.gated) card.append(element('p','Download kan kræve godkendelse.','small muted')); if (model.eligibility === 'candidate') card.append(element('p','Download og tilladt finjustering er endnu ikke fuldt verificeret til denne måling.','small muted')); link(card,'Modelkort / download ↗',model.source_url); $('catalog-list').append(card); });
    if (!catalog.models.length) $('catalog-list').append(element('p','Kandidatlisten er endnu ikke tilgængelig.','empty'));
    $('excluded-list').replaceChildren(); (catalog.excluded || []).forEach(item => $('excluded-list').append(element('li',typeof item === 'string' ? item : `${item.name || item.id || 'Model'}: ${item.reason || 'Ikke verificeret'}`)));
    set('judge-meta',`Dommer: ${results.judge_model || 'Ikke verificeret'} · planlagte prøver pr. model: ${results.repetitions ?? 'Ikke verificeret'}`); set('prompt',typeof results.prompt === 'string' && results.prompt ? results.prompt : 'Afventer offentlig målekonfiguration.');
    $('sources').replaceChildren(); (catalog.sources || []).forEach(source => { const li = element('li'); if (typeof source === 'string') link(li,source,source); else link(li,source.name || source.title || source.url,source.url); if (li.childNodes.length) $('sources').append(li); });
    if (!$('sources').childNodes.length) $('sources').append(element('li','Ingen verificerede kildelinks tilgængelige.'));
  }
  ['search','family','size','sort'].forEach(id => $(id).addEventListener(id === 'search' ? 'input' : 'change',renderRanking)); $('run-select').addEventListener('change',renderStory);
  async function fetchData(path) { const response = await fetch(path); if (!response.ok) throw new Error('Data unavailable'); const data = await response.json(); if (data.schema_version !== 1) throw new Error('Unsupported schema'); return data; }
  Promise.allSettled([fetchData('data/catalog.json'),fetchData('data/results.json')]).then(items => {
    const warnings = [];
    if (items[0].status === 'fulfilled' && Array.isArray(items[0].value.models)) catalog = items[0].value; else warnings.push('Kataloget kunne ikke hentes eller læses.');
    if (items[1].status === 'fulfilled' && Array.isArray(items[1].value.runs)) results = items[1].value; else warnings.push('Målingerne kunne ikke hentes eller læses.');
    if (warnings.length) { $('notice').hidden = false; set('notice',warnings.join(' ') + ' Prøv at genindlæse siden senere.'); } render();
  }).catch(() => { $('notice').hidden = false; set('notice','Data kunne ikke vises. Prøv at genindlæse siden senere.'); });
}
