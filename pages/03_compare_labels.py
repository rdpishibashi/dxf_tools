import streamlit as st
import os
import sys
import pandas as pd

# utils モジュールをインポート可能にするためのパスの追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.compare_labels import compare_labels_multi
from common_utils import save_uploadedfile, handle_error

def app():
    st.title('図面ラベル差分抽出')
    st.write('複数のDXFファイルペアのラベルを比較し、差分をExcel形式で出力します。')
    
    # オプション設定
    with st.expander("オプション設定", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            filter_option = st.checkbox(
                "回路記号（候補）のみ抽出", 
                value=False, 
                help="回路記号以外と判断されるラベルを除外します"
            )
        
        with col2:
            sort_option = st.selectbox(
                "並び替え", 
                options=[
                    ("昇順", "asc"), 
                    ("逆順", "desc"),
                    ("並び替えなし", "none")
                ],
                format_func=lambda x: x[0],
                help="ラベルの並び替え順を指定します",
                index=0  # デフォルトで昇順を選択
            )
            sort_value = sort_option[1]  # タプルの2番目の要素（実際の値）を取得
    
    # 出力ファイル名設定
    output_filename = st.text_input("出力Excelファイル名", "label_diff_result.xlsx")
    if not output_filename.endswith('.xlsx'):
        output_filename += '.xlsx'
    
    # ファイルペア登録UI
    st.subheader("ファイルペア登録")
    st.write("最大5ペアのDXFファイルを登録できます")
    
    # セッション状態の初期化
    if 'file_pairs' not in st.session_state:
        st.session_state.file_pairs = []
        for i in range(5):  # 最大5ペア
            st.session_state.file_pairs.append({
                'fileA': None,
                'fileB': None,
                'name': f"Pair{i+1}"
            })
    
    # 各ペアの入力フォーム
    file_pairs_valid = []
    
    for i in range(5):  # 最大5ペア
        with st.expander(f"ファイルペア {i+1}", expanded=i==0):
            col1, col2, col3 = st.columns([2, 2, 1])
            
            with col1:
                uploaded_file_a = st.file_uploader(
                    f"DXFファイルA {i+1}", 
                    type="dxf", 
                    key=f"label_a_{i}"
                )
                if uploaded_file_a:
                    st.session_state.file_pairs[i]['fileA'] = uploaded_file_a
                
            with col2:
                uploaded_file_b = st.file_uploader(
                    f"DXFファイルB {i+1}", 
                    type="dxf", 
                    key=f"label_b_{i}"
                )
                if uploaded_file_b:
                    st.session_state.file_pairs[i]['fileB'] = uploaded_file_b
            
            with col3:
                pair_name = st.text_input(
                    "ペア名",
                    value=st.session_state.file_pairs[i]['name'],
                    key=f"pair_name_{i}"
                )
                st.session_state.file_pairs[i]['name'] = pair_name
            
            # 両方のファイルが選択されている場合、有効なペアとして追加
            if st.session_state.file_pairs[i]['fileA'] and st.session_state.file_pairs[i]['fileB']:
                file_pairs_valid.append((
                    st.session_state.file_pairs[i]['fileA'],
                    st.session_state.file_pairs[i]['fileB'],
                    st.session_state.file_pairs[i]['name']
                ))
                
                # プレビュー表示
                st.success(f"Pair{i+1}: {st.session_state.file_pairs[i]['fileA'].name} と {st.session_state.file_pairs[i]['fileB'].name} を比較")
    
    # ヘルプ情報を表示
    st.info("""
    このツールは、複数のDXFファイルペアからテキスト要素（ラベル）を抽出し、各ペアごとに比較結果をExcelファイルに出力します。
    
    1. 各ファイルペアを登録してください（最大5ペア）
    2. 「出力Excelファイル名」を設定します
    3. 「ラベル差分を比較」ボタンをクリックして処理を実行します
    
    Excelファイルは以下の内容を含みます：
    - 各ペアごとに個別のシートを作成
    - サマリーシートで全体の比較結果を表示
    - 各シートでは、ファイルAのみ、ファイルBのみ、両方に存在するが数が異なるラベルを色分けして表示
    """)
    
    if file_pairs_valid:
        try:
            # ファイルが選択されたら処理ボタンを表示
            if st.button("ラベル差分を比較", disabled=len(file_pairs_valid) == 0):
                # 全てのファイルを一時ディレクトリに保存
                with st.spinner('DXFファイルを処理中...'):
                    temp_file_pairs = []
                    
                    for file_a, file_b, pair_name in file_pairs_valid:
                        temp_file_a = save_uploadedfile(file_a)
                        temp_file_b = save_uploadedfile(file_b)
                        temp_file_pairs.append((file_a, file_b, temp_file_a, temp_file_b, pair_name))
                    
                    # Excel出力を生成
                    excel_data = compare_labels_multi(
                        temp_file_pairs,
                        filter_non_parts=filter_option,
                        sort_order=sort_value
                    )
                    
                    # 結果を表示
                    st.success(f"{len(file_pairs_valid)}ペアのDXFファイルの比較が完了しました")
                    
                    # ダウンロードボタンを作成
                    st.download_button(
                        label="Excel比較結果をダウンロード",
                        data=excel_data,
                        file_name=output_filename,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
                    
                    # 一時ファイルの削除
                    for _, _, temp_file_a, temp_file_b, _ in temp_file_pairs:
                        try:
                            os.unlink(temp_file_a)
                            os.unlink(temp_file_b)
                        except:
                            pass
        
        except Exception as e:
            handle_error(e)
    else:
        st.warning("少なくとも1つのファイルペア（Aファイル、Bファイル）を登録してください。")

if __name__ == "__main__":
    app()
