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
    const reservationDateTime = setupReservationDateTime();

    function setupReservationDateTime() {
        const dateInput = form.querySelector('.js-reservation-date');
        const timeInput = form.querySelector('.js-reservation-time');
        const dateStatus = form.querySelector('.js-reservation-date-status');
        if (!dateInput || !timeInput || !dateStatus) return null;

        // 営業時間12:00〜19:00・水曜定休。最終開始18:30は仮設定。
        // 30分は開始時刻の間隔であり、試奏の所要時間ではない。
        const firstStart = 12 * 60;
        const lastStart = 18 * 60 + 30;
        const step = 30;
        const closedWeekday = 3;
        const japanClock = new Intl.DateTimeFormat('en-CA', {
            timeZone: 'Asia/Tokyo', year: 'numeric', month: '2-digit', day: '2-digit',
            hour: '2-digit', minute: '2-digit', hourCycle: 'h23'
        });
        let picker = null;
        let minimumDate = '';
        let refreshing = false;

        function nowInJapan() {
            const parts = Object.fromEntries(japanClock.formatToParts(new Date()).map(part => [part.type, part.value]));
            return {
                date: `${parts.year}-${parts.month}-${parts.day}`,
                minutes: Number(parts.hour) * 60 + Number(parts.minute)
            };
        }

        function parseDate(value) {
            if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return null;
            const [year, month, day] = value.split('-').map(Number);
            const date = new Date(year, month - 1, day, 12);
            return date.getFullYear() === year && date.getMonth() === month - 1 && date.getDate() === day ? date : null;
        }

        function dateError(value, now) {
            if (!value) return '';
            const date = parseDate(value);
            if (!date) return '日付をYYYY-MM-DD形式で正しく入力してください。';
            if (value < now.date) return '本日以降の日付を選択してください。';
            if (date.getDay() === closedWeekday) return '水曜日は定休日です。別の日付を選択してください。';
            return '';
        }

        function refresh({ syncCalendar = false } = {}) {
            if (refreshing) return;
            refreshing = true;
            try {
                const now = nowInJapan();
                const value = dateInput.value;
                const error = dateError(value, now);
                if (minimumDate !== now.date) {
                    minimumDate = now.date;
                    if (picker) picker.set('minDate', minimumDate);
                    else dateInput.min = minimumDate;
                    // flatpickrが古い選択日を除去しても、入力は残して検証エラーを伝える。
                    dateInput.value = value;
                }
                if (picker && syncCalendar) {
                    if (value && !error) picker.setDate(value, false, 'Y-m-d');
                    else picker.clear(false);
                    dateInput.value = value;
                    picker.redraw();
                }

                const previousTime = timeInput.value;
                const options = [new Option('時間を選択', '')];
                for (let minutes = firstStart; minutes <= lastStart; minutes += step) {
                    const time = `${String(Math.floor(minutes / 60)).padStart(2, '0')}:${String(minutes % 60).padStart(2, '0')}`;
                    const option = new Option(time, time);
                    option.disabled = Boolean(value) && (Boolean(error) || (value === now.date && minutes <= now.minutes));
                    options.push(option);
                }
                timeInput.replaceChildren(...options);
                timeInput.value = options.some(option => option.value === previousTime && !option.disabled) ? previousTime : '';
                const noTimes = Boolean(value) && !error && !options.some(option => option.value && !option.disabled);
                const message = error || (noTimes ? 'この日に選択できる時間はありません。別の日付を選択してください。' : '');
                dateInput.setCustomValidity(message);
                dateStatus.textContent = message;
            } finally {
                refreshing = false;
            }
        }

        try {
            if (typeof window.flatpickr !== 'function' || !window.flatpickr.l10ns.ja) throw new Error('Date picker unavailable');
            minimumDate = nowInJapan().date;
            picker = window.flatpickr(dateInput, {
                locale: 'ja', dateFormat: 'Y-m-d', ariaDateFormat: 'Y年n月j日',
                allowInput: true, disableMobile: true, static: true,
                minDate: minimumDate, disable: [date => date.getDay() === closedWeekday],
                monthSelectorType: 'static',
                parseDate: value => parseDate(value) || undefined,
                onChange: () => refresh(),
                onClose: () => refresh(),
                onOpen: () => {
                    refresh({ syncCalendar: true });
                    window.requestAnimationFrame(() => {
                        if (picker?.isOpen) picker.calendarContainer.scrollIntoView({ block: 'nearest', behavior: 'instant' });
                    });
                }
            });
            if (!picker?.calendarContainer) throw new Error('Date picker initialization failed');
            // 年などのカレンダー操作欄を、予約フォームの必須・範囲検証から分離する。
            picker.calendarContainer.querySelectorAll('input, select, button').forEach(control => control.setAttribute('form', ''));
        } catch (error) {
            dateInput._flatpickr?.destroy();
            picker = null;
            minimumDate = '';
            dateInput.type = 'date';
            dateInput.readOnly = false;
            dateInput.removeAttribute('inputmode');
        }

        dateInput.addEventListener('input', () => refresh());
        dateInput.addEventListener('change', () => refresh({ syncCalendar: true }));
        timeInput.addEventListener('focus', () => refresh());
        timeInput.addEventListener('pointerdown', () => refresh());
        timeInput.addEventListener('change', () => refresh());
        // 不正な手入力をflatpickrが別の日付へ繰り上げたり、空欄へ変えたりする前に止める。
        dateInput.addEventListener('blur', event => {
            if (dateError(dateInput.value, nowInJapan())) event.stopImmediatePropagation();
            const enteringCalendar = picker && event.relatedTarget instanceof Node && picker.calendarContainer.contains(event.relatedTarget);
            refresh({ syncCalendar: !enteringCalendar });
        }, true);
        dateInput.addEventListener('keydown', event => {
            if (event.key === 'ArrowDown' && picker) {
                event.preventDefault();
                event.stopImmediatePropagation();
                picker.open();
                const calendar = picker.calendarContainer;
                const day = calendar.querySelector('.selected:not(.flatpickr-disabled)') ||
                    calendar.querySelector('.today:not(.flatpickr-disabled)') ||
                    calendar.querySelector('.flatpickr-day:not(.flatpickr-disabled):not(.prevMonthDay):not(.nextMonthDay)');
                day?.focus();
            }
            if (event.key === 'Enter' && dateError(dateInput.value, nowInJapan())) {
                event.preventDefault();
                event.stopImmediatePropagation();
                refresh();
                dateInput.reportValidity();
            }
        }, true);
        // カレンダー内のEscapeは先に消費し、モーダル全体を閉じない。
        dialog.addEventListener('keydown', event => {
            if (event.key !== 'Escape' || !picker?.isOpen) return;
            event.preventDefault();
            event.stopImmediatePropagation();
            dateInput.focus({ preventScroll: true });
            picker.close();
        }, true);
        refresh();
        return { refresh, close: () => picker?.close() };
    }

    function openReservation(product = '') {
        if (dialog.classList.contains('is-open')) return;
        lastFocus = document.activeElement;
        window.dispatchEvent(new CustomEvent('hody:reservation-open'));
        dialog.inert = false;
        dialog.classList.add('is-open');
        dialog.setAttribute('aria-hidden', 'false');
        document.body.classList.add('is-locked');
        reservationDateTime?.refresh({ syncCalendar: true });
        if (product && [...productInput.options].some(option => option.value === product)) productInput.value = product;
        closeButton.focus();
    }

    function closeReservation() {
        if (!dialog.classList.contains('is-open')) return;
        reservationDateTime?.close();
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
            const focusables = [...panel.querySelectorAll('button, select, input, textarea, a[href], [tabindex]')].filter(el =>
                !el.disabled && el.tabIndex >= 0 && el.getClientRects().length && getComputedStyle(el).visibility !== 'hidden');
            const first = focusables[0], last = focusables[focusables.length - 1];
            if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
            else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
        }
    });

    form.addEventListener('submit', event => {
        event.preventDefault();
        reservationDateTime?.refresh({ syncCalendar: true });
        // Figma未提示の「予約内容確認画面」と送信APIは制作範囲外。ここではHTML標準の入力チェックまで。
        if (!form.checkValidity()) { form.reportValidity(); return; }
        // 確認画面が未設計のため、内容の送信・保存は行わない。
        console.info('HODY GUITAR: 必須項目の入力確認が完了しました。確認画面・送信先は未実装です。');
    });
})();
