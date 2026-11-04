import { QUESTIONS } from './finder-config.js';

const includes = (values, value) => Array.isArray(values) && values.includes(value);
const supportsBoth = product => ['ストローク', '指弾き'].every(style => includes(product.playing_styles, style));

export function scoreProduct(product, answers) {
    let score = 0;
    if (includes(product.tone_impressions, answers.tone)) score += 3;
    if (product.body_size === answers.size) score += 4;
    if (answers.style === 'any') {
        if (supportsBoth(product)) score += 3;
        else if (['ストローク', '指弾き'].some(style => includes(product.playing_styles, style))) score += 1;
    } else if (includes(product.playing_styles, answers.style)) {
        score += 2;
    }
    return score;
}

export function getResultType(products, answers) {
    if (!products.length) return null;
    const all = condition => products.every(condition);
    if (all(product => product.body_size === '小さめ')) return 'compact';
    if (all(product => product.body_size === '大きめ')) return 'large';
    if (answers.style === '指弾き' && all(product => includes(product.playing_styles, '指弾き'))) return 'finger';
    if (answers.style === 'ストローク' && all(product => includes(product.playing_styles, 'ストローク'))) return 'stroke';
    if (all(product => includes(product.tone_impressions, 'バランス') && supportsBoth(product))) return 'allround';
    if (all(product => includes(product.tone_impressions, '明るい'))) return 'bright';
    // 形状が混在しても、body_shape_referenceと矛盾する固有の形状名を付けない。
    return 'compare';
}

export function recommendGuitars(products, answers) {
    const complete = QUESTIONS.every(question => question.options.some(option => option.value === answers[question.key]));
    if (!complete) return { status: 'incomplete', typeId: null, recommendations: [] };
    const undecided = QUESTIONS.every(question => answers[question.key] === 'any');
    const seen = new Set();
    const candidates = products.filter(product => {
        if (!product || typeof product.id !== 'string' || !product.id || seen.has(product.id)) return false;
        if (!product.brand || !product.model || !Number.isFinite(product.sort_order)) return false;
        seen.add(product.id);
        return true;
    }).map(product => ({
        product,
        score: scoreProduct(product, answers),
        preferred: undecided && product.body_size === '標準' && includes(product.tone_impressions, 'バランス') && supportsBoth(product)
    })).filter(candidate => candidate.score > 0).sort((first, second) =>
        Number(second.preferred) - Number(first.preferred) || second.score - first.score ||
        first.product.sort_order - second.product.sort_order || first.product.id.localeCompare(second.product.id)
    );
    const recommendations = candidates.slice(0, 2).map(({ product, score }) => ({ product, score }));
    return {
        status: recommendations.length ? 'ready' : 'no-candidates',
        typeId: getResultType(recommendations.map(candidate => candidate.product), answers),
        recommendations
    };
}
