import streamlit as st
import os
import sys
import traceback

# utils モジュールをインポート可能にするためのパスの追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.compare_partslist import compare_parts_list_multi
from common_utils import save_uploadedfile, get_comparison_filename, handle_error

def app():
    st.title('機器符号リスト差分抽出')
    st.write('複数の機器符号リストのペアを比較し、差分をExcel形式で出力します。')
    
    # オプション設定
    with st.expander("オプション設定", expanded=True):
        # 出力ファイル名設定
        output_filename = st.text_input("出力Excelファイル名", "partslist_diff_result.xlsx")
        if not output_filename.endswith('.xlsx'):
            output_filename += '.xlsx'
    
    # ファイルペア登録UI
    st.subheader("ファイル・ペアの登録")
    st.write("最大5ペアの機器符号リストファイルを登録できます")
    
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
        with st.expander(f"ファイル・ペア {i+1}", expanded=i==0):
            col1, col2, col3 = st.columns([2, 2, 1])
            
            with col1:
                uploaded_file_a = st.file_uploader(
                    f"機器符号リスト・ファイルA {i+1}", 
                    type=["txt", "csv"], 
                    key=f"partslist_a_{i}"
                )
                if uploaded_file_a:
                    st.session_state.file_pairs[i]['fileA'] = uploaded_file_a
                
            with col2:
                uploaded_file_b = st.file_uploader(
                    f"機器符号リスト・ファイルB {i+1}", 
                    type=["txt", "csv"], 
                    key=f"partslist_b_{i}"
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
    このツールは、複数の機器符号リストのファイル・ペアを比較し、各ペアごとに比較結果をExcelファイルに出力します。
    
    1. 各ファイル・ペアを登録してください（最大5ペア）
    2. 「出力Excelファイル名」を設定します
    3. 「機器符号リストを比較」ボタンをクリックして処理を実行します
    
    入力ファイルは以下の形式に対応しています：
    - 1行に1つの機器符号が記載されたテキストファイル
    - CSVフォーマットの場合、1行目が機器符号、2列目がメーカー名、3列目が製品名として処理されます
    
    Excelファイルは以下の内容を含みます：
    - 各ペアごとに個別のシートを作成
    - サマリーシートで全体の比較結果を表示
    - 各シートでは、ファイルAのみ、ファイルBのみ、両方に存在するが数が異なるラベルを色分けして表示
    """)
    
    if file_pairs_valid:
        try:
            # ファイルが選択されたら処理ボタンを表示
            if st.button("機器符号リストを比較", disabled=len(file_pairs_valid) == 0):
                # 全てのファイルを一時ディレクトリに保存
                with st.spinner('機器符号リストファイルを処理中...'):
                    temp_file_pairs = []
                    
                    # ファイルの保存とペア情報の作成
                    # 元のファイル名を維持するために仕組みを変更
                    for file_a, file_b, pair_name in file_pairs_valid:
                        # 一時ファイルを保存
                        temp_file_a = save_uploadedfile(file_a)
                        temp_file_b = save_uploadedfile(file_b)
                        
                        # ファイル名情報を保持するために.nameを使う
                        real_file_a = temp_file_a
                        real_file_b = temp_file_b
                        
                        # ファイル名を追加 - 一時ファイルパスは使うが、シート表示用のファイル名はオリジナルのものに
                        # ファイル名を変更
                        try:
                            # ディレクトリとファイル名を分離
                            dir_a = os.path.dirname(temp_file_a)
                            dir_b = os.path.dirname(temp_file_b)
                            
                            # 元のファイル名を取得
                            orig_name_a = file_a.name
                            orig_name_b = file_b.name
                            
                            # シンボリックリンクではなく、ファイル名を変更した新しい一時ファイルパスを作成
                            new_temp_file_a = os.path.join(dir_a, f"orig_{orig_name_a}")
                            new_temp_file_b = os.path.join(dir_b, f"orig_{orig_name_b}")
                            
                            # ファイル名を変更してコピー
                            os.rename(temp_file_a, new_temp_file_a)
                            os.rename(temp_file_b, new_temp_file_b)
                            
                            # 新しいパスを使用
                            real_file_a = new_temp_file_a
                            real_file_b = new_temp_file_b
                        except Exception as e:
                            st.warning(f"ファイル名の変更中にエラーが発生しました: {str(e)}")
                            # エラーがあっても継続、元のパスを使用
                            real_file_a = temp_file_a
                            real_file_b = temp_file_b
                        
                        temp_file_pairs.append((real_file_a, real_file_b, pair_name))
                    
                    try:
                        # Excel出力を生成
                        excel_data = compare_parts_list_multi(temp_file_pairs)
                        
                        if excel_data is None:
                            st.error("Excel出力の生成に失敗しました。データがNoneとして返されました。")
                        else:
                            # 結果を表示
                            st.success(f"{len(file_pairs_valid)}ペアの機器符号リストの比較が完了しました")
                            
                            # ダウンロードボタンを作成
                            st.download_button(
                                label="Excel比較結果をダウンロード",
                                data=excel_data,
                                file_name=output_filename,
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            )
                    except Exception as e:
                        st.error(f"処理中にエラーが発生しました: {str(e)}")
                        st.text(traceback.format_exc())
                    
                    # 一時ファイルの削除
                    for file_a, file_b, _ in temp_file_pairs:
                        try:
                            if os.path.exists(file_a):
                                os.unlink(file_a)
                            if os.path.exists(file_b):
                                os.unlink(file_b)
                        except Exception as e:
                            st.warning(f"一時ファイルの削除中にエラー: {str(e)}")
        
        except Exception as e:
            handle_error(e)
    else:
        st.warning("少なくとも1つのファイル・ペア（Aファイル、Bファイル）を登録してください。")

if __name__ == "__main__":
    app()