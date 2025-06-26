# Travel Route Generator 🌟

AIを活用した20-30代女性向けの旅行ルート生成WEBアプリケーション

## 機能

✨ **主要機能**
- AIチャットによる旅行相談
- Instagram映えスポットの提案
- 自動ルート生成と地図表示
- 周辺飲食店の検索・表示
- SNS共有機能
- レスポンシブデザイン

🎯 **ターゲットユーザー**
- 20-30代女性
- Instagram愛用者
- 友達との旅行を楽しみたい人
- 写真映えするスポットを探している人

## セットアップ方法

### 1. 必要なAPIキーの取得

#### OpenAI API
1. [OpenAI Platform](https://platform.openai.com/) でアカウント作成
2. API キーを生成

#### Google Maps API
1. [Google Cloud Console](https://console.cloud.google.com/) でプロジェクト作成
2. 以下のAPIを有効化：
   - Maps JavaScript API
   - Places API
   - Directions API
3. APIキーを生成

### 2. 環境変数の設定

```bash
# .env.example をコピーして .env ファイルを作成
cp .env.example .env

# .env ファイルを編集してAPIキーを設定
```

### 3. 依存関係のインストール

```bash
pip install -r requirements.txt
```

### 4. アプリケーションの起動

```bash
python main.py
```

ブラウザで `http://localhost:5000` にアクセス

## 使用例

### 基本的な使い方
1. チャット欄に旅行の希望を入力
   - 例：「山梨の富士山周辺を友達と観光したいです」
2. AIが Instagram映えするスポットを提案
3. 地図にルートと飲食店が表示される
4. 共有ボタンでSNSにシェア可能

### 入力例
- 「富士五湖を2日間で巡りたい」
- 「河口湖でインスタ映えする写真を撮りたい」
- 「山梨のワイナリー巡りをしたい」
- 「友達と山梨のほうとうを食べに行きたい」

## 技術スタック

### バックエンド
- **Flask** - Webフレームワーク
- **OpenAI GPT** - AI会話エンジン
- **Google Maps API** - 地図・場所検索
- **Folium** - 地図可視化

### フロントエンド
- **HTML5/CSS3** - 基本構造
- **JavaScript (ES6+)** - インタラクション
- **Bootstrap 5** - UIフレームワーク
- **Font Awesome** - アイコン

## ディレクトリ構造

```
yamanashi-AI-Concerge/
├── main.py                 # メインアプリケーション
├── requirements.txt        # Python依存関係
├── .env.example           # 環境変数テンプレート
├── README.md              # このファイル
├── templates/
│   └── index.html         # メインページHTML
├── static/
│   ├── image/            # 背景画像等
│   └── maps/             # 生成された地図ファイル
└── .gitignore            # Git除外設定
```

## APIエンドポイント

### POST /chat
チャット機能のメインエンドポイント

**リクエスト:**
```json
{
  "message": "ユーザーからのメッセージ"
}
```

**レスポンス:**
```json
{
  "response": "AIからの返答",
  "map_data": {
    "url": "/static/maps/travel_route_xxx.html",
    "locations": [...],
    "restaurants": [...],
    "route": {...}
  },
  "locations": [...],
  "restaurants": [...],
  "route": {...}
}
```

### POST /share
共有機能用エンドポイント

## カスタマイズ

### AIプロンプトの調整
`main.py` の `chat()` 関数内のシステムメッセージを編集

### UIデザインの変更
`templates/index.html` のCSSスタイルを編集

### 地図の表示設定
`main.py` の `create_travel_route_map()` 関数を編集

## トラブルシューティング

### よくある問題

1. **APIキーエラー**
   - `.env` ファイルの設定を確認
   - API キーの有効性を確認

2. **地図が表示されない**
   - Google Maps API の有効化を確認
   - Places API の権限を確認

3. **AI応答が遅い**
   - OpenAI APIの利用制限を確認
   - ネットワーク接続を確認

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。

## 貢献

プルリクエストやイシューの報告を歓迎します！

## 連絡先

質問や提案がある場合は、GitHubのIssueでお知らせください。