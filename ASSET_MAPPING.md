# 画像配置一覧（2026-11-04）

ユーザーが提供したファイルの元のファイル名を保持して `assets/images/` に格納しています。20点すべてを HTML から参照しています。

| 添付画像 | 使用位置 | 表示仕様 |
| --- | --- | --- |
| `top_slider01.jpg` | FVスライド1 | PC/SP共通・`object-fit: cover` |
| `top_slider02.jpg` | FVスライド2 | PC/SP共通 |
| `top_slider03.jpg` | FVスライド3 | PC/SP共通 |
| `top_slider04.jpg` | FVスライド4 | PC/SP共通 |
| `guitar-outline.png` | おすすめギター診断 | PC/SPの寸法だけ切り替え |
| `guitar-icon.png` | 固定試奏予約CTA | ボタン内に表示 |
| `guitar01.jpg` | 商品 Gibson J-45 | PC/SP共通 |
| `guitar02.jpg` | 商品 Martin D-28 | PC/SP共通 |
| `guitar03.jpg` | SP商品カード3 Taylor 114ce | SPのみ |
| `guitar04.jpg` | SP商品カード4 Taylor 114ce | SPのみ、Figma表記を維持 |
| `about.jpg` | ABOUT | PC/SP共通 |
| `staff011.jpg` | 飯塚 健（STORE MANAGER） | PC/SP共通 |
| `staff02.jpg` | 佐藤 芽衣（GUITAR ADVISER） | PC/SP共通 |
| `guide.jpg` | TEST-PLAYING GUIDE | PCは右側画像、SPは背景画像 |
| `instagram01.jpg` | Instagram 1枚目 | PCの繰り返しカードにも使用 |
| `instagram02.jpg` | Instagram 2枚目 | PCの繰り返しカードにも使用 |
| `instagram04.jpg` | Instagram 3枚目 | カンプの画像順に合わせて配置 |
| `instagram03.jpg` | Instagram 4枚目 | カンプの画像順に合わせて配置 |
| `footer_shop-pc.jpg` | フッター店舗外観 PC | PC・タブレット |
| `footer_shop-sp.jpg` | フッター店舗外観 SP | 768px以下 |

**今回提供されていない素材：** 店舗情報の地図（PC/SPの画像）。そのため `index.html` の地図部分のみ、既存の画像参照を残しています。

**FVの挙動：** 画像は 01→02→03→04→01 の順に切り替わります。現在の切り替え間隔（6秒）は実装上の仮値です。

## 試奏ガイド専用ページ

`guide.html` は指定Figma `2114:5050` / `2114:5709` に対応します。TOP用の画像は置換していません。

| ローカル素材 | Figma内の対応・表示 |
| --- | --- |
| `guide_step01.svg`〜`guide_step05.svg` | 指・記入・人物・音符・会話の順。提供済み素材を各50×50pxで使用 |
| `guide/intro.png` | PC導入 `2114:5060` / SP導入 `2114:5716`。同じ4032×3024px写真、中央cover＋95%チャコール重ね色 |
| `guide/shop-pc.png` | `2114:5194`。1672×941px原本、PC高さ506px・object-position 30.29% |
| `guide/shop-sp.png` | `2114:5872`。1122×1402px原本、SPカンプの幅390px・高さ487pxを375px枠の左端で切り出す |
| `guide/logo-charcoal.svg` / `logo-white.svg` | Figmaの濃色ヘッダー・明色フッターロゴ。フッターは原本を背景で257×132px／117×60px表示 |
| `guide/connector-01.svg`〜`connector-03.svg` | PCの点線原本。2→3と4→5はFigma上でも同一ベクター |
| `guide/step-arrow.svg` / `step-arrow-narrow.svg` | SPステップ間の下向き矢印原本。04の直前のみ幅47px |
| `guide/guitar-blue.svg` / `guitar-ivory.svg` | 下部予約ボタン／SP固定バーの32×32pxギター |
| `guide/arrow-header.svg` / `arrow-blue.svg` / `arrow-ivory.svg` | ヘッダー／下部予約／固定バーの矢印原本 |
| `guide/menu.svg` / `footer-line.svg` | SPヘッダーの二本線／フッター罫線の原本 |

提供済みステップ素材はFigmaと照合済み。01・02・03・05は描画属性が一致、04は書き出し座標の小数丸め差のみです。既存写真は同じ被写体でも画角・比率が異なるため、ガイドではFigmaから取得した上記原本を使用しています。仮のFigma画像URLは実装に残していません。
