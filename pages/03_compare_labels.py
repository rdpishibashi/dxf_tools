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
                "機器符号（候補）のみ抽出", 
                value=False, 
                help="以下のパターンに一致するラベルのみを機器符号として抽出します："
                     "\n\n【基本パターン】"
                     "\n• 英文字のみ: CNCNT, FB"
                     "\n• 英文字+数字: R10, CN3, PSW1"  
                     "\n• 英文字+数字+英文字: X14A, RMSS2A"
                     "\n\n【括弧付きパターン】"
                     "\n• 英文字(補足): FB(), MSS(MOTOR)"
                     "\n• 英文字+数字(補足): R10(2.2K), MSSA(+)"
                     "\n• 英文字+数字+英文字(補足): U23B(DAC)"
                     "\n\n※英文字だけの場合は英文字2個以上、それ以外の場合は英文字1個以上、数字1個以上必要です"
            )
            
            # 機器符号妥当性チェックオプション（機器符号フィルタリングが有効な場合のみ表示）
            validate_ref_designators = False
            if filter_option:
                validate_ref_designators = st.checkbox(
                    "機器符号妥当性チェック", 
                    value=False,
                    help="抽出された機器符号がフォーマットに適合するかチェックします。"
                         "\n適合しない機器符号のリストを別シートに出力します。"
                         "\n（例：CBnnn, ELB(CB) nnn, R, Annn等の標準フォーマット）"
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
    help_text = [
        "このツールは、複数のDXFファイルペアからテキスト要素（ラベル）を抽出し、各ペアごとに比較結果をExcelファイルに出力します。",
        "",
        "**使用手順：**",
        "1. 各ファイルペアを登録してください（最大5ペア）",
        "2. 「出力Excelファイル名」を設定します",
        "3. 必要に応じてオプションを設定します",
        "4. 「ラベル差分を比較」ボタンをクリックして処理を実行します",
        "",
        "**Excelファイルの内容：**",
        "- 各ペアごとに個別のシートを作成",
        "- サマリーシートで全体の比較結果を表示",
        "- 各シートでは、ファイルAのみ、ファイルBのみ、両方に存在するが数が異なるラベルを色分けして表示"
    ]
    
    # 機器符号妥当性チェックが有効な場合の追加説明
    if filter_option and validate_ref_designators:
        help_text.extend([
            "",
            "**機器符号妥当性チェック：**",
            "- 適合しない機器符号を各ペアの「_Invalid」シートに出力",
            "- サマリーシートに適合しない機器符号の数を表示",
            "- 標準フォーマット（CBnnn, ELB(CB) nnn, R, Annn等）との適合性をチェック"
        ])
    
    st.info("\n".join(help_text))
    
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
                        sort_order=sort_value,
                        validate_ref_designators=validate_ref_designators
                    )
                    
                    # 結果を表示
                    success_message = f"{len(file_pairs_valid)}ペアのDXFファイルの比較が完了しました"
                    
                    # 処理オプションの情報を追加
                    option_info = []
                    if filter_option:
                        option_info.append("機器符号フィルタリング: 有効")
                        if validate_ref_designators:
                            option_info.append("機器符号妥当性チェック: 有効")
                    else:
                        option_info.append("機器符号フィルタリング: 無効")
                    
                    if sort_value != "none":
                        sort_text = "昇順" if sort_value == "asc" else "逆順"
                        option_info.append(f"並び替え: {sort_text}")
                    
                    if option_info:
                        success_message += f"\n（{', '.join(option_info)}）"
                    
                    st.success(success_message)
                    
                    # ダウンロードボタンを作成
                    download_label = "Excel比較結果をダウンロード"
                    if validate_ref_designators and filter_option:
                        download_label += " (妥当性チェック結果含む)"
                    
                    st.download_button(
                        label=download_label,
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