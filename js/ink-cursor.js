(() => {
    'use strict';

    const root = document.documentElement;
    const desktop = window.matchMedia('(min-width: 769px) and (hover: hover) and (pointer: fine) and (prefers-reduced-motion: no-preference)');
    const svgNamespace = 'http://www.w3.org/2000/svg';
    const editable = 'input, textarea, select, [contenteditable]:not([contenteditable="false"])';
    const buttonSelector = '.js-ink-button, .js-finder-reserve, .js-finder-retry';
    const finder = document.querySelector('.js-finder');
    const finderScreen = finder?.querySelector('.js-finder-screen');
    const cursorPage = !document.body.classList.contains('p-selection-page');
    const center = 96;
    const count = 20;
    const radius = 7;
    const tailReach = 80;
    const dots = [];
    const pointer = { x: 0, y: 0, valid: false };
    const head = { x: 0, y: 0 };
    let overlay;
    let svg;
    let iconFilters;
    let hoveredButton = null;
    let frameId = 0;
    let interactionFrameId = 0;
    let visible = false;
    let lastFrame = 0;
    let lastMovedAt = 0;
    let activeTime = 0;
    let idleWeight = 0;
    let speedAt = 0;
    let mouseSpeed = 0;
    let fastMode = false;
    let fastWeight = 0;
    let stopFastWeight = 0;

    function svgElement(name, attributes = {}) {
        const node = document.createElementNS(svgNamespace, name);
        Object.entries(attributes).forEach(([key, value]) => node.setAttribute(key, value));
        return node;
    }

    function mountFilters() {
        if (iconFilters) return;
        // カーソルを生成しない商品一覧でも、CTAのアイコン用filterは使用する。
        iconFilters = svgElement('svg', {
            class: 'c-ink-cursor__filters', width: 0, height: 0, 'aria-hidden': 'true', focusable: 'false'
        });
        const definitions = svgElement('defs');
        const colors = getComputedStyle(root);
        ['blue', 'sand', 'ivory', 'charcoal'].forEach(name => {
            const filter = svgElement('filter', {
                id: `hody-ink-icon-${name}`, x: 0, y: 0, width: '100%', height: '100%',
                'color-interpolation-filters': 'sRGB'
            });
            filter.append(
                svgElement('feFlood', { 'flood-color': colors.getPropertyValue(`--color-${name}`).trim(), result: 'paint' }),
                svgElement('feComposite', { in: 'paint', in2: 'SourceAlpha', operator: 'in' })
            );
            definitions.append(filter);
        });
        iconFilters.append(definitions);
        document.body.append(iconFilters);
    }

    function mountCursor() {
        if (overlay) return;
        overlay = document.createElement('div');
        overlay.className = 'c-ink-cursor';
        overlay.setAttribute('aria-hidden', 'true');
        overlay.hidden = true;
        svg = svgElement('svg', {
            class: 'c-ink-cursor__svg', width: 192, height: 192, viewBox: '0 0 192 192', focusable: 'false'
        });
        const definitions = svgElement('defs');
        const goo = svgElement('filter', {
            id: 'hody-ink-goo', filterUnits: 'userSpaceOnUse', x: -96, y: -96, width: 384, height: 384,
            'color-interpolation-filters': 'sRGB'
        });
        goo.append(
            svgElement('feGaussianBlur', { in: 'SourceAlpha', stdDeviation: 1.2, result: 'blur' }),
            svgElement('feColorMatrix', {
                in: 'blur', type: 'matrix', result: 'ink',
                values: '0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 20 -9'
            }),
            svgElement('feFlood', { 'flood-color': 'currentColor', result: 'paint' }),
            svgElement('feComposite', { in: 'paint', in2: 'ink', operator: 'in' })
        );
        definitions.append(goo);
        const shape = svgElement('g', { class: 'c-ink-cursor__shape' });
        const fluid = svgElement('g', { filter: 'url(#hody-ink-goo)' });
        for (let index = 0; index < count; index += 1) {
            const dotRadius = radius - 4 * index / (count - 1);
            const circle = svgElement('circle', { class: 'c-ink-cursor__dot', r: dotRadius, cx: center, cy: center });
            dots.push({ node: circle, radius: dotRadius, x: 0, y: 0 });
            fluid.append(circle);
        }
        shape.append(fluid);
        svg.append(definitions, shape);
        overlay.append(svg);
        document.body.append(overlay);
    }

    function blocked() {
        return !desktop.matches || document.hidden || !document.hasFocus() ||
            root.classList.contains('is-loading') || root.classList.contains('is-loading-pending') ||
            document.body.classList.contains('is-locked') ||
            document.body.classList.contains('is-reservation-locked') ||
            Boolean(document.activeElement?.closest(editable));
    }

    function buttonAvailable(button) {
        return button && button.isConnected && !button.matches(':disabled, [aria-disabled="true"]') &&
            !button.closest('[inert], [hidden]');
    }

    function leaveButton() {
        hoveredButton?.classList.remove('is-ink-hover');
        hoveredButton = null;
        overlay?.classList.remove('is-absorbed');
    }

    function resetMotion() {
        lastFrame = 0;
        speedAt = 0;
        mouseSpeed = 0;
        fastMode = false;
        fastWeight = 0;
        stopFastWeight = 0;
    }

    // FINDER内で止める場合は座標とCTA状態を残し、イベントから復帰できるようにする。
    function pauseCursor() {
        visible = false;
        window.cancelAnimationFrame(frameId);
        frameId = 0;
        resetMotion();
        if (overlay) overlay.hidden = true;
    }

    function invalidatePointer() {
        pointer.valid = false;
        window.cancelAnimationFrame(interactionFrameId);
        interactionFrameId = 0;
        pauseCursor();
        leaveButton();
    }

    function enterButton(button) {
        if (hoveredButton === button) return;
        leaveButton();
        if (!buttonAvailable(button)) return;
        button.classList.add('c-ink-button');
        const bounds = button.getBoundingClientRect();
        const x = Math.max(0, Math.min(bounds.width, pointer.x - bounds.left));
        const y = Math.max(0, Math.min(bounds.height, pointer.y - bounds.top));
        const reach = Math.hypot(Math.max(x, bounds.width - x), Math.max(y, bounds.height - y));
        button.style.setProperty('--ink-fill-x', `${x}px`);
        button.style.setProperty('--ink-fill-y', `${y}px`);
        button.style.setProperty('--ink-fill-size', `${Math.ceil(reach * 2 + 2)}px`);
        button.classList.add('is-ink-hover');
        hoveredButton = button;
        overlay?.classList.add('is-absorbed');
    }

    function finderSuppressesCursor() {
        if (!finder) return false;
        const step = finder.dataset.finderStep;
        const answering = ['1', '2', '3'].includes(step);
        const waiting = step === 'result' && finderScreen.getAttribute('aria-busy') === 'true';
        if (!answering && !waiting) return false;
        const bounds = finder.getBoundingClientRect();
        return pointer.x >= bounds.left && pointer.x < bounds.right &&
            pointer.y >= bounds.top && pointer.y < bounds.bottom;
    }

    function showCursor(tone) {
        mountCursor();
        overlay.dataset.tone = tone;
        if (!visible) {
            resetMotion();
            head.x = pointer.x;
            head.y = pointer.y;
            dots.forEach(dot => {
                dot.x = pointer.x;
                dot.y = pointer.y;
                dot.node.setAttribute('transform', 'translate(0 0)');
            });
            lastMovedAt = performance.now();
            speedAt = lastMovedAt;
            idleWeight = 0;
            svg.style.transform = `translate3d(${pointer.x - center}px, ${pointer.y - center}px, 0)`;
            visible = true;
            overlay.hidden = false;
        }
        overlay.classList.toggle('is-absorbed', Boolean(hoveredButton));
        requestFrame();
    }

    // 描画ループから独立させ、インク非表示中もスクロールや状態変更を判定する。
    function updateInteraction() {
        interactionFrameId = 0;
        if (!pointer.valid || blocked()) {
            invalidatePointer();
            return;
        }
        const target = document.elementFromPoint(pointer.x, pointer.y);
        if (!target || target.closest(`${editable}, iframe`) || target.closest('[inert]')) {
            invalidatePointer();
            return;
        }
        const button = target.closest(buttonSelector);
        if (buttonAvailable(button)) enterButton(button);
        else leaveButton();
        if (!cursorPage || finderSuppressesCursor()) {
            pauseCursor();
            return;
        }
        showCursor(target.closest('[data-cursor-tone]')?.dataset.cursorTone || 'light');
    }

    function targetsChanged() {
        if (pointer.valid && !interactionFrameId) {
            interactionFrameId = window.requestAnimationFrame(updateInteraction);
        }
    }

    function requestFrame() {
        if (visible && !frameId) frameId = window.requestAnimationFrame(renderCursor);
    }

    function renderCursor(now) {
        frameId = 0;
        if (!visible || !pointer.valid || !cursorPage) return;
        if (blocked()) {
            invalidatePointer();
            return;
        }
        if (hoveredButton && !buttonAvailable(hoveredButton)) leaveButton();
        const delta = lastFrame ? Math.min(64, now - lastFrame) : 1000 / 60;
        lastFrame = now;
        activeTime += delta / 1000;
        const stoppedFor = now - lastMovedAt;
        if (stoppedFor > 40) mouseSpeed *= Math.exp(-delta / 60);
        if (!fastMode && mouseSpeed >= 1200) fastMode = true;
        else if (fastMode && mouseSpeed <= 650) fastMode = false;
        const fastTarget = fastMode ? Math.min(1, Math.max(0, (mouseSpeed - 650) / 1750)) : 0;
        const fastEase = 1 - Math.exp(-delta / (fastTarget > fastWeight ? 80 : 280));
        fastWeight += (fastTarget - fastWeight) * fastEase;
        const reach = tailReach + 100 * fastWeight;
        const idle = stoppedFor >= 150;
        idleWeight = Math.max(0, Math.min(1, idleWeight + delta / (idle ? 450 : -150)));
        const gatherWeight = Math.max(0, Math.min(1, (stoppedFor - 150) / 100));
        const gather = 1 - Math.exp(-delta * gatherWeight / (170 + 60 * stopFastWeight));

        const follow = 1 - Math.exp(-delta / 65);
        head.x += (pointer.x - head.x) * follow;
        head.y += (pointer.y - head.y) * follow;
        const headDistance = Math.hypot(pointer.x - head.x, pointer.y - head.y);
        if (headDistance > 24) {
            head.x = pointer.x + (head.x - pointer.x) * 24 / headDistance;
            head.y = pointer.y + (head.y - pointer.y) * 24 / headDistance;
        }

        let previousDrawX = 0;
        let previousDrawY = 0;
        dots.forEach((dot, index) => {
            if (index === 0) {
                dot.x = head.x;
                dot.y = head.y;
            } else {
                const previous = dots[index - 1];
                const loose = Math.max(0, (index - 13) / 6);
                const ease = 1 - Math.exp(-delta / (48 + index * 1.6 + 110 * fastWeight * loose));
                dot.x += (previous.x - dot.x) * ease;
                dot.y += (previous.y - dot.y) * ease;
                // 停止直後の余韻を残し、高速時ほどゆっくり本体へ集める。
                dot.x += (head.x - dot.x) * gather;
                dot.y += (head.y - dot.y) * gather;
                const distance = Math.hypot(dot.x - head.x, dot.y - head.y);
                const limit = reach * index / (count - 1);
                if (distance > limit) {
                    dot.x = head.x + (dot.x - head.x) * limit / distance;
                    dot.y = head.y + (dot.y - head.y) * limit / distance;
                }
                const linkDistance = Math.hypot(dot.x - previous.x, dot.y - previous.y);
                const connected = Math.min(reach / (count - 1), dot.radius + previous.radius - 1.5);
                // 高速時だけ末尾6円の間隔を緩め、前方のインクはつないでおく。
                const linkLimit = connected + (18 - connected) * fastWeight * loose;
                if (linkDistance > linkLimit) {
                    dot.x = previous.x + (dot.x - previous.x) * linkLimit / linkDistance;
                    dot.y = previous.y + (dot.y - previous.y) * linkLimit / linkDistance;
                }
            }
            // 5方向へまとまりを作り、均等な拡縮ではなく輪郭の一部を膨らませる。
            const lobe = Math.max(0, index - 1) % 5;
            const angle = lobe * Math.PI * 2 / 5;
            const time = activeTime * Math.PI * 2 * 1.5;
            const bulge = Math.max(0, Math.min(3.5,
                1.65 + 1.05 * Math.sin(time / 1.75 + 2 * angle) +
                0.6 * Math.sin(time / 2.35 - 2 * angle + 0.8) +
                0.15 * Math.sin(time / (1.9 + 0.1 * (index % 5)) + index * 2.399963)));
            const orbit = index === 0 ? 0 : radius - dot.radius + bulge;
            let x = dot.x - head.x + Math.cos(angle) * orbit * idleWeight;
            let y = dot.y - head.y + Math.sin(angle) * orbit * idleWeight;
            // 描画側も同じ速度条件で緩め、減速すると滑らかに再結合させる。
            if (index > 0) {
                const drawDistance = Math.hypot(x - previousDrawX, y - previousDrawY);
                const connected = dot.radius + dots[index - 1].radius - 1.5;
                const loose = Math.max(0, (index - 13) / 6);
                const drawLimit = connected + (18 - connected) * fastWeight * loose;
                if (drawDistance > drawLimit) {
                    x = previousDrawX + (x - previousDrawX) * drawLimit / drawDistance;
                    y = previousDrawY + (y - previousDrawY) * drawLimit / drawDistance;
                }
            }
            previousDrawX = x;
            previousDrawY = y;
            dot.node.setAttribute('transform', `translate(${x.toFixed(3)} ${y.toFixed(3)})`);
        });
        svg.style.transform = `translate3d(${(head.x - center).toFixed(3)}px, ${(head.y - center).toFixed(3)}px, 0)`;
        // 表示中はidleでも継続。FINDER内の抑止時とページ全体の抑止時には停止する。
        requestFrame();
    }

    function pointerMoved(event) {
        if (event.pointerType !== 'mouse') return;
        if (blocked()) {
            invalidatePointer();
            return;
        }
        if (event.clientX < 0 || event.clientY < 0 || event.clientX >= window.innerWidth || event.clientY >= window.innerHeight) {
            invalidatePointer();
            return;
        }
        const now = performance.now();
        const changed = pointer.valid && (pointer.x !== event.clientX || pointer.y !== event.clientY);
        if (visible && changed) {
            const elapsed = Math.max(1, now - speedAt);
            const instantaneous = Math.min(6000, Math.hypot(event.clientX - pointer.x, event.clientY - pointer.y) * 1000 / elapsed);
            mouseSpeed += (instantaneous - mouseSpeed) * (1 - Math.exp(-elapsed / 60));
            stopFastWeight = fastWeight;
            lastMovedAt = now;
        }
        pointer.x = event.clientX;
        pointer.y = event.clientY;
        pointer.valid = true;
        speedAt = now;
        targetsChanged();
    }

    function eligibilityChanged() {
        root.classList.toggle('is-ink-cursor-enabled', desktop.matches && cursorPage);
        root.classList.toggle('is-ink-hover-enabled', desktop.matches);
        if (desktop.matches) {
            mountFilters();
            targetsChanged();
        } else invalidatePointer();
    }

    document.addEventListener('pointermove', pointerMoved, { passive: true });
    document.addEventListener('pointerover', event => {
        if (event.pointerType !== 'mouse') return;
        if (event.target.closest(`${editable}, iframe`)) invalidatePointer();
        else targetsChanged();
    }, { passive: true });
    document.addEventListener('pointerdown', event => {
        if (event.pointerType !== 'mouse') invalidatePointer();
    }, { passive: true });
    document.addEventListener('pointerout', event => {
        // 回答ボタンの差し替えによる境界イベントは、画面外への移動と区別する。
        if (!event.relatedTarget && event.target.isConnected) invalidatePointer();
        else targetsChanged();
    }, { passive: true });
    root.addEventListener('pointerleave', invalidatePointer, { passive: true });
    document.addEventListener('focusin', event => { if (event.target.closest(editable)) invalidatePointer(); });
    document.addEventListener('focusout', targetsChanged);
    document.addEventListener('visibilitychange', () => { if (document.hidden) invalidatePointer(); });
    document.addEventListener('hody:loading-start', invalidatePointer);
    window.addEventListener('hody:reservation-open', invalidatePointer);
    window.addEventListener('blur', invalidatePointer);
    window.addEventListener('pagehide', invalidatePointer);
    window.addEventListener('pageshow', invalidatePointer);
    window.addEventListener('scroll', targetsChanged, { passive: true });
    window.addEventListener('resize', targetsChanged, { passive: true });
    desktop.addEventListener('change', eligibilityChanged);

    const stateObserver = new MutationObserver(targetsChanged);
    stateObserver.observe(root, { attributes: true, attributeFilter: ['class'] });
    stateObserver.observe(document.body, { attributes: true, attributeFilter: ['class'] });
    if (finder && finderScreen) {
        const finderObserver = new MutationObserver(() => {
            finderScreen.querySelectorAll('.js-finder-reserve, .js-finder-retry').forEach(button => button.classList.add('c-ink-button'));
            targetsChanged();
        });
        finderObserver.observe(finder, { attributes: true, attributeFilter: ['data-finder-step'] });
        finderObserver.observe(finderScreen, { childList: true, subtree: true, attributes: true, attributeFilter: ['aria-busy'] });
        if (typeof ResizeObserver === 'function') {
            const finderResizeObserver = new ResizeObserver(targetsChanged);
            finderResizeObserver.observe(finder);
        }
    }
    const fixedReservation = document.querySelector('.js-fixed-reservation');
    if (fixedReservation) {
        const fixedObserver = new MutationObserver(targetsChanged);
        fixedObserver.observe(fixedReservation, { attributes: true, attributeFilter: ['inert'] });
    }
    eligibilityChanged();
})();
