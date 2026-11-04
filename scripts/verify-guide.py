#!/usr/bin/env python3
"""Guide screenshots and browser checks. Requires playwright and Pillow.

python3 scripts/verify-guide.py --baseline-dir /path/to/before-snapshot
The optional snapshot contains the original index.html and style.css.
"""
import argparse
import json
from pathlib import Path

from PIL import Image, ImageChops, ImageStat
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--baseline-dir', type=Path)
parser.add_argument('--browser', default='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')
parser.add_argument('--output', type=Path, default=ROOT / 'artifacts/guide')
parser.add_argument('--base-url', default='http://127.0.0.1:8765/')
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=True)
report = {'viewports': {}, 'regression': {}}


def ready(page, filename='guide.html'):
    page.goto(args.base_url.rstrip('/') + '/' + filename)
    page.wait_for_load_state('networkidle')
    page.evaluate('document.fonts.ready')
    page.evaluate('''async () => {
        for (const image of document.images) {
            image.loading = 'eager';
            await image.decode().catch(() => {});
        }
    }''')


def same_pixels(first, second):
    a = Image.open(first).convert('RGB')
    b = Image.open(second).convert('RGB')
    return a.size == b.size and ImageChops.difference(a, b).getbbox() is None


def raster_error(first, second):
    a = Image.open(first).convert('RGB')
    b = Image.open(second).convert('RGB')
    assert a.size == b.size, 'Page dimensions changed.'
    return max(ImageStat.Stat(ImageChops.difference(a, b)).mean)


def dialog_fonts(page):
    session = page.context.new_cdp_session(page)
    session.send('DOM.enable')
    session.send('CSS.enable')
    document = session.send('DOM.getDocument')
    node = session.send('DOM.querySelector', {
        'nodeId': document['root']['nodeId'], 'selector': '.p-reservation__title',
    })
    fonts = session.send('CSS.getPlatformFontsForNode', {'nodeId': node['nodeId']})['fonts']
    session.detach()
    return fonts


with sync_playwright() as playwright:
    browser = playwright.chromium.launch(executable_path=args.browser, headless=True)
    for width, height in [(1440, 900), (375, 812), (320, 812), (768, 900), (769, 900), (1024, 900)]:
        page = browser.new_page(viewport={'width': width, 'height': height}, device_scale_factor=1, reduced_motion='reduce')
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        ready(page)
        assert not page.evaluate('document.documentElement.scrollWidth > innerWidth'), f'Overflow: {width}'
        assert page.evaluate('[...document.images].every(i => i.complete && i.naturalWidth > 0)')
        assert page.locator('h1').count() == 1
        assert page.locator('.p-guide-page__step').count() == 5
        assert page.locator('details').count() == 6
        assert page.locator('details[open]').count() == 1
        assert page.evaluate('''() => [...document.fonts].some(f =>
            f.family === 'HODY Guide JP' && f.status === 'loaded')''')
        overlaps = page.evaluate('''() => [...document.querySelectorAll('.p-guide-page__step')].flatMap(step => {
            const title = step.querySelector('h3');
            const icon = step.querySelector('.p-guide-page__step-icon').getBoundingClientRect();
            const range = document.createRange();
            range.selectNodeContents(title);
            return [...range.getClientRects()].filter(r => r.left < icon.right && r.right > icon.left &&
                r.top < icon.bottom && r.bottom > icon.top).map(() => title.textContent);
        })''')
        assert not overlaps, f'Title/icon overlap: {width}: {overlaps}'
        geometry = page.evaluate('''() => Object.fromEntries(
            ['intro','flow','faq','invite'].map(name => {
                const r = document.querySelector('.p-guide-page__' + name).getBoundingClientRect();
                return [name, {y: r.y, height: r.height}];
            }))''')
        if width in (1440, 375):
            page.screenshot(path=str(args.output / f'guide-{width}.png'), full_page=True)
            if width == 375:
                page.screenshot(path=str(args.output / 'viewport-375.png'))
                page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                page.screenshot(path=str(args.output / 'footer-viewport-375.png'))
                bar = page.locator('.p-guide-page__fixed').bounding_box()
                assert abs(bar['y'] + bar['height'] - height) < 1
        summaries = page.locator('summary')
        summaries.nth(1).click()
        assert page.locator('details[open]').count() == 2
        for i in range(6):
            summary = summaries.nth(i)
            if page.locator('details').nth(i).get_attribute('open') is not None:
                summary.click()
            summary.focus()
            page.keyboard.press('Enter')
            assert page.locator('details').nth(i).get_attribute('open') is not None
            assert page.locator('.p-guide-page__answer').nth(i).evaluate('el => el.scrollHeight <= el.clientHeight + 1')
            page.keyboard.press('Space')
            assert page.locator('details').nth(i).get_attribute('open') is None
        # Every currently visible reservation CTA opens the shared dialog.
        buttons = page.locator('.js-open-reservation')
        for i in range(buttons.count()):
            button = buttons.nth(i)
            if not button.is_visible():
                continue
            button.click()
            assert page.locator('.js-reservation').get_attribute('aria-hidden') == 'false'
            assert page.locator('body').evaluate("el => el.classList.contains('is-locked')")
            page.keyboard.press('Escape')
            assert page.locator('.js-reservation').get_attribute('aria-hidden') == 'true'
            assert button.evaluate('el => document.activeElement === el')
        # Isolate keyboard/form checks from the rapid CTA open/close smoke test.
        page.close()
        page = browser.new_page(viewport={'width': width, 'height': height}, device_scale_factor=1, reduced_motion='reduce')
        page.on('pageerror', lambda error: errors.append(str(error)))
        ready(page)
        opener = '.p-guide-page__fixed' if width <= 768 else '.l-header__reserve'
        page.locator(opener).click()
        expect(page.locator('.p-reservation__close')).to_be_visible()
        page.locator('.p-reservation__close').focus()
        page.keyboard.press('Shift+Tab')
        expect(page.locator('.p-reservation__submit')).to_be_focused()
        page.keyboard.press('Tab')
        expect(page.locator('.p-reservation__close')).to_be_focused()
        assert not page.locator('form').evaluate('el => el.checkValidity()')
        page.locator('#reserve-name').fill('試奏テスト')
        page.locator('#reserve-email').fill('test@example.com')
        page.locator('#reserve-date').fill('2026-11-05T14:00')
        assert page.locator('form').evaluate('el => el.checkValidity()')
        page.locator('.p-reservation__submit').click()
        assert page.locator('.js-reservation').get_attribute('aria-hidden') == 'false'
        page.locator('.js-close-reservation').click()
        if width <= 768:
            page.locator('.js-menu-open').click()
            assert page.locator('.js-menu-open').get_attribute('aria-expanded') == 'true'
            page.locator('.p-mobile-menu__reserve').click()
            assert page.locator('.js-mobile-menu').get_attribute('aria-hidden') == 'true'
            assert page.locator('.js-reservation').get_attribute('aria-hidden') == 'false'
            page.keyboard.press('Escape')
        else:
            page.locator(opener).click()
            page.locator('.js-reservation-backdrop').click(position={'x': 5, 'y': 5})
            assert page.locator('.js-reservation').get_attribute('aria-hidden') == 'true'
        assert not errors, errors
        report['viewports'][str(width)] = {'passed': True, 'geometry': geometry, 'js_errors': errors}
        page.close()
        print(f'{width}px: screenshots/layout, FAQ, reservation and keyboard checks passed.', flush=True)

    if args.baseline_dir:
        for width, height in [(1440, 900), (375, 812)]:
            snapshots = []
            panels = []
            panel_fonts = []
            for original in (True, False):
                page = browser.new_page(viewport={'width': width, 'height': height}, device_scale_factor=1, reduced_motion='reduce')
                if original:
                    page.route('**/index.html', lambda route: route.fulfill(body=(args.baseline_dir / 'index.html').read_text(), content_type='text/html'))
                    page.route('**/css/style.css', lambda route: route.fulfill(body=(args.baseline_dir / 'style.css').read_text(), content_type='text/css'))
                ready(page, 'index.html')
                shot = args.baseline_dir / f'top-{"before" if original else "after"}-{width}.png'
                page.screenshot(path=str(shot), full_page=True)
                snapshots.append(shot)
                if width == 375:
                    page.locator('.js-menu-open').click()
                    page.locator('.p-mobile-menu__reserve').click()
                else:
                    page.locator('.l-header__reserve').click()
                expect(page.locator('.p-reservation__close')).to_be_visible()
                page.evaluate('document.fonts.ready')
                panel_fonts.append(dialog_fonts(page))
                page.wait_for_timeout(100)
                page.mouse.move(0, 0)
                panel = args.baseline_dir / f'panel-{"before" if original else "after"}-{width}.png'
                page.locator('.p-reservation__panel').screenshot(path=str(panel))
                panels.append(panel)
                page.close()
            # GPU photo resampling can differ slightly between browser contexts.
            error = raster_error(*snapshots)
            assert error < .1, f'TOP visual regression: {width}: mean channel error {error}'
            panel_error = raster_error(*panels)
            assert panel_error < .1, f'Reservation visual regression: {width}: {panel_error}'
            # Compare the guide dialog itself against the unchanged TOP dialog.
            page = browser.new_page(viewport={'width': width, 'height': height}, reduced_motion='reduce')
            ready(page)
            page.locator('.p-guide-page__fixed' if width == 375 else '.l-header__reserve').click()
            expect(page.locator('.p-reservation__close')).to_be_visible()
            page.evaluate('document.fonts.ready')
            guide_fonts = dialog_fonts(page)
            assert panel_fonts[0] == panel_fonts[1] == guide_fonts, 'Reservation title font changed.'
            page.wait_for_timeout(100)
            page.mouse.move(0, 0)
            guide_panel = args.baseline_dir / f'guide-panel-{width}.png'
            page.locator('.p-reservation__panel').screenshot(path=str(guide_panel))
            guide_panel_error = raster_error(panels[0], guide_panel)
            assert guide_panel_error < .1, f'Guide dialog differs from TOP: {width}: {guide_panel_error}'
            page.close()
            report['regression'][str(width)] = {
                'top_mean_channel_error_0_to_255': error,
                'top_threshold': .1,
                'reservation_panels_pixel_identical': same_pixels(*panels),
                'reservation_mean_channel_error_0_to_255': panel_error,
                'guide_panel_mean_channel_error_0_to_255': guide_panel_error,
                'guide_panel_threshold': .1,
                'reservation_title_fonts': guide_fonts,
                'guide_panel_matches_top_within_threshold': True,
            }
            print(f'{width}px: TOP and reservation visual regression passed.', flush=True)

    page = browser.new_page(viewport={'width': 1440, 'height': 900})
    ready(page, 'index.html')
    page.wait_for_function("document.querySelector('.p-hero__progress').getAttribute('aria-label') === 'スライド 2 / 4'", timeout=10000)
    assert page.locator('.p-hero__slide.is-active').count() == 1
    assert page.locator('.p-hero__progress-bar.is-active').count() == 1
    report['slider'] = 'Passed: first-to-second automatic transition; one active slide and bar.'
    browser.close()

(args.output / 'verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=4) + '\n')
print('All guide checks passed.', flush=True)
