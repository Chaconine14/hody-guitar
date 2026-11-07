(() => {
    'use strict';

    const root = document.documentElement;
    if (!root.classList.contains('is-loading')) return;
    const finish = () => document.dispatchEvent(new Event('hody:loading-finish'));

    try {
        const loader = document.querySelector('.js-loading');
        if (!loader || getComputedStyle(loader).position !== 'fixed') {
            finish();
            return;
        }

        // 準備完了後の最初の描画から、既存の4秒の演出を再生する。
        const motion = {
            duration: 4000,
            fadeStart: 750,
            fadeEnd: 1625,
            holeStart: 1375,
            expandStart: 1625
        };
        if (window.scrollX || window.scrollY) {
            finish();
            return;
        }

        const svg = loader.querySelector('.js-loading-svg');
        const mask = loader.querySelector('.js-loading-mask');
        const maskBase = loader.querySelector('.js-loading-mask-base');
        const background = loader.querySelector('.js-loading-background');
        const logo = loader.querySelector('.js-loading-logo');
        const otherLetters = loader.querySelector('.js-loading-letters');
        const soundhole = loader.querySelector('.js-loading-hole');
        const holePosition = loader.querySelector('.js-loading-hole-position');
        const holeScale = loader.querySelector('.js-loading-hole-scale');
        const letterO = loader.querySelector('.js-loading-o');
        const firstImage = document.querySelector('.p-hero__slide img');
        if (!svg || !mask || !maskBase || !background || !logo || !otherLetters || !soundhole || !holePosition || !holeScale || !letterO || !firstImage) {
            finish();
            return;
        }

        // 元のロゴは117×60。穴とOを同じ中心・同じ倍率で拡大する。
        const hole = { x: 48.1891, y: 20.6685, minimumRadius: 3.4002 };
        let maximumScale = 1;
        let imageReady = false;
        let stopped = false;
        let frameId = 0;
        let resizeObserver;
        let startedAt = null;

        function stop() {
            stopped = true;
            window.cancelAnimationFrame(frameId);
            window.removeEventListener('resize', resize);
            resizeObserver?.disconnect();
            document.removeEventListener('hody:loading-end', stop);
            document.removeEventListener('visibilitychange', visibilityChanged);
            firstImage.removeEventListener('load', imageLoaded);
            firstImage.removeEventListener('error', finish);
        }

        function imageLoaded() {
            if (stopped) return;
            imageReady = firstImage.naturalWidth > 0;
            if (imageReady) prepare();
            else finish();
        }

        function prepare() {
            if (stopped || startedAt !== null || frameId || !imageReady || document.hidden) return;
            frameId = window.requestAnimationFrame(render);
        }

        function visibilityChanged() {
            if (document.hidden && startedAt === null) {
                window.cancelAnimationFrame(frameId);
                frameId = 0;
            } else {
                prepare();
            }
        }

        function resize() {
            if (stopped) return;
            try {
                const box = loader.getBoundingClientRect();
                const logoWidth = parseFloat(getComputedStyle(loader).getPropertyValue('--loading-logo-width'));
                if (!box.width || !box.height || !logoWidth) {
                    finish();
                    return;
                }
                const scale = logoWidth / 117;
                const left = (box.width - logoWidth) / 2;
                const top = (box.height - 60 * scale) / 2;
                const position = `translate(${left} ${top}) scale(${scale})`;
                svg.setAttribute('viewBox', `0 0 ${box.width} ${box.height}`);
                for (const rectangle of [mask, maskBase, background]) {
                    rectangle.setAttribute('width', box.width);
                    rectangle.setAttribute('height', box.height);
                }
                logo.setAttribute('transform', position);
                holePosition.setAttribute('transform', position);
                const centerX = left + hole.x * scale;
                const centerY = top + hole.y * scale;
                const cornerDistance = Math.max(...[0, box.width].flatMap(x =>
                    [0, box.height].map(y => Math.hypot(x - centerX, y - centerY))));
                maximumScale = cornerDistance / (hole.minimumRadius * scale) + 2;
            } catch {
                finish();
            }
        }

        const clamp = value => Math.min(1, Math.max(0, value));
        const ease = value => {
            const t = clamp(value);
            return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
        };
        function render(now) {
            if (stopped) return;
            frameId = 0;
            try {
                if (startedAt === null) {
                    if (document.hidden) return;
                    document.dispatchEvent(new Event('hody:loading-start'));
                    if (stopped || !root.classList.contains('is-loading')) return;
                    startedAt = now;
                    root.classList.remove('is-loading-pending');
                }
                const progress = clamp((now - startedAt) / motion.duration);
                const time = progress * motion.duration;
                otherLetters.setAttribute('opacity', 1 - ease((time - motion.fadeStart) / (motion.fadeEnd - motion.fadeStart)));
                soundhole.setAttribute('opacity', ease((time - motion.holeStart) / (motion.expandStart - motion.holeStart)));
                const scale = 1 + (maximumScale - 1) * ease((time - motion.expandStart) / (motion.duration - motion.expandStart));
                const transform = `translate(${hole.x} ${hole.y}) scale(${scale}) translate(${-hole.x} ${-hole.y})`;
                holeScale.setAttribute('transform', transform);
                letterO.setAttribute('transform', transform);
                if (progress >= 1) finish();
                else frameId = window.requestAnimationFrame(render);
            } catch {
                finish();
            }
        }

        document.addEventListener('hody:loading-end', stop);
        document.addEventListener('visibilitychange', visibilityChanged);
        window.addEventListener('resize', resize);
        firstImage.addEventListener('error', finish);
        loader.hidden = false;
        resize();
        if (stopped) return;
        // Safariでwindow.resizeより先に本体の高さが変わっても、SVGを同じ寸法に揃える。
        if (typeof ResizeObserver === 'function') {
            resizeObserver = new ResizeObserver(resize);
            resizeObserver.observe(loader);
        }
        if (typeof firstImage.decode === 'function') {
            firstImage.decode().then(imageLoaded, () => { if (!stopped) finish(); });
        } else if (firstImage.complete) {
            imageLoaded();
        } else {
            firstImage.addEventListener('load', imageLoaded, { once: true });
        }
    } catch {
        finish();
    }
})();
