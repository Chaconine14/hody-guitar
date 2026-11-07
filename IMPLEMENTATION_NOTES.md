# HODY GUITAR｜TOPページの実装メモ

## 参照した正式なFigmaフレーム

- PC TOP: `2114:4177`（1440px幅）
- PC 試奏予約ダイアログ: `2114:4500`
- SP TOP: `2114:5342`（375px幅）
- SP 試奏予約ダイアログ: `2114:5890`
- SP ハンバーガーメニュー: `2117:6608`

## 実装済み

- PC / SP共通のTOPページ：FV、GUITAR FINDER、SELECTION、ABOUT、STAFF、TEST-PLAYING GUIDE、STORE INFORMATION、Instagram、店舗写真・フッター
- PC のデスクトップナビゲーション、SP のスライド式ハンバーガーメニュー
- 試奏予約のPC中央モーダル、SP右から左へのスライドイン
- モーダルのEscキー、背面クリックでの閉じる操作、フォーカス循環・スクロール固定
- 商品カード選択時の試奏予約フォームへの商品名反映
- 氏名・メール・希望日時のHTML入力検証（予約の確定送信は行わない）

## Figmaから確認したデザイン指標

| 項目 | PC | SP |
|---|---:|---:|
| カンプの横幅 | 1440px | 375px |
| FVの高さ | 790px | 650px |
| 診断セクションの高さ | 676px | 619px |
| 商品紹介セクションの高さ | 951px | 773px |
| スタッフのカード | 横2件 | 縦2件 |
| ガイドセクションの高さ | 475px | 336px |
| 店舗情報セクションの高さ | 720px | 761px |
| 文字色 | #4a4a4a | #4a4a4a |
| 濃いアイボリー | #f4ecdd | #f4ecdd |
| 明るいアイボリー | #fbf7ef | #fbf7ef |
| 予約CTAの青 | #024578 | #024578 |

## 画像の差し込み状況（2026-11-04 更新）

ユーザー提供の JPG/PNG **20ファイルすべて**を `assets/images/` に保存し、PC/SP共通の `index.html` に紐づけました。写真・人物・商品・アイコン・PC/SP別の店舗外観を実画像で表示できます。正確な紐づけは `ASSET_MAPPING.md` に記載しています。

- 旧版のFigma仮画像URL取得スクリプトは削除しました。画像はすべてZIP内に収録されています。
- FVは4枚の写真を使用する自動切り替えを追加しました（暫定6秒間隔）。
- **店舗情報の地図は今回の20点に含まれていません。** `store-map-pc.png` / `store-map-sp.png` の参照だけが残っています。
- 1440px / 375pxで画像配置後の画面をレンダリングし、いずれも横はみ出しがないこと、提供素材が描画されることを確認しています。ただしFigmaとのピクセル単位の最終検証は継続事項です。

## 仕様未確定のため、実装を保留している機能

1. 「おすすめギター診断」：TOP内で完結する3問のインライン診断を実装済み。48通りの判定、PC／SPの画面操作、既存予約への引き継ぎを検証。詳細は `docs/FINDER_IMPLEMENTATION.md` を参照。
2. FVのスライダー：提供画像4点を使用してクロスフェード自動再生に更新（暫定6秒）。スライド間隔の正式仕様は要確認。
3. 商品一覧は `selection.html` に実装済み。詳細は `docs/SELECTION_IMPLEMENTATION.md` を参照。試奏ガイドは `guide.html` に実装し、TOPのヘッダー・紹介枠・フッター・SPメニューから接続済み。詳細は `GUIDE_IMPLEMENTATION.md` を参照。
4. InstagramのアカウントURL：未提示のため、ひとまずTOP内のInstagramセクションに接続。正規のアカウントURLに差し替える。
5. 予約フォームの「内容確認」画面、送信先、受付可否、営業時間との照合：未提示。入力の検証までを実装。実際の予約送信は行わない。
6. PCの選択カードは2件、SPは4件。2026-11-07、ユーザー承認によりSPの4枚目を重複したTaylor 114ceから、商品マスター登録のGibson B-25へ変更。PCの2商品とSPの1〜3枚目は維持する。
7. ブレイクポイントは過去コードに合わせて768px。Figmaで中間幅のデザインが提示されていないため、タブレット幅は破綻しない範囲の暫定調整。画像差し込み後は375px・1440pxをレンダリングして横幅を確認。

## 実装方針

- `CODING_RULES.md` のFLOCSS・PCファースト・4スペース・10px基準remを踏襲。
- Sassのビルドに必要な開発用ツール以外のライブラリは採用しない（JSはVanilla JS）。
- セクション別SCSS、機能別JavaScriptに分割。
- PC/SPとも同じDOMを基本にして、専用要素は必要なものだけ表示切り替え。
- 誤操作を防ぐためリンク・ボタンの意味とキーボード操作を考慮。

## 次回の差分チェック

提供画像を配置した表示は **1440px × 900px** および **375px × 812px** でレンダリングしました。残る地図素材を追加した後、同じ幅のFigmaと比較して、各画像の`object-position`、セクション間隔、文字の改行位置を最終調整してください。

## FV プログレスバー改修（2026-11-04）

従来はアクティブなバーの色が即座に変わっていたのを、表示時間に合わせてグレーから白に左→右へ伸びる描画に変更。CSSの `animationend` を切り替えの基準とし、6秒のクロスフェードスライダーと同期。4分割で既存の合計248pxを保持。細部の視覚差分はFigmaとの再比較対象です。

## FVのバーの修正（2026-11-04・再調整）

- 4本すべてを常時表示する（合計248px、線間4px）。
- **白く伸びるのは表示中の写真に対応する1本だけ**。先に再生した写真のバーを白く残さず、グレーへ戻す。
- `js/slider.js` では `.is-complete` の管理を廃止し、`.is-active` のみ切り替える。
- 1本の表示時間は引き続き6000ms、CSSアニメーションの完了で次スライドに切り替え。

## 予約モーダルの背景固定（2026-11-06）

- iPhone Safariで下部入力中に背景が露出する問題への対策として、予約表示中のbodyを元のスクロール位置で固定。終了時に入力フォーカスを外し、固定解除後に同じ位置へ即時復元する。
- 元々スクロールバーがある画面はhtml側に領域を残し、固定中の横ずれを防ぐ。予約専用の状態を使い、メニュー用の`is-locked`の仕様は変更しない。
- SP外枠をパネルと同色にし、パネルのスクロール連鎖を抑制。背景色は既存のスライド完了後に適用し、動きを減らす設定では待機しない。
- CSSを優先し、`visualViewport`の位置補正は未追加。フォーム・カレンダー・文字サイズと既存のブレイクポイントは維持する。
- JavaScriptの構文、8条件での開閉状態・位置復元（DOM代替による確認）、予約以外のCSS宣言が不変であることを確認。iPhone実機のキーボードとブラウザ表示は未検証のため、下部入力・内部スクロール・キーボード開閉・終了後の位置を実機で確認する必要がある。

## TOPのサウンドホール演出（2026-11-06）

- 既存の`assets/icons/logo-charcoal.svg`の全10パスをインラインSVGへ再利用。ロゴ全体からH・D・Y・GUITARを消し、元の穴を原点にOと透過部分を同じ倍率で拡大する。素材そのものは変更しない。
- 表示条件はTOPの同一タブ初回、または再読み込み時。`sessionStorage`の`hody:top-loading-seen`で管理し、通常のページ間移動での再訪・アンカー・履歴復帰・スクロール位置復元・動きを減らす設定・ストレージ利用不可時は省略。スクロール位置を書き換えず、操作時は解除して元の操作を続ける。再読み込みの再生条件に合わせて検証スクリプトも更新し、起動処理の分岐を確認した。
- 起動はheadの小さな処理、描画は`js/loading.js`に分離。外部JSの失敗時も起動から4500msのタイマーで解除する。画像未準備時や起動が遅い場合は待機を延長しない。
- `is-loading`中はバーのアニメーションを未開始に保つ。共通の終了処理が`hody:loading-end`を通知し、スライダーを1枚目に揃えてから状態を解除する。既存の5000ms・linearのバーと900msの画像フェードは維持する。
- 調整箇所：`js/loading.js`の`motion`が全体4000ms、保持750ms、フェード終了1625ms、穴の表示開始1375ms、拡大開始1625msを定義し、`ease`が補間を担当する。初期実装から各区間を一律2.5倍の時間へ変更し、動きの比率を維持した。`_loading.scss`の`--loading-logo-width`がPC280px／SP220px、色も同ファイルの変数で指定する。4500msの異常時解除は`index.html`の起動処理で管理する。
- `scripts/verify-loading.py`を追加。初回実装時にChromeの375・768・1024・1440pxで初期ロゴ・Oのみ・終了後を撮影し、Oの中心が不変なことを確認。終了から5026msで初回の画像切り替えを確認し、再訪・履歴・JS無効・外部JSの欠落／例外・画像未準備・動きを減らす設定・アンカー・メニュー／予約／診断／CTA／位置復元も通過。既存CSS宣言は変更なし。速度調整後は構文と時間設定の比率・解除期限の整合を確認し、検証スクリプトの解除期限も更新した。ブラウザでの再検証は未実施。
- 検証結果と画像は`artifacts/_local/loading/`。iPhone実機SafariのSVG描画・縦横回転・アドレスバー変化は未検証であり、ChromeのSP幅での確認とは区別する。

## iOS Safariのローディング背景の被覆（2026-11-07）

- 報告環境はiOS 27.0.1。ローディング本体は`fixed; inset: 0`で、ベージュはSVG内だけに描画していた。FVは`100vh`とチャコール背景を持ち、本体の高さやSVGの描画範囲が不足すると下端にその色が露出しうる。Safari実機での原因は未確定。
- `_loading.scss`の`html.is-loading`と同状態のbody背景を既存の`--color-sand`（`#f4ecdd`）に揃え、Safariの画面端の背景を補う。既存の終了処理がクラスを外すため、終了後は従来の背景へ戻る。
- 準備中の疑似要素と本体は`inset: 0`を維持し、`min-height: 100dvh`で動的な表示領域の高さを下回らないようにした。本体のCSS背景は透明のままにし、SVGの穴からFVを見せる演出を維持する。ページ全体のviewport設定・FV・固定CTAは変更しない。
- Chromeで34pxの高さ不足を模擬すると、修正前は下端がチャコール、修正後はベージュになることを確認。一方、`window.resize`を伴わない本体サイズの変化ではSVGの数値寸法が古いまま残るため、`js/loading.js`に`ResizeObserver`を追加して既存の`resize()`を再利用した。終了時には監視を切断し、非対応環境では従来のwindowリサイズ処理を使う。
- ロゴ幅PC280px／SP220px、全体4000msと各区間、補間・拡大の計算、4500msの異常時解除、スクロール処理は維持。生成CSS・圧縮CSSと各ソースマップを更新し、追加したローディング2ルール以外のCSSが変更前と同一であることを確認。
- 最終版で既存の`verify-loading.py`が375・768・1024・1440pxと全シナリオを通過。終了後の初回スライド切り替えは5018msで、メニュー・予約・診断・固定CTA・スクロール位置復元も確認した。追加の模擬検証では高さ変更・縦横変更・ResizeObserver非対応・動きを減らす設定・監視解除を通過し、PC／SPで同時刻のSVG座標・倍率・透明度が修正前と一致した。結果と比較画像は`artifacts/_local/loading-safari/loader-final/`と`artifacts/_local/loading-safari/coverage/`。
- これらはローカルChromeの模擬検証であり、iPhone実機Safariのツールバー表示・非表示中の描画を確認したものではない。実機で開始から終了までの下端と、終了後のスクロールを確認する必要がある。

## 共通フッター写真と固定CTAの動き（2026-11-06）

- 3ページの既存写真枠に`js-footer-parallax`を追加し、最後のdeferスクリプトとして`js/footer-parallax.js`を読み込む。枠高506px／SP487pxとフッター全体の寸法、写真ごとのobject-position、下層SPの最小画像幅390pxは維持する。
- `_footer.scss`の`--footer-parallax-range`がPC120px／SP60pxを定義（2026-11-07、動きを明確にするため50px／25pxから変更）。JSが有効なときだけ画像を移動量＋4pxだけ高くして上下へ配置し、両端で2pxの余裕を残す。画像高はPC630px／SP551px。余裕確保に必要な範囲で写真のトリミングが変わる。
- 写真の画面進入から退出またはページ末尾までを進捗にし、translate3dで−60pxから＋60px、SPでは−30pxから＋30pxへ動かす。IntersectionObserverと1回のRAF予約で制御し、画面外・非表示タブ・背景固定中は更新を停止。本文の高さ変更、画像読み込み、リサイズ、履歴復帰、固定解除時に再計算する。
- `_fixed-reservation.scss`の`c-fixed-reservation-guitar-wobble`で、表示中のギター画像だけを3秒周期の末尾0.9秒で0°→−9°→＋9°→−4.5°→＋2.25°→0°へ回転（2026-11-07、5秒周期・最大±6°から変更）。回転中心は50% 75%。非表示・メニュー／モーダル中はリセットし、再表示後は2.1秒静止してから揺れる。
- 両方とも動きを減らす設定で停止し、写真は元の静止表示へ戻る。JS無効・新規JSの取得失敗時も既存写真を表示する。読み込み時間を理由とした開始期限は追加していない。
- ローディング・FV・予約処理のソースは変更なし。既存CSS宣言は追加した演出以外で不変であることを確認。公開時は3ページのHTML、生成済みCSS、新規JSを揃えて配信する。
- `scripts/verify-footer-motion.py`でローカルChromeの3ページ×375・768・1024・1440pxの12条件を検証。変更前との枠・フッター寸法比較、移動量と上下左右の被覆、スクロール往復、ギターの周期・角度・他要素の不変、モーダル中の停止・位置復元、動きを減らす設定を通過。リサイズ・商品絞り込み・履歴復帰・新規JS欠落／JS無効時の静止表示も通過した。
- Node VMでもIntersectionObserver非対応時、30回のscroll通知を1フレームへ集約すること、背景固定・設定変更・非表示タブでの停止と再開を確認。検証結果と画像は`artifacts/_local/footer-motion/`に保存。iPhone実機Safariと公開先URLでの確認は未実施。
- 2026-11-07の強化後も、Chromeの3ページ×4画面幅の12条件、およびリサイズ・商品絞り込み・履歴復帰・JS欠落／無効時の検証をすべて通過。3秒周期・静止2.1秒・揺れ0.9秒・最大±9°、移動PC120px／SP60pxと端の余裕を確認した。HTML・各機能のJS・ローディング／FVのSCSSはハッシュ比較で不変、生成CSSも今回の数値・キーフレーム以外は不変。結果と画像は`artifacts/_local/footer-motion-strong/`。

## TOPのSP商品カード4枚目（2026-11-07）

- ユーザー承認により、4枚目のダミー商品をGibson B-25へ変更。CSV／JSONで表示順4番の商品を採用し、画像・ブランド・モデル・キャッチコピー・alt・data-product・aria-labelをマスターに揃えた。旧`guitar04.jpg`は3枚目の画像と同一内容で、ファイルは未使用のまま保持する。
- 通常の予約処理は`data-product`と商品選択肢の値が一致した場合だけ選択されるため、TOPの予約欄に`Gibson B-25`を1件追加。予約モーダルのJavaScript・仕様は変更していない。
- PC／SPの1〜2枚目は共通DOM、3〜4枚目は768px以下だけに表示する構造を維持。TOPの静的HTML・予約選択肢と商品マスターは従来どおり別管理とし、今回の共通化や自動生成は行わない。1〜3枚目・CSS・JavaScript・商品マスター・商品一覧ページは作業前と同一であることを比較確認した。
- ローカルChromeの375・390・768・769・1440pxで変更前後を比較し、SP4件／PC2件とカード・写真・文字枠・gapの寸法が一致。PCの比較画像も一致した。各カードの予約値・フォームの商品値・終了後のスクロールとフォーカス復元、診断からの予約後に全5選択肢を復元してB-25を再選択する流れ、商品一覧12件→小さめ6件→予約→12件リセットも通過した。結果と比較画像は`artifacts/_local/selection-card/`。iPhone実機では未検証。

## TOPローディングの起動条件の見直しと実機測定（2026-11-07）

上のローディング関連項目は当時の実装・検証の履歴として残す。今回の起動条件は以下を正とする。iPhone実機の下端の灰色については原因未確定であり、今回の変更だけで解消したとは扱わない。

- 起動候補になったらベージュの準備画面を表示し、先頭FV画像の準備と描画処理の準備を待つ。prepareの上限はページが可視である時間の累計2000ms。裏で開いたページでは可視になるまで演出を開始せず、非表示の時間はprepareの上限へ加算しない。
- 演出を実際に開始するときだけ`sessionStorage`の`hody:top-loading-seen`を保存し、`hody:loading-start`を通知する。準備中の離脱・タイムアウトなどで実開始しなかった場合は、再訪の機会を消費しない。
- 実開始から4000msの既存演出を再生し、異常時の解除は実開始から4500ms。ロゴ・Oの穴・各区間の時間と補間は維持する。prepareの待機時間は演出の4000msに含めない。
- ローディングJSを先頭のdeferスクリプトとして読み込み、先頭FV画像をpreloadする。FVスライダー・予約CTA・モーダルの仕様は変更しない。
- 下端については既存のhtml/body背景、`fixed; inset: 0`、`min-height: 100dvh`、ResizeObserverを維持し、CSSは追加・変更しない。実機測定で不足している領域を特定してから修正方法を選ぶ。

### Safari実機の確認手順

1. 今回変更した`index.html`と`js/loading.js`を公開先へ反映してから確認する。iPhoneの設定内でSafariの「詳細」→「Webインスペクタ」を有効にし、MacのSafariの設定「詳細」で開発者向けの機能を表示する。iPhoneをMacへケーブル接続し、iPhoneのSafariで[公開TOP](https://tokyo-designplex.jp/~26G_miyauchi/practice/)を開き、MacのSafariの開発メニューからiPhoneと対象ページを選ぶ。[WebKitの接続手順](https://webkit.org/web-inspector/enabling-web-inspector/)も参照。実際の端末名・OS・Safariの版、URL、LINE等の入口アプリ、縦横、ツールバー表示状態を記録する。過去メモにあるOS情報を今回の端末の確認値として転記しない。
2. キャッシュを消す前に、Networkで実機が取得したHTML・`css/style.css`・`js/loading.js`の内容と応答ヘッダーを保存し、ローカルの配信対象と比較する。通常キャッシュの再現を先に取り、その後キャッシュ無効でも再現するかを別条件として記録する。
3. Sourcesで`js/loading.js`の、`loader.hidden = false`に続く初回`resize()`が完了した直後（prepareの待機開始・`hody:loading-start`の前）にブレークポイントを置く。アクションを`Evaluate JavaScript`とし、下のコードを貼り付け、**Automatically continue after evaluating**を有効にする。通常の一時停止は時間判定に影響するため使わない。機能の説明は[WebKitのJavaScript Breakpoints](https://webkit.org/web-inspector/javascript-breakpoints/)を参照。
4. iPhoneで画面録画を開始してから再読み込みする。読み込み中は触らず、ベージュの準備画面、ロゴ、穴の拡大、通常表示までを撮る。終了後にConsoleで`JSON.stringify(window.__hodyLoadingProbe.samples, null, 2)`を実行し、文字列をコピーして録画と同じ確認結果へ保存する。計測コードはページのメモリだけを使い、HTML・CSS・ストレージ・公開ファイルを変更しない。
5. ツールバーが表示された状態・隠れた状態からの読み込み、縦・横、端末回転を別々に確認する。ローディング中のスワイプ・タップは既存仕様で演出を解除するため、ツールバーを隠すためにスワイプした後の画面を「演出継続中の隙間」と判定しない。操作による解除の確認は無操作の確認と分ける。
6. 初回アクセスはSafariの独立した新規タブでTOPへ直接アクセスして確認する。LINEのリンクから開いた場合は、LINE内ブラウザでの表示と「Safariで開く」後の表示を分け、Safariの再読み込みも続けて記録する。別アプリからの切り替えで非表示→可視になったとき、prepareから実開始に進むか、実開始前にseenを保存していないかを確認する。Safariへの切り替えが同じタブの継続か新しいタブかも記録する。
7. 計測後は追加したブレークポイントを削除する。計測自体の負荷の影響を区別するため、計測なしの無操作録画でも症状の有無を比較する。

### 一時的な計測コード

以下はWeb Inspectorの自動継続ブレークポイントのアクション専用。リポジトリのJSには追加しない。100ms間隔、windowのresize、visualViewportのresize/scroll、ローディングのstart/endを記録する。設置から5秒で解除するタイマーを持ち、startを受けた場合は実開始から5秒へ更新する。endを受けた場合はその場でタイマーとリスナーをすべて解除する。prepareが最長2秒あるため、設置から固定5秒だけで計測を切ると演出の末尾を取り逃がす。

```js
(() => {
    window.__hodyLoadingProbe?.stop();
    const root = document.documentElement;
    const loader = document.querySelector('.js-loading');
    const svg = loader?.querySelector('.js-loading-svg');
    const background = loader?.querySelector('.js-loading-background');
    const mask = loader?.querySelector('.js-loading-mask');
    const maskBase = loader?.querySelector('.js-loading-mask-base');
    const hole = loader?.querySelector('.js-loading-hole');
    const holeScale = loader?.querySelector('.js-loading-hole-scale');
    const viewport = window.visualViewport;
    const samples = [];
    const listeners = [];
    let intervalId;
    let timeoutId;
    let stopped = false;

    function box(node) {
        if (!node) return null;
        const rect = node.getBoundingClientRect();
        return {
            left: rect.left, top: rect.top,
            right: rect.right, bottom: rect.bottom,
            width: rect.width, height: rect.height,
            documentBottom: rect.bottom + window.scrollY
        };
    }

    function attributes(node, names) {
        return node ? Object.fromEntries(names.map(name => [name, node.getAttribute(name)])) : null;
    }

    function capture(reason) {
        const loaderBox = box(loader);
        const viewportBottom = viewport ? viewport.offsetTop + viewport.height : window.innerHeight;
        const image = document.querySelector('.p-hero__slide img');
        const style = loader ? getComputedStyle(loader) : null;
        const sample = {
            reason, time: performance.now(),
            loading: root.classList.contains('is-loading'),
            pending: root.classList.contains('is-loading-pending'),
            hidden: document.hidden,
            loadingStartedAt: root.dataset.loadingStartedAt ?? null,
            scrollX: window.scrollX, scrollY: window.scrollY,
            innerWidth: window.innerWidth, innerHeight: window.innerHeight,
            clientWidth: root.clientWidth, clientHeight: root.clientHeight,
            devicePixelRatio: window.devicePixelRatio,
            viewport: viewport ? {
                width: viewport.width, height: viewport.height,
                offsetLeft: viewport.offsetLeft, offsetTop: viewport.offsetTop,
                pageLeft: viewport.pageLeft, pageTop: viewport.pageTop,
                scale: viewport.scale, bottom: viewportBottom,
                documentBottom: viewport.pageTop + viewport.height
            } : null,
            loader: loaderBox,
            svg: box(svg),
            background: box(background),
            viewBox: svg?.getAttribute('viewBox') ?? null,
            backgroundAttributes: attributes(background, ['x', 'y', 'width', 'height']),
            mask: attributes(mask, ['x', 'y', 'width', 'height', 'maskUnits', 'maskContentUnits']),
            maskBase: attributes(maskBase, ['x', 'y', 'width', 'height']),
            holeOpacity: hole?.getAttribute('opacity') ?? null,
            holeTransform: holeScale?.getAttribute('transform') ?? null,
            loaderStyle: style ? {
                position: style.position, top: style.top, bottom: style.bottom,
                height: style.height, minHeight: style.minHeight,
                background: style.backgroundColor
            } : null,
            rootBackground: getComputedStyle(root).backgroundColor,
            bodyBackground: document.body ? getComputedStyle(document.body).backgroundColor : null,
            loaderBottomShortfall: loaderBox ? viewportBottom - loaderBox.bottom : null,
            firstImage: image ? { complete: image.complete, naturalWidth: image.naturalWidth } : null
        };
        samples.push(sample);
        if (samples.length > 500) samples.shift();
    }

    function stop(reason = 'manual-stop') {
        if (stopped) return;
        capture(reason);
        stopped = true;
        window.clearInterval(intervalId);
        window.clearTimeout(timeoutId);
        for (const [target, type, callback] of listeners) target.removeEventListener(type, callback);
    }

    function armTimeout() {
        window.clearTimeout(timeoutId);
        timeoutId = window.setTimeout(() => stop('probe-timeout'), 5000);
    }

    function listen(target, type, callback) {
        if (!target) return;
        target.addEventListener(type, callback, { passive: true });
        listeners.push([target, type, callback]);
    }

    listen(window, 'resize', () => capture('window-resize'));
    listen(viewport, 'resize', () => capture('visualViewport-resize'));
    listen(viewport, 'scroll', () => capture('visualViewport-scroll'));
    listen(document, 'visibilitychange', () => capture('visibilitychange'));
    listen(document, 'hody:loading-start', () => {
        capture('hody:loading-start');
        armTimeout();
    });
    listen(document, 'hody:loading-end', () => stop('hody:loading-end'));
    window.__hodyLoadingProbe = { samples, stop };
    capture('installed-after-first-resize');
    intervalId = window.setInterval(() => capture('interval'), 100);
    armTimeout();
})();
```

### 数値と画面の照合方法

- まずズームなし（`visualViewport.scale === 1`）で比較する。すべてのDOM寸法はCSS px。layout座標の可視下端`visualViewport.offsetTop + visualViewport.height`とloaderの`getBoundingClientRect().bottom`を比較する。document座標で比べる場合はloaderの`bottom + scrollY`と`visualViewport.pageTop + visualViewport.height`に揃える。`visualViewport.height`だけをbottom座標と直接比較しない。録画の物理pxにdevicePixelRatioだけを掛けて同一視しない。座標の定義は[CSSOM ViewのVisualViewport](https://drafts.csswg.org/cssom-view/#the-visualviewport-interface)を参照。
- loaderが可視下端へ届かなければ外枠、loaderは届くがSVGが短ければSVGのCSSサイズ、SVGは届くが背景rectやviewBoxが古ければ数値寸法の同期を調べる。maskBaseなどdefs内の要素は、属性とSVGの座標変換を確認する。
- rectのBCRが全面でも、mask後にその範囲すべてがベージュで塗られていることは保証されない。全寸法が一致しても穴の未到達部分に帯が出る場合は、画面録画とSVG/maskの描画を追加調査する。loaderは`pointer-events: none`なので、`elementFromPoint()`がFVを返しても被覆不足の証拠にはならない。
- 灰色の位置をWebの可視領域と照合し、Safariのツールバー等のUI領域と分ける。Oの穴が下端へ達した後にFVが見える部分と、穴が未到達なのに残る矩形の帯も分ける。`hody:loading-end`時点のサンプルは終了処理が状態を外す直前であり、その後の通常FVをローディング中と扱わない。
- 過去の34px不足のChrome模擬検証は、実機の不足量や原因を特定したものではない。測定結果がない状態で高さを加算したり、ベージュ背景を重ねたり、`100svh`やviewport設定へ切り替えたりしない。

### 今回の検証状態

- iPhone実機Safari・公開サーバーでの確認は未実施。下端の灰色の原因は未確定。
- `/private/tmp/hody-cta-venv/bin/python scripts/verify-loading.py --output artifacts/_local/loading-start/final`を実行し、ローカルChromeの375・390・768・1024・1440pxと全シナリオが通過。通常の準備時間は約92〜106ms、演出は約4000〜4016msで、2秒の固定待機はない。既存ロゴのパス、PC280px／SP220pxの幅、Oの中心、進捗線の停止も確認した。
- JS・先頭画像・画像decode・外部フォントCSS・メインCSSを個別に1500ms遅延させても約4000〜4017ms再生した。後続のflatpickr JSを1500ms遅らせた場合も約116msで開始し、後続JSの実行は約1453ms後だった。JS・画像・CSSの期限超過／欠落、JS例外、decode失敗、ストレージの読み書き拒否では解除し、未再生のseenを保存しない。遅れて取得・decodeが完了しても再表示しないことを確認した。
- Chrome上で可視状態を模擬し、初期非表示、準備中の非表示からの再開、可視時間累計2秒、開始後の非表示終了を確認。再生処理を停止させる検証では、実開始から約4502msで異常時解除された。これらはSafari実機のライフサイクル検証ではない。
- 初回・再読み込み・通常再訪・履歴復帰・アンカー・JS無効・動きを減らす設定を確認。終了後の初回スライド切り替えは約5023msで、既存の5000ms周期・900msフェードを維持。メニュー・予約・診断・固定CTA・スクロール位置復元も通過した。
- 結果JSONと5画面幅の画像は`artifacts/_local/loading-start/final/`。今回の変更は4ファイルに限定し、TOP本文DOM・SCSS・生成CSS・他機能JS・下層ページは変更していない。一時計測コードは構文と代替DOMでのタイマー／リスナー解除を確認したが、iPhoneでの描画は未検証。
