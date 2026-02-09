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

## プロジェクトルール

- 日本語でコミュニケーションする
- コミットメッセージは英語で書く
