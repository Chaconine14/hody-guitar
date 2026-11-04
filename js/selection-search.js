// 表示と検索条件の編集から独立した、商品マスターのAND検索。
export function filterProducts(products, filters = {}) {
    return products.filter(product => {
        if (filters.price_band) {
            const price = product.price_yen;
            if (!Number.isFinite(price)) return false;
            const bands = {
                lt150000: price < 150000,
                '150000_299999': price >= 150000 && price < 300000,
                '300000_499999': price >= 300000 && price < 500000,
                gte500000: price >= 500000
            };
            if (!bands[filters.price_band]) return false;
        }
        if (filters.body_size && product.body_size !== filters.body_size) return false;
        if (filters.playing_style === 'どちらも') {
            if (!['ストローク', '指弾き'].every(style => product.playing_styles.includes(style))) return false;
        } else if (filters.playing_style && !product.playing_styles.includes(filters.playing_style)) {
            return false;
        }
        if (filters.tone_impression && !product.tone_impressions.includes(filters.tone_impression)) return false;
        if (filters.amp_connection === 'yes' && product.amp_connection !== true) return false;
        if (filters.amp_connection === 'no' && product.amp_connection !== false) return false;
        return true;
    }).sort((first, second) => first.sort_order - second.sort_order);
}
