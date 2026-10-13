import http.server, threading, shutil
from pathlib import Path
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parents[1]
class Handler(http.server.SimpleHTTPRequestHandler):
 def translate_path(self,path):
  return str(root/path.removeprefix('/Kingsdale/').split('?')[0].lstrip('/'))
 def log_message(self,*args): pass
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler)
threading.Thread(target=server.serve_forever,daemon=True).start()
url=f'http://127.0.0.1:{server.server_port}/Kingsdale/'
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path=shutil.which('chromium'),headless=True,args=['--no-sandbox'])
 page=browser.new_page(); errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto(url);page.wait_for_function("document.querySelector('#model-count').textContent==='0'")
 assert page.locator('#ranking-empty').is_visible(); assert page.locator('.model-card').count()>0
 assert not errors,errors
 page.screenshot(path='/tmp/kingsdale-desktop.png',full_page=True)
 page.set_viewport_size({'width':390,'height':844});page.screenshot(path='/tmp/kingsdale-mobile.png',full_page=True)
 assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
 catalog={'schema_version':1,'models':[{'id':'alpha','name':'Alpha','family':'A','parameters_b':2,'eligibility':'eligible','source_url':'javascript:alert(1)'}],'max_parameters_b':9}
 story='<img src=x onerror="window.bad=true">\nHele originalteksten.'
 results={'schema_version':1,'runs':[{'id':'one','model_id':'alpha','status':'complete','repeat':1,'story':story,'word_count':200,'evaluation':{'grammar':4,'naturalness':5,'narrative':3,'period':4,'explanation':'<script>window.bad=true</script>','examples':['Konkret kommentar']}}]}
 page.route('**/data/catalog.json',lambda route:route.fulfill(json=catalog));page.route('**/data/results.json',lambda route:route.fulfill(json=results))
 page.reload();page.wait_for_function("document.querySelector('#model-count').textContent==='1'")
 assert page.locator('#story-text').inner_text()==story
 assert page.locator('#story-text img').count()==0
 assert page.locator('#catalog-list a').count()==0
 assert page.evaluate('window.bad === undefined')
 page.locator('#search').fill('missing');assert page.locator('#ranking-empty').is_visible()
 page.locator('#search').fill('alpha');assert page.locator('#ranking-table').is_visible()
 page.locator('#size').select_option('large');assert page.locator('#ranking-empty').is_visible()
 page.locator('nav a[href="#method"]').click();assert page.url.endswith('#method')
 results['runs'][0]['status']='judge_failed'; results['runs'][0].pop('evaluation'); results['budget']={'spent_usd':'0.25','reserved_usd':'0.50','usd_dkk_rate':8,'limit_dkk':100};results['status']='partial';results['budget']['cost_basis']='quoted_token_upper_bound';catalog['models'][0]['availability']='unpriced';catalog['models'][0]['reason']='Tokenpris mangler i offentlig prisliste'
 page.reload();page.wait_for_function("document.querySelector('#spent').textContent==='2 kr.'")
 assert page.locator('#ranking-empty').is_visible()
 assert page.locator('#story-text').inner_text()==story
 assert '4 kr.' in page.locator('#budget-note').inner_text()
 assert 'Aktiv API-rute · pris afventer verificering' in page.locator('#catalog-list').inner_text()
 assert 'Tokenpris mangler i offentlig prisliste' in page.locator('#catalog-list').inner_text()
 assert 'ikke verificeret mod en faktura' in page.locator('#budget-note').inner_text()
 assert 'Beregnet forbrug' in page.locator('#spent-label').inner_text()
 assert 'ingen gyldig dommervurdering' in page.locator('#explanation').inner_text()
 assert not errors,errors
 browser.close()
server.shutdown()
print('PASS: real Chromium desktop/mobile empty data, results, filters, full-text XSS safety, judge failure, decimal accounting, navigation, /Kingsdale/ paths, no page errors or mobile overflow')
