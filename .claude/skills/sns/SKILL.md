---
name: sns
description: SNSの投稿文を作成する。Instagram、X、Facebook、LinkedIn等の投稿作成時に使用。
disable-model-invocation: true
context: fork
agent: writer
---

以下の情報に基づいて、魅力的なSNS投稿文を5つ作成してください。

# 各投稿に含める要素
1. 本文（プラットフォームの文字数制限内に収める）
2. ハッシュタグ案（関連性の高いもの5〜8個）
3. 絵文字の適切な使用
4. CTA（Call to Action）

# ルール
- 投稿ごとに異なるアプローチでバリエーションを持たせる
- プラットフォームの文化に合ったトーンで書く（Xなら簡潔、Instagramなら視覚的、LinkedInならプロフェッショナル）
- ハッシュタグは関連性の高いものだけ使う。無関係なトレンドタグは入れない
- CTAは自然な文脈で入れる。唐突な「今すぐチェック！」は避ける
- AI臭のある定型表現を使わない（humanize スキルのルールに準拠）
- 投稿として不自然にならない範囲で情報を盛り込む

# 入力

$ARGUMENTS
