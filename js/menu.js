(() => {
    'use strict';

    const menu = document.querySelector('.js-mobile-menu');
    const openButton = document.querySelector('.js-menu-open');
    const closeButton = document.querySelector('.js-menu-close');
    if (!menu || !openButton || !closeButton) return;
    let lastFocus = null;

    function openMenu() {
        if (menu.classList.contains('is-open')) return;
        lastFocus = document.activeElement;
        menu.inert = false;
        menu.classList.add('is-open');
        menu.setAttribute('aria-hidden', 'false');
        openButton.setAttribute('aria-expanded', 'true');
        document.body.classList.add('is-locked');
        closeButton.focus();
    }

    function closeMenu({ restoreFocus = true } = {}) {
        if (!menu.classList.contains('is-open')) return;
        menu.classList.remove('is-open');
        menu.setAttribute('aria-hidden', 'true');
        menu.inert = true;
        openButton.setAttribute('aria-expanded', 'false');
        document.body.classList.remove('is-locked');
        if (restoreFocus) (lastFocus || openButton).focus();
    }

    openButton.addEventListener('click', openMenu);
    closeButton.addEventListener('click', () => closeMenu());
    menu.querySelectorAll('.p-mobile-menu__nav a').forEach(link => {
        link.addEventListener('click', () => closeMenu({ restoreFocus: false }));
    });
    document.addEventListener('keydown', event => {
        if (!menu.classList.contains('is-open')) return;
        if (event.key === 'Escape') closeMenu();
        if (event.key === 'Tab') {
            const focusables = [...menu.querySelectorAll('a,button')].filter(el => !el.disabled);
            const first = focusables[0], last = focusables[focusables.length - 1];
            if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
            else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
        }
    });
    window.matchMedia('(min-width: 769px)').addEventListener('change', evt => {
        if (evt.matches) closeMenu({ restoreFocus: false });
    });
    // 予約画面をメニュー上から開く場合も背面のメニューを閉じる
    window.addEventListener('hody:reservation-open', () => closeMenu({ restoreFocus: false }));
})();

// メニューの開閉処理とは独立して、SPヘッダーの表示だけを管理する。
(() => {
    'use strict';

    const header = document.querySelector('.js-header');
    if (!header) return;
    const root = document.documentElement;
    const menu = document.querySelector('.js-mobile-menu');
    const reservation = document.querySelector('.js-reservation');
    const mobileViewport = window.matchMedia('(max-width: 768px)');
    const topBoundary = 80;
    const directionThreshold = 12;
    let hidden = false;
    let referenceY = topBoundary;
    let maximumScroll = 0;
    let frameId = 0;
    let viewportWidth = window.innerWidth;
    let menuOpen = Boolean(menu?.classList.contains('is-open'));
    let reservationOpen = isReservationOpen();

    function isReservationOpen() {
        return document.body.classList.contains('is-reservation-locked') ||
            Boolean(reservation?.classList.contains('is-open'));
    }

    function refreshRange() {
        if (isReservationOpen()) return;
        maximumScroll = Math.max(0, root.scrollHeight - window.innerHeight);
    }

    function scrollPosition() {
        // iOSの上下端バウンスを、通常のスクロール範囲へ補正する。
        return Math.min(maximumScroll, Math.max(0, window.scrollY));
    }

    function setHidden(value) {
        if (hidden === value) return;
        hidden = value;
        header.classList.toggle('is-scroll-hidden', value);
        header.inert = value;
    }

    function cancelUpdate() {
        window.cancelAnimationFrame(frameId);
        frameId = 0;
    }

    function reset({ show = false } = {}) {
        cancelUpdate();
        refreshRange();
        referenceY = Math.max(topBoundary, scrollPosition());
        if (show) setHidden(false);
    }

    function update() {
        frameId = 0;
        // 背景固定によるscrollYの変化は、最上部判定より先に除外する。
        if (!mobileViewport.matches || isReservationOpen() || root.classList.contains('is-loading')) return;
        if (menu?.classList.contains('is-open')) return;
        const y = scrollPosition();
        if (y <= topBoundary) {
            setHidden(false);
            referenceY = topBoundary;
            return;
        }

        // 1イベントの差分ではなく、表示中は最小位置、非表示中は最大位置を基準にする。
        if (hidden) {
            referenceY = Math.max(referenceY, y);
            if (referenceY - y < directionThreshold) return;
            setHidden(false);
        } else {
            referenceY = Math.max(topBoundary, Math.min(referenceY, y));
            if (y - referenceY < directionThreshold) return;
            setHidden(true);
        }
        referenceY = y;
    }

    function requestUpdate() {
        if (!mobileViewport.matches || frameId || isReservationOpen() ||
            menu?.classList.contains('is-open') || root.classList.contains('is-loading')) return;
        frameId = window.requestAnimationFrame(update);
    }

    function configure() {
        cancelUpdate();
        // inertにはメディアクエリが効かないため、予約中でもPCでは必ず解除する。
        if (!mobileViewport.matches) {
            setHidden(false);
            return;
        }
        if (!isReservationOpen()) reset({ show: true });
    }

    const lockObserver = new MutationObserver(() => {
        const nextMenuOpen = Boolean(menu?.classList.contains('is-open'));
        const nextReservationOpen = isReservationOpen();
        // 商品検索など、別用途のbodyクラス変更では基準位置を変えない。
        if (nextMenuOpen === menuOpen && nextReservationOpen === reservationOpen) return;
        menuOpen = nextMenuOpen;
        reservationOpen = nextReservationOpen;
        cancelUpdate();
        if (!mobileViewport.matches || reservationOpen) return;
        // モーダル解除時は、既存処理による座標復元後の位置を基準に再開する。
        reset({ show: menuOpen });
    });
    lockObserver.observe(document.body, { attributes: true, attributeFilter: ['class'] });

    window.addEventListener('scroll', requestUpdate, { passive: true });
    window.addEventListener('resize', () => {
        const widthChanged = viewportWidth !== window.innerWidth;
        viewportWidth = window.innerWidth;
        if (!mobileViewport.matches || isReservationOpen()) return;
        // アドレスバーによる高さだけの変化では、方向判定の累積を保持する。
        if (widthChanged) reset();
        else refreshRange();
    });
    window.addEventListener('load', configure);
    window.addEventListener('pageshow', configure);
    window.addEventListener('pagehide', cancelUpdate);
    mobileViewport.addEventListener('change', configure);
    document.addEventListener('hody:loading-end', () => {
        cancelUpdate();
        // 終了イベント後にis-loadingが解除されるため、次の描画で再設定する。
        frameId = window.requestAnimationFrame(() => {
            frameId = 0;
            configure();
        });
    });
    // 本文の伸縮時だけ範囲を更新し、毎スクロールの寸法計測を避ける。
    const resizeObserver = new ResizeObserver(refreshRange);
    resizeObserver.observe(document.body);
    configure();
})();
