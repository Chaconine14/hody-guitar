#!/usr/bin/env python3
"""Selection browser verification. Needs Playwright/Pillow and a local HTTP server.

python3 scripts/verify-selection.py --base-url http://127.0.0.1:8766 --baseline-dir /path/to/snapshot
The optional snapshot mirrors index.html, guide.html, css/style.css and js/reservation.js.
"""
import argparse
import csv
import json
from pathlib import Path
from PIL import Image, ImageChops, ImageStat
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--base-url', default='http://127.0.0.1:8766')
parser.add_argument('--browser', default='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')
parser.add_argument('--baseline-dir', type=Path)
parser.add_argument('--only-regression', action='store_true')
parser.add_argument('--output', type=Path, default=ROOT / 'artifacts/selection')
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=True)
report = {'data': {}, 'viewports': {}, 'scenarios': {}, 'regression': {}}
if args.only_regression and (args.output / 'verification.json').exists():
    report = json.loads((args.output / 'verification.json').read_text())
catalog = json.loads((ROOT / 'data/products.json').read_text())
products = sorted(catalog['products'], key=lambda product: product['sort_order'])
scenarios = json.loads((ROOT / 'data/test_scenarios.json').read_text())['scenarios']


def checkpoint():
    (args.output / 'verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=4) + '\n')


def ready(page, filename='selection.html'):
    page.goto(args.base_url.rstrip('/') + '/' + filename)
    if filename == 'selection.html':
        page.wait_for_selector('main[aria-busy="false"]')
    page.evaluate('document.fonts.ready')
    page.evaluate('''async () => {
        for (const image of document.images) {
            image.loading = 'eager';
            await image.decode().catch(() => {});
        }
    }''')


def no_overflow(page):
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Horizontal overflow'
    assert not page.evaluate('''() => [...document.querySelectorAll('.p-selection-page__card, .p-selection-page__filters')].some(el => el.scrollWidth > el.clientWidth + 1)'''), 'Card/filter overflow'


def ids(page):
    return page.locator('[data-product-id]').evaluate_all('(nodes) => nodes.map(n => n.dataset.productId)')


def open_filters(page):
    if not page.locator('.js-selection-form').is_visible():
        page.locator('.js-filter-toggle').click()


def search(page, filters):
    open_filters(page)
    for name in catalog['filter_options']:
        page.select_option(f'.js-selection-form [name="{name}"]', filters.get(name, ''))
    page.locator('.p-selection-page__search').click()


def reset(page):
    open_filters(page)
    page.locator('.js-filter-reset').click()


def screenshot(page, name):
    page.evaluate('''async () => {
        await document.fonts.ready;
        await Promise.all([...document.images].map(i => i.decode().catch(() => {})));
        window.scrollTo({top: 0, behavior: 'instant'});
    }''')
    page.mouse.move(0, 0)
    page.screenshot(path=str(args.output / name), full_page=True)


def geometry(page):
    return page.evaluate('''() => Object.fromEntries([
        '.l-header', '.p-selection-page__intro', '.p-selection-page__filters',
        '.p-selection-page__results-heading', '.p-selection-page__photo',
        '.p-selection-page__empty', '.c-trial-invite', '.l-footer__visual', '.l-footer__bottom'
    ].map(selector => {
        const r = document.querySelector(selector)?.getBoundingClientRect();
        return [selector, r ? {x:r.x, y:r.y + scrollY, width:r.width, height:r.height} : null];
    }))''')


def image_error(first, second):
    a, b = Image.open(first).convert('RGB'), Image.open(second).convert('RGB')
    assert a.size == b.size, f'Regression dimensions: {a.size} != {b.size}'
    return max(ImageStat.Stat(ImageChops.difference(a, b)).mean)


def dialog_fonts(page):
    session = page.context.new_cdp_session(page)
    session.send('DOM.enable')
    session.send('CSS.enable')
    root = session.send('DOM.getDocument')['root']['nodeId']
    node = session.send('DOM.querySelector', {'nodeId': root, 'selector': '.p-reservation__title'})
    fonts = session.send('CSS.getPlatformFontsForNode', {'nodeId': node['nodeId']})['fonts']
    session.detach()
    return fonts


csv_products = list(csv.DictReader((ROOT / 'data/products.csv').open(encoding='utf-8-sig')))
assert len(products) == len(csv_products) == 12
for product, row in zip(products, csv_products):
    assert product['id'] == row['id']
    assert product['image_src'] == row['image_src']
    assert product['image_status'] == row['image_status']
    image = ROOT / product['image_src']
    assert image.is_file() and image.stat().st_size > 0
    Image.open(image).verify()
if args.baseline_dir:
    original = json.loads((args.baseline_dir / 'data/products.json').read_text())
    actual = json.loads(json.dumps(catalog))
    changes = []
    for before, after in zip(original['products'], actual['products']):
        if before['image_status'] == 'MISSING':
            assert after['image_status'] == 'PROVIDED_LOCAL_IMAGE'
            changes.append(after['id'])
            after['image_status'] = 'MISSING'
    assert original == actual, 'Non-image JSON data changed'
    assert len(changes) == 9
    old_csv = (args.baseline_dir / 'data/products.csv').read_bytes()
    assert old_csv.replace(b'MISSING', b'PROVIDED_LOCAL_IMAGE') == (ROOT / 'data/products.csv').read_bytes()
    assert (args.baseline_dir / 'data/test_scenarios.json').read_bytes() == (ROOT / 'data/test_scenarios.json').read_bytes()
    report['data']['status_changes_only'] = changes
report['data']['images'] = {p['id']: p['image_src'] for p in products}
checkpoint()

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=args.browser, headless=True)
    for width in (() if args.only_regression else (1440, 375, 320, 768, 769, 1024)):
        page = browser.new_page(viewport={'width': width, 'height': 900}, reduced_motion='reduce')
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        ready(page)
        no_overflow(page)
        assert ids(page) == [product['id'] for product in products]
        assert page.locator('h1').count() == 1
        assert page.locator('.js-results-count').inner_text() == '12 ITEMS'
        assert page.locator('#reserve-product option').count() == 13
        assert page.evaluate('''() => [...document.fonts].some(f => f.family === 'HODY Selection JP' && f.status === 'loaded')''')
        images = page.locator('.p-selection-page__photo').evaluate_all('''nodes => nodes.map(n => ({
            id:n.closest('article').dataset.productId, src:n.getAttribute('src'),
            loaded:n.complete && n.naturalWidth > 0, fit:getComputedStyle(n).objectFit,
            w:n.width, h:n.height
        }))''')
        assert all(image['loaded'] and image['fit'] == 'contain' for image in images)
        assert {image['id']: image['src'] for image in images} == report['data']['images']
        details = {'images': images, 'initial': geometry(page)}
        if width in (1440, 375):
            device = 'pc' if width == 1440 else 'sp'
            screenshot(page, f'{device}-initial.png')
            for scenario in scenarios:
                search(page, scenario['filters'])
                assert ids(page) == scenario['expected_ids'], scenario['name']
                assert page.locator('.js-results-count').inner_text() == f"{len(scenario['expected_ids'])}件"
                assert page.locator('.js-empty-results').is_visible() == (not scenario['expected_ids'])
                assert page.locator('.js-selection-form').is_visible() == (width > 768)
            report['scenarios'][str(width)] = {'passed': len(scenarios)}
            # 実際に使用している検索モジュールで価格境界・未確認値を検証。
            boundaries = page.evaluate('''async () => {
                const {filterProducts} = await import('./js/selection-search.js');
                const base = {playing_styles:['ストローク','指弾き'], tone_impressions:['明るい'], amp_connection:null};
                const data = [null,149999,150000,299999,300000,499999,500000].map((price,i) => ({...base,id:String(i),price_yen:price,sort_order:i}));
                return Object.fromEntries(['','lt150000','150000_299999','300000_499999','gte500000'].map(band => [band,filterProducts(data,{price_band:band}).map(p=>p.id)]));
            }''')
            assert boundaries == {'': ['0','1','2','3','4','5','6'], 'lt150000':['1'], '150000_299999':['2','3'], '300000_499999':['4','5'], 'gte500000':['6']}
            details['price_boundaries'] = boundaries
            # 選択変更は未適用。パネル開閉・幅変更でも保持。
            search(page, {'body_size': '小さめ'})
            previous = ids(page)
            open_filters(page)
            page.select_option('[name="tone_impression"]', '力強い')
            assert ids(page) == previous
            applied_text = page.locator('.js-applied-list').first.inner_text()
            assert '力強い' not in applied_text
            if width == 375:
                page.locator('.js-filter-toggle').click()
                page.locator('.js-filter-toggle').click()
                assert page.locator('[name="tone_impression"]').input_value() == '力強い'
                page.set_viewport_size({'width': 1024, 'height': 900})
                expect(page.locator('.js-selection-form')).to_be_visible()
                page.set_viewport_size({'width': 375, 'height': 900})
            reset(page)
            assert ids(page) == [product['id'] for product in products]
            assert page.locator('.js-results-title').inner_text() == 'PRODUCTS'
            assert page.locator('.js-selection-form').is_visible()
            # 全12機種：その属性で検索し、カードから予約名称を引き継ぐ。
            for product in products:
                filters = {'body_size': product['body_size'], 'playing_style': product['playing_styles'][0], 'tone_impression': product['tone_impressions'][0]}
                if product['amp_connection'] is not None:
                    filters['amp_connection'] = 'yes' if product['amp_connection'] else 'no'
                search(page, filters)
                assert product['id'] in ids(page)
                button = page.locator(f'[data-product-id="{product["id"]}"] .js-open-reservation')
                button.click()
                expect(page.locator('.p-reservation__close')).to_be_visible()
                assert page.locator('#reserve-product').input_value() == product['display_name']
                page.keyboard.press('Escape')
                expect(button).to_be_focused()
            details['all_products_search_and_reservation'] = 12
            search(page, {'body_size': '小さめ'})
            screenshot(page, f'{device}-results.png')
            details['results'] = geometry(page)
            search(page, {'body_size': '小さめ', 'tone_impression': '力強い'})
            screenshot(page, f'{device}-empty.png')
            details['empty'] = geometry(page)
            # 同じ条件・空欄画面でも下部予約導線が開く。
            page.locator('.c-trial-invite__button').click()
            expect(page.locator('.p-reservation__close')).to_be_visible()
            page.locator('.p-reservation__close').focus()
            page.keyboard.press('Shift+Tab')
            expect(page.locator('.p-reservation__submit')).to_be_focused()
            page.keyboard.press('Tab')
            expect(page.locator('.p-reservation__close')).to_be_focused()
            assert not page.locator('.js-reservation-form').evaluate('f => f.checkValidity()')
            page.locator('#reserve-name').fill('試奏テスト')
            page.locator('#reserve-email').fill('test@example.com')
            page.locator('#reserve-date').fill('2026-11-05T14:00')
            assert page.locator('.js-reservation-form').evaluate('f => f.checkValidity()')
            page.locator('.p-reservation__submit').click()
            assert page.locator('.js-reservation').get_attribute('aria-hidden') == 'false'
            page.locator('.js-close-reservation').click()
            if width == 375:
                page.locator('.js-menu-open').click()
                expect(page.locator('.js-menu-close')).to_be_visible()
                page.locator('.p-mobile-menu__reserve').click()
                expect(page.locator('.js-mobile-menu')).to_have_attribute('aria-hidden', 'true')
                expect(page.locator('.js-reservation')).to_have_attribute('aria-hidden', 'false')
                page.keyboard.press('Escape')
            else:
                page.locator('.l-header__reserve').click()
                page.locator('.js-reservation-backdrop').click(position={'x': 5, 'y': 5})
            no_overflow(page)
        else:
            search(page, {'body_size': '小さめ'})
            no_overflow(page)
            search(page, {'body_size': '小さめ', 'tone_impression': '力強い'})
            no_overflow(page)
            reset(page)
            no_overflow(page)
            if width <= 768:
                page.locator('.js-filter-toggle').focus()
                page.keyboard.press('Enter')
                expect(page.locator('.js-selection-form')).to_be_hidden()
                page.keyboard.press('Space')
                expect(page.locator('.js-selection-form')).to_be_visible()
        assert not errors, errors
        details['passed'] = True
        report['viewports'][str(width)] = details
        checkpoint()
        page.close()
        print(f'{width}px passed: layout, images, search and interactions.', flush=True)

    # データ取得失敗は0件とは別の画面。HTTP失敗・不正JSONを両方確認。
    for failure in ('http', 'invalid-json'):
        page = browser.new_page(viewport={'width': 375, 'height': 900})
        page.route('**/data/products.json', lambda route: route.fulfill(status=503 if failure == 'http' else 200, body='not JSON', content_type='application/json'))
        ready(page)
        expect(page.locator('.js-catalog-error')).to_be_visible()
        expect(page.locator('.js-empty-results')).to_be_hidden()
        assert page.locator('.js-results-count').inner_text() == '—'
        assert page.locator('.js-selection-form select:enabled').count() == 0
        expect(page.locator('.p-selection-page__search')).to_be_disabled()
        assert page.locator('#reserve-product option').count() == 1
        assert page.locator('.c-trial-invite').is_visible()
        page.close()
    report['fetch_failure'] = ['HTTP 503', 'invalid JSON: distinct from zero; search disabled']
    checkpoint()

    if args.baseline_dir:
        for width in (1440, 375):
            report['regression'][str(width)] = {}
            for filename in ('index.html', 'guide.html'):
                shots, panels, fonts = [], [], []
                for original in (True, False):
                    page = browser.new_page(viewport={'width': width, 'height': 900}, reduced_motion='reduce')
                    if original:
                        for resource, mime in ((filename,'text/html'), ('css/style.css','text/css'), ('js/reservation.js','text/javascript')):
                            body = (args.baseline_dir / resource).read_bytes()
                            page.route('**/' + resource, lambda route, request, body=body, mime=mime: route.fulfill(body=body, content_type=mime))
                    ready(page, filename)
                    shot = args.output / f'{filename[:-5]}-{"before" if original else "after"}-{width}.png'
                    screenshot(page, shot.name)
                    shots.append(shot)
                    if width == 375:
                        page.locator('.js-menu-open').click()
                        expect(page.locator('.js-menu-close')).to_be_visible()
                        page.locator('.p-mobile-menu__reserve').click()
                    else:
                        page.locator('.l-header__reserve').click()
                    expect(page.locator('.p-reservation__close')).to_be_visible()
                    page.evaluate('document.fonts.ready')
                    page.wait_for_timeout(100)
                    page.mouse.move(0, 0)
                    panel = args.output / f'{filename[:-5]}-dialog-{"before" if original else "after"}-{width}.png'
                    page.locator('.p-reservation__panel').screenshot(path=str(panel))
                    panels.append(panel)
                    fonts.append(dialog_fonts(page))
                    # 既存ページの選択肢・閉じる操作・FAQも維持。
                    assert page.locator('#reserve-product option').count() == 4
                    page.keyboard.press('Escape')
                    if filename == 'guide.html':
                        assert page.locator('details[open]').count() == 1
                        page.locator('summary').nth(1).click()
                        assert page.locator('details[open]').count() == 2
                    page.close()
                visual, modal = image_error(*shots), image_error(*panels)
                assert visual < .1, f'{filename} {width}px changed: {visual}'
                assert modal < .1, f'{filename} modal {width}px changed: {modal}'
                assert fonts[0] == fonts[1], 'Existing reservation font changed'
                report['regression'][str(width)][filename] = {'page_mean_channel_error': visual, 'dialog_mean_channel_error': modal, 'threshold_0_to_255': .1, 'fonts_unchanged': True}
                checkpoint()
                print(f'{filename} {width}px regression passed.', flush=True)
    page = browser.new_page(viewport={'width': 1440, 'height': 900})
    ready(page, 'index.html')
    page.wait_for_function("document.querySelector('.p-hero__progress').getAttribute('aria-label') === 'スライド 2 / 4'", timeout=10000)
    assert page.locator('.p-hero__slide.is-active').count() == 1
    assert page.locator('.p-hero__progress-bar.is-active').count() == 1
    report['slider'] = 'Automatic transition to slide 2; exactly one active slide/progress bar.'
    page.close()
    browser.close()
report['passed'] = True
checkpoint()
print('All selection checks passed.', flush=True)
