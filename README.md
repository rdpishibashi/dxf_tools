# DXF分析ツール

CADで使用されるDXFファイルを分析・比較するためのWebアプリケーションです。

## 機能

このツールは以下の機能を提供します：

1. **ラベル抽出**
   - DXFファイルからテキストラベル（MTEXTエンティティ）を抽出
   - 結果をテキストファイルとしてダウンロード可能

2. **DXF構造分析**
   - DXFファイルの内部構造を詳細に分析
   - Excelファイルとして結果をダウンロード可能

3. **DXF階層抽出**
   - DXFファイルの階層構造をMarkdown形式で出力
   - 結果をMarkdownファイルとしてダウンロード可能

4. **DXF差分比較（図形）**
   - 2つのDXFファイルの図形要素の差分を比較
   - 追加/削除/変更された要素を色分けしたDXFファイルとして出力

5. **DXF差分比較（ラベル）**
   - 2つのDXFファイルに含まれるラベルの差分を比較
   - 結果をMarkdown形式でダウンロード可能

## インストール方法

### ローカル環境での実行

1. リポジトリをクローン
   ```bash
   git clone https://github.com/yourusername/dxf-analyzer.git
   cd dxf-analyzer
   ```

2. 依存関係をインストール
   ```bash
   pip install -r requirements.txt
   ```

3. アプリケーションを起動
   ```bash
   streamlit run app.py
   ```

4. ブラウザで以下のURLにアクセス
   ```
   http://localhost:8501
   ```

### Streamlit Cloudでのデプロイ

1. GitHubでリポジトリを作成

2. Streamlit Cloudにアクセスし、アカウントを作成またはログイン
   https://streamlit.io/cloud

3. 「New app」をクリックし、GitHubリポジトリとブランチを選択

4. アプリを公開

## 使用方法

1. サイドバーからツールを選択
2. DXFファイルをアップロード
3. 必要に応じて出力ファイル名やパラメータを設定
4. 「処理実行」ボタンをクリック
5. 結果を確認し、ファイルをダウンロード

## 必要条件

- Python 3.8以上
- ezdxf 1.1.0以上
- streamlit 1.30.0以上
- pandas 2.1.3以上