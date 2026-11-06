(() => {
    'use strict';

    const hero = document.querySelector('.p-hero');
    if (!hero) return;

    const slides = Array.from(hero.querySelectorAll('.p-hero__slide'));
    const progress = hero.querySelector('.p-hero__progress');
    const indicators = Array.from(hero.querySelectorAll('.p-hero__progress-bar'));

    if (!progress || slides.length === 0 || slides.length !== indicators.length) return;

    let currentIndex = 0;

    function showSlide(index) {
        currentIndex = index;

        slides.forEach((slide, i) => {
            slide.classList.toggle('is-active', i === currentIndex);
        });

        indicators.forEach((indicator, i) => {
            indicator.classList.toggle('is-active', i === currentIndex);
        });

        progress.setAttribute('aria-label', `スライド ${currentIndex + 1} / ${slides.length}`);
    }

    // 4本ともグレーのまま表示し、現在のスライドのバーだけ白く伸ばす。
    // 前のバーは次の写真に切り替わるとグレーに戻る。
    // バーが100%になるタイミングを、画像切り替えのタイミングにする。
    // これならCSSのアニメーション時間を変えても表示時間がずれない。
    progress.addEventListener('animationend', (event) => {
        if (document.documentElement.classList.contains('is-loading')) return;
        if (event.animationName !== 'p-hero-progress' || event.pseudoElement !== '::after') return;
        if (event.target !== indicators[currentIndex]) return;

        showSlide((currentIndex + 1) % slides.length);
    });

    // 別タブで開いている間は時間を進めず、戻ったら続きから再開する。
    function updateVisibility() {
        progress.classList.toggle('is-paused', document.hidden);
    }

    // ローディング解除前に先頭へ戻し、解除後のバー開始と写真を揃える。
    document.addEventListener('hody:loading-end', () => {
        showSlide(0);
        updateVisibility();
    });

    document.addEventListener('visibilitychange', updateVisibility);
    updateVisibility();
    showSlide(0);

    // prefers-reduced-motion の場合はCSS側で動きを停止し、最初の写真を固定表示する。
})();
