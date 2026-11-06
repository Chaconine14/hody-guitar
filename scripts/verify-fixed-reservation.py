#!/usr/bin/env python3
"""Shared reservation CTA checks. Requires Playwright/Pillow and HTTP servers.

python3 scripts/verify-fixed-reservation.py --base-url http://127.0.0.1:8770/ \
    --baseline-url http://127.0.0.1:8772/ --output artifacts/_local/shared-cta
"""
import argparse
import json
from pathlib import Path

from PIL import Image, ImageChops
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--base-url', default='http://127.0.0.1:8770/')
parser.add_argument('--baseline-url')
parser.add_argument('--pages', nargs='+', choices=('index.html', 'selection.html', 'guide.html'), default=('index.html', 'selection.html', 'guide.html'))
parser.add_argument('--resume', action='store_true', help='Keep earlier viewport results when checking selected pages again.')
parser.add_argument('--only-regression', action='store_true', help='Run resize/history/motion and feature checks without repeating screenshots.')
parser.add_argument('--output', type=Path, default=ROOT / 'artifacts/_local/shared-cta')
parser.add_argument('--browser', default='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=True)
report = {'viewports': {}, 'regression': {}, 'motion': {}}
if args.resume and (args.output / 'verification.json').exists():
    report = json.loads((args.output / 'verification.json').read_text())
report['passed'] = False
CTA = '.js-fixed-reservation'
PAGES = ('index.html', 'selection.html', 'guide.html')
WIDTHS = (375, 768, 1024, 1440)


def save():
    (args.output / 'verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=4) + '\n')


def ready(page, filename, base_url=None):
    page.goto((base_url or args.base_url).rstrip('/') + '/' + filename, wait_until='domcontentloaded')
    if filename == 'selection.html':
        expect(page.locator('.js-selection-page')).to_have_attribute('aria-busy', 'false')
    page.evaluate('''async () => {
        await document.fonts.ready;
        await Promise.all([...document.images].map(image => {
            image.loading = 'eager';
            return image.decode().catch(() => {});
        }));
    }''')
    page.wait_for_timeout(80)


def scroll(page, y):
    page.evaluate('y => window.scrollTo({top: y, behavior: "instant"})', y)
    page.wait_for_timeout(60)


def start_position(page, filename):
    if filename == 'index.html':
        return page.locator('.js-reservation-hero').evaluate('hero => hero.getBoundingClientRect().bottom + scrollY - innerHeight * .5')
    return 150


def visible(page, expected):
    cta = page.locator(CTA)
    expect(cta).to_have_count(1)
    if expected:
        assert cta.evaluate('node => node.classList.contains("is-visible")')
        expect(cta).to_be_visible()
    else:
        assert not cta.evaluate('node => node.classList.contains("is-visible")')
        expect(cta).to_be_hidden()
    assert cta.evaluate('node => node.inert') is not expected


def geometry(page):
    return page.evaluate('''() => {
        const nodes = [...document.querySelectorAll('body > header, main, main section, main article, main img, main h1, main h2, main h3, main p, main button, main input, main select, main textarea, .l-footer, .l-footer *')];
        return nodes.filter(node => !node.closest('.js-fixed-reservation, .p-finder__reservation, .p-guide-page__fixed')).map(node => {
            const box = node.getBoundingClientRect();
            const style = getComputedStyle(node);
            const round = value => Math.round(value * 1000) / 1000;
            const closedDetails = node.closest('details:not([open])');
            const closedAnswer = closedDetails && !closedDetails.querySelector('summary')?.contains(node);
            const displayed = node.getClientRects().length > 0 && !closedAnswer;
            return {tag: node.tagName, class: node.className.replace(/ js-reservation-footer/g, ''),
                x: displayed ? round(box.x) : null, y: displayed ? round(box.y + scrollY) : null,
                width: displayed ? round(box.width) : 0, height: displayed ? round(box.height) : 0,
                padding: style.padding, margin: style.margin, font: style.font, display: style.display};
        });
    }''')


def cta_metrics(page, selector=CTA):
    return page.locator(selector).evaluate('''node => {
        const round = value => Math.round(value * 1000) / 1000;
        const metrics = el => {
            const box = el.getBoundingClientRect();
            const style = getComputedStyle(el);
            return {x: round(box.x), y: round(box.y), width: round(box.width), height: round(box.height),
                styles: Object.fromEntries(['fontFamily', 'fontSize', 'fontWeight', 'lineHeight', 'color', 'backgroundColor',
                    'padding', 'border', 'borderRadius', 'gap', 'alignSelf', 'textAlign', 'position', 'zIndex', 'display'].map(key => [key, style[key]])),
                src: el.currentSrc || null};
        };
        return [node, ...node.querySelectorAll('picture, img, span, small, strong')].map(metrics);
    }''')


def same_geometry(actual, expected, label):
    output = args.output / (label + '-geometry-differences.json')
    if actual != expected:
        differences = [{'index': i, 'before': a, 'after': b} for i, (a, b) in enumerate(zip(expected, actual)) if a != b]
        output.write_text(json.dumps(differences, ensure_ascii=False, indent=4))
        raise AssertionError(f'Non-CTA geometry changed: {label}; {len(expected)}/{len(actual)} nodes, {len(differences)} differences')
    output.unlink(missing_ok=True)


def shot(page, name, full_page=False):
    page.mouse.move(0, 0)
    page.screenshot(path=str(args.output / name), animations='disabled', full_page=full_page)


def overlay_in_front(page, selector):
    details = page.evaluate('''selector => {
        const cta = document.querySelector('.js-fixed-reservation');
        const overlay = document.querySelector(selector);
        const box = cta.getBoundingClientRect();
        const nodes = document.elementsFromPoint(box.x + box.width / 2, box.y + box.height / 2);
        return {overlayZ: getComputedStyle(overlay).zIndex, ctaZ: getComputedStyle(cta).zIndex,
            visibility: getComputedStyle(overlay).visibility, pointerEvents: getComputedStyle(overlay).pointerEvents,
            classes: overlay.className, inert: overlay.inert,
            box: box.toJSON(), overlay: overlay.getBoundingClientRect().toJSON(),
            nodes: nodes.map(node => node.className),
            inFront: nodes.some(node => node === overlay || overlay.contains(node))};
    }''', selector)
    assert int(details['overlayZ']) > int(details['ctaZ']) and details['inFront'], f'{selector} is behind the CTA: {details}'


with sync_playwright() as playwright:
    browser = playwright.chromium.launch(executable_path=args.browser, headless=True)
    for filename in (() if args.only_regression else args.pages):
        for width in WIDTHS:
            label = f'{filename.removesuffix(".html")}-{width}'
            page = browser.new_page(viewport={'width': width, 'height': 900}, reduced_motion='reduce')
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            ready(page, filename)
            before = geometry(page)
            visible(page, False)
            assert page.locator(CTA).evaluate('node => node.parentElement === document.body')
            page.locator(CTA).evaluate('node => node.focus()')
            assert not page.locator(CTA).evaluate('node => document.activeElement === node')
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Horizontal overflow'
            shot(page, label + '-initial.png')
            shot(page, label + '-full.png', full_page=True)

            baseline_metrics = None
            baseline_close_focused = None
            if args.baseline_url:
                baseline = browser.new_page(viewport={'width': width, 'height': 900}, reduced_motion='reduce')
                ready(baseline, filename, args.baseline_url)
                original = geometry(baseline)
                same_geometry(before, original, label + '-baseline')
                if filename == 'index.html':
                    scroll(baseline, start_position(baseline, filename) + 20)
                    baseline_metrics = cta_metrics(baseline, '.p-finder__reservation')
                    baseline.locator('.p-finder__reservation').screenshot(path=str(args.output / (label + '-cta-before.png')))
                    baseline.locator('.p-finder__reservation').click()
                    baseline.wait_for_timeout(80)
                    baseline_close_focused = baseline.locator('.js-close-reservation').evaluate('node => document.activeElement === node')
                baseline.close()

            boundary = start_position(page, filename)
            scroll(page, boundary - 1)
            visible(page, False)
            scroll(page, boundary)
            visible(page, True)
            scroll(page, boundary + 20)
            current_metrics = cta_metrics(page)
            if baseline_metrics is not None:
                # Same-origin asset URLs differ only by the baseline server port.
                for entries in (baseline_metrics, current_metrics):
                    for entry in entries:
                        if entry['src']:
                            entry['src'] = entry['src'].split('/assets/', 1)[-1]
                assert current_metrics == baseline_metrics, f'TOP CTA appearance changed: {width}'
                after_shot = args.output / (label + '-cta-after.png')
                page.locator(CTA).screenshot(path=str(after_shot))
                a = Image.open(args.output / (label + '-cta-before.png')).convert('RGB')
                b = Image.open(after_shot).convert('RGB')
                assert a.size == b.size and ImageChops.difference(a, b).getbbox() is None, f'TOP CTA pixels changed: {width}'
            shot(page, label + '-visible.png')
            same_geometry(geometry(page), before, label + '-show')

            page.locator(CTA).click()
            expect(page.locator('.js-reservation')).to_have_attribute('aria-hidden', 'false')
            page.wait_for_timeout(80)
            shot(page, label + '-modal.png')
            overlay_in_front(page, '.js-reservation')
            close_focused = page.locator('.js-close-reservation').evaluate('node => document.activeElement === node')
            if baseline_close_focused is not None:
                assert close_focused == baseline_close_focused, f'Modal initial focus changed: {label}'
            page.locator('.js-close-reservation').focus()
            page.keyboard.press('Shift+Tab')
            expect(page.locator('.p-reservation__submit')).to_be_focused()
            page.keyboard.press('Tab')
            expect(page.locator('.js-close-reservation')).to_be_focused()
            shot(page, label + '-modal.png')
            page.locator('#reserve-name').fill('CTA動作確認')
            page.keyboard.press('Escape')
            expect(page.locator('.js-reservation')).to_have_attribute('aria-hidden', 'true')
            expect(page.locator(CTA)).to_be_focused()
            page.locator(CTA).click()
            expect(page.locator('#reserve-name')).to_have_value('CTA動作確認')
            page.locator('.js-close-reservation').click()

            if width <= 768:
                page.locator('.js-menu-open').evaluate('node => node.click()')
                expect(page.locator('.js-mobile-menu')).to_have_attribute('aria-hidden', 'false')
                page.wait_for_timeout(80)
                overlay_in_front(page, '.js-mobile-menu')
                page.keyboard.press('Escape')
                footer = page.locator('.js-reservation-footer').evaluate('node => node.getBoundingClientRect().top + scrollY')
                scroll(page, footer - 901)
                visible(page, True)
                scroll(page, footer - 899)
                visible(page, False)
                shot(page, label + '-footer.png')
                scroll(page, footer - 901)
                visible(page, True)
            else:
                scroll(page, page.locator('.js-reservation-footer').evaluate('node => node.getBoundingClientRect().top + scrollY'))
                visible(page, True)

            scroll(page, boundary + 20)
            page.reload(wait_until='domcontentloaded')
            page.wait_for_timeout(200)
            visible(page, True)
            scroll(page, boundary - 1)
            visible(page, False)
            scroll(page, 0)
            same_geometry(geometry(page), before, label + '-hide')
            assert not errors, errors
            report['viewports'][label] = {'passed': True, 'boundary': boundary, 'geometry_nodes': len(before),
                'baseline_geometry_equal': bool(args.baseline_url), 'top_cta_equal': baseline_metrics is not None,
                'initial_hidden': True, 'modal_and_focus': True, 'modal_initial_close_focused': close_focused,
                'baseline_initial_close_focused': baseline_close_focused, 'footer_hide': width <= 768, 'page_errors': errors}
            save()
            page.close()
            print(label + ': passed', flush=True)

    for filename in PAGES:
        page = browser.new_page(viewport={'width': 768, 'height': 900}, reduced_motion='reduce')
        ready(page, filename)
        scroll(page, start_position(page, filename) + 50)
        visible(page, True)
        for width in (769, 768, 1024, 375):
            page.set_viewport_size({'width': width, 'height': 900})
            page.wait_for_timeout(80)
            visible(page, True)
            box = page.locator(CTA).bounding_box()
            if width <= 768:
                assert box['x'] == 0 and box['width'] == width and box['y'] + box['height'] == 900
            else:
                assert box['y'] == 182 and box['width'] == 161 and box['x'] + box['width'] == width
        # A real history navigation must restore the current scroll state.
        previous_scroll = page.evaluate('scrollY')
        destination = 'selection.html' if filename == 'guide.html' else 'guide.html'
        page.goto(args.base_url.rstrip('/') + '/' + destination, wait_until='domcontentloaded')
        page.go_back(wait_until='domcontentloaded')
        page.wait_for_timeout(200)
        assert abs(page.evaluate('scrollY') - previous_scroll) <= 1, (filename, previous_scroll, page.evaluate('scrollY'))
        visible(page, True)
        report['regression'][filename] = {'resize_boundary': True, 'history_restore': True}
        save()
        page.close()

    for width in (375, 1440):
        page = browser.new_page(viewport={'width': width, 'height': 900}, reduced_motion='no-preference')
        ready(page, 'guide.html')
        cta = page.locator(CTA)
        transition = cta.evaluate('node => getComputedStyle(node).transition')
        assert '0.4s' in transition and 'ease-out' in transition
        scroll(page, 151)
        assert cta.evaluate('node => node.classList.contains("is-visible")')
        moving = cta.evaluate('node => getComputedStyle(node).transform')
        assert moving != 'matrix(1, 0, 0, 1, 0, 0)', 'Slide-in did not animate'
        scroll(page, 149)
        assert cta.evaluate('node => node.inert')
        scroll(page, 151)
        page.wait_for_timeout(450)
        assert cta.evaluate('node => getComputedStyle(node).transform') == 'matrix(1, 0, 0, 1, 0, 0)'
        scroll(page, 149)
        page.wait_for_timeout(450)
        visible(page, False)
        page.emulate_media(reduced_motion='reduce')
        assert cta.evaluate('node => getComputedStyle(node).transitionDuration') == '0s'
        scroll(page, 151)
        visible(page, True)
        scroll(page, 149)
        visible(page, False)
        report['motion'][str(width)] = {'transition': transition, 'reversal': True, 'reduced_motion': True}
        save()
        page.close()

    page = browser.new_page(viewport={'width': 375, 'height': 900}, reduced_motion='reduce')
    ready(page, 'index.html')
    page.locator('.js-finder-start').click()
    for answer in ('any', 'any', 'any'):
        page.locator(f'.js-finder-answer[data-answer="{answer}"]').click()
        visible(page, True)
    page.wait_for_selector('.p-finder[data-finder-step="result"] .js-finder-screen[aria-busy="false"]')
    assert page.locator('.p-finder__card').count() == 2
    page.locator('.js-finder-reserve').click()
    assert page.locator('#reserve-product option[data-product-id]').count() == 2
    page.keyboard.press('Escape')
    page.locator('.js-finder-retry').click()
    expect(page.locator('.p-finder')).to_have_attribute('data-finder-step', '1')
    report['regression']['diagnosis'] = {'result_cards': 2, 'recommendation_reservation': True, 'retry': True}
    save()
    ready(page, 'selection.html')
    initial_count = page.locator('.js-product-cards > *').count()
    if not page.locator('.js-selection-form').is_visible():
        page.locator('.js-filter-toggle').click()
    page.locator('#filter-price_band').select_option(index=1)
    page.locator('.js-selection-form').evaluate('form => form.requestSubmit()')
    page.wait_for_timeout(100)
    assert page.locator('.js-product-cards > *').count() < initial_count
    footer = page.locator('.js-reservation-footer').evaluate('node => node.getBoundingClientRect().top + scrollY')
    scroll(page, footer - 899)
    visible(page, False)
    scroll(page, footer - 901)
    visible(page, True)
    if not page.locator('.js-selection-form').is_visible():
        page.locator('.js-filter-toggle').click()
    page.locator('.js-filter-reset').click()
    expect(page.locator('.js-product-cards > *')).to_have_count(initial_count)
    report['regression']['search'] = {'initial_products': initial_count, 'filter_and_reset': True, 'filtered_footer_boundary': True}
    page.close()

    page = browser.new_page(viewport={'width': 1440, 'height': 900}, reduced_motion='no-preference')
    ready(page, 'index.html')
    first = page.locator('.p-hero__progress').get_attribute('aria-label')
    page.wait_for_function('label => document.querySelector(".p-hero__progress").getAttribute("aria-label") !== label', arg=first, timeout=7000)
    report['regression']['hero_slider'] = {'from': first, 'to': page.locator('.p-hero__progress').get_attribute('aria-label')}
    page.close()
    browser.close()
report['passed'] = True
save()
print('Shared CTA: all viewport, baseline, motion and regression checks passed.', flush=True)
