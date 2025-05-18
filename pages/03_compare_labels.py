import streamlit as st
import os
import sys

# utils モジュールをインポート可能にするためのパスの追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.compare_labels import compare_labels
from common_utils import save_uploadedfile, get_comparison_filename, handle_error

def app():
    st.title('図面ラベル差分抽出')
    st.write('2つのDXFファイルのラベルを比較し、差分をマークダウン形式で出力します。')
    
    # ファイルアップロードUI
    col1, col2 = st.columns(2)
    
    with col1:
        uploaded_file_a = st.file_uploader("基準DXFファイル (A)", type="dxf", key="label_a")
    
    with col2:
        uploaded_file_b = st.file_uploader("比較対象DXFファイル (B)", type="dxf", key="label_b")
    
    # デフォルトのファイル名を設定
    default_filename = "label_diff.md"
    if uploaded_file_a is not None and uploaded_file_b is not None:
        default_filename = get_comparison_filename(uploaded_file_a.name, uploaded_file_b.name, 'label_diff')
        
    output_filename = st.text_input("出力ファイル名", default_filename)
    if not output_filename.endswith('.md'):
        output_filename += '.md'
    
    # ヘルプ情報を表示
    st.info("""
    このツールは、2つのDXFファイルからテキスト要素（ラベル）を抽出し、追加・削除されたラベルを比較します。
    
    比較結果は以下の形式で出力されます：
    - 追加されたラベル: 基準ファイル(A)には存在せず、比較対象ファイル(B)に追加されたラベル
    - 削除されたラベル: 基準ファイル(A)に存在し、比較対象ファイル(B)からは削除されたラベル
    
    複数回出現するラベルの場合は、その回数の差分も表示されます。
    """)
    
    if uploaded_file_a is not None and uploaded_file_b is not None:
        try:
            # ファイルが選択されたら処理ボタンを表示
            if st.button("ラベル差分を比較"):
                # ファイルを一時ディレクトリに保存
                temp_file_a = save_uploadedfile(uploaded_file_a)
                temp_file_b = save_uploadedfile(uploaded_file_b)
                
                with st.spinner('DXFラベルを比較中...'):
                    comparison_result = compare_labels(temp_file_a, temp_file_b)
                    
                    # 結果を表示
                    st.subheader("図面ラベル差分抽出結果")
                    st.markdown(comparison_result)
                    
                    # ダウンロードボタンを作成
                    st.download_button(
                        label="差分テキストファイルをダウンロード",
                        data=comparison_result.encode('utf-8'),
                        file_name=output_filename,
                        mime="text/markdown",
                    )
                
                # 一時ファイルの削除
                try:
                    os.unlink(temp_file_a)
                    os.unlink(temp_file_b)
                except:
                    pass
        
        except Exception as e:
            handle_error(e)
    else:
        st.info("基準ファイル(A)と比較対象ファイル(B)をアップロードしてください。")

if __name__ == "__main__":
    app()