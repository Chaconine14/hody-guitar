import { filterProducts } from './selection-search.js';

const root = document.querySelector('.js-selection-page');

if (root) {
    const form = root.querySelector('.js-selection-form');
    const panel = root.querySelector('.js-selection-filters');
    const toggle = root.querySelector('.js-filter-toggle');
    const reset = root.querySelector('.js-filter-reset');
    const cards = root.querySelector('.js-product-cards');
    const count = root.querySelector('.js-results-count');
    const title = root.querySelector('.js-results-title');
    const empty = root.querySelector('.js-empty-results');
    const smallScreen = window.matchMedia('(max-width: 768px)');
    const fields = [...form.querySelectorAll('select')];
    const labels = Object.fromEntries(fields.map(field => [field.name, form.querySelector(`label[for="${field.id}"]`).textContent]));
    let products = [];
    let options = {};
    let applied = {};
    let hasSearched = false;
    let panelOpen = true;

    function element(tag, className, text) {
        const node = document.createElement(tag);
        node.className = className;
        if (text !== undefined) node.textContent = text;
        return node;
    }

    function productCard(product) {
        const card = element('article', 'p-selection-page__card');
        card.dataset.productId = product.id;
        const image = element('img', 'p-selection-page__photo');
        image.src = product.image_src;
        image.alt = product.display_name;
        image.width = 648;
        image.height = 810;
        const content = element('div', 'p-selection-page__card-content');
        content.append(
            element('p', 'p-selection-page__tagline', product.tagline),
            element('p', 'p-selection-page__brand', product.brand),
            element('h3', 'p-selection-page__model', product.model),
            element('p', 'p-selection-page__description', product.description),
            element('p', 'p-selection-page__price', `価格：${product.price_yen.toLocaleString('ja-JP')}円(税込)`)
        );
        const button = element('button', 'p-selection-page__reserve js-open-reservation');
        button.type = 'button';
        button.dataset.product = product.display_name;
        button.setAttribute('aria-label', `${product.display_name}：このギターを試奏する`);
        const arrow = element('img', 'p-selection-page__card-arrow');
        arrow.src = 'assets/images/selection/card-arrow.svg';
        arrow.width = 32;
        arrow.height = 32;
        arrow.alt = '';
        button.append(element('span', '', 'このギターを試奏する'), arrow);
        content.append(button);
        card.append(image, content);
        return card;
    }

    function syncPanel() {
        panel.classList.toggle('is-filter-open', panelOpen);
        const expanded = !smallScreen.matches || panelOpen;
        toggle.setAttribute('aria-expanded', String(expanded));
        form.hidden = !expanded;
    }

    function render() {
        const matches = filterProducts(products, applied);
        document.body.classList.toggle('is-searched', hasSearched);
        root.querySelector('.js-selection-breadcrumb').hidden = !hasSearched;
        title.textContent = hasSearched ? '検索結果' : 'PRODUCTS';
        count.textContent = hasSearched ? `${matches.length}件` : `${matches.length} ITEMS`;
        cards.replaceChildren(...matches.map(productCard));
        empty.hidden = matches.length !== 0;
        const conditions = Object.entries(applied).filter(([, value]) => value);
        root.querySelectorAll('.js-applied-conditions').forEach(summary => {
            summary.hidden = conditions.length === 0;
            summary.querySelector('.js-applied-list').replaceChildren(...conditions.map(([key, value]) => {
                const label = options[key].find(option => option.value === value).label;
                return element('li', '', `${labels[key]}：${label}`);
            }));
        });
        syncPanel();
    }

    form.addEventListener('submit', event => {
        event.preventDefault();
        applied = Object.fromEntries(fields.map(field => [field.name, field.value]));
        hasSearched = true;
        panelOpen = false;
        render();
        if (smallScreen.matches) toggle.focus();
    });

    reset.addEventListener('click', () => {
        form.reset();
        applied = {};
        hasSearched = false;
        panelOpen = true;
        render();
    });

    toggle.addEventListener('click', () => {
        panelOpen = !panelOpen;
        syncPanel();
    });
    smallScreen.addEventListener('change', syncPanel);
    syncPanel();

    async function loadCatalog() {
        try {
            const response = await fetch('data/products.json');
            if (!response.ok) throw new Error(`Catalog HTTP ${response.status}`);
            const data = await response.json();
            if (!Array.isArray(data.products) || !data.filter_options || fields.some(field => !Array.isArray(data.filter_options[field.name]))) {
                throw new Error('Invalid catalog');
            }
            products = data.products;
            options = data.filter_options;
            fields.forEach(field => {
                field.replaceChildren(...options[field.name].map(option => new Option(option.label, option.value)));
            });
            const reservation = document.getElementById('reserve-product');
            const undecided = reservation.options[0].cloneNode(true);
            reservation.replaceChildren(undecided, ...filterProducts(products).map(product => new Option(product.display_name, product.display_name)));
            render();
            form.querySelectorAll('[disabled]').forEach(control => { control.disabled = false; });
        } catch (error) {
            cards.replaceChildren();
            empty.hidden = true;
            root.querySelector('.js-catalog-error').hidden = false;
            console.error('HODY GUITAR: 商品データの取得に失敗しました。', error);
        } finally {
            root.setAttribute('aria-busy', 'false');
        }
    }

    loadCatalog();
}
