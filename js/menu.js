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
