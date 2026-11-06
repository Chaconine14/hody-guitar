#!/usr/bin/env python3
"""Finder checks and screenshots. Requires Playwright/Pillow and a local HTTP server."""
import argparse
import collections
import itertools
import json
from pathlib import Path

from PIL import Image, ImageChops, ImageStat, ImageDraw
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--base-url', default='http://127.0.0.1:8767')
parser.add_argument('--baseline-dir', type=Path)
parser.add_argument('--output', type=Path, default=ROOT / 'artifacts/finder')
parser.add_argument('--browser', default='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')
parser.add_argument('--only-regression', action='store_true')
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=True)
master = json.loads((ROOT / 'data/products.json').read_text())
products = master['products']
report = {'logic': {}, 'viewports': {}, 'failures': {}, 'regression': {}}
if args.only_regression and (args.output / 'verification.json').exists():
    report = json.loads((args.output / 'verification.json').read_text())

# 手計算で確認した期待順位。音色→サイズ→弾き方の順に4×4×3を網羅。
PAIRS = {
    'A': ['gibson-b-25', 'taylor-gs-mini'],
    'B': ['taylor-114ce', 'taylor-214ce'],
    'C': ['gibson-j-45', 'martin-d-28'],
    'D': ['martin-d-28', 'yamaha-ll16-are'],
    'E': ['taylor-114ce', 'gibson-b-25'],
    'F': ['gibson-b-25', 'martin-000-18'],
    'G': ['martin-000-18', 'martin-000-28'],
    'H': ['martin-d-28', 'taylor-114ce']
}
MATRIX = [
    ['AAA', 'BBB', 'CDD', 'EEE'],
    ['FFF', 'BBB', 'CDD', 'CDD'],
    ['GGG', 'BBB', 'CDD', 'CHH'],
    ['FFF', 'BBB', 'CDD', 'CHB']
]
TONES = ['明るい', '力強い', 'バランス', 'any']
SIZES = ['小さめ', '標準', '大きめ', 'any']
STYLES = ['ストローク', '指弾き', 'any']
cases = []
for ti, tone in enumerate(TONES):
    for si, size in enumerate(SIZES):
        for pi, style in enumerate(STYLES):
            pair = MATRIX[ti][si][pi]
            type_id = {'A': 'compact', 'F': 'compact', 'G': 'compact', 'C': 'large', 'D': 'large'}.get(pair)
            if not type_id:
                type_id = ['stroke', 'finger', 'bright' if pair == 'E' else 'allround'][pi]
            cases.append({'answers': {'tone': tone, 'size': size, 'style': style}, 'expected_ids': PAIRS[pair], 'expected_type': type_id})


def checkpoint():
    (args.output / 'verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=4) + '\n')


def ready(page, filename='index.html'):
    page.goto(args.base_url.rstrip('/') + '/' + filename)
    page.evaluate('document.fonts.ready')


def images_ready(page):
    page.evaluate('''async () => {
        await document.fonts.ready;
        await Promise.all([...document.querySelectorAll('.p-finder img')].map(image => image.decode().catch(() => {})));
    }''')


def answer(page, value):
    page.locator(f'.js-finder-answer[data-answer="{value}"]').click()


def result_ready(page):
    page.wait_for_selector('.p-finder[data-finder-step="result"] .js-finder-screen[aria-busy="false"]')


def run_flow(page, answers):
    start = page.locator('.js-finder-start')
    if start.count():
        start.click()
    else:
        page.locator('.js-finder-retry').click()
    for key in ('tone', 'size', 'style'):
        answer(page, answers[key])
    result_ready(page)


def ids(page):
    return page.locator('.p-finder__card').evaluate_all('nodes => nodes.map(node => node.dataset.productId)')


def layout(page):
    overflow = page.locator('.p-finder').evaluate('''root => [...root.querySelectorAll('*')].filter(el =>
        el.getClientRects().length && !el.classList.contains('p-finder__status') &&
        el.scrollWidth > el.clientWidth + 1).map(el => el.className)''')
    assert not overflow, f'Finder overflow: {overflow}'
    assert not page.locator('body').evaluate('body => body.classList.contains("is-locked")'), 'Inline diagnosis locked the page'
    assert page.locator('main > section:visible').count() == 8, 'Other TOP sections disappeared'


def shot(page, filename):
    images_ready(page)
    page.mouse.move(0, 0)
    page.locator('.p-finder').screenshot(path=str(args.output / filename))


def geometry(page):
    return page.locator('.p-finder').evaluate('''root => {
        const top = root.getBoundingClientRect().top;
        return Object.fromEntries(['.p-finder__inner','.p-finder__head','.p-finder__answers','.p-finder__photo','.p-finder__actions'].map(s => {
            const r = root.querySelector(s)?.getBoundingClientRect();
            return [s, r ? {x:r.x,y:r.y-top,width:r.width,height:r.height} : null];
        }));
    }''')


def image_error(first, second):
    a, b = Image.open(first).convert('RGB'), Image.open(second).convert('RGB')
    assert a.size == b.size, f'Dimensions changed: {a.size} / {b.size}'
    return max(ImageStat.Stat(ImageChops.difference(a, b)).mean)


def non_image_error(first, second, boxes):
    images = [Image.open(path).convert('RGB') for path in (first,second)]
    for image in images:
        draw = ImageDraw.Draw(image)
        for box in boxes:
            draw.rectangle((box['x']-1,box['y']-1,box['x']+box['width']+1,box['y']+box['height']+1),fill='black')
    return max(ImageStat.Stat(ImageChops.difference(*images)).mean)


if args.baseline_dir:
    for name in ['data/products.json', 'data/products.csv', 'data/test_scenarios.json', 'js/menu.js', 'js/slider.js']:
        assert (ROOT / name).read_bytes() == (args.baseline_dir / name).read_bytes(), f'Unrelated file changed: {name}'
    report['unchanged_files'] = ['product JSON/CSV/scenarios', 'menu.js', 'slider.js']

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=args.browser, headless=True)
    if not args.only_regression:
        page = browser.new_page(viewport={'width': 1440, 'height': 900}, reduced_motion='reduce')
        ready(page)
        results = page.evaluate('''async ({products,cases}) => {
            const logic = await import('./js/finder-logic.js');
            const before = JSON.stringify(products);
            const results = cases.map(c => {
                const first = logic.recommendGuitars(products,c.answers);
                const second = logic.recommendGuitars([...products].reverse(),c.answers);
                if (JSON.stringify(first) !== JSON.stringify(second)) throw new Error('Unstable ranking');
                return {ids:first.recommendations.map(r=>r.product.id), scores:first.recommendations.map(r=>r.score), type:first.typeId};
            });
            if (before !== JSON.stringify(products)) throw new Error('Master was mutated');
            const product = {id:'one',brand:'Test',model:'One',sort_order:1,body_size:'標準',tone_impressions:['明るい'],playing_styles:['ストローク']};
            const base = {tone:'any',size:'any',style:'指弾き'};
            const points = [logic.scoreProduct(product,base),logic.scoreProduct(product,{...base,tone:'明るい'}),logic.scoreProduct(product,{...base,size:'標準'}),logic.scoreProduct(product,{...base,style:'ストローク'}),logic.scoreProduct(product,{...base,style:'any'}),logic.scoreProduct({...product,playing_styles:['ストローク','指弾き']},{...base,style:'any'})];
            const incomplete = logic.recommendGuitars(products,{tone:null,size:'any',style:'any'});
            const empty = logic.recommendGuitars([],base);
            const zero = logic.recommendGuitars([product],base);
            const duplicate = logic.recommendGuitars([product,product],{...base,style:'ストローク'});
            return {results,points,incomplete,empty,zero,duplicateIds:duplicate.recommendations.map(r=>r.product.id)};
        }''', {'products': products, 'cases': cases})
        for case, result in zip(cases, results['results']):
            assert result['ids'] == case['expected_ids'], (case, result)
            assert result['type'] == case['expected_type'], (case, result)
            assert len(set(result['ids'])) == 2
        assert results['points'] == [0,3,4,2,1,3]
        assert results['incomplete']['status'] == 'incomplete'
        assert results['empty']['status'] == results['zero']['status'] == 'no-candidates'
        assert results['duplicateIds'] == ['one']
        report['logic'] = {'passed_patterns': 48, 'point_checks': results['points'], 'results': [dict(case, actual=result) for case, result in zip(cases, results['results'])], 'type_counts': dict(collections.Counter(r['type'] for r in results['results']))}
        checkpoint()
        page.close()
        print('Logic: all 48 golden cases, points, incomplete/empty/duplicate and non-mutation checks passed.', flush=True)

    for width in (() if args.only_regression else (1440,375,320,768,769,1024)):
        page = browser.new_page(viewport={'width':width,'height':900}, reduced_motion='reduce')
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        ready(page)
        layout(page)
        if width in (1440,375):
            label = 'pc' if width == 1440 else 'sp'
            shot(page, f'{label}-intro.png')
        page.locator('.js-finder-start').click()
        for step, value in enumerate(['力強い','大きめ','any']):
            layout(page)
            buttons = page.locator('.js-finder-answer')
            assert buttons.count() == (4 if step < 2 else 3)
            positions = [buttons.nth(i).bounding_box() for i in range(buttons.count())]
            if width > 768:
                assert abs(positions[0]['y'] - positions[1]['y']) < 1
                if step < 2:assert positions[2]['y'] > positions[0]['y']
                else:assert abs(positions[0]['y'] - positions[2]['y']) < 1
            else:
                assert all(positions[i+1]['y'] > positions[i]['y'] for i in range(buttons.count()-1))
            expect(page.locator('.p-finder__question-title')).to_be_focused()
            fixed = page.locator('.js-fixed-reservation')
            expect(fixed).to_have_count(1)
            assert page.locator('.js-reservation-hero').evaluate('el => el.getBoundingClientRect().bottom <= innerHeight * .5')
            expect(fixed).to_be_visible()
            assert not fixed.evaluate('el => el.inert')
            if width in (1440,375):shot(page, f'{label}-q{step+1}.png')
            answer(page,value)
        result_ready(page)
        layout(page)
        assert ids(page) == ['martin-d-28','yamaha-ll16-are']
        photos = page.locator('.p-finder__photo')
        assert photos.nth(0).bounding_box()['y'] == photos.nth(1).bounding_box()['y']
        photo_sizes = [photos.nth(i).bounding_box() for i in range(2)]
        for size in photo_sizes:assert abs(size['height'] / size['width'] - 1.25) < .01
        if width in (1440,375):shot(page, f'{label}-result.png')
        details = {'passed': True, 'result_geometry': geometry(page)}
        # Previous answers remain editable; restart clears every pressed state.
        page.locator('.js-finder-back').click()
        expect(page.locator('[data-answer="any"]')).to_have_attribute('aria-pressed','true')
        page.locator('.js-finder-back').click()
        expect(page.locator('[data-answer="大きめ"]')).to_have_attribute('aria-pressed','true')
        answer(page,'小さめ')
        answer(page,'指弾き')
        result_ready(page)
        assert ids(page) == ['gibson-b-25','martin-000-18']
        page.locator('.js-finder-retry').click()
        assert page.locator('.js-finder-answer[aria-pressed="true"]').count() == 0
        assert page.locator('.js-finder-back').count() == 0
        page.keyboard.press('Escape')
        assert page.locator('.p-finder').get_attribute('data-finder-step') == '1'
        page.locator('[data-answer="any"]').focus()
        page.keyboard.press('Enter')
        page.locator('[data-answer="any"]').focus()
        page.keyboard.press('Space')
        answer(page,'any')
        result_ready(page)
        assert ids(page) == ['taylor-114ce','taylor-214ce']
        # Reservation context: both IDs, name/selection, second choice, focus and ordinary options restored.
        original_options = page.locator('#reserve-product option').evaluate_all('nodes=>nodes.map(n=>n.value)')
        original_value = page.locator('#reserve-product').input_value()
        page.locator('.js-finder-reserve').click()
        expect(page.locator('.js-close-reservation')).to_be_visible()
        options = page.locator('#reserve-product option').evaluate_all('nodes=>nodes.map(n=>({value:n.value,id:n.dataset.productId}))')
        assert [o.get('id') for o in options[1:]] == ['taylor-114ce','taylor-214ce']
        assert page.locator('#reserve-product').input_value() == 'Taylor 114ce'
        page.select_option('#reserve-product','Taylor 214ce')
        page.locator('#reserve-name').fill('診断テスト')
        page.keyboard.press('Escape')
        expect(page.locator('.js-finder-reserve')).to_be_focused()
        assert page.locator('#reserve-product option').evaluate_all('nodes=>nodes.map(n=>n.value)') == original_options
        assert page.locator('#reserve-product').input_value() == original_value
        assert page.locator('#reserve-name').input_value() == '診断テスト'
        layout(page)
        if width in (1440,375):
            for case in cases:
                run_flow(page,case['answers'])
                assert ids(page) == case['expected_ids'], case
                assert page.locator('.p-finder').get_attribute('data-finder-type') == case['expected_type']
                associations = page.locator('.p-finder__card').evaluate_all('nodes => nodes.map(n=>({id:n.dataset.productId,src:n.querySelector("img").getAttribute("src"),brand:n.querySelector(".p-finder__brand").textContent,model:n.querySelector("h4").textContent}))')
                for card in associations:
                    product = next(product for product in products if product['id'] == card['id'])
                    assert all(card[k] == product[{'src':'image_src'}.get(k,k)] for k in ['src','brand','model'])
            details['ui_patterns'] = 48
            # Save all-unknown and compact examples in addition to the large-body comparison.
            shot(page,f'{label}-result-allround.png')
            run_flow(page,{'tone':'明るい','size':'小さめ','style':'指弾き'})
            shot(page,f'{label}-result-compact.png')
        assert not errors, errors
        report['viewports'][str(width)] = details
        checkpoint()
        page.close()
        print(f'{width}px: inline layout, keyboard, back/reset, images and reservation passed.',flush=True)

    if not args.only_regression:
        for mode in ['http','invalid-json','empty','one','missing-image','broken-image','long-content']:
            page = browser.new_page(viewport={'width':320,'height':900},reduced_motion='reduce')
            data = json.loads(json.dumps(master))
            if mode == 'empty':data['products'] = []
            if mode == 'one':data['products'] = [data['products'][1]]
            if mode in ('missing-image','broken-image'):
                for product in data['products']:product['image_src'] = '' if mode == 'missing-image' else 'assets/images/not-found-finder-test.jpg'
            if mode == 'long-content':
                for product in data['products']:
                    product['brand'] *= 5
                    product['model'] *= 12
            attempts = [0]
            def route_catalog(route):
                attempts[0] += 1
                if mode == 'http' and attempts[0] == 1:route.fulfill(status=503,body='Unavailable')
                elif mode == 'invalid-json':route.fulfill(status=200,body='invalid',content_type='application/json')
                else:route.fulfill(json=data)
            page.route('**/data/products.json',route_catalog)
            ready(page)
            if mode == 'long-content':
                page.evaluate('''async()=>{const {RESULT_TYPES}=await import('./js/finder-config.js');RESULT_TYPES.large.name=RESULT_TYPES.large.name.repeat(4);RESULT_TYPES.large.description=RESULT_TYPES.large.description.repeat(5)}''')
            run_flow(page,{'tone':'力強い','size':'大きめ','style':'any'})
            layout(page)
            if mode in ('http','invalid-json','empty'):
                assert not ids(page)
                expect(page.locator('.js-finder-reserve')).to_be_disabled()
                expect(page.locator('.p-finder__message')).to_be_visible()
                if mode == 'http':
                    run_flow(page,{'tone':'力強い','size':'大きめ','style':'any'})
                    assert len(ids(page)) == 2 and attempts[0] == 2
            elif mode == 'one':
                assert ids(page) == ['martin-d-28']
            elif mode in ('missing-image','broken-image'):
                expect(page.locator('.p-finder__image-fallback').first).to_be_visible()
                assert len(ids(page)) == 2
                for item in page.locator('.p-finder__photo').all():assert abs(item.bounding_box()['height']/item.bounding_box()['width']-1.25)<.01
            else:
                assert len(ids(page)) == 2
                assert page.locator('.p-finder__inner').bounding_box()['height'] > 1000
            report['failures'][mode] = 'passed'
            checkpoint()
            page.close()
        # Delayed response must not replace a question after the user goes back.
        page = browser.new_page(reduced_motion='reduce')
        pending = []
        page.route('**/data/products.json',lambda route:pending.append(route))
        ready(page)
        page.locator('.js-finder-start').click()
        for value in ['力強い','大きめ','any']:answer(page,value)
        expect(page.locator('.js-finder-screen')).to_have_attribute('aria-busy','true')
        page.locator('.js-finder-back').click()
        assert pending
        pending[0].fulfill(json=master)
        page.wait_for_timeout(100)
        assert page.locator('.p-finder').get_attribute('data-finder-step') == '3'
        answer(page,'any')
        result_ready(page)
        assert ids(page) == ['martin-d-28','yamaha-ll16-are']
        report['failures']['stale-response'] = 'passed'
        page.close()
        checkpoint()
        print('Fetch errors, retry, 0/1 candidate, missing/broken images, long content and delayed response passed.',flush=True)

    if args.baseline_dir:
        # Compare unaffected TOP sections individually: Finder height changes only move later sections.
        sections = ['.p-hero','.p-selection','.p-about','.p-staff','.p-guide','.p-store','.p-instagram','.l-footer']
        for width in (1440,375):
            snapshots = []
            metrics = []
            for original in (True,False):
                page = browser.new_page(viewport={'width':width,'height':900},reduced_motion='reduce')
                if original:
                    for resource,mime in [('index.html','text/html'),('css/style.css','text/css'),('js/reservation.js','text/javascript')]:
                        body = (args.baseline_dir/resource).read_bytes()
                        page.route('**/'+resource,lambda route,request,body=body,mime=mime:route.fulfill(body=body,content_type=mime))
                ready(page)
                page.evaluate('''async()=>{for(const i of document.images){i.loading='eager';await i.decode().catch(()=>{})}}''')
                images = {}
                measurements = {}
                for selector in sections:
                    measurements[selector] = page.locator(selector).evaluate('''root => {
                        const r=root.getBoundingClientRect();
                        return [...root.querySelectorAll('*')].map(el=>{
                            const b=el.getBoundingClientRect(),c=getComputedStyle(el);
                            return {tag:el.tagName,x:b.x-r.x,y:b.y-r.y,width:b.width,height:b.height,font:c.font,fontFamily:c.fontFamily,color:c.color,src:el.getAttribute('src'),fit:c.objectFit,position:c.objectPosition};
                        });
                    }''')
                    target = args.output/f'regression-{selector[1:]}-{width}-{"before" if original else "after"}.png'
                    page.mouse.move(0,0)
                    page.locator(selector).screenshot(path=str(target))
                    images[selector] = target
                if width == 375:
                    page.locator('.js-menu-open').click()
                    page.locator('.p-mobile-menu__reserve').click()
                else:page.locator('.l-header__reserve').click()
                expect(page.locator('.js-close-reservation')).to_be_visible()
                page.wait_for_timeout(100)
                target = args.output/f'regression-reservation-{width}-{"before" if original else "after"}.png'
                page.mouse.move(0,0)
                page.locator('.p-reservation__panel').screenshot(path=str(target))
                images['reservation'] = target
                snapshots.append(images)
                metrics.append(measurements)
                page.close()
            errors = {name:image_error(snapshots[0][name],snapshots[1][name]) for name in snapshots[0]}
            assert metrics[0] == metrics[1], 'Unaffected geometry/font/color/image association changed'
            masked = {name:non_image_error(snapshots[0][name],snapshots[1][name],[box for box in metrics[0][name] if box['tag']=='IMG']) for name in sections}
            # Chrome can resample photographs differently between contexts. Text/layout remains strict.
            assert max(masked.values()) < .1, f'TOP text/layout regression {width}: {masked}'
            assert max(errors.values()) < 1, f'TOP photograph regression {width}: {errors}'
            assert errors['reservation'] < .1, f'Reservation regression {width}'
            report['regression'][str(width)] = {'mean_channel_errors_0_to_255':errors,'non_image_errors':masked,'geometry_fonts_colors_and_image_sources_identical':True,'non_image_threshold':.1,'photograph_threshold':1,'reservation_threshold':.1}
            checkpoint()
            print(f'TOP {width}px: all unaffected sections and ordinary reservation comparison passed.',flush=True)
    browser.close()
report['passed'] = True
checkpoint()
print('All finder checks passed.',flush=True)
