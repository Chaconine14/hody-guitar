// 質問・タイプの文言設定。商品名・画像・商品属性は共通マスターで管理する。
export const QUESTIONS = [
    {
        key: 'tone',
        title: 'どんな音が好き？',
        options: [
            { value: '明るい', label: 'キラキラした明るい音' },
            { value: '力強い', label: 'ズシッと響く力強い音' },
            { value: 'バランス', label: 'バランスの取れた音' },
            { value: 'any', label: 'まだわからない' }
        ]
    },
    {
        key: 'size',
        title: 'どんなサイズがちょうど良さそう？',
        options: [
            { value: '小さめ', label: '小さめで抱えやすいサイズ' },
            { value: '標準', label: '標準的なサイズ' },
            { value: '大きめ', label: '大きめで存在感のあるサイズ' },
            { value: 'any', label: '持ってから確かめたい' }
        ]
    },
    {
        key: 'style',
        title: 'どんなふうに弾きたい？',
        options: [
            { value: 'ストローク', label: 'コードをジャカジャカ弾きたい' },
            { value: '指弾き', label: '指でポロポロ弾きたい' },
            { value: 'any', label: 'どちらも好き・まだわからない' }
        ]
    }
];

export const RESULT_TYPES = {
    compact: {
        name: 'コンパクトで抱えやすい',
        description: '小ぶりなボディの候補です。抱えたときの収まりや弾き心地を、店頭で確かめてみませんか。'
    },
    large: {
        name: '響き豊かなラージボディ',
        description: '大きめのボディの候補です。音の広がりと抱え心地を、実際に弾き比べてみてください。'
    },
    finger: {
        name: '指弾きを楽しむ',
        description: '軽くつま弾きながら、好みの響きを探してみませんか。'
    },
    stroke: {
        name: 'ストロークを楽しむ',
        description: 'いつものコードを鳴らして、音の響きや弾き心地を確かめてみてください。'
    },
    allround: {
        name: 'バランス型オールラウンダー',
        description: 'コードも指弾きも楽しめる候補です。弾き方を変えながら、自分に合う響きを探してみませんか。'
    },
    bright: {
        name: '明るい音を楽しむ',
        description: '明るい響きが気になる方への候補です。実際に音を出して、好みの音色を確かめてみませんか。'
    },
    compare: {
        name: '弾き比べで見つける',
        description: '候補のギターを実際に弾いて、音や抱え心地を確かめてみませんか。'
    }
};
