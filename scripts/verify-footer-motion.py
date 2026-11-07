#!/usr/bin/env python3
"""Check footer parallax and fixed-CTA guitar motion in Chrome.

Requires Playwright. Starts a local HTTP server unless --base-url is supplied.
Use --baseline-dir with a source snapshot to compare unchanged layout geometry.
iPhone Safari remains a separate physical-device check.
"""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--base-url')
parser.add_argument('--baseline-dir', type=Path)
parser.add_argument('--browser', default='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')
parser.add_argument('--output', type=Path, default=ROOT / 'artifacts/_local/footer-motion')
parser.add_argument('--only-regression', action='store_true', help='Reuse saved viewport results and run only regression checks.')
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=True)
report = {'viewports': {}, 'regression': {}, 'passed': False}
if args.only_regression and (args.output / 'verification.json').exists():
    report = json.loads((args.output / 'verification.json').read_text())
    report['passed'] = False
PAGES = ('index.html', 'selection.html', 'guide.html')
PHOTO = '.l-footer__visual'
CTA = '.js-fixed-reservation'
ICON = '.c-fixed-reservation picture > img'


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *values):
        pass


def context_for(browser, width, **options):
    context = browser.new_context(viewport={'width': width, 'height': 850}, **options)
    context.route('https://**/*', lambda route: route.abort())
    context.add_init_script('''
        if (window === window.top) {
            try { sessionStorage.setItem('hody:top-loading-seen', '1'); } catch {}
        }
    ''')
    return context


def settle(page):
    if page.locator('.js-selection-page').count():
        expect(page.locator('.js-selection-page')).to_have_attribute('aria-busy', 'false')
    page.evaluate('''async () => {
        await document.fonts.ready;
        await Promise.all([...document.images].map(image => {
            image.loading = 'eager';
            return image.decode().catch(() => {});
        }));
    }''')
    page.wait_for_timeout(100)


def ready(page, filename):
    page.goto(base_url + '/' + filename, wait_until='domcontentloaded')
    settle(page)


def scroll(page, y):
    page.evaluate('value => scrollTo({top: value, behavior: "instant"})', y)
    page.wait_for_timeout(100)


def geometry(page):
    return page.evaluate('''() => {
        const selectors = ['body > header', 'main', 'main > section', '.l-footer',
            '.l-footer__visual', '.l-footer__bottom', '.l-footer__brand', '.l-footer__address',
            '.l-footer__copyright'];
        return selectors.flatMap(selector => [...document.querySelectorAll(selector)].map(node => {
            const box = node.getBoundingClientRect();
            return [selector, ...[box.x, box.y + scrollY, box.width, box.height].map(n => Math.round(n * 100) / 100)];
        }));
    }''')


def bounds(page):
    return page.locator(PHOTO).evaluate('''node => {
        const box = node.getBoundingClientRect();
        const start = Math.max(0, box.top + scrollY - innerHeight);
        const end = Math.min(box.bottom + scrollY, document.documentElement.scrollHeight - innerHeight);
        return {start, end};
    }''')


def photo(page):
    return page.locator(PHOTO).evaluate('''node => {
        const box = node.getBoundingClientRect(), image = node.querySelector('img');
        const pixels = image.getBoundingClientRect(), style = getComputedStyle(image);
        return {height: box.height, width: box.width,
            imageWidth: pixels.width, imageHeight: pixels.height,
            topSpare: box.top - pixels.top, bottomSpare: pixels.bottom - box.bottom,
            leftSpare: box.left - pixels.left, rightSpare: pixels.right - box.right,
            offset: parseFloat(image.style.getPropertyValue('--footer-parallax-y')) || 0,
            transform: style.transform, position: style.objectPosition,
            enhanced: node.classList.contains('is-parallax')};
    }''')


def assert_covered(value):
    assert value['topSpare'] >= 1, value
    assert value['bottomSpare'] >= 1, value
    assert value['leftSpare'] >= -.1 and value['rightSpare'] >= -.1, value


def travel(page, width, label):
    # Form focus can start native smooth scrolling; cancel it before measuring endpoints.
    page.evaluate('''() => {
        document.activeElement?.blur();
        scrollTo({top: 0, behavior: 'instant'});
    }''')
    page.wait_for_function('Math.abs(scrollY) <= 1')
    page.wait_for_timeout(150)
    extent = bounds(page)
    assert extent['end'] > extent['start'], extent
    half = 30 if width <= 768 else 60
    values = []
    for name, y, target in (
        ('start', extent['start'] + 1, -half),
        ('middle', (extent['start'] + extent['end']) / 2, 0),
        ('end', extent['end'], half),
        ('reverse', (extent['start'] + extent['end']) / 2, 0),
    ):
        scroll(page, y)
        value = photo(page)
        if abs(value['offset'] - target) > .2:
            diagnostic = page.locator(PHOTO).evaluate('''node => ({
                scrollY, hidden: document.hidden, bodyClasses: document.body.className,
                classes: node.className, rect: node.getBoundingClientRect().toJSON()
            })''')
            diagnostic.update({'requestedY': y, 'bounds': extent})
            raise AssertionError((label, name, value, target, diagnostic))
        assert_covered(value)
        assert value['height'] == (487 if width <= 768 else 506), value
        values.append(value)
        if name in ('middle', 'end'):
            page.screenshot(path=str(args.output / f'{label}-{name}.png'))
    return values


def icon_sample(page, time):
    return page.locator(ICON).evaluate('''(image, time) => {
        const animation = image.getAnimations()[0];
        if (!animation) throw new Error('Guitar animation missing');
        animation.pause();
        animation.currentTime = time;
        const matrix = new DOMMatrix(getComputedStyle(image).transform);
        const selectors = ['.c-fixed-reservation', '.c-fixed-reservation__text', '.c-fixed-reservation__arrow'];
        return {angle: Math.atan2(matrix.b, matrix.a) * 180 / Math.PI,
            duration: animation.effect.getTiming().duration,
            boxes: selectors.map(selector => {
                const box = document.querySelector(selector).getBoundingClientRect();
                return [box.x, box.y, box.width, box.height];
            })};
    }''', time)


server = None
if args.base_url:
    base_url = args.base_url.rstrip('/')
else:
    server = ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, directory=str(ROOT)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base_url = 'http://127.0.0.1:' + str(server.server_port)

try:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=args.browser, headless=True)
        for filename in (() if args.only_regression else PAGES):
            for width in (375, 768, 1024, 1440):
                label = filename.replace('.html', '') + '-' + str(width)
                context = context_for(browser, width)
                page = context.new_page()
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                ready(page, filename)
                initial_geometry = geometry(page)
                original_position = photo(page)['position']
                if args.baseline_dir:
                    baseline = context.new_page()
                    baseline.route('**/' + filename, lambda route, request, name=filename: route.fulfill(
                        body=(args.baseline_dir / name).read_bytes(), content_type='text/html'))
                    baseline.route('**/css/style.css', lambda route: route.fulfill(
                        body=(args.baseline_dir / 'css/style.css').read_bytes(), content_type='text/css'))
                    ready(baseline, filename)
                    assert initial_geometry == geometry(baseline), label
                    assert original_position == photo(baseline)['position'], label
                    baseline.close()
                    page.bring_to_front()
                    page.wait_for_function('!document.hidden')
                    page.wait_for_timeout(100)
                values = travel(page, width, label)
                assert all(item['position'] == original_position for item in values)
                if filename != 'index.html' and width < 390:
                    assert values[0]['imageWidth'] == 390, values[0]

                # Body locking must keep the photograph still, then restore its position.
                frozen = photo(page)['offset']
                saved_scroll = page.evaluate('scrollY')
                page.locator('.js-open-reservation').first.evaluate('node => node.click()')
                page.wait_for_timeout(100)
                page.evaluate("dispatchEvent(new Event('resize'))")
                page.wait_for_timeout(80)
                assert photo(page)['offset'] == frozen, label
                assert page.locator(ICON).evaluate('node => node.getAnimations().length') == 0
                page.locator('.js-close-reservation').evaluate('node => node.click()')
                page.wait_for_timeout(100)
                assert abs(page.evaluate('scrollY') - saved_scroll) <= 1
                assert abs(photo(page)['offset'] - frozen) <= .1

                page.emulate_media(reduced_motion='reduce')
                page.wait_for_timeout(80)
                static = photo(page)
                assert not static['enhanced'] and static['transform'] == 'none'
                assert static['imageHeight'] == static['height']
                page.emulate_media(reduced_motion='no-preference')
                page.wait_for_timeout(80)
                assert photo(page)['enhanced']
                assert_covered(photo(page))

                # Sample the real CSS animation without waiting through every 3s cycle.
                scroll(page, 500)
                page.wait_for_timeout(450)
                expect(page.locator(CTA)).to_be_visible()
                neutral = icon_sample(page, 0)
                samples = []
                for time, target in ((2000, 0), (2100, 0), (2300, -9), (2500, 9), (2700, -4.5), (2850, 2.25), (3000, 0)):
                    sample = icon_sample(page, time)
                    assert sample['duration'] == 3000
                    assert abs(sample['angle'] - target) <= .05, (label, time, sample)
                    assert sample['boxes'] == neutral['boxes'], (label, time, sample)
                    samples.append([time, sample['angle']])
                page.locator(CTA).click()
                expect(page.locator('.p-reservation__panel')).to_be_visible()
                assert page.locator(ICON).evaluate('node => node.getAnimations().length') == 0
                page.locator('.js-close-reservation').click()
                page.wait_for_timeout(100)
                assert abs(page.evaluate('scrollY') - 500) <= 1
                assert abs(icon_sample(page, 0)['angle']) < .01
                page.emulate_media(reduced_motion='reduce')
                assert page.locator(ICON).evaluate('node => node.getAnimations().length') == 0
                page.emulate_media(reduced_motion='no-preference')
                scroll(page, 0)
                assert page.locator(ICON).evaluate('node => node.getAnimations().length') == 0

                assert not errors, (label, errors)
                report['viewports'][label] = {'photo': values, 'guitar': samples, 'layout_unchanged': True}
                print('PASS', label, 'layout, travel, coverage, modal, reduced motion, guitar cycle', flush=True)
                context.close()

        # Resize across the SP breakpoint, restore history, and change product-page height.
        context = context_for(browser, 1440)
        page = context.new_page()
        ready(page, 'selection.html')
        page.set_viewport_size({'width': 375, 'height': 850})
        settle(page)
        travel(page, 375, 'selection-resized')
        if not page.locator('.js-selection-form').is_visible():
            page.locator('.js-filter-toggle').click()
        page.locator('#filter-price_band').select_option('lt150000')
        page.locator('.js-selection-form').evaluate('node => node.requestSubmit()')
        settle(page)
        travel(page, 375, 'selection-filtered')
        # Check history independently of catalog filter/fold state, which is not persisted.
        ready(page, 'guide.html')
        extent = bounds(page)
        scroll(page, (extent['start'] + extent['end']) / 2)
        restored_scroll = page.evaluate('scrollY')
        restored_offset = photo(page)['offset']
        page.goto(base_url + '/selection.html', wait_until='domcontentloaded')
        page.go_back(wait_until='domcontentloaded')
        settle(page)
        assert abs(page.evaluate('scrollY') - restored_scroll) <= 1
        assert abs(photo(page)['offset'] - restored_offset) <= .2
        assert_covered(photo(page))
        report['regression']['resize_filter_history'] = True
        context.close()

        for name, context_options in (('missing_script', {}), ('javascript_disabled', {'java_script_enabled': False})):
            context = context_for(browser, 375, **context_options)
            page = context.new_page()
            if name == 'missing_script':
                page.route('**/js/footer-parallax.js', lambda route: route.abort())
            ready(page, 'guide.html')
            scroll(page, bounds(page)['end'])
            value = photo(page)
            assert not value['enhanced'] and value['transform'] == 'none'
            assert value['imageHeight'] == value['height']
            report['regression'][name] = True
            context.close()
        browser.close()
        report['passed'] = True
finally:
    (args.output / 'verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=4) + '\n')
    if server:
        server.shutdown()

print('Footer motion checks passed.', flush=True)
