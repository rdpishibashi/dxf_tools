import streamlit as st
import os
import sys
import traceback
import tempfile
import pandas as pd

# utils モジュールをインポート可能にするためのパスの追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.extract_symbols import extract_circuit_symbols
from common_utils import save_uploadedfile, get_output_filename, handle_error

def safe_save_uploadedfile(uploaded_file):
    """
    アップロードされたファイルを安全に保存する関数
    
    Args:
        uploaded_file: アップロードされたファイルオブジェクト
        
    Returns:
        str: 保存されたファイルのパス
    """
    try:
        # まず通常の方法で保存を試みる
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as f:
            f.write(uploaded_file.getbuffer())
            return f.name
    except Exception as e:
        st.warning(f"標準的な方法でのファイル保存に失敗しました: {str(e)}。代替方法を試みます。")
        try:
            # 代替方法: バイナリモードで開く
            temp_path = tempfile.mktemp(suffix=os.path.splitext(uploaded_file.name)[1])
            with open(temp_path, 'wb') as f:
                f.write(uploaded_file.getbuffer())
            return temp_path
        except Exception as e2:
            st.error(f"ファイル保存の代替方法も失敗しました: {str(e2)}")
            raise

def find_assembly_numbers(excel_path):
    """
    Excelファイルから利用可能な図面番号一覧を抽出する
    
    Args:
        excel_path: Excelファイルのパス
        
    Returns:
        list: 利用可能な図面番号のリスト
    """
    try:
        # まずopenpyxlでExcelを読み込む
        try:
            df = pd.read_excel(excel_path, engine='openpyxl')
        except Exception:
            # openpyxlが失敗したら他のエンジンを試す
            try:
                df = pd.read_excel(excel_path, engine='xlrd')
            except Exception:
                # 最後の手段
                df = pd.read_excel(excel_path, engine=None)
        
        # 図面番号列が存在するか確認
        if "図面番号" not in df.columns:
            # 大文字小文字の違いを無視して検索
            for col in df.columns:
                if col.lower() == "図面番号".lower():
                    df = df.rename(columns={col: "図面番号"})
                    break
        
        # 図面番号列がない場合
        if "図面番号" not in df.columns:
            return []
        
        # 利用可能な図面番号を検索
        possible_assemblies = []
        
        for i in range(len(df) - 1):  # 最後の行は次の行がないので対象外
            current_row = df.iloc[i]
            next_row = df.iloc[i + 1]
            
            # 現在の行に図面番号があり、次の行の図面番号が空白の場合
            if (pd.notna(current_row["図面番号"]) and 
                (pd.isna(next_row["図面番号"]) or str(next_row["図面番号"]).strip() == "")):
                # 有効な図面番号のみを追加（空白や特殊文字のみではないもの）
                assembly_no = str(current_row["図面番号"]).strip()
                if assembly_no and assembly_no not in possible_assemblies:
                    possible_assemblies.append(assembly_no)
        
        return possible_assemblies
    except Exception as e:
        st.error(f"図面番号抽出中にエラーが発生しました: {str(e)}")
        return []

def app():
    st.title('Excel機器符号抽出')
    st.write('ULKES Excelファイルから機器符号を抽出します。')
    
    # ファイルアップロードUI
    uploaded_file = st.file_uploader("Excelファイルをアップロード", type=["xlsx"], key="circuit_extractor")
    
    # ファイルがアップロードされた場合
    if uploaded_file is not None:
        try:
            with st.spinner('ファイルを解析中...'):
                # ファイルを一時保存
                temp_file = safe_save_uploadedfile(uploaded_file)
                
                # 図面番号を抽出
                assembly_numbers = find_assembly_numbers(temp_file)
                
                if not assembly_numbers:
                    st.warning("図面番号が見つかりませんでした。ファイル形式を確認してください。")
                    try:
                        os.unlink(temp_file)
                    except:
                        pass
                    return
            
            # 図面番号の選択UI
            st.subheader("処理する図面番号の選択")
            st.write(f"ファイル内に {len(assembly_numbers)} 個の図面番号が見つかりました。")
            
            # セッション状態の初期化（選択状態を保持するため）
            if 'selected_assemblies' not in st.session_state:
                st.session_state.selected_assemblies = {assembly: True for assembly in assembly_numbers}
            
            # 全選択/全解除ボタン
            col1, col2 = st.columns([1, 3])
            with col1:
                if st.button("全て選択"):
                    for assembly in assembly_numbers:
                        st.session_state.selected_assemblies[assembly] = True
            
            with col2:
                if st.button("全て解除"):
                    for assembly in assembly_numbers:
                        st.session_state.selected_assemblies[assembly] = False
            
            # 各図面番号のチェックボックスを3列で表示
            st.write("処理する図面番号をチェックしてください:")
            
            # 図面番号を3列に分けて表示
            cols = st.columns(3)
            
            for i, assembly in enumerate(assembly_numbers):
                with cols[i % 3]:
                    st.session_state.selected_assemblies[assembly] = st.checkbox(
                        assembly,
                        value=st.session_state.selected_assemblies.get(assembly, True),
                        key=f"checkbox_{assembly}"
                    )
            
            # 選択された図面番号のリスト
            selected_assemblies = [
                assembly for assembly in assembly_numbers 
                if st.session_state.selected_assemblies.get(assembly, False)
            ]
            
            # 出力オプション
            st.subheader("出力オプション")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # デフォルトのファイル名を設定
                default_filename = "circuit_symbols.txt"
                if selected_assemblies:
                    # 最初に選択された図面番号をベースに出力ファイル名を設定
                    default_filename = f"{selected_assemblies[0]}_symbols.txt"
                else:
                    # 選択がない場合は最初の図面番号を使用
                    default_filename = f"{assembly_numbers[0]}_symbols.txt" if assembly_numbers else "circuit_symbols.txt"
                
                output_filename = st.text_input("出力ファイル名", default_filename)
                if not output_filename.endswith('.txt'):
                    output_filename += '.txt'
            
            with col2:
                include_maker_info = st.checkbox("メーカー情報を含める", value=False,
                                                help="出力にメーカー名とメーカー型式を含めます。CSVフォーマットになります。")
            
            # 処理実行ボタン
            if len(selected_assemblies) == 0:
                st.warning("少なくとも1つの図面番号を選択してください。")
            else:
                if st.button("機器符号を抽出"):
                    try:
                        # 選択された図面番号ごとに機器符号を抽出
                        all_symbols = []
                        total_processed_rows = 0
                        total_symbols = 0
                        
                        with st.spinner('機器符号を抽出中...'):
                            # 処理結果の表示用プログレスバー
                            progress_bar = st.progress(0)
                            
                            # 各図面番号に対して処理
                            for i, assembly_number in enumerate(selected_assemblies):
                                # 処理進捗の更新
                                progress = (i) / len(selected_assemblies)
                                progress_bar.progress(progress)
                                
                                # 現在処理中の図面番号を表示
                                status_text = st.empty()
                                status_text.info(f"処理中: {assembly_number} ({i+1}/{len(selected_assemblies)})")
                                
                                # 図面番号を指定して機器符号を抽出
                                symbols, info = extract_circuit_symbols(
                                    temp_file,
                                    assembly_number=assembly_number,
                                    use_all_assemblies=False,  # 常にFalse（個別処理）
                                    include_maker_info=include_maker_info
                                )
                                
                                # エラーがなければ結果を追加
                                if not info["error"]:
                                    all_symbols.extend(symbols)
                                    total_processed_rows += info["processed_rows"]
                                    total_symbols += info["total_symbols"]
                                else:
                                    st.warning(f"図面番号 '{assembly_number}' の処理中にエラーが発生しました: {info['error']}")
                            
                            # 進捗バーを完了
                            progress_bar.progress(1.0)
                            status_text.empty()
                        
                        # 処理結果の表示
                        st.subheader("抽出結果")
                        st.success(f"処理完了！ {len(selected_assemblies)} 個の図面番号を処理しました。")
                        st.info(f"処理した図面番号: {', '.join(selected_assemblies)}")
                        st.info(f"対象データ行数: {total_processed_rows}")
                        st.info(f"抽出された機器符号数: {len(all_symbols)}")
                        
                        # 抽出された機器符号の表示
                        st.text_area("機器符号リスト", "\n".join(all_symbols), height=300)
                        
                        # ダウンロードボタンを作成
                        if all_symbols:
                            txt_str = "\n".join(all_symbols)
                            st.download_button(
                                label="テキストファイルをダウンロード",
                                data=txt_str.encode('utf-8'),
                                file_name=output_filename,
                                mime="text/plain",
                            )
                    
                    except Exception as e:
                        st.error(f"処理中にエラーが発生しました: {str(e)}")
                        st.error(traceback.format_exc())
            
            # 一時ファイルの削除は処理終了時のみ
            # ページが再読み込みされると、新たにファイルが生成されるため
        
        except Exception as e:
            st.error(f"ファイル処理中に予期しないエラーが発生しました: {str(e)}")
            st.error(traceback.format_exc())
    else:
        st.info("ULKESフォーマットのExcelファイルをアップロードしてください。")

if __name__ == "__main__":
    app()