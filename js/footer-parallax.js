(() => {
    'use strict';

    const visual = document.querySelector('.js-footer-parallax');
    const image = visual?.querySelector('img');
    if (!visual || !image) return;

    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
    const observesIntersection = 'IntersectionObserver' in window;
    let enabled = false;
    let visible = false;
    let frameId = 0;

    function isLocked() {
        return document.body.classList.contains('is-locked') ||
            document.body.classList.contains('is-reservation-locked');
    }

    function pause() {
        window.cancelAnimationFrame(frameId);
        frameId = 0;
        visual.classList.remove('is-parallax-active');
    }

    function requestUpdate(force = false) {
        if (!enabled || document.hidden || isLocked() || (!visible && !force) || frameId) return;
        frameId = window.requestAnimationFrame(update);
    }

    function update() {
        frameId = 0;
        if (!enabled || document.hidden || isLocked()) return;

        const box = visual.getBoundingClientRect();
        const viewportHeight = window.innerHeight;
        visible = box.height > 0 && box.bottom >= 0 && box.top <= viewportHeight;
        if (!visible) {
            visual.classList.remove('is-parallax-active');
            return;
        }

        const range = parseFloat(getComputedStyle(visual).getPropertyValue('--footer-parallax-range'));
        if (!Number.isFinite(range) || range <= 0) {
            enabled = false;
            visual.classList.remove('is-parallax', 'is-parallax-active');
            image.style.removeProperty('--footer-parallax-y');
            return;
        }

        // ページ末尾で写真が画面上へ抜け切らない場合も、移動量を使い切る。
        const scrollY = window.scrollY;
        const start = Math.max(0, scrollY + box.top - viewportHeight);
        const maximumScroll = Math.max(0, document.documentElement.scrollHeight - viewportHeight);
        const end = Math.min(scrollY + box.bottom, maximumScroll);
        const progress = end > start ? Math.min(1, Math.max(0, (scrollY - start) / (end - start))) : 0.5;
        const offset = (progress - 0.5) * range;

        visual.classList.add('is-parallax-active');
        image.style.setProperty('--footer-parallax-y', `${offset}px`);
    }

    function configure() {
        pause();
        enabled = !reduceMotion.matches;
        visual.classList.toggle('is-parallax', enabled);
        if (enabled) requestUpdate(true);
        else image.style.removeProperty('--footer-parallax-y');
    }

    window.addEventListener('scroll', () => requestUpdate(!observesIntersection), { passive: true });
    window.addEventListener('resize', () => requestUpdate(true));
    window.addEventListener('load', () => requestUpdate(true));
    window.addEventListener('pageshow', () => requestUpdate(true));
    window.addEventListener('pagehide', pause);
    image.addEventListener('load', () => requestUpdate(true));
    document.addEventListener('visibilitychange', () => {
        if (document.hidden) pause();
        else requestUpdate(true);
    });
    reduceMotion.addEventListener('change', configure);

    if (observesIntersection) {
        const intersection = new IntersectionObserver(entries => {
            visible = entries[entries.length - 1].isIntersecting;
            if (visible) requestUpdate(true);
            else pause();
        });
        intersection.observe(visual);
    }

    if ('ResizeObserver' in window) {
        const resize = new ResizeObserver(() => requestUpdate(true));
        resize.observe(visual);
        const main = document.querySelector('main');
        if (main) resize.observe(main);
    }

    // body固定中は座標を保持し、解除後のスクロール位置で再計算する。
    const lockObserver = new MutationObserver(() => {
        if (isLocked()) pause();
        else requestUpdate(true);
    });
    lockObserver.observe(document.body, { attributes: true, attributeFilter: ['class'] });
    configure();
})();
