(() => {
    'use strict';

    const hero = document.querySelector('.js-reservation-hero');
    const fixedReservation = document.querySelector('.js-fixed-reservation');
    const footer = document.querySelector('.js-reservation-footer');
    if (hero && fixedReservation && footer) {
        const mobileViewport = window.matchMedia('(max-width: 768px)');
        let updatePending = false;

        function updateFixedReservation() {
            const passedHero = hero.getBoundingClientRect().bottom <= window.innerHeight * 0.5;
            const reachedFooter = mobileViewport.matches && footer.getBoundingClientRect().top < window.innerHeight;
            const isVisible = passedHero && !reachedFooter;
            fixedReservation.classList.toggle('is-visible', isVisible);
            fixedReservation.inert = !isVisible;
            updatePending = false;
        }

        function requestFixedReservationUpdate() {
            if (updatePending) return;
            updatePending = true;
            window.requestAnimationFrame(updateFixedReservation);
        }

        window.addEventListener('scroll', requestFixedReservationUpdate, { passive: true });
        window.addEventListener('resize', requestFixedReservationUpdate);
        window.addEventListener('load', requestFixedReservationUpdate);
        window.addEventListener('pageshow', requestFixedReservationUpdate);
        mobileViewport.addEventListener('change', requestFixedReservationUpdate);
        // 100vhや画像読み込みによるFV・本文の実寸変更後にも判定する。
        const resizeObserver = new ResizeObserver(requestFixedReservationUpdate);
        resizeObserver.observe(hero);
        resizeObserver.observe(footer);
        resizeObserver.observe(document.querySelector('main'));
        updateFixedReservation();
    }

    const dialog = document.querySelector('.js-reservation');
    const panel = dialog?.querySelector('.p-reservation__panel');
    const closeButton = dialog?.querySelector('.js-close-reservation');
    const productInput = dialog?.querySelector('#reserve-product');
    const form = dialog?.querySelector('.js-reservation-form');
    if (!dialog || !panel || !closeButton || !form) return;
    let lastFocus = null;
    let finderOptions = null;

    function openReservation(product = '') {
        if (dialog.classList.contains('is-open')) return;
        lastFocus = document.activeElement;
        window.dispatchEvent(new CustomEvent('hody:reservation-open'));
        dialog.inert = false;
        dialog.classList.add('is-open');
        dialog.setAttribute('aria-hidden', 'false');
        document.body.classList.add('is-locked');
        if (product && [...productInput.options].some(option => option.value === product)) productInput.value = product;
        closeButton.focus();
    }

    function closeReservation() {
        if (!dialog.classList.contains('is-open')) return;
        dialog.classList.remove('is-open');
        dialog.setAttribute('aria-hidden', 'true');
        dialog.inert = true;
        document.body.classList.remove('is-locked');
        if (finderOptions) {
            productInput.replaceChildren(...finderOptions.options);
            productInput.value = finderOptions.value;
            finderOptions = null;
        }
        if (lastFocus?.isConnected) lastFocus.focus();
    }

    // 診断から開いた間だけ推薦候補を表示し、通常の予約選択肢へ戻せるよう保持する。
    window.addEventListener('hody:finder-reservation', event => {
        if (dialog.classList.contains('is-open')) return;
        const { products, returnFocus } = event.detail || {};
        if (!Array.isArray(products) || !products.length) return;
        const unique = products.filter((product, index) => product.id && product.brand && product.model &&
            products.findIndex(candidate => candidate.id === product.id) === index);
        if (!unique.length) return;
        finderOptions = {
            options: [...productInput.options].map(option => option.cloneNode(true)),
            value: productInput.value
        };
        const undecided = productInput.options[0].cloneNode(true);
        const options = unique.map(product => {
            const name = product.display_name || `${product.brand} ${product.model}`;
            const option = new Option(name, name);
            option.dataset.productId = product.id;
            return option;
        });
        productInput.replaceChildren(undecided, ...options);
        openReservation(options[0].value);
        if (returnFocus instanceof HTMLElement && returnFocus.isConnected) lastFocus = returnFocus;
    });

    // JSONから再描画されたカードにも対応。既存の静的ボタンも同じ入口を使う。
    document.addEventListener('click', event => {
        const button = event.target instanceof Element ? event.target.closest('.js-open-reservation') : null;
        if (!button || button.disabled) return;
        openReservation(button.dataset.product || '');
    });
    closeButton.addEventListener('click', closeReservation);
    dialog.querySelector('.js-reservation-backdrop').addEventListener('click', closeReservation);

    document.addEventListener('keydown', event => {
        if (!dialog.classList.contains('is-open')) return;
        if (event.key === 'Escape') closeReservation();
        if (event.key === 'Tab') {
            const focusables = [...panel.querySelectorAll('button, select, input, textarea, a[href]')].filter(el => !el.disabled);
            const first = focusables[0], last = focusables[focusables.length - 1];
            if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
            else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
        }
    });

    form.addEventListener('submit', event => {
        event.preventDefault();
        // Figma未提示の「予約内容確認画面」と送信APIは制作範囲外。ここではHTML標準の入力チェックまで。
        if (!form.checkValidity()) { form.reportValidity(); return; }
        // 確認画面が未設計のため、内容の送信・保存は行わない。
        console.info('HODY GUITAR: 必須項目の入力確認が完了しました。確認画面・送信先は未実装です。');
    });
})();
