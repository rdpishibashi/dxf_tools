import streamlit as st
import os
import sys

# utils モジュールをインポート可能にするためのパスの追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.compare_partslist import compare_parts_list
from common_utils import save_uploadedfile, get_comparison_filename, handle_error

def app():
    st.title('回路記号リスト差分抽出')
    st.write('2つの回路記号リストを比較し、差分をマークダウン形式で出力します。')
    
    # ファイルアップロードUI
    col1, col2 = st.columns(2)
    
    with col1:
        uploaded_file_a = st.file_uploader("回路記号リスト・ファイルA", type=["txt"], key="partslist_a")
    
    with col2:
        uploaded_file_b = st.file_uploader("回路記号リスト・ファイルB", type=["txt"], key="partslist_b")
    
    # デフォルトのファイル名を設定
    default_filename = "partslist_diff.md"
    if uploaded_file_a is not None and uploaded_file_b is not None:
        default_filename = get_comparison_filename(uploaded_file_a.name, uploaded_file_b.name, 'partslist_diff')
        
    output_filename = st.text_input("出力ファイル名", default_filename)
    if not output_filename.endswith('.md'):
        output_filename += '.md'
    
    # ヘルプ情報
    st.info("""
    このツールは、2つの回路記号リストファイルを比較し、差分を抽出します。
    入力ファイルは、1行に1つの回路記号が記載されたテキストファイルです。
    
    比較結果は以下のような情報を含みます：
    - 処理概要（各リストの総数、共通数、不足数）
    - 図面に不足しているラベル（回路記号リストには存在する）
    - 回路記号リストに不足しているラベル（図面には存在する）
    
    不足している部分を調整することで、図面と回路記号リストの整合性を確保できます。
    """)
    
    with st.expander("入力ファイルのフォーマット"):
        st.markdown("""
        ### 入力ファイルのフォーマット
        
        入力ファイルは、1行に1つの回路記号が記載されたシンプルなテキストファイルです。例えば：
        
        ```
        R1
        R2
        C1
        IC1
        ```
        
        通常、「図面ラベル抽出」ツールまたは「Excel回路記号抽出」ツールで生成したテキストファイルを使用します。
        
        ### 比較の仕組み
        
        比較時には以下の処理が行われます：
        
        1. 各回路記号は正規化され、大文字に統一されます（例：「r1」→「R1」）
        2. 重複する回路記号も考慮されます
        3. ファイルAをDXF図面、ファイルBを回路記号リストとして比較を行います
        
        結果として、図面に存在しないラベルや回路記号リストに存在しないラベルを特定できます。
        """)
    
    if uploaded_file_a is not None and uploaded_file_b is not None:
        try:
            # ファイルが選択されたら処理ボタンを表示
            if st.button("回路記号リストを比較"):
                # ファイルを一時ディレクトリに保存
                temp_file_a = save_uploadedfile(uploaded_file_a)
                temp_file_b = save_uploadedfile(uploaded_file_b)
                
                with st.spinner('回路記号リストを比較中...'):
                    # パーツリストの比較
                    comparison_result = compare_parts_list(temp_file_a, temp_file_b)
                    
                    # 結果を表示
                    st.subheader("回路記号リスト差分抽出結果")
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
        st.info("比較対象となる2つのテキストファイルをアップロードしてください。")

if __name__ == "__main__":
    app()