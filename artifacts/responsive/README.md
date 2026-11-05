# TOPレスポンシブ修正・検証記録

添付SP_TOP.jpg（375px相当）とPC_TOP.jpg（1440px相当）を基準に修正。FVは依頼どおり全幅100vhを維持しています。

## 編集ファイルと理由

| ファイル | 変更内容・理由 |
| --- | --- |
| `index.html` | TOP専用クラス、CTA操作用フック、Instagram全サムネイル・両ボタンの外部リンク、指定Googleマップiframeを追加。 |
| `js/reservation.js` | FV下端50%でCTA表示。SPはフッター進入時に非表示。初期表示・スクロール・リサイズ・履歴復元・本文実寸変更を再判定。 |
| `scss/object/project/_selection.scss` | SPの固定高・絶対配置を通常フローへ変更。375pxで写真162×202px・列間25px。1024pxまで見出しを折り返して写真幅を確保。 |
| `scss/object/project/_staff.scss` | SP・タブレットの写真を元画像686:858の比率で表示。内容に応じたカード高とカンプの余白を確保。SPのリード・氏名の太さ、本文上余白・字間も調整し、375pxで本文がカンプと同じ各5行になることを確認。 |
| `scss/object/project/_hero.scss` | 100vhを維持し、SPはFV下端を基準に内容を配置。タブレットは短い画面でも内容が収まる上余白に調整。既存の進捗線の左基準設定は保持。 |
| `scss/object/project/_finder.scss` | 固定CTAの400ms・ease-outのスライド表示、非表示時の操作抑止、prefers-reduced-motionを追加。SPは画面下部固定。 |
| `scss/object/project/_about.scss` | SPの段落間を26px、見出しから本文までを40pxに調整。 |
| `scss/object/project/_guide.scss` | SPの案内ボタンを中央配置。 |
| `scss/object/project/_store.scss` | iframeを既存マップ領域に合わせる。SPの上下余白、地図・住所間、各項目の行高をカンプに合わせ、固定高の不足を解消。 |
| `scss/object/project/_instagram.scss` | 画像リンクの寸法と既存の外観を維持。SPのフッター写真までの60pxの余白を反映。 |
| `scss/layout/_footer.scss` | TOPのSPに限定してロゴ・ナビ・住所・コピーライトの配置を修正。 |
| `css/style.css`、`css/style.min.css`、各`.map` | SCSSの変更を生成成果物へ反映。既存の互換用プレフィックスを保持。 |

## ブラウザ検証

Chrome / Playwrightで375・390・768・1024・1440pxを確認。Google Fonts読み込み後に撮影しました。

- 全幅で横スクロールなし。商品写真・スタッフ写真の寸法と比率、セクション内への収まりを確認。
- CTAのFV境界、SPのフッター境界、上方向への復帰、途中再読み込み、リサイズを確認。
- CTA切り替えによるセクション座標・高さの変化なし。
- 予約モーダル開閉、診断3問→結果→予約、FVスライダー自動切り替え、動きを減らす設定を確認。
- Instagram全8リンクのURL・別タブ・rel属性と、画像全体のクリック領域を確認。
- Googleマップ埋め込みのHTTP 200、UIと地図タイルの描画を確認。
- ガイド・商品一覧ページの予約モーダルも確認。
- PC1440pxは修正前後のセクション・商品カード・スタッフ画像・フッターの位置、寸法、字体指定が一致。地図領域を除いた画像の平均差は0.0065未満（0〜255）。

## 比較画像と差異

- `top-375.png` / `top-390.png` / `top-768.png` / `top-1024.png` / `top-1440.png`：修正後の全体画像。
- `comparison-sp.png`：添付SPカンプと375px実装の並列比較。
- `pc-before-1440.png` / `pc-after-1440.png`：PCの修正前後比較。
- `map-375.png`：実際のGoogleマップ描画。
- `verification.json`：寸法と動作検証の結果。

比較画像ではカンプに合わせて375px幅の画面高さ650px、1440px幅の画面高さ790pxを使用。実際のFV高は100vhなので画面高さに応じて変わります。Googleマップは埋め込みの操作UIと現在の地図表示を含むため、カンプ内の静止画像とは表示内容が異なります。JPEG原稿とブラウザの文字描画・端数処理による数pxの差、およびスタッフ本文の一部の改行位置に差が残ります。文字サイズ・画像比率を保ち、カンプの幅と余白へ合わせています。
