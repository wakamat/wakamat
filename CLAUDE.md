# wakamat プロジェクト

Claude Code の Skills / Sub-agents / Agent Teams を活用した業務効率化テンプレートです。

## スキル一覧

| コマンド | 用途 | 使用エージェント |
|---|---|---|
| `/humanize` | AI臭のある文章を自然な日本語に書き直す | writer |
| `/proposal` | 企画書を作成する | planner |
| `/chat` | 社内チャット・メールの文面を構成する | writer |
| `/research` | マーケットリサーチとレポート作成（競合分析含む） | researcher |
| `/document` | 報告書・提案書・マニュアル等の資料作成 | writer |
| `/analysis` | 統計を用いたデータ分析と可視化（ROI分析含む） | analyst |
| `/mockup` | 企画をもとにUIモックアップを作成 | developer |
| `/persona` | ターゲットペルソナを詳細に作成 | researcher |
| `/content-plan` | 3ヶ月間のコンテンツマーケティング計画を作成 | planner |
| `/sns` | SNS投稿文を作成（X、Instagram、LinkedIn等） | writer |
| `/copy` | マーケティングコピーを改善・ブラッシュアップ | writer |
| `/keywords` | SEO・AI検索向けキーワード拡張 | researcher |
| `/voc` | 顧客の声（レビュー・フィードバック）を分析 | analyst |
| `/email-scenario` | メールマーケティングのシナリオを設計 | writer |

## Sub-agents

| エージェント | 役割 |
|---|---|
| writer | 日本語の文章作成・編集の専門家 |
| researcher | マーケットリサーチと情報収集の専門家 |
| analyst | データ分析と可視化の専門家 |
| planner | 企画立案と構成設計の専門家 |
| developer | フロントエンド開発とモック作成の専門家 |

## Agent Teams の使い方

自然言語で指示するだけでチームが作れます：

```
このPRをレビューするチームを作って。
セキュリティ担当、パフォーマンス担当、テスト担当の3人で。
```

### チームメンバーへの指示のコツ

- 各メンバーには明確な役割を与える
- 担当するファイルやディレクトリを分ける（同じファイルを複数人で編集しない）
- 大きすぎず小さすぎないタスクに分割する（1メンバーあたり5〜6タスクが目安）

### マーケティング業務でのチーム例

**新商品ローンチ準備チーム**
```
新商品「〇〇」のローンチ準備をチームで進めて。
- researcher: 市場調査と競合分析
- planner: 企画書とコンテンツ計画の策定
- writer: LP用コピーとSNS投稿文の作成
```

**キャンペーン分析チーム**
```
先月のキャンペーン結果を分析して改善案を出して。
- analyst: データ分析とROI計算
- researcher: 競合のキャンペーン調査
- planner: 次回キャンペーンの改善企画
```

### delegate モード

Agent Teams 使用時、リーダーを調整役に専念させるモードです。リーダーは直接ファイル編集やコマンド実行をせず、すべてチームメイトに委任します。大規模なタスクで役割分担を明確にしたい場合に有効です。

## 出力ファイルの保存先

- スキルやチームが生成したファイルは `output/` ディレクトリに保存する
- ファイル名は日付とスキル名を含める: `output/YYYYMMDD_スキル名_内容.md`
- 例: `output/20260209_research_競合分析.md`
- モックアップは `output/mockup/` に保存する

## パーミッション設定

settings.json で以下を自動許可済み：
- ファイルの読み書き・編集（Read, Write, Edit, Glob, Grep）
- Web検索・取得（WebFetch, WebSearch）
- Python, Node.js, npm の実行

以下は安全のため拒否済み：
- `rm -rf`（再帰的削除）
- `git reset --hard`（変更の消失防止）

git push 等は都度確認が入る（allowにもdenyにも入れていない）。

## Hooks 設定

- **Stop hook**: タスクの完了状態をAIが自動チェック。未完了のタスクがあれば作業を継続する
- **SubagentStop hook**: サブエージェントの作業品質をAIが自動チェック。不十分なら作業を継続する

## プロジェクトルール

- 日本語でコミュニケーションする
- コミットメッセージは英語で書く
