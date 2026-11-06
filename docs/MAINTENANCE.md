# HODY GUITAR 保守ガイド

このガイドは、現在のサイトを自分で編集するときの手順です。既存の `README.md` は変更せず、現在の実装に合わせた補足をまとめています。

今回のファイル整理では、表示用HTML・SCSS・JavaScript・CSS・商品データを変更せず、CSSの再コンパイルも行いません。

## 編集する場所

| 編集したい内容 | 編集元 |
| --- | --- |
| TOPの文章・画像・リンク | `index.html` |
| 試奏ガイドの文章・FAQ | `guide.html` |
| 商品一覧の画面構造 | `selection.html` |
| 商品名・価格・分類・商品画像の指定 | `data/products.csv` |
| 色・基本スタイル | `scss/foundation/` |
| ヘッダー・フッター | `scss/layout/` |
| ボタンなどの共通部品 | `scss/object/component/` |
| FV・商品紹介・スタッフなど各セクション | `scss/object/project/` |
| 表示切り替えなどの補助指定 | `scss/object/utility/` |
| メニュー・予約・スライダー | `js/menu.js`、`js/reservation.js`、`js/slider.js` |
| 商品検索 | `js/selection.js`、`js/selection-search.js` |
| ギター診断 | `js/finder.js`、`js/finder-config.js`、`js/finder-logic.js` |

作業前に `AGENTS.md` と `CODING_RULES.md` を確認してください。既存のHTML・Vanilla JavaScript・FLOCSSの構成を維持します。SCSSの入口は `scss/style.scss` で、各セクションのpartialを `@use` しています。

`css/style.css` はブラウザが読み込む生成物です。手編集せず、対応するSCSSを編集してください。SCSSのファイル名を変える場合は、入口の `@use` も確認します。

## ブラウザで確認する

VS Codeでプロジェクトのフォルダーを開き、ターミナルをプロジェクト直下で起動します。

```bash
python3 -m http.server 8000
```

サーバーを起動したまま、次のURLを開いてください。

- TOP：`http://localhost:8000/`
- 試奏ガイド：`http://localhost:8000/guide.html`
- 商品一覧：`http://localhost:8000/selection.html`

商品一覧と診断はJSONを取得するため、HTMLを直接ダブルクリックする `file://` 表示では確認しません。サーバーはターミナルで `Ctrl+C` を押すと終了します。

## SCSSを編集・コンパイルする

### 現在のVS Codeの方法を使う

確認時点のDartSass拡張のユーザー設定は、次の値です。

```json
"dartsass.targetDirectory": "css"
```

`css` はプロジェクト直下を基準とする出力先です。現在の拡張は通常版・圧縮版・Source Mapを生成し、互換用のプレフィックスも付けます。

1. `scss/style.scss` を開きます。
2. 必要に応じてコマンドパレットから `DartSass: Sass Watch` を開始します。
3. 対象セクションのSCSSを編集して保存します。
4. `css/style.css` が更新され、コンパイルエラーが出ていないことを確認します。
5. ブラウザを再読み込みし、PCとSPの両方を確認します。古い表示が残る場合は強制再読み込みを試します。

自動更新されない場合は、拡張の監視状態、出力先、エラー表示を確認してください。`scss/style.css` に出力されても、サイトが読み込むCSSには反映されません。

Live Sass Compilerなど別の拡張と、DartSassの監視を同時に動かさないでください。異なる場所への二重出力や、設定の異なるCSSでの上書きを避けるためです。今回削除した `scss/style.css` とそのMapは、旧出力です。

### npmを使う場合

Node.jsとnpmが使える環境が必要です。初回にプロジェクト直下で依存を導入します。

```bash
npm install
```

SCSSを監視して通常版CSSへ反映するコマンドは次です。

```bash
npm run watch
```

一度だけ通常版CSSを生成するコマンドもあります。

```bash
npm run build
```

ただし現在のnpm設定は、通常版の `css/style.css` を生成するだけです。`build` は `--no-source-map` 指定で、圧縮版CSSや既存Mapをまとめて更新しません。DartSass拡張のプレフィックス付与も含みません。現在の出力形式を保ちたい場合は、既存のVS Codeの方法を継続し、npm方式へ無断で切り替えないでください。npm監視と拡張の監視も同時に動かしません。

`scripts/build-css.py` は旧方式です。Sassをコンパイルせずpartialを連結するため、現在のSCSSの `//` コメントなどを正しく扱えません。既存資料の参照を保つためファイルは残していますが、現在のCSS生成には使わないでください。

## 商品データを更新する

`data/products.csv` は手編集用、`data/products.json` は商品検索・診断が読み込むデータです。両方を残してください。

変換スクリプトは既存JSONを読み、`products` の配列だけをCSVから置き換えます。検索選択肢の `filter_options` やメタデータは既存JSONにしかないため、JSONを削除してからCSVだけで作り直すことはできません。

1. 作業前にGitの状態を確認し、CSVとJSONを両方保存・バックアップします。
2. CSVをUTF-8形式で編集します。列名は変えず、商品の `id` を重複させないでください。
3. 商品画像のパスは `assets/images/...` のようにプロジェクト直下から指定し、画像ファイルの存在も確認します。
4. プロジェクト直下で次を実行します。

```bash
python3 scripts/csv_to_json.py
python3 scripts/check_data.py
```

5. CSVとJSONの差分を確認し、商品一覧の検索結果と診断結果をブラウザで確認します。

`playing_styles` と `tone_impressions` に複数の値を入れる場合は `|` 区切りです。既存の値を見本にしてください。

商品数・価格・分類を変更すると、`data/test_scenarios.json` の期待結果も変わることがあります。現在の `check_data.py` は商品12件と検索8シナリオを検証します。商品を増減したり分類を変えたりする際は、検証の件数・期待結果と、診断の期待順位も別途確認してください。エラーを消すためだけに期待値を書き換えず、実際に意図した商品が出ていることを確認します。

## 試奏予約の日付・時間を変更する

予約フォームは `index.html`・`guide.html`・`selection.html` にあります。画面構造を変える場合は3ページを揃えてください。日時の選択条件と入力チェックは `js/reservation.js`、見た目は `scss/object/project/_reservation.scss` で共通管理しています。

- 日付：`id="reserve-date" name="date"`。入力値は `YYYY-MM-DD` です。
- 時間：`id="reserve-time" name="time"`。入力値は `HH:mm` です。
- 日付・時間はどちらも必須です。画面上では別の入力欄で、隠し入力に結合した日時は保持しません。

カレンダーにはflatpickr **4.6.13**を使用しています。本体・日本語ロケール・CSS・ライセンスは `assets/vendor/flatpickr/` に保存しており、CDNへの接続は不要です。更新する場合は本体と日本語データの版を揃え、ライセンスを残し、PC・SPの両方で確認してください。ライブラリの読み込み・初期化に失敗した場合はブラウザ標準の日付入力へ戻り、予約条件の検証は引き続き行います。

店舗情報は **12:00〜19:00・水曜定休**です。現在の時間候補は **12:00〜18:30の14枠、30分刻み**です。**最終受付18:30は仮設定**のため、店舗で確定した運用に合わせて `js/reservation.js` の時間候補設定を変更してください。30分刻みは開始時刻の間隔であり、試奏時間が30分と確定したものではありません。

日付・時刻は端末のタイムゾーンではなく、日本時間（`Asia/Tokyo`）を基準に判定します。過去の日付・水曜日・実在しない日付は選択できません。当日は現在時刻より後の時間枠だけ選べます。たとえば12:00ちょうどには12:00枠を選べず、18:30以降は当日の枠が残りません。その場合は画面に理由を表示し、別の日付を選びます。

モーダルを開いた時・日付を変更した時・送信前に条件を再確認します。日付変更などで選択済みの時間が無効になった場合は、時間を未選択へ戻します。手入力も同じ検証の対象です。開閉ではその他の入力値と商品引き継ぎを保持します。

変更後は、3ページで日本語表示、空欄、過去日、水曜日、存在しない日付、当日の時刻境界、日付変更後の時間候補を確認します。Tab・Shift+Tabで入力を移動でき、Escapeは開いているカレンダー、次にモーダルを閉じることも確認してください。送信API・確認画面・予約完了画面は未実装のため、入力チェックを通過しても店舗へ送信・保存はされません。

## 編集後に確認すること

画面幅375・390・768・1024・1440pxで、横スクロール、画像の縮小・見切れ、文章やボタンのはみ出しを確認します。

- FVの高さ・画像・スライダー・進捗線。
- CTAのFV境界での出入り、SPのフッターでの非表示、上へ戻った際の再表示。
- 商品一覧の初期表示・条件変更・0件表示・条件クリア。
- 診断の3問・戻る・結果・再診断。
- 通常の予約と診断結果からの予約、閉じるボタンとEscキー。
- SPメニュー、ガイドFAQ、Instagramの別タブリンク、Googleマップ。

Google FontsとGoogleマップの確認にはインターネット接続が必要です。画像の撮影では、遅延読み込みの地図を一度画面内に入れ、地図タイルが表示されてから撮影します。

### 自動検証を使う場合

`check_data.py` とCSV変換は標準Pythonだけで動きます。ブラウザ検証スクリプトには、PythonのPlaywright・Pillow、Google Chrome、HTTPサーバーが必要です。

検証環境を新しく用意する場合の例です。既存の検証用環境がある場合は、それを使用できます。

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install playwright Pillow
```

別のターミナルで前述のHTTPサーバーを起動してから、次を実行します。

```bash
python3 scripts/check_data.py
python3 scripts/verify-guide.py --base-url http://localhost:8000/ --output artifacts/_local/guide
python3 scripts/verify-selection.py --base-url http://localhost:8000/ --output artifacts/_local/selection
python3 scripts/verify-finder.py --base-url http://localhost:8000/ --output artifacts/_local/finder
```

各スクリプトはmacOSの標準的なGoogle Chromeの場所を既定にしています。Chromeの場所が違う場合は `--browser` で実行ファイルを指定してください。

`artifacts/_local/` はGit管理しない一時出力先です。`--output` を省略すると既存の比較画像・検証JSONを上書きしたり、整理済みの旧出力を再生成したりするため、通常の再検証では必ず指定します。

変更前後の画像比較を行う `--baseline-dir` は、変更前のファイル一式が別途必要です。各スクリプトの冒頭にある形式に合わせて用意します。保存済みの検証画像だけがあれば、すべての回帰比較を再実行できるわけではありません。

ガイド・商品一覧の検証は、日本時間の翌日以降（水曜を除く）と14:00を使用します。旧日時UIと比較する場合、日時欄の追加によるモーダルの高さ差は意図した変更として記録し、その他の入力欄・装飾・間隔・フォントと、モーダルを閉じたページ全体を比較します。新UI同士の比較ではモーダル全体も比較します。

## Gitと復元

整理前の完成状態の復元ポイントは、次のコミットです。

```text
6e74fe20be34572bdc0cda06c10e969118a8e49d
レイアウト修正依頼後
```

作業前後には、プロジェクト直下で差分を確認します。

```bash
git status --short
git diff --stat
```

整理で削除したファイルを1件だけ戻す場合の例です。

```bash
git restore --source=6e74fe20be34572bdc0cda06c10e969118a8e49d -- assets/icons/icon-guitar.svg
```

指定したファイルに新しい編集があると上書きされるため、実行前に対象と差分を確認してください。プロジェクト全体を一括で戻す操作は、後から行った編集まで失うため、このガイドでは案内しません。

## 既存資料との違い・未実装の範囲

- 旧READMEや実装記録には「地図画像が未提供」とありますが、現在のTOPは指定のGoogleマップiframeを使用しています。
- スライダーの旧説明は6秒ですが、現在は `_hero.scss` の `--hero-slide-duration: 5000ms` が表示時間です。時間を変える場合はこの値を確認します。
- 予約モーダルの表示・入力確認はありますが、予約内容の確認画面・送信API・予約完了画面は未実装です。予約画面が開くことと、店舗へ予約を送信できることは別です。
- `.DS_Store`、開発用の依存、Pythonキャッシュ、一時出力はGit管理しません。配信用CSS・Map、商品CSV・JSON、使用素材、フォントのライセンスは保持します。

上記の旧説明や未実装部分は、今回のファイル整理でコードを修正する対象には含めていません。
