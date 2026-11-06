#!/usr/bin/env python3
"""Verify the TOP loader and its handoff to the existing hero slider.

Requires Playwright/Pillow. Starts a local server unless --base-url is supplied.
Physical iPhone Safari verification remains a separate manual check.
"""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
import xml.etree.ElementTree as ET

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--base-url')
parser.add_argument('--browser', default='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')
parser.add_argument('--output', type=Path, default=ROOT / 'artifacts/_local/loading')
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=True)
report = {'viewports': {}, 'scenarios': {}, 'passed': False}


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *values):
        pass


def record(name, value=True):
    report['scenarios'][name] = value


def state(page):
    return page.evaluate('''() => {
        const bar = document.querySelector('.p-hero__progress-bar');
        const style = getComputedStyle(bar, '::after');
        const o = document.querySelector('.js-loading-o');
        const center = new DOMPoint(48.1891, 20.6685).matrixTransform(o.getScreenCTM());
        return {
            loading: document.documentElement.classList.contains('is-loading'),
            first: document.querySelector('.p-hero__slide').classList.contains('is-active'),
            animation: style.animationName, transform: style.transform,
            letters: Number(document.querySelector('.js-loading-letters').getAttribute('opacity') ?? 1),
            hole: Number(document.querySelector('.js-loading-hole').getAttribute('opacity')),
            center: [center.x, center.y],
            logoWidth: getComputedStyle(document.querySelector('.js-loading')).getPropertyValue('--loading-logo-width').trim(),
            scroll: scrollY
        };
    }''')


def fresh(browser, **options):
    context = browser.new_context(**options)
    # External font latency is unrelated to the loader's timing contract.
    context.route('https://fonts.googleapis.com/**', lambda route: route.abort())
    context.route('https://fonts.gstatic.com/**', lambda route: route.abort())
    context.add_init_script('''
        document.addEventListener('hody:loading-end', () => {
            window.loadingEndedAt = performance.now();
        });
    ''')
    return context


def finished(page):
    page.wait_for_function("!document.documentElement.classList.contains('is-loading')")
    expect(page.locator('.js-loading')).to_be_hidden()


def scenario(browser, name, setup=None, context_options=None):
    context = fresh(browser, viewport={'width': 375, 'height': 850}, **(context_options or {}))
    page = context.new_page()
    if setup:
        setup(page)
    page.goto(base_url + '/index.html', wait_until='domcontentloaded')
    return context, page


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
        for width in (375, 768, 1024, 1440):
            context = fresh(browser, viewport={'width': width, 'height': 850})
            page = context.new_page()
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.goto(base_url + '/index.html', wait_until='domcontentloaded')
            expect(page.locator('.js-loading')).to_be_visible()
            initial = state(page)
            assert initial['loading'] and initial['first']
            assert initial['animation'] == 'none'
            assert initial['transform'].startswith('matrix(0,')
            assert initial['logoWidth'] == ('220px' if width <= 768 else '280px')
            assert initial['letters'] > .95
            originals = [node.attrib['d'] for node in ET.parse(ROOT / 'assets/icons/logo-charcoal.svg').getroot()]
            actual = page.locator('.js-loading-logo path').evaluate_all('(nodes) => nodes.map(node => node.getAttribute("d"))')
            assert sorted(originals) == sorted(actual)
            page.screenshot(path=str(args.output / f'logo-{width}.png'))
            page.wait_for_function('''() =>
                Number(document.querySelector('.js-loading-letters').getAttribute('opacity')) < .01 &&
                Number(document.querySelector('.js-loading-hole').getAttribute('opacity')) === 1 &&
                document.documentElement.classList.contains('is-loading')
            ''')
            opening = state(page)
            assert opening['first'] and opening['animation'] == 'none'
            assert all(abs(a - b) < .1 for a, b in zip(initial['center'], opening['center']))
            page.screenshot(path=str(args.output / f'opening-{width}.png'))
            finished(page)
            assert page.evaluate('scrollY') == 0
            page.screenshot(path=str(args.output / f'finished-{width}.png'))
            assert not errors, errors
            report['viewports'][str(width)] = {'initial': initial, 'opening': opening}
            if width == 375:
                # The first slide must receive the full existing 5000ms after handoff.
                page.wait_for_function('performance.now() - window.loadingEndedAt >= 4650')
                assert page.locator('.p-hero__slide').first.evaluate('node => node.classList.contains("is-active")')
                page.wait_for_function("document.querySelectorAll('.p-hero__slide')[1].classList.contains('is-active')")
                elapsed = page.evaluate('performance.now() - window.loadingEndedAt')
                assert 4900 <= elapsed <= 5500, elapsed
                record('first_change_after_handoff_ms', elapsed)
                bar = page.locator('.p-hero__progress-bar').nth(1)
                assert bar.evaluate("node => getComputedStyle(node, '::after').animationDuration") == '5s'
                assert page.locator('.p-hero__slide').nth(1).evaluate('node => getComputedStyle(node).transitionDuration') == '.9s'.replace('.9', '0.9')
                page.reload(wait_until='domcontentloaded')
                assert state(page)['loading']
                finished(page)
                record('reload_replays')
                page.goto(base_url + '/guide.html')
                page.go_back(wait_until='domcontentloaded')
                finished(page)
                record('history_skip')
            context.close()

        for name, setup, options in (
            ('reduced_motion', None, {'reduced_motion': 'reduce'}),
            ('storage_unavailable', lambda page: page.add_init_script("Storage.prototype.getItem = () => { throw new Error('blocked'); };"), None),
            ('missing_script', lambda page: page.route('**/js/loading.js', lambda route: route.abort()), None),
            ('broken_script', lambda page: page.route('**/js/loading.js', lambda route: route.fulfill(body='throw new Error("test failure");', content_type='text/javascript')), None),
            ('image_not_ready', lambda page: page.add_init_script('HTMLImageElement.prototype.decode = () => new Promise(() => {});'), None),
        ):
            context, page = scenario(browser, name, setup, options)
            finished(page)
            assert page.locator('.p-hero__slide').first.evaluate('node => node.classList.contains("is-active")')
            if name in ('missing_script', 'broken_script'):
                assert page.evaluate('window.loadingEndedAt') <= 4650
            record(name)
            context.close()

        context = fresh(browser, viewport={'width': 375, 'height': 850}, java_script_enabled=False)
        page = context.new_page()
        page.goto(base_url + '/index.html')
        expect(page.locator('.js-loading')).to_be_hidden()
        expect(page.locator('.p-hero__title')).to_be_visible()
        record('javascript_disabled')
        context.close()

        context = fresh(browser, viewport={'width': 375, 'height': 850})
        page = context.new_page()
        page.goto(base_url + '/index.html#store')
        finished(page)
        assert page.evaluate('location.hash') == '#store'
        page.wait_for_function('scrollY > 0')
        record('anchor_preserved')
        context.close()

        # The first pointer action must both dismiss the loader and operate the menu.
        context, page = scenario(browser, 'first_interaction')
        assert state(page)['loading']
        page.locator('.js-menu-open').click()
        finished(page)
        assert page.locator('.js-mobile-menu').evaluate('node => node.classList.contains("is-open")')
        page.locator('.p-mobile-menu__reserve').click()
        assert page.locator('.js-reservation').evaluate('node => node.classList.contains("is-open")')
        page.locator('.js-close-reservation').click()
        assert page.evaluate('scrollY') == 0
        page.locator('.js-finder-start').click()
        for _ in range(3):
            page.locator('.js-finder-answer').first.click()
        expect(page.locator('.p-finder')).to_have_attribute('data-finder-step', 'result')
        page.evaluate('scrollTo({top: 1000, behavior: "instant"})')
        expect(page.locator('.js-fixed-reservation')).to_be_visible()
        saved_scroll = page.evaluate('scrollY')
        page.locator('.js-fixed-reservation').click()
        expect(page.locator('.p-reservation__panel')).to_be_visible()
        page.locator('.js-close-reservation').click()
        assert abs(page.evaluate('scrollY') - saved_scroll) <= 1
        record('menu_reservation_finder_cta_scroll_regression')
        context.close()
        browser.close()
        report['passed'] = True
finally:
    (args.output / 'verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=4) + '\n')
    if server:
        server.shutdown()

print(json.dumps(report, ensure_ascii=False, indent=2))
