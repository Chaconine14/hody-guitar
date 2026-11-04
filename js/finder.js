import { QUESTIONS, RESULT_TYPES } from './finder-config.js';
import { recommendGuitars } from './finder-logic.js';

const root = document.querySelector('.js-finder');

if (root) {
    const screen = root.querySelector('.js-finder-screen');
    const status = root.querySelector('.js-finder-status');
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
    let answers = {};
    let step = 0;
    let version = 0;
    let catalog = { status: 'idle', products: [], promise: null };
    let recommendations = [];

    function element(tag, className, text) {
        const node = document.createElement(tag);
        node.className = className;
        if (text !== undefined) node.textContent = text;
        return node;
    }

    function button(className, text) {
        const node = element('button', className, text);
        node.type = 'button';
        return node;
    }

    function header() {
        const head = element('div', 'p-finder__head');
        const title = element('div', 'c-section-heading p-finder__heading');
        const heading = element('h2', 'c-section-heading__en', 'GUITAR FINDER');
        heading.id = 'finder-heading';
        title.append(heading, element('p', 'c-section-heading__ja', 'おすすめギター診断'));
        head.append(title);
        if (step > 0) {
            const back = button('p-finder__back js-finder-back', '前の質問へ');
            back.addEventListener('click', () => {
                step = Math.min(step - 1, QUESTIONS.length - 1);
                renderQuestion();
            });
            head.append(back);
        }
        return head;
    }

    function announce(heading, message) {
        status.textContent = message;
        heading.tabIndex = -1;
        heading.focus({ preventScroll: true });
        root.scrollIntoView({ block: 'start', behavior: reduceMotion.matches ? 'instant' : 'smooth' });
    }

    function loadCatalog() {
        if (catalog.status === 'loaded' || catalog.status === 'loading') return catalog.promise;
        catalog.status = 'loading';
        catalog.promise = fetch('data/products.json').then(response => {
            if (!response.ok) throw new Error(`Catalog HTTP ${response.status}`);
            return response.json();
        }).then(data => {
            if (!Array.isArray(data.products)) throw new Error('Invalid product catalog');
            catalog.products = data.products;
            catalog.status = 'loaded';
            return data.products;
        }).catch(error => {
            catalog.status = 'failed';
            throw error;
        });
        return catalog.promise;
    }

    function start() {
        answers = Object.fromEntries(QUESTIONS.map(question => [question.key, null]));
        step = 0;
        recommendations = [];
        loadCatalog().catch(() => {});
        renderQuestion();
    }

    function renderQuestion() {
        version += 1;
        root.classList.add('is-started');
        root.classList.remove('is-result');
        delete root.dataset.finderType;
        root.dataset.finderStep = String(step + 1);
        screen.setAttribute('aria-busy', 'false');
        const question = QUESTIONS[step];
        const content = element('div', 'p-finder__question');
        const prompt = element('div', 'p-finder__prompt');
        const progress = element('p', 'p-finder__progress', `QUESTION ${step + 1} / ${QUESTIONS.length}`);
        progress.id = 'finder-progress';
        const title = element('h3', 'p-finder__question-title', question.title);
        title.setAttribute('aria-describedby', progress.id);
        prompt.append(progress, title);
        const options = element('div', `p-finder__answers p-finder__answers--${question.options.length}`);
        question.options.forEach(option => {
            const answer = button('p-finder__answer js-finder-answer');
            answer.dataset.answer = option.value;
            answer.setAttribute('aria-pressed', String(answers[question.key] === option.value));
            const arrow = element('span', 'p-finder__answer-arrow', '▶︎');
            arrow.setAttribute('aria-hidden', 'true');
            answer.append(element('span', 'p-finder__answer-label', option.label), arrow);
            answer.addEventListener('click', () => {
                answers[question.key] = option.value;
                step += 1;
                if (step === QUESTIONS.length) renderResult();
                else renderQuestion();
            });
            options.append(answer);
        });
        content.append(prompt, options, element('p', 'p-finder__hint', '回答を選ぶと次の画面に進みます。'));
        screen.replaceChildren(header(), content);
        announce(title, `QUESTION ${step + 1} / ${QUESTIONS.length} ${question.title}`);
    }

    function productCard(product) {
        const card = element('article', 'p-finder__card');
        card.dataset.productId = product.id;
        const photo = element('div', 'p-finder__photo');
        const fallback = element('p', 'p-finder__image-fallback', '画像を表示できません');
        fallback.hidden = Boolean(product.image_src);
        photo.append(fallback);
        if (product.image_src) {
            const image = element('img', '');
            image.alt = `${product.brand} ${product.model}`;
            image.width = 256;
            image.height = 320;
            image.addEventListener('error', () => {
                image.hidden = true;
                fallback.hidden = false;
            }, { once: true });
            image.src = product.image_src;
            photo.append(image);
        }
        card.append(photo, element('p', 'p-finder__brand', product.brand), element('h4', 'p-finder__model', product.model));
        return card;
    }

    function resultActions(enabled) {
        const actions = element('div', 'p-finder__actions');
        const retry = button('c-button c-button--outline p-finder__retry js-finder-retry');
        const retryArrow = element('img', 'p-finder__button-arrow');
        retryArrow.src = 'assets/images/guide/arrow-header.svg';
        retryArrow.width = 16.5;
        retryArrow.height = 7.36396;
        retryArrow.alt = '';
        retry.append(element('span', '', 'もう一度診断する'), retryArrow);
        retry.addEventListener('click', start);
        const reserve = button('c-button p-finder__reserve js-finder-reserve');
        reserve.disabled = !enabled;
        const reserveArrow = retryArrow.cloneNode();
        reserveArrow.src = 'assets/images/finder/arrow-light.svg';
        reserve.append(element('span', '', 'このタイプのギターを試奏する'), reserveArrow);
        reserve.addEventListener('click', () => {
            if (!recommendations.length) return;
            window.dispatchEvent(new CustomEvent('hody:finder-reservation', {
                detail: { products: recommendations.map(candidate => candidate.product), returnFocus: reserve }
            }));
        });
        actions.append(retry, reserve);
        return actions;
    }

    async function renderResult() {
        const currentVersion = ++version;
        root.classList.add('is-result');
        root.dataset.finderStep = 'result';
        const content = element('div', 'p-finder__result');
        const title = element('h3', 'p-finder__result-heading', '診断結果');
        const body = element('div', 'p-finder__result-body');
        body.append(element('p', 'p-finder__message', '結果を確認しています。'));
        screen.replaceChildren(header(), content);
        content.append(title, body);
        screen.setAttribute('aria-busy', 'true');
        announce(title, '診断結果を確認しています。');
        try {
            if (catalog.status === 'failed') throw new Error('Catalog unavailable');
            const products = await catalog.promise;
            if (version !== currentVersion) return;
            const result = recommendGuitars(products, answers);
            recommendations = result.recommendations;
            if (result.status !== 'ready') {
                body.replaceChildren(element('p', 'p-finder__message', '候補をご案内できませんでした。もう一度診断してみてください。'), resultActions(false));
                status.textContent = '診断結果：候補をご案内できませんでした。';
                return;
            }
            root.dataset.finderType = result.typeId;
            const type = RESULT_TYPES[result.typeId];
            const typeBlock = element('div', 'p-finder__type');
            typeBlock.append(element('p', 'p-finder__type-name', type.name), element('p', 'p-finder__type-caption', 'タイプがおすすめ！'));
            const cards = element('div', 'p-finder__cards');
            cards.append(...recommendations.map(candidate => productCard(candidate.product)));
            body.replaceChildren(typeBlock, element('p', 'p-finder__description', type.description), cards, resultActions(true));
            status.textContent = `診断結果：${type.name}タイプがおすすめです。`;
        } catch (error) {
            if (version !== currentVersion) return;
            recommendations = [];
            body.replaceChildren(element('p', 'p-finder__message', '商品情報を読み込めませんでした。時間をおいて、もう一度診断してください。'), resultActions(false));
            status.textContent = '商品情報を読み込めませんでした。';
        } finally {
            if (version === currentVersion) screen.setAttribute('aria-busy', 'false');
        }
    }

    root.querySelector('.js-finder-start').addEventListener('click', start);
}
