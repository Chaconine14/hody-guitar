# 画像配置一覧（2026-11-04）

ユーザーが提供したファイルの元のファイル名を保持して `assets/images/` に格納しています。20点すべてを HTML から参照しています。

| 添付画像 | 使用位置 | 表示仕様 |
| --- | --- | --- |
| `top_slider01.jpg` | FVスライド1 | PC/SP共通・`object-fit: cover` |
| `top_slider02.jpg` | FVスライド2 | PC/SP共通 |
| `top_slider03.jpg` | FVスライド3 | PC/SP共通 |
| `top_slider04.jpg` | FVスライド4 | PC/SP共通 |
| `finder/intro.png` | おすすめギター診断 | 旧 `guitar-outline.png` を置換。PC/SPの寸法だけ切り替え |
| `finder/guitar-pc.svg` / `guide/guitar-ivory.svg` | 固定試奏予約CTA | 旧 `guitar-icon.png` を置換。PC/SP別のアイコンを表示 |
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

## 商品一覧（2026-11-04）

更新済み `data/products.json` の指定画像をPC／SP共通で使用。全12点を確認し、画像自体の編集・差し替えはしていません。

| 商品ID | 機種 | 画像パス |
| --- | --- | --- |
| `gibson-j-45` | Gibson J-45 | `assets/images/guitar01.jpg` |
| `martin-d-28` | Martin D-28 | `assets/images/guitar02.jpg` |
| `taylor-114ce` | Taylor 114ce | `assets/images/guitar03.jpg` |
| `gibson-b-25` | Gibson B-25 | `assets/images/products/gibson-b-25.jpg` |
| `martin-000-18` | Martin 000-18 | `assets/images/products/martin-000-18.jpg` |
| `martin-000-28` | Martin 000-28 | `assets/images/products/martin-000-28.jpg` |
| `taylor-214ce` | Taylor 214ce | `assets/images/products/taylor-214ce.jpg` |
| `taylor-gs-mini` | Taylor GS Mini | `assets/images/products/taylor-gs-mini.jpg` |
| `k-yairi-rf-65` | K.Yairi RF-65 | `assets/images/products/k-yairi-rf-65.jpg` |
| `yamaha-ll16-are` | YAMAHA LL16 ARE | `assets/images/products/yamaha-ll16-are.jpg` |
| `yamaha-ls16-are` | YAMAHA LS16 ARE | `assets/images/products/yamaha-ls16-are.jpg` |
| `cole-clark-fl2ec` | Cole Clark FL2EC | `assets/images/products/cole-clark-fl2ec.jpg` |

画像枠は `1122 / 1402`、`object-fit: contain` で中央配置し、縦長素材もギター全体を保持します。

| 用途 | 参照先 |
| --- | --- |
| カード予約の丸矢印（32×32） | `assets/images/selection/card-arrow.svg` |
| PC／SPセレクト矢印 | `assets/images/selection/select-pc.svg` / `select-sp.svg` |
| SP検索パネルの開閉三角 | `assets/images/selection/filter-toggle.svg` |
| SP適用条件の区切り線 | `assets/images/selection/condition-line.svg` |
| 0件シルエット | `assets/images/selection/empty-guitar.png` |
| 共通ロゴ・アイコン・矢印・店舗写真・罫線 | `assets/images/guide/` 内の対応素材 |

上記の新規6点はFigma正式素材です。店舗写真・共通ロゴ・予約アイコン・矢印はFigma書き出しと既存ファイルが一致。SPロゴはレイヤーIDだけが異なり、形状・色・寸法が一致します。メニューとフッター罫線も照合済みです。0件シルエットは既存診断用の画像とは異なるため流用していません。

和文フォントは `assets/fonts/selection-noto-jp-{400,500,700}.ttf`。Google FontsのNoto Sans JPから使用文字を取得し、既存の `OFL-NotoSansJP.txt` のライセンスで配信。別名 `HODY Selection JP` とし、商品一覧の本体だけに適用しています。

検証画像は `artifacts/selection/product-images.png`、素材照合は `artifacts/selection/asset-comparison.json`、詳細は `docs/SELECTION_IMPLEMENTATION.md` を参照してください。

## GUITAR FINDER（2026-11-04）

診断の推薦画像は共通JSONの `image_src` を使用し、商品一覧と同じ商品IDに同じ画像を表示します。4:5枠にcontainで中央配置し、別機種の写真で代替しません。

| 用途 | 参照先 | 原寸 |
| --- | --- | --- |
| 導入シルエット | `assets/images/finder/intro.png` | 1024×1536 PNG、PC／SP共通 |
| PC導入予約アイコン | `assets/images/finder/guitar-pc.svg` | 52×52 |
| 結果の予約矢印 | `assets/images/finder/arrow-light.svg` | 16.5×7.36396 |
| SP結果の罫線 | `assets/images/finder/result-line.svg` | 298×1 |
| SP導入予約アイコン | `assets/images/guide/guitar-ivory.svg` | 32×32、Figma原本と一致 |
| 導入予約バナーの矢印 | `assets/images/guide/arrow-ivory.svg` | 10.5×7.36396、Figma原本と一致 |
| 再診断の矢印 | `assets/images/guide/arrow-header.svg` | 16.5×7.36396、Figma原本と一致 |

新規4点はFigmaの正式素材をそのまま保存しました。既存の低解像度シルエットPNGを加工せず、診断セクションの参照だけ原本に変更しています。選択肢の三角はカンプで文字として指定された `▶︎` を使用します。

和文は `assets/fonts/finder-noto-jp-{400,500,700}.ttf` を別名 `HODY Finder JP` で登録し、診断内に限定。既存の `OFL-NotoSansJP.txt` を適用します。素材の一致は `artifacts/finder/assets.json`、描画フォントは `artifacts/finder/fonts-and-extra-checks.json`、画面比較は `artifacts/finder/comparison.html` に記録しています。
