# HODY GUITAR｜TOPページ実装（画像差し込み版）

HODY GUITAR の TOP ページを HTML / SCSS / Vanilla JavaScript / FLOCSS で実装したデータです。2026-11-04、ユーザー提供の写真・アイコン **20点** をローカルの `assets/images/` に組み込みました。画像はZIPに含まれています（画像取得スクリプトの実行は不要です）。

## 表示方法

TOPは `index.html`、試奏ガイドは `guide.html`、商品一覧は `selection.html` です。商品一覧はJSONをHTTPで取得するため、以下のローカルサーバーで確認してください（`file://` 直開きは対象外）。

```bash
cd hody-guitar
python3 -m http.server 8000
```

ブラウザで `http://localhost:8000/` を表示します。

## SCSS の修正

コンパイル済み `css/style.css` を同梱しているため、サイトの表示には Node.js は不要です。SCSS を変更する場合は次のとおりです。

```bash
npm install
npm run watch
```

Node.js / npm を使わない場合は、このプロジェクトの単純なSCSS partialに対応する `python3 scripts/build-css.py` でもCSSを再生成できます。

## 主な実装範囲

- PC版・SP版TOPページ（ヒーロー、診断導線、商品、ABOUT、スタッフ、ガイド、店舗情報、Instagram、フッター）
- 提供された **4枚のFV写真** のクロスフェード切り替え（各6秒、表示中のグレーのプログレスバーが左から白に伸び切ると次の写真へ進みます。前のバーは切り替わった時点でグレーに戻り、常時表示する4本のうち現在の1本だけが左から白く伸びます。動きの軽減を指定した環境では自動切り替えを行いません）
- 商品画像4点、診断ギターシルエットと予約アイコン、スタッフ2点、ABOUT、ガイド、Instagram 4点、PC・SP別店舗外観2点
- PC版中央モーダル / SP版右からのスライド型予約ダイアログ、SPナビゲーション

画像と各UIの対応は `ASSET_MAPPING.md` を参照してください。

## 未完了・要確認

- **店舗情報の地図画像は未提供**です。`assets/images/store-map-pc.png` と `store-map-sp.png` は未配置のため、サイト内では画像が表示されません。正式素材のご提供後に挿入できます。
- 予約完了・内容確認画面、送信APIは未実装です。診断の質問・結果はTOP内に実装済みです。
- カンプに対する最終的な文字位置・細かな余白・画像トリミングの調整は引き続き必要です。
- Figmaに固定の切り替え周期が明記されていないため、FVの6秒間隔は仮の設定です。

実装の詳しい状態は `IMPLEMENTATION_NOTES.md` を参照してください。

## FVスライダーのプログレスバー（2026-11-04 追加）

`scss/object/project/_hero.scss` の `.p-hero__progress` に設定した `--hero-slide-duration: 6000ms;` が各写真の表示時間です。

- グレーのバーが左から白になるアニメーションはCSSの `@keyframes p-hero-progress` で描画します。
- `js/slider.js` がそのアニメーションの終了イベントを検知して写真を切り替えるため、写真とバーの周期がずれません。`setInterval` は使用していません。4本の線は4pxの間隔で区切っています。
- 4本とも常にグレーのベースラインを表示します。表示中のバーだけ `is-active` となって左から白く伸び、次の写真に移ると直前のバーはグレーに戻ります。完了状態を保持するクラスは使いません。
- 非表示タブではアニメーションを一時停止します。
- `prefers-reduced-motion: reduce` の環境では写真の自動切替とプログレスアニメーションを停止します。
- 変更したい場合は `--hero-slide-duration` を調整してください。HTMLの画像やほかのセクションは変更していません。

## 商品一覧ページ

`http://localhost:8000/selection.html` から確認できます。実装・検証結果と変更ファイル一覧は [docs/SELECTION_IMPLEMENTATION.md](docs/SELECTION_IMPLEMENTATION.md)、6状態の比較は [artifacts/selection/comparison.html](artifacts/selection/comparison.html) を参照してください。全12点の画像は配置済みですが、商品マスターの仮価格・紹介文・分類は公開前の承認が必要です。

```bash
python3 scripts/check_data.py
# Playwright / Pillowのある検証用Python環境で実行
python3 scripts/verify-selection.py --base-url http://localhost:8000
```

## おすすめギター診断

TOPの「おすすめギター診断を始める」から、同じセクション内で3問に回答できます。結果の予約ボタンだけが既存モーダルを開きます。[実装・判定条件・検証記録](docs/FINDER_IMPLEMENTATION.md)、[PC／SP比較画像](artifacts/finder/comparison.html) を参照してください。

```bash
# Playwright / Pillowのある検証用Python環境で実行
python3 scripts/verify-finder.py --base-url http://localhost:8000
```
