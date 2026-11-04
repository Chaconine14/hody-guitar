(() => {
    'use strict';

    const dialog = document.querySelector('.js-reservation');
    const panel = dialog?.querySelector('.p-reservation__panel');
    const closeButton = dialog?.querySelector('.js-close-reservation');
    const productInput = dialog?.querySelector('#reserve-product');
    const form = dialog?.querySelector('.js-reservation-form');
    if (!dialog || !panel || !closeButton || !form) return;
    let lastFocus = null;

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
        if (lastFocus?.isConnected) lastFocus.focus();
    }

    document.querySelectorAll('.js-open-reservation').forEach(button => {
        button.addEventListener('click', () => openReservation(button.dataset.product || ''));
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
