import streamlit as st

st.set_page_config(
    page_title="DXF file Analysis Tools",
    page_icon="📊",
    layout="wide",
)

st.title('DXF file Analysis Tools')
st.write('CADのDXFファイルを分析・比較するツールです。')

st.markdown("""
## 機能一覧

このアプリケーションでは以下の機能が利用できます：

1. **図面ラベル抽出** (extract labels) - DXFファイルからラベル（テキスト）を抽出します
2. **図面差分抽出** (compare dxf) - 2つのDXFファイルを比較し、差分をDXFフォーマットで出力します
3. **図面ラベル差分抽出** (compare labels) - 2つのDXFファイルのラベルを比較し、差分をExcel形式で出力します
4. **Excel回路記号抽出** (extract symbols) - ULKES Excelファイルから回路記号を抽出します
5. **回路記号リスト差分抽出** (compare partslist) - 2つの回路記号リストを比較し、差分をExcel形式で出力します

左側のサイドバーから利用したい機能を選んでください。
""")

st.sidebar.title("ナビゲーション")
st.sidebar.info(
    "各機能の実行は左上のメニューを選択してください。"
)

# バージョン情報やツールの説明などを表示
st.markdown("---")
st.markdown("### 使用方法")
st.markdown("""
各機能ページでファイルをアップロードし、必要なオプションを設定し処理を実行します。
処理結果はダウンロードしていただくことになります。
""")

# フッター
st.markdown("---")
st.markdown("DXF file Analysis Tools")