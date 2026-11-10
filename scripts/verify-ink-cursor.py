#!/usr/bin/env python3
"""Verify the ink cursor, CTA integration and unchanged page geometry in Chrome.

Requires the existing Playwright/Pillow environment and local HTTP servers.
Safari rendering remains a separate check; simulated lifecycle events below do
not claim to exercise the operating system's actual window lifecycle.

python3 scripts/verify-ink-cursor.py --base-url http://127.0.0.1:8780/ \
    --baseline-url http://127.0.0.1:8783/ --output artifacts/_local/ink-cursor
"""
import argparse
import io
import json
import math
from pathlib import Path
import re

from PIL import Image, ImageChops
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
PAGES = ('index.html', 'guide.html', 'selection.html')
WIDTHS = (1440, 1024, 769, 768, 375)
CURSOR = '.c-ink-cursor'
CHARCOAL = (74, 74, 74)
SAND = (244, 236, 221)
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--base-url', default='http://127.0.0.1:8780/')
parser.add_argument('--baseline-url')
parser.add_argument('--browser', default='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')
parser.add_argument('--output', type=Path, default=ROOT / 'artifacts/_local/ink-cursor-scope')
checks = parser.add_mutually_exclusive_group()
checks.add_argument('--only-motion', action='store_true', help='Run only the painted shape and motion checks')
checks.add_argument('--only-finder', action='store_true', help='Run only Finder scope and result-state checks')
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=True)
report = {'viewports': {}, 'motion': {}, 'lifecycle': {}, 'cta': {}, 'finder': {}, 'passed': False}

AUDIT_SCRIPT = '''
    window.inkAudit = {requested: 0, executed: 0, cancelled: 0, pending: new Set()};
    document.addEventListener('pointermove', event => {
        if (event.pointerType === 'mouse') {
            window.inkAudit.lastMouse = performance.now();
            window.inkAudit.lastPoint = [event.clientX, event.clientY];
        }
    }, {passive: true});
    const request = window.requestAnimationFrame.bind(window);
    const cancel = window.cancelAnimationFrame.bind(window);
    window.requestAnimationFrame = callback => {
        const ink = callback.name === 'renderCursor';
        const id = request(time => {
            if (ink) {
                window.inkAudit.pending.delete(id);
                window.inkAudit.executed += 1;
            }
            callback(time);
        });
        if (ink) {
            window.inkAudit.requested += 1;
            window.inkAudit.pending.add(id);
        }
        return id;
    };
    window.cancelAnimationFrame = id => {
        if (window.inkAudit.pending.delete(id)) window.inkAudit.cancelled += 1;
        cancel(id);
    };
    window.setInkTestHidden = value => {
        Object.defineProperty(document, 'hidden', {configurable: true, get: () => value});
        document.dispatchEvent(new Event('visibilitychange'));
    };
'''


def save():
    (args.output / 'verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=4) + '\n')


def context_for(browser, width=1440, skip_loading=True, **options):
    context = browser.new_context(viewport={'width': width, 'height': 900}, **options)
    context.route('https://**/*', lambda route: route.abort())
    context.add_init_script(AUDIT_SCRIPT)
    if skip_loading:
        context.add_init_script("try { sessionStorage.setItem('hody:top-loading-seen', '1'); } catch {}")
    return context


def ready(page, filename='guide.html', base_url=None):
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
    page.wait_for_timeout(100)


def is_visible(page):
    return page.evaluate('''() => {
        const cursor = document.querySelector('.c-ink-cursor');
        return Boolean(cursor && !cursor.hidden && getComputedStyle(cursor).display !== 'none');
    }''')


def shown(page):
    try:
        page.wait_for_function('''() => {
            const cursor = document.querySelector('.c-ink-cursor');
            return cursor && !cursor.hidden && getComputedStyle(cursor).display !== 'none';
        }''', timeout=5000)
    except Exception as error:
        details = page.evaluate('''() => {
            const finder = document.querySelector('.js-finder');
            const point = inkAudit.lastPoint;
            const target = point && document.elementFromPoint(...point);
            return {point, target: target?.className, focus: document.hasFocus(), hidden: document.hidden,
                active: document.activeElement?.outerHTML.slice(0, 300), scrollY,
                body: document.body.className, html: document.documentElement.className,
                finder: finder?.getBoundingClientRect().toJSON(), step: finder?.dataset.finderStep,
                busy: document.querySelector('.js-finder-screen')?.getAttribute('aria-busy')};
        }''')
        (args.output / 'show-failure.json').write_text(json.dumps(details, ensure_ascii=False, indent=4))
        page.screenshot(path=str(args.output / 'show-failure.png'))
        raise AssertionError(f'Ink did not resume: {details}') from error


def hidden_and_stopped(page):
    page.wait_for_timeout(80)
    assert not is_visible(page), 'Cursor remained visible while suppressed'
    count = page.evaluate('window.inkAudit.executed')
    page.wait_for_timeout(180)
    state = page.evaluate('({executed: inkAudit.executed, pending: inkAudit.pending.size})')
    assert state['executed'] == count and state['pending'] == 0, state


def scroll(page, y):
    page.evaluate('y => scrollTo({top: y, behavior: "instant"})', y)
    page.wait_for_timeout(120)


def hover(page, selector):
    target = page.locator(selector).first
    target.scroll_into_view_if_needed()
    page.wait_for_timeout(100)
    box = target.bounding_box()
    assert box, selector
    page.mouse.move(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
    expect(target).to_have_class(re.compile(r'.*\bis-ink-hover\b.*'))
    page.wait_for_timeout(520)
    return target


def geometry(page):
    return page.evaluate('''() => {
        const selectors = 'body > header, main, main section, main article, main img, main h1, main h2, main h3, main p, main button, main input, main select, main textarea, .l-footer, .l-footer *, .js-fixed-reservation';
        return [...document.querySelectorAll(selectors)].map(node => {
            const box = node.getBoundingClientRect(), style = getComputedStyle(node);
            const round = number => Math.round(number * 100) / 100;
            return {tag: node.tagName, classes: [...node.classList].filter(name =>
                !['c-ink-button', 'js-ink-button', 'is-ink-hover'].includes(name)).join(' '),
                box: [box.x, box.y + scrollY, box.width, box.height].map(round),
                padding: style.padding, margin: style.margin, font: style.font,
                border: style.border, radius: style.borderRadius, display: style.display};
        });
    }''')


def snapshot(page):
    return page.evaluate('''() => {
        const svg = document.querySelector('.c-ink-cursor__svg');
        const matrix = new DOMMatrix(getComputedStyle(svg).transform);
        const dots = [...document.querySelectorAll('.c-ink-cursor__dot')].map(dot => {
            const box = dot.getBoundingClientRect();
            return [box.x + box.width / 2, box.y + box.height / 2, box.width, box.height];
        });
        return {center: [matrix.m41 + 96, matrix.m42 + 96], dots,
            bounds: [Math.min(...dots.map(dot => dot[0] - dot[2] / 2)),
                Math.min(...dots.map(dot => dot[1] - dot[3] / 2)),
                Math.max(...dots.map(dot => dot[0] + dot[2] / 2)),
                Math.max(...dots.map(dot => dot[1] + dot[3] / 2))]};
    }''')


def capture_core(page, name, expected):
    center = snapshot(page)['center']
    shot = page.screenshot(clip={'x': center[0] - 40, 'y': center[1] - 40, 'width': 80, 'height': 80})
    (args.output / name).write_bytes(shot)
    image = Image.open(io.BytesIO(shot)).convert('RGB')
    count = sum(1 for pixel in image.getdata() if pixel == expected)
    assert count >= 100, f'Expected solid cursor color {expected}, found {count} pixels'
    return count


def capture_ink(page, name, expected, half=96):
    """Inspect painted pixels, including the filter output and the complete tail."""
    center = snapshot(page)['center']
    shot = page.screenshot(clip={'x': center[0] - half, 'y': center[1] - half,
                                 'width': half * 2, 'height': half * 2})
    (args.output / name).write_bytes(shot)
    image = Image.open(io.BytesIO(shot)).convert('RGB')
    pixels = {(x, y) for y in range(image.height) for x in range(image.width)
              if image.getpixel((x, y)) == expected}
    assert len(pixels) >= 100, f'Missing solid ink color in {name}: {len(pixels)} pixels'
    left = min(x for x, y in pixels)
    top = min(y for x, y in pixels)
    right = max(x for x, y in pixels) + 1
    bottom = max(y for x, y in pixels) + 1
    profile = [0] * 24
    for x, y in pixels:
        dx, dy = x + .5 - half, y + .5 - half
        angle = math.atan2(dy, dx) % (math.pi * 2)
        sector = int(angle / (math.pi * 2) * len(profile))
        profile[sector] = max(profile[sector], math.hypot(dx, dy))
    return {'image': image, 'pixels': pixels, 'width': right - left, 'height': bottom - top,
            'profile': profile, 'center': center}


def component_sizes(pixels):
    remaining = set(pixels)
    sizes = []
    while remaining:
        stack = [remaining.pop()]
        size = 0
        while stack:
            x, y = stack.pop()
            size += 1
            for neighbor in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                if neighbor in remaining:
                    remaining.remove(neighbor)
                    stack.append(neighbor)
        sizes.append(size)
    return sizes


def viewport_checks(browser):
    for filename in PAGES:
        for width in WIDTHS:
            label = f'{filename.removesuffix(".html")}-{width}'
            context = context_for(browser, width)
            page = context.new_page()
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            ready(page, filename)
            initial = geometry(page)
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), label
            assert page.locator('body').evaluate('node => getComputedStyle(node).cursor !== "none"')
            assert page.locator('.l-header__reserve').evaluate('node => getComputedStyle(node).cursor !== "none"')
            page.mouse.move(width / 2, 180)
            page.wait_for_timeout(300)
            enabled = width >= 769 and filename != 'selection.html'
            if enabled:
                shown(page)
                expect(page.locator('.c-ink-cursor__dot')).to_have_count(20)
                assert page.locator(CURSOR).get_attribute('aria-hidden') == 'true'
                assert page.locator(CURSOR).evaluate('node => getComputedStyle(node).pointerEvents === "none"')
                assert page.evaluate('''() => !document.elementFromPoint(innerWidth / 2, 180)?.closest('.c-ink-cursor')''')
                page.mouse.move(-10, -10)
                hidden_and_stopped(page)
            else:
                hidden_and_stopped(page)
                assert not page.locator('html').evaluate('node => node.classList.contains("is-ink-cursor-enabled")')
                if filename == 'selection.html':
                    expect(page.locator(CURSOR)).to_have_count(0)
                    expect(page.locator('.c-ink-cursor__dot')).to_have_count(0)
                    assert page.evaluate('window.inkAudit.requested') == 0
            assert page.locator('html').evaluate('node => node.classList.contains("is-ink-hover-enabled")') == (width >= 769)
            assert geometry(page) == initial, f'Cursor interaction changed geometry: {label}'
            if args.baseline_url:
                baseline_context = context_for(browser, width)
                baseline = baseline_context.new_page()
                ready(baseline, filename, args.baseline_url)
                original = geometry(baseline)
                if original != initial:
                    differences = [{'index': i, 'before': a, 'after': b}
                                   for i, (a, b) in enumerate(zip(original, initial)) if a != b]
                    (args.output / (label + '-geometry-differences.json')).write_text(
                        json.dumps(differences, ensure_ascii=False, indent=4))
                    raise AssertionError(f'Baseline geometry changed: {label}; {len(original)}/{len(initial)} nodes')
                baseline_context.close()
            assert not errors, errors
            if width in (1440, 375):
                page.screenshot(path=str(args.output / (label + '-layout.png')), full_page=True, animations='disabled')
            report['viewports'][label] = {'enabled': enabled, 'geometry_unchanged': True, 'js_errors': errors}
            save()
            context.close()


def motion_checks(browser):
    context = context_for(browser)
    page = context.new_page()
    ready(page)
    # Keep actual input intervals deterministic while screenshots and Python
    # pixel masks are processed. Those operations must not slow a fast gesture.
    page.clock.install(time=page.evaluate('Date.now() / 1000'))
    page.clock.pause_at(page.evaluate('Date.now() / 1000') + .1)
    page.evaluate('() => {' + AUDIT_SCRIPT + '}')
    tick = page.clock.run_for

    def suppressed():
        tick(32)
        assert not is_visible(page), 'Cursor remained visible while suppressed'
        executed = page.evaluate('window.inkAudit.executed')
        tick(240)
        state = page.evaluate('({executed: inkAudit.executed, pending: inkAudit.pending.size})')
        assert state['executed'] == executed and state['pending'] == 0, state

    # Isolate the actual ink from similarly colored text only in this QA context.
    # Visibility preserves layout; product HTML/CSS and its tone remain unchanged.
    page.add_style_tag(content='.p-guide-page__intro * { visibility: hidden !important; }')
    page.mouse.move(240, 220)
    tick(48)
    assert is_visible(page), 'Cursor did not appear after three explicit frames'
    # Native CSS color transitions use compositor time rather than fake timers.
    page.wait_for_timeout(350)
    page.mouse.move(-10, -10)
    suppressed()
    page.mouse.move(240, 220)
    tick(48)
    assert is_visible(page), 'Cursor did not appear after three explicit frames'
    basic = capture_ink(page, 'basic-14px.png', SAND)
    assert 13 <= basic['width'] <= 15 and 13 <= basic['height'] <= 15, basic
    tick(900)
    first = snapshot(page)
    initial_count = page.evaluate('window.inkAudit.executed')
    capture_core(page, 'idle-dark-background-a.png', SAND)
    idle_frames = []
    for index in range(10):
        if index:
            tick(180)
        idle_frames.append(capture_ink(page, f'idle-outline-{index:02}.png', SAND))
    second = snapshot(page)
    capture_core(page, 'idle-dark-background-b.png', SAND)
    assert ImageChops.difference(idle_frames[0]['image'], idle_frames[-1]['image']).getbbox(), \
        'Rendered idle outline did not change'
    for frame in idle_frames:
        assert max(abs(a - b) for a, b in zip(first['center'], frame['center'])) < .1, frame['center']
        assert 13 <= frame['width'] <= 24 and 13 <= frame['height'] <= 24, \
            (frame['width'], frame['height'])
    profiles = [frame['profile'] for frame in idle_frames]
    contour_change = max(max(profile[sector] for profile in profiles) -
                         min(profile[sector] for profile in profiles) for sector in range(24))
    normalized = [[radius / (sum(profile) / len(profile)) for radius in profile] for profile in profiles]
    local_change = max(max(profile[sector] for profile in normalized) -
                       min(profile[sector] for profile in normalized) for sector in range(24))
    assert contour_change >= 2, f'Painted idle deformation is barely visible: {contour_change}'
    assert local_change >= .12, f'Idle changes only by uniform scaling: {local_change}'
    assert page.evaluate('window.inkAudit.executed') > initial_count + 10
    def sample_settling():
        page.evaluate('''() => {
            window.inkSettleSamples = [];
            const stoppedAt = window.inkAudit.lastMouse;
            for (const target of [100, 200, 400, 600, 800, 1000]) {
                setTimeout(() => {
                    const boxes = [...document.querySelectorAll('.c-ink-cursor__dot')].map(node => node.getBoundingClientRect());
                    inkSettleSamples.push({target_ms: target, elapsed_ms: performance.now() - stoppedAt,
                        width_px: Math.max(...boxes.map(box => box.right)) - Math.min(...boxes.map(box => box.left)),
                        height_px: Math.max(...boxes.map(box => box.bottom)) - Math.min(...boxes.map(box => box.top))});
                }, Math.max(0, target - (performance.now() - stoppedAt)));
            }
        }''')

    moving = []
    # 6px per input, rather than the previous 24px, stays below the fast gate.
    for x in range(240, 961, 6):
        page.mouse.move(x, 220)
        tick(16)
        moving.append(snapshot(page))
    maximum = max(item['bounds'][2] - item['bounds'][0] for item in moving)
    assert 65 <= maximum <= 105, f'Normal movement failed to form a connected thin tail: {maximum}'
    thickness = max(item['bounds'][3] - item['bounds'][1] for item in moving[-8:])
    assert 13 <= thickness <= 17, f'Moving ink became too thick: {thickness}'
    sample_settling()
    tail = capture_ink(page, 'movement-normal-tail.png', SAND)
    assert 55 <= tail['width'] <= 105 and 12 <= tail['height'] <= 18, \
        f'Painted normal tail is clipped, too short or too thick: {tail["width"]}x{tail["height"]}'
    normal_components = [size for size in component_sizes(tail['pixels']) if size >= 3]
    assert len(normal_components) == 1, f'Normal-speed ink split: {normal_components}'
    tick(1050)
    assert page.evaluate('window.inkSettleSamples.length') == 6
    normal_settling = page.evaluate('window.inkSettleSamples')
    assert normal_settling[0]['width_px'] >= 35 and normal_settling[1]['width_px'] > 24, normal_settling
    assert normal_settling[3]['width_px'] <= 28 and normal_settling[-1]['width_px'] <= 24, normal_settling
    resumed = snapshot(page)
    assert abs(resumed['center'][0] - 960) <= .5, resumed

    # Rendered components are sampled across successive fast passes, so a single
    # antialiasing pixel or one timing-dependent frame cannot establish breakup.
    fast_snapshots = []
    fast_frames = []
    page.mouse.move(320, 220)
    tick(1200)
    for direction, positions in enumerate((range(320, 1131, 45), range(1130, 319, -45))):
        for index, x in enumerate(positions):
            page.mouse.move(x, 220)
            tick(16)
            fast_snapshots.append(snapshot(page))
            if index in (8, 12, 16):
                frame = capture_ink(page, f'movement-fast-{direction}-{index:02}.png', SAND, half=220)
                fast_frames.append(frame)
    fast_maximum = max(item['bounds'][2] - item['bounds'][0] for item in fast_snapshots)
    assert maximum + 30 <= fast_maximum <= 215, (maximum, fast_maximum)
    separated_frames = [frame for frame in fast_frames
                        if len([size for size in component_sizes(frame['pixels']) if size >= 3]) > 1]
    assert len(separated_frames) >= 2, 'Fast tail never produced persistent, visible small separated drops'
    assert all(frame['width'] < 215 for frame in fast_frames), 'Fast tail exceeded the intended filter reach'
    sample_settling()
    tick(1050)
    assert page.evaluate('window.inkSettleSamples.length') == 6
    fast_settling = page.evaluate('window.inkSettleSamples')
    assert fast_settling[0]['width_px'] >= 45 and fast_settling[1]['width_px'] > 24, fast_settling
    assert fast_settling[-1]['width_px'] <= 26, fast_settling
    assert fast_settling[2]['width_px'] > normal_settling[2]['width_px'], \
        (normal_settling, fast_settling)
    reunited = capture_ink(page, 'movement-fast-rejoined.png', SAND)
    assert len([size for size in component_sizes(reunited['pixels']) if size >= 3]) == 1
    # After the fast envelope decays, the same normal pace must remain connected.
    for x in range(320, 801, 6):
        page.mouse.move(x, 220)
        tick(16)
    slow_again = capture_ink(page, 'movement-slow-after-fast.png', SAND)
    assert len([size for size in component_sizes(slow_again['pixels']) if size >= 3]) == 1
    report['motion']['organic_idle'] = {
        'rendered_contour_change_px': contour_change,
        'normalized_local_change': local_change,
        'basic_rendered_size_px': [basic['width'], basic['height']],
        'idle_rendered_sizes_px': [[frame['width'], frame['height']] for frame in idle_frames],
        'center_drift_px': [b - a for a, b in zip(first['center'], second['center'])],
        'normal_max_width_px': maximum,
        'normal_painted_size_px': [tail['width'], tail['height']],
        'normal_components': len(normal_components),
        'moving_thickness_px': thickness,
        'normal_settling': normal_settling,
        'fast_max_width_px': fast_maximum,
        'fast_painted_sizes_px': [[frame['width'], frame['height']] for frame in fast_frames],
        'fast_separated_frames': len(separated_frames),
        'fast_settling': fast_settling,
        'reunited_after_fast': True,
    }
    # A stationary pointer must respond to background changes caused by scrolling.
    page.mouse.move(30, 150)
    tick(300)
    assert page.locator(CURSOR).get_attribute('data-tone') == 'dark'
    scroll(page, 600)
    tick(32)
    assert page.locator(CURSOR).get_attribute('data-tone') == 'light'
    tick(320)
    page.wait_for_timeout(350)
    capture_core(page, 'light-background.png', CHARCOAL)
    scroll(page, 0)
    tick(32)
    assert page.locator(CURSOR).get_attribute('data-tone') == 'dark'
    report['motion']['stationary_scroll_color'] = True
    context.close()


def cta_checks(browser):
    for filename in PAGES:
        context = context_for(browser)
        page = context.new_page()
        ready(page, filename)
        button = hover(page, '.l-header__reserve')
        if filename != 'selection.html':
            assert page.locator(CURSOR).evaluate('node => node.classList.contains("is-absorbed")')
        else:
            expect(page.locator(CURSOR)).to_have_count(0)
            assert page.evaluate('window.inkAudit.requested') == 0
        assert button.evaluate('node => getComputedStyle(node).opacity') == '1'
        assert button.evaluate('node => getComputedStyle(node, "::before").transform !== "none"')
        page.screenshot(path=str(args.output / (filename.removesuffix('.html') + '-header-hover.png')))
        button.click()
        expect(page.locator('.js-reservation')).to_have_attribute('aria-hidden', 'false')
        hidden_and_stopped(page)
        page.locator('#reserve-name').fill('カーソル確認')
        hidden_and_stopped(page)
        page.keyboard.press('Escape')
        expect(page.locator('.js-reservation')).to_have_attribute('aria-hidden', 'true')
        assert not is_visible(page), 'Cursor must wait for a fresh parent mouse move'
        page.mouse.move(20, 180)
        if filename != 'selection.html':
            shown(page)
        else:
            hidden_and_stopped(page)
        # Preserve the native keyboard focus ring.
        page.keyboard.press('Tab')
        button.focus()
        assert button.evaluate('node => getComputedStyle(node).outlineStyle !== "none"')
        page.evaluate('document.activeElement.blur()')
        scroll(page, 900 if filename == 'index.html' else 200)
        fixed = hover(page, '.js-fixed-reservation')
        assert fixed.evaluate('node => getComputedStyle(node).position') == 'fixed'
        assert fixed.evaluate('node => getComputedStyle(node).transitionProperty').split(',')[0].strip() == 'transform'
        fixed.click()
        expect(page.locator('.js-reservation')).to_have_attribute('aria-hidden', 'false')
        hidden_and_stopped(page)
        page.keyboard.press('Escape')
        invite_selector = '.p-guide-page__reserve' if filename == 'guide.html' else '.c-trial-invite__button'
        if filename != 'index.html':
            invite = hover(page, invite_selector)
            assert invite.evaluate('node => getComputedStyle(node).color') == 'rgb(244, 236, 221)'
            assert invite.evaluate('node => getComputedStyle(node, "::before").backgroundColor') == 'rgb(2, 69, 120)'
            assert invite.evaluate('node => getComputedStyle(node, "::after").boxShadow') != 'none'
        if filename == 'selection.html':
            price = page.locator('#filter-price_band')
            price.select_option('lt150000')
            page.locator('.p-selection-page__search').click()
            expect(page.locator('.js-selection-page')).to_have_attribute('aria-busy', 'false')
            expect(page.locator('.js-product-cards > *')).to_have_count(5)
            expect(page.locator('.js-results-count')).to_have_text('5件')
            page.locator('.js-filter-reset').click()
            expect(price).to_have_value('')
            expect(page.locator('.js-product-cards > *')).to_have_count(12)
            hidden_and_stopped(page)
            expect(page.locator(CURSOR)).to_have_count(0)
            assert page.evaluate('window.inkAudit.requested') == 0
            report['lifecycle']['selection_search_cta_no_cursor_no_raf'] = True
        report['cta'][filename] = {'header_and_fixed_click': True, 'focus_ring': True}
        context.close()
    context = context_for(browser)
    page = context.new_page()
    ready(page, 'index.html')
    page.locator('.js-finder-start').click()
    for _ in range(3):
        page.locator('.js-finder-answer').first.click()
    expect(page.locator('.p-finder')).to_have_attribute('data-finder-step', 'result')
    expect(page.locator('.js-finder-reserve')).to_be_enabled()
    page.mouse.move(20, 100)
    reserve = page.locator('.js-finder-reserve')
    reserve.scroll_into_view_if_needed()
    box = reserve.bounding_box()
    page.mouse.move(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
    expect(reserve).to_have_class(re.compile(r'.*\bis-ink-hover\b.*'))
    page.wait_for_timeout(80)
    first_scale = reserve.evaluate('node => new DOMMatrix(getComputedStyle(node, "::before").transform).m11')
    assert 0 < first_scale < 1, f'First dynamic hover skipped its transition: {first_scale}'
    report['cta']['dynamic_first_hover_scale'] = first_scale
    hover(page, '.js-finder-reserve')
    retry = hover(page, '.js-finder-retry')
    assert retry.evaluate('node => node.classList.contains("c-ink-button")')
    assert page.locator(CURSOR).evaluate('node => node.classList.contains("is-absorbed")')
    assert retry.evaluate('node => getComputedStyle(node, "::before").backgroundColor') == 'rgb(74, 74, 74)'
    assert retry.evaluate('node => getComputedStyle(node).color') == 'rgb(251, 247, 239)'
    page.keyboard.press('Tab')
    retry.focus()
    assert retry.evaluate('node => getComputedStyle(node).outlineStyle !== "none"')
    page.evaluate('document.activeElement.blur()')
    page.locator('.js-finder-reserve').evaluate('node => { node.disabled = true; }')
    page.wait_for_timeout(100)
    assert not page.locator('.js-finder-reserve').evaluate('node => node.classList.contains("is-ink-hover")')
    page.locator('.js-finder-reserve').evaluate('node => { node.disabled = false; }')
    page.mouse.move(20, 300)
    hover(page, '.js-finder-reserve')
    page.locator('.js-finder-retry').evaluate('node => node.click()')
    page.wait_for_timeout(200)
    # The smaller question screen can move Finder away from this stationary
    # result-button point; visibility depends on the full section's new bounds.
    assert not page.locator(CURSOR).evaluate('node => node.classList.contains("is-absorbed")')
    assert not page.locator('.is-ink-hover').count()
    hover(page, '.p-instagram__more--pc')
    assert page.locator('.p-instagram__more--pc').get_attribute('target') == '_blank'
    report['cta']['dynamic_finder_and_instagram'] = True
    context.close()


def finder_checks(browser):
    """Use real Finder state changes while keeping rendering state independent."""
    context = context_for(browser)
    page = context.new_page()
    ready(page, 'index.html')
    root = page.locator('.js-finder')
    screen = page.locator('.js-finder-screen')
    pointer = (20, 200)  # Section padding, outside the narrower inner content.

    def position(where='inside', move=False):
        bounds = root.evaluate('node => { const box = node.getBoundingClientRect(); return {top: box.top + scrollY, bottom: box.bottom + scrollY}; }')
        offset = {'inside': bounds['top'] - pointer[1] + 20,
                  'above': bounds['top'] - pointer[1] - 30,
                  'below': bounds['bottom'] - pointer[1] + 30}[where]
        scroll(page, offset)
        if move:
            page.mouse.move(*pointer)

    def question(number):
        expect(root).to_have_attribute('data-finder-step', str(number))
        position()
        hidden_and_stopped(page)
        position('above')
        shown(page)
        assert max(abs(a - b) for a, b in zip(snapshot(page)['center'], pointer)) < .5, \
            'Restored ink retained an old position'
        position()
        hidden_and_stopped(page)

    position(move=True)
    shown(page)
    page.locator('.js-finder-start').evaluate('node => node.click()')
    question(1)
    page.locator('.js-finder-answer').first.evaluate('node => node.click()')
    question(2)
    page.locator('.js-finder-back').evaluate('node => node.click()')
    question(1)
    page.locator('.js-finder-answer').first.evaluate('node => node.click()')
    question(2)
    page.locator('.js-finder-answer').first.evaluate('node => node.click()')
    question(3)
    # The fixed reservation overlaps the full Finder rectangle even though it
    # belongs to another DOM branch. CTA animation remains active while the ink
    # is locally suppressed, and its modal then takes global precedence.
    fixed = page.locator('.js-fixed-reservation')
    expect(fixed).to_have_class(re.compile(r'.*\bis-visible\b.*'))
    fixed_box = fixed.bounding_box()
    assert fixed_box
    fixed_point = (fixed_box['x'] + fixed_box['width'] / 2,
                   fixed_box['y'] + fixed_box['height'] / 2)
    assert root.evaluate('''(node, point) => {
        const box = node.getBoundingClientRect();
        return point[0] >= box.left && point[0] < box.right &&
            point[1] >= box.top && point[1] < box.bottom;
    }''', fixed_point), 'Fixed CTA must overlap Finder for this check'
    page.mouse.move(*fixed_point)
    expect(fixed).to_have_class(re.compile(r'.*\bis-ink-hover\b.*'))
    hidden_and_stopped(page)
    assert fixed.evaluate('node => getComputedStyle(node).transitionProperty').split(',')[0].strip() == 'transform'
    assert fixed.evaluate('node => new DOMMatrix(getComputedStyle(node, "::before").transform).m11') > 0
    fixed.click()
    expect(page.locator('.js-reservation')).to_have_attribute('aria-hidden', 'false')
    position('above')
    hidden_and_stopped(page)
    page.keyboard.press('Escape')
    hidden_and_stopped(page)
    # Closing the reservation restores its original scroll position inside Finder.
    # Move outside again after that restoration; the invalid point must stay hidden.
    position('above')
    hidden_and_stopped(page)
    page.mouse.move(*pointer)
    shown(page)
    position()
    hidden_and_stopped(page)

    # ResizeObserver must catch a bottom edge moving across a stationary point.
    position('below')
    shown(page)
    original_style = root.get_attribute('style')
    root.evaluate('node => node.style.minHeight = (node.getBoundingClientRect().height + 120) + "px"')
    hidden_and_stopped(page)
    root.evaluate('(node, value) => value === null ? node.removeAttribute("style") : node.setAttribute("style", value)', original_style)
    shown(page)
    # Width changes exercise resize while a valid local point is retained.
    position()
    page.set_viewport_size({'width': 1024, 'height': 900})
    position()
    hidden_and_stopped(page)
    position('above')
    shown(page)
    page.set_viewport_size({'width': 1440, 'height': 900})
    position()
    hidden_and_stopped(page)
    page.locator('.js-finder-answer').first.evaluate('node => node.click()')
    expect(root).to_have_attribute('data-finder-step', 'result')
    expect(screen).to_have_attribute('aria-busy', 'false')
    position()
    shown(page)
    expect(page.locator('.js-finder-reserve')).to_be_enabled()
    retry = hover(page, '.js-finder-retry')
    assert page.locator(CURSOR).evaluate('node => node.classList.contains("is-absorbed")')
    retry.click()
    position(move=True)
    hidden_and_stopped(page)
    position('above')
    shown(page)
    report['finder']['questions_back_retry_padding_scroll_resize_modal_priority'] = True
    context.close()

    catalog = (ROOT / 'data/products.json').read_text()
    for result in ('success', 'empty', 'error'):
        context = context_for(browser)
        page = context.new_page()
        pending = []
        page.route('**/data/products.json', lambda route: pending.append(route))
        ready(page, 'index.html')
        root = page.locator('.js-finder')
        screen = page.locator('.js-finder-screen')
        page.locator('.js-finder-start').evaluate('node => node.click()')
        for _ in range(3):
            page.locator('.js-finder-answer').first.evaluate('node => node.click()')
        expect(screen).to_have_attribute('aria-busy', 'true')
        position(move=True)
        hidden_and_stopped(page)
        position('above')
        shown(page)
        position()
        hidden_and_stopped(page)
        assert len(pending) == 1, pending
        response = catalog if result == 'success' else json.dumps({'products': []})
        pending.pop().fulfill(status=503 if result == 'error' else 200,
                              content_type='application/json', body=response)
        expect(screen).to_have_attribute('aria-busy', 'false')
        # No mouse motion after the pending response has been released.
        shown(page)
        assert max(abs(a - b) for a, b in zip(snapshot(page)['center'], pointer)) < .5
        if result == 'success':
            expect(page.locator('.js-finder-reserve')).to_be_enabled()
        else:
            expect(page.locator('.js-finder-reserve')).to_be_disabled()
        retry = hover(page, '.js-finder-retry')
        assert retry.evaluate('node => node.classList.contains("c-ink-button")')
        assert page.locator(CURSOR).evaluate('node => node.classList.contains("is-absorbed")')
        report['finder']['pending_to_' + result + '_stationary_restore'] = True
        context.close()

    context = context_for(browser)
    page = context.new_page()
    ready(page, 'index.html')
    page.locator('.js-finder-start').evaluate('node => node.click()')
    for _ in range(3):
        page.locator('.js-finder-answer').first.evaluate('node => node.click()')
    expect(page.locator('.js-finder-screen')).to_have_attribute('aria-busy', 'false')
    hidden_and_stopped(page)
    assert page.evaluate('window.inkAudit.requested') == 0, 'Keyboard result invented a pointer origin'
    report['finder']['keyboard_result_requires_pointer_origin'] = True
    context.close()


def lifecycle_checks(browser):
    context = context_for(browser)
    page = context.new_page()
    ready(page, 'guide.html')
    page.mouse.move(700, 180)
    shown(page)
    # A QA-only field isolates focus suppression from the reservation modal gate.
    page.evaluate('''() => {
        const input = document.createElement('input');
        input.id = 'ink-test-field';
        input.style.cssText = 'position:fixed;left:20px;top:300px';
        document.body.append(input);
    }''')
    page.locator('#ink-test-field').focus()
    hidden_and_stopped(page)
    page.mouse.move(710, 180)
    hidden_and_stopped(page)
    page.evaluate('document.activeElement.blur(); document.querySelector("#ink-test-field").remove()')
    page.mouse.move(720, 180)
    shown(page)
    for hide, restore in (
        ("window.dispatchEvent(new Event('blur'))", "window.dispatchEvent(new Event('focus'))"),
        ('setInkTestHidden(true)', 'setInkTestHidden(false)'),
        ("window.dispatchEvent(new PageTransitionEvent('pagehide'))", "window.dispatchEvent(new PageTransitionEvent('pageshow', {persisted: true}))"),
    ):
        page.evaluate(hide)
        hidden_and_stopped(page)
        page.evaluate(restore)
        assert not is_visible(page)
        page.mouse.move(700, 180)
        page.mouse.move(710, 180)
        shown(page)
    page.dispatch_event('body', 'pointerdown', {'pointerType': 'touch', 'pointerId': 7})
    hidden_and_stopped(page)
    page.dispatch_event('body', 'pointermove', {'pointerType': 'touch', 'clientX': 740, 'clientY': 180})
    hidden_and_stopped(page)
    page.mouse.move(730, 180)
    shown(page)
    page.emulate_media(reduced_motion='reduce')
    hidden_and_stopped(page)
    page.emulate_media(reduced_motion='no-preference')
    page.mouse.move(740, 180)
    shown(page)
    page.set_viewport_size({'width': 768, 'height': 900})
    hidden_and_stopped(page)
    page.set_viewport_size({'width': 769, 'height': 900})
    page.mouse.move(700, 180)
    shown(page)
    report['lifecycle']['input_window_visibility_history_touch_live_media'] = True
    context.close()
    context = context_for(browser, has_touch=True, is_mobile=True)
    page = context.new_page()
    ready(page)
    page.mouse.move(100, 180)
    hidden_and_stopped(page)
    assert not page.locator('html').evaluate('node => node.classList.contains("is-ink-cursor-enabled")')
    report['lifecycle']['coarse_pointer_at_desktop_width'] = True
    context.close()
    context = context_for(browser, reduced_motion='reduce')
    page = context.new_page()
    ready(page)
    page.mouse.move(100, 180)
    hidden_and_stopped(page)
    report['lifecycle']['initial_reduced_motion'] = True
    context.close()
    context = context_for(browser, skip_loading=False)
    page = context.new_page()
    page.goto(args.base_url.rstrip('/') + '/index.html', wait_until='domcontentloaded')
    assert page.locator('html').evaluate('node => node.classList.contains("is-loading")')
    page.mouse.move(500, 250)
    hidden_and_stopped(page)
    page.wait_for_function('!document.documentElement.classList.contains("is-loading")', polling=50)
    assert not is_visible(page)
    page.mouse.move(510, 250)
    shown(page)
    iframe = page.locator('iframe').first
    if iframe.count():
        iframe.scroll_into_view_if_needed()
        box = iframe.bounding_box()
        page.mouse.move(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
        hidden_and_stopped(page)
        page.mouse.move(20, 200)
        shown(page)
    report['lifecycle']['loading_and_map_iframe'] = True
    context.close()


try:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=args.browser, headless=True)
        if args.only_finder:
            finder_checks(browser)
        else:
            if not args.only_motion:
                viewport_checks(browser)
            motion_checks(browser)
            if not args.only_motion:
                cta_checks(browser)
                finder_checks(browser)
                lifecycle_checks(browser)
        browser.close()
    report['passed'] = True
finally:
    save()

print(json.dumps(report, ensure_ascii=False, indent=2))
