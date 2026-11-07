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
import time
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
    # Keep the normal checks deterministic; a separate scenario delays font CSS.
    context.route('https://fonts.googleapis.com/**', lambda route: route.abort())
    context.route('https://fonts.gstatic.com/**', lambda route: route.abort())
    context.add_init_script('''
        const key = 'hody:top-loading-seen';
        const write = Storage.prototype.setItem;
        window.loadingAudit = {starts: [], ends: [], writes: [], preparedAt: null};
        window.readLoadingSeen = () => sessionStorage[key] ?? null;
        Storage.prototype.setItem = function(name, value) {
            const result = write.call(this, name, value);
            if (this === sessionStorage && name === key) {
                window.loadingAudit.writes.push({at: performance.now(), value: String(value)});
            }
            return result;
        };
        new MutationObserver(() => {
            if (window.loadingAudit.preparedAt === null &&
                document.documentElement?.classList.contains('is-loading')) {
                window.loadingAudit.preparedAt = performance.now();
            }
        }).observe(document, {subtree: true, attributes: true, attributeFilter: ['class']});
        document.addEventListener('hody:loading-start', () => {
            window.loadingAudit.starts.push(performance.now());
        });
        document.addEventListener('hody:loading-end', () => {
            window.loadingEndedAt = performance.now();
            window.loadingAudit.ends.push(window.loadingEndedAt);
        });
    ''')
    return context


def finished(page):
    # The failsafe scenario deliberately stops RAF; polling must remain independent.
    page.wait_for_function("!document.documentElement.classList.contains('is-loading')", polling=50)
    expect(page.locator('.js-loading')).to_be_hidden()


def started(page):
    page.wait_for_function('window.loadingAudit.starts.length === 1', polling=50)
    expect(page.locator('.js-loading')).to_be_visible()
    audit = page.evaluate('window.loadingAudit')
    assert page.evaluate('window.readLoadingSeen()') == '1'
    assert len(audit['writes']) == 1, audit
    assert abs(audit['writes'][0]['at'] - audit['starts'][0]) < 100, audit


def full_playback(page):
    started(page)
    finished(page)
    audit = page.evaluate('window.loadingAudit')
    assert len(audit['starts']) == len(audit['ends']) == 1, audit
    elapsed = audit['ends'][0] - audit['starts'][0]
    assert 3900 <= elapsed <= 4300, audit
    return elapsed


def skipped(page, preparation_timeout=False, rejected_start=False):
    finished(page)
    audit = page.evaluate('window.loadingAudit')
    assert len(audit['starts']) == (1 if rejected_start else 0), audit
    assert not audit['writes'], audit
    assert page.evaluate('window.readLoadingSeen()') is None
    if preparation_timeout:
        assert len(audit['ends']) == 1 and audit['preparedAt'] is not None, audit
        elapsed = audit['ends'][0] - audit['preparedAt']
        assert 1900 <= elapsed <= 2400, audit
    return audit


def delay_resource(page, pattern, milliseconds, body=None):
    def delayed(route):
        time.sleep(milliseconds / 1000)
        if body is None:
            route.continue_()
        else:
            route.fulfill(body=body, content_type='text/css')
    page.route(pattern, delayed)


def controlled_visibility(page, hidden=False):
    # Browser-side simulation only; physical Safari lifecycle still needs testing.
    page.add_init_script('''
        window.loadingTestHidden = %s;
        Object.defineProperty(document, 'hidden', {get: () => window.loadingTestHidden});
        Object.defineProperty(document, 'visibilityState', {
            get: () => window.loadingTestHidden ? 'hidden' : 'visible'
        });
        window.setLoadingTestHidden = hidden => {
            window.loadingTestHidden = hidden;
            document.dispatchEvent(new Event('visibilitychange'));
        };
    ''' % ('true' if hidden else 'false'))


def gated_decode(page):
    page.add_init_script('''
        const decode = HTMLImageElement.prototype.decode;
        const gate = new Promise(resolve => { window.releaseLoadingDecode = resolve; });
        HTMLImageElement.prototype.decode = function() {
            return Promise.all([decode.call(this), gate]);
        };
    ''')


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
        for width in (375, 390, 768, 1024, 1440):
            context = fresh(browser, viewport={'width': width, 'height': 850})
            page = context.new_page()
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.goto(base_url + '/index.html', wait_until='domcontentloaded')
            started(page)
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
            audit = page.evaluate('window.loadingAudit')
            preparation_ms = audit['starts'][0] - audit['preparedAt']
            playback_ms = audit['ends'][0] - audit['starts'][0]
            assert 0 <= preparation_ms < 1000, audit
            assert 3900 <= playback_ms <= 4300, audit
            assert page.evaluate('scrollY') == 0
            page.screenshot(path=str(args.output / f'finished-{width}.png'))
            assert not errors, errors
            report['viewports'][str(width)] = {
                'initial': initial, 'opening': opening,
                'preparation_ms': preparation_ms, 'playback_ms': playback_ms,
            }
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
                replay_ms = full_playback(page)
                record('reload_replays')
                record('reload_full_duration_ms', replay_ms)
                page.goto(base_url + '/guide.html')
                page.goto(base_url + '/index.html', wait_until='domcontentloaded')
                finished(page)
                assert not page.evaluate('window.loadingAudit.starts')
                assert page.evaluate('window.readLoadingSeen()') == '1'
                record('normal_revisit_skip')
                page.goto(base_url + '/guide.html')
                page.go_back(wait_until='domcontentloaded')
                finished(page)
                assert not page.evaluate('window.loadingAudit.starts')
                record('history_skip')
            context.close()

        for name, setup, options, timeout in (
            ('reduced_motion', None, {'reduced_motion': 'reduce'}, False),
            ('storage_unavailable', lambda page: page.add_init_script("Storage.prototype.getItem = () => { throw new Error('blocked'); };"), None, False),
            ('storage_write_rejected', lambda page: page.add_init_script("Storage.prototype.setItem = () => { throw new Error('blocked'); };"), None, False),
            ('missing_script', lambda page: page.route('**/js/loading.js', lambda route: route.abort()), None, True),
            ('missing_main_css', lambda page: page.route('**/css/style.css', lambda route: route.abort()), None, False),
            ('broken_script', lambda page: page.route('**/js/loading.js', lambda route: route.fulfill(body='throw new Error("test failure");', content_type='text/javascript')), None, True),
            ('image_not_ready', gated_decode, None, True),
            ('image_decode_failed', lambda page: page.add_init_script('HTMLImageElement.prototype.decode = () => Promise.reject(new Error("decode failed"));'), None, False),
            ('missing_image', lambda page: page.route('**/assets/images/top_slider01.jpg', lambda route: route.abort()), None, False),
        ):
            context, page = scenario(browser, name, setup, options)
            skipped(page, preparation_timeout=timeout, rejected_start=name == 'storage_write_rejected')
            assert page.locator('.p-hero__slide').first.evaluate('node => node.classList.contains("is-active")')
            record(name)
            context.close()

        # Loading immediately after readiness keeps the original full animation,
        # even when the first request or decode consumes most of the preparation budget.
        for name, setup in (
            ('script_delayed_1500ms', lambda page: delay_resource(page, '**/js/loading.js', 1500)),
            ('image_delayed_1500ms', lambda page: delay_resource(page, '**/assets/images/top_slider01.jpg', 1500)),
            ('decode_delayed_1500ms', lambda page: page.add_init_script('''
                const decode = HTMLImageElement.prototype.decode;
                HTMLImageElement.prototype.decode = function() {
                    return Promise.all([decode.call(this), new Promise(resolve => setTimeout(resolve, 1500))]);
                };
            ''')),
            ('font_css_delayed_1500ms', lambda page: delay_resource(page, 'https://fonts.googleapis.com/**', 1500, body='')),
            ('main_css_delayed_1500ms', lambda page: delay_resource(page, '**/css/style.css', 1500)),
        ):
            context, page = scenario(browser, name, setup)
            record(name, {'playback_ms': full_playback(page)})
            context.close()

        # Late resources must not resurrect a loader whose preparation timed out.
        for name, pattern in (
            ('script_late_completion', '**/js/loading.js'),
            ('image_late_completion', '**/assets/images/top_slider01.jpg'),
            ('main_css_late_completion', '**/css/style.css'),
        ):
            context, page = scenario(browser, name, lambda page: delay_resource(page, pattern, 2600))
            skipped(page, preparation_timeout=True)
            page.wait_for_timeout(700)
            skipped(page)
            record(name)
            context.close()

        def delayed_following_defer(page):
            def delayed(route):
                response = route.fetch()
                time.sleep(1.5)
                route.fulfill(response=response, body=(
                    'window.followingDeferExecutedAt = performance.now();\n' + response.text()
                ))
            page.route('**/assets/vendor/flatpickr/flatpickr.min.js', delayed)

        context, page = scenario(browser, 'following_defer_delayed_1500ms', delayed_following_defer)
        started(page)
        audit = page.evaluate('window.loadingAudit')
        following_at = page.evaluate('window.followingDeferExecutedAt')
        preparation_ms = audit['starts'][0] - audit['preparedAt']
        assert 0 <= preparation_ms < 1000, audit
        assert following_at - audit['starts'][0] >= 1000, {'audit': audit, 'following_at': following_at}
        record('following_defer_delayed_1500ms', {
            'preparation_ms': preparation_ms,
            'following_defer_after_start_ms': following_at - audit['starts'][0],
            'playback_ms': full_playback(page),
        })
        context.close()

        # The timeout leaves the tab eligible for a later normal TOP visit.
        context, page = scenario(browser, 'retry_after_preparation_timeout', gated_decode)
        skipped(page, preparation_timeout=True)
        page.evaluate('window.releaseLoadingDecode()')
        page.wait_for_timeout(100)
        skipped(page)
        # Navigate in the same tab so the missing seen flag is tested without reload.
        page.goto(base_url + '/guide.html')
        page.goto(base_url + '/index.html', wait_until='domcontentloaded')
        # The init script installs a fresh gate, so release it for this retry.
        page.evaluate('window.releaseLoadingDecode()')
        record('retry_after_preparation_timeout', {'playback_ms': full_playback(page)})
        context.close()

        context, page = scenario(browser, 'initial_hidden', lambda page: controlled_visibility(page, hidden=True))
        page.wait_for_timeout(2200)
        assert page.evaluate('document.documentElement.classList.contains("is-loading-pending")')
        assert not page.evaluate('window.loadingAudit.starts')
        assert page.evaluate('window.readLoadingSeen()') is None
        page.evaluate('window.setLoadingTestHidden(false)')
        record('initial_hidden', {'playback_ms': full_playback(page)})
        context.close()

        def hidden_preparation(page):
            controlled_visibility(page)
            gated_decode(page)

        context, page = scenario(browser, 'hidden_preparation_resume', hidden_preparation)
        page.wait_for_timeout(700)
        page.evaluate('window.setLoadingTestHidden(true)')
        page.wait_for_timeout(2200)
        assert page.evaluate('document.documentElement.classList.contains("is-loading-pending")')
        assert page.evaluate('window.readLoadingSeen()') is None
        page.evaluate('window.releaseLoadingDecode()')
        page.wait_for_timeout(100)
        assert not page.evaluate('window.loadingAudit.starts')
        page.evaluate('window.setLoadingTestHidden(false)')
        record('hidden_preparation_resume', {'playback_ms': full_playback(page)})
        context.close()

        context, page = scenario(browser, 'preparation_visible_time_budget', hidden_preparation)
        page.wait_for_timeout(700)
        page.evaluate('window.setLoadingTestHidden(true)')
        page.wait_for_timeout(2200)
        assert page.evaluate('document.documentElement.classList.contains("is-loading-pending")')
        resumed_at = page.evaluate('''() => {
            window.setLoadingTestHidden(false);
            return performance.now();
        }''')
        audit = skipped(page)
        remaining = audit['ends'][0] - resumed_at
        assert 950 <= remaining <= 1500, {'remaining_ms': remaining, 'audit': audit}
        record('preparation_visible_time_budget', {'remaining_ms': remaining})
        context.close()

        context, page = scenario(browser, 'hidden_after_start', controlled_visibility)
        started(page)
        page.evaluate('window.setLoadingTestHidden(true)')
        finished(page)
        page.evaluate('window.setLoadingTestHidden(false)')
        page.wait_for_timeout(100)
        assert len(page.evaluate('window.loadingAudit.starts')) == 1
        assert page.evaluate('window.readLoadingSeen()') == '1'
        record('hidden_after_start')
        context.close()

        context, page = scenario(browser, 'playback_failsafe', lambda page: page.add_init_script('''
            document.addEventListener('hody:loading-start', () => {
                window.requestAnimationFrame = () => 0;
            });
        '''))
        started(page)
        finished(page)
        audit = page.evaluate('window.loadingAudit')
        watchdog_ms = audit['ends'][0] - audit['starts'][0]
        assert 4400 <= watchdog_ms <= 4800, audit
        record('playback_failsafe', {'elapsed_ms': watchdog_ms})
        context.close()

        context, page = scenario(browser, 'cancel_before_start', gated_decode)
        assert page.evaluate('window.readLoadingSeen()') is None
        page.locator('.js-menu-open').click()
        skipped(page)
        assert page.locator('.js-mobile-menu').evaluate('node => node.classList.contains("is-open")')
        page.evaluate('window.releaseLoadingDecode()')
        page.wait_for_timeout(150)
        skipped(page)
        record('cancel_before_start')
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
        started(page)
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
