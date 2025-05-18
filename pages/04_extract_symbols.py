import streamlit as st
import os
import sys

# utils モジュールをインポート可能にするためのパスの追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.extract_symbols import extract_circuit_symbols, extract_assembly_number_from_filename
from common_utils import save_uploadedfile, get_output_filename, handle_error

def app():
    st.title('Excel回路記号抽出')
    st.write('ULKES Excelファイルから回路記号を抽出します。')
    
    # ファイルアップロードUI
    uploaded_file = st.file_uploader("Excelファイルをアップロード", type=["xlsx"], key="circuit_extractor")
    
    # 各種オプション設定
    col1, col2 = st.columns(2)
    
    with col1:
        # デフォルトのファイル名を設定
        default_filename = "circuit_symbols.txt"
        if uploaded_file is not None:
            default_filename = get_output_filename(uploaded_file.name, 'symbols')
            
        output_filename = st.text_input("出力ファイル名", default_filename)
        if not output_filename.endswith('.txt'):
            output_filename += '.txt'
    
    with col2:
        use_filename = st.checkbox("ファイル名にある図面番号を使用", value=True, 
                                   help="ファイル名から図面番号を自動抽出します。例：'ULKES構成_EE6312-000-01A.xlsx' から 'EE6312-000-01A' を抽出")
        assembly_number = None if use_filename else st.text_input("図面番号", "")
    
    # 追加オプション
    col3, col4 = st.columns(2)
    
    with col3:
        use_all_assemblies = st.checkbox("全ての可能な図面番号を使用", value=False, 
                                        help="Excelファイル内で検出できる部品を含む全ての図面番号に対して処理を行います。")
    
    with col4:
        include_maker_info = st.checkbox("メーカー情報を含める", value=False,
                                        help="出力にメーカー名とメーカー型式を含めます。CSVフォーマットになります。")
    
    # ヘルプ情報
    with st.expander("詳細情報"):
        st.markdown("""
        ### このツールについて
        このツールは、ULKES形式のExcelファイルから回路記号を抽出します。出力形式は以下のような特徴があります：
        
        1. 基本的に、各行の「符号」または「構成コメント」欄から回路記号を抽出します。
        2. 複数の回路記号が存在する場合は「_」（アンダースコア）で区切られます。
        3. 「構成数」（数量）に基づいて、不足分の回路記号は自動生成されます。
        4. メーカー情報を含める設定にすると、CSV形式で「回路記号,メーカー名,メーカー型式」の形式で出力されます。
        
        ### 図面番号とは
        図面番号は、Excelファイル内の「図面番号」列に記載される識別子で、通常「EE6312-000-01A」のような形式です。
        これは、その行以降の部品が属する対象図面を示します。
        
        - 「ファイル名にある図面番号を使用」オプションをONにすると、ファイル名から図面番号を自動抽出します。
          例：「ULKES構成_EE6312-000-01A.xlsx」から「EE6312-000-01A」を抽出。
        - 手動で図面番号を指定することも可能です。
        - 「全ての可能な図面番号を使用」オプションをONにすると、ファイル内に存在する全ての図面番号に対して処理を行います。
        """)
        
    if uploaded_file is not None:
        try:
            # ファイルが選択されたら処理ボタンを表示
            if st.button("回路記号を抽出"):
                # ファイルを一時ディレクトリに保存
                temp_file = save_uploadedfile(uploaded_file)
                
                with st.spinner('回路記号を抽出中...'):
                    # ファイル名からアセンブリ番号を取得
                    if use_filename:
                        assembly_number = extract_assembly_number_from_filename(uploaded_file.name)
                    
                    # 回路記号を抽出
                    symbols, info = extract_circuit_symbols(
                        temp_file,
                        assembly_number=assembly_number,
                        use_all_assemblies=use_all_assemblies,
                        include_maker_info=include_maker_info
                    )
                    
                    # 処理結果の表示
                    st.subheader("抽出結果")
                    
                    if info["error"]:
                        st.error(f"エラー: {info['error']}")
                    else:
                        st.info(f"図面番号: {info['assembly_number']}")
                        st.info(f"対象データ行数: {info['processed_rows']} / {info['total_rows']}")
                        st.info(f"抽出された回路記号数: {info['total_symbols']}")
                        
                        # 抽出された回路記号の表示
                        st.text_area("回路記号リスト", "\n".join(symbols), height=300)
                        
                        # ダウンロードボタンを作成
                        if symbols:
                            txt_str = "\n".join(symbols)
                            st.download_button(
                                label="テキストファイルをダウンロード",
                                data=txt_str.encode('utf-8'),
                                file_name=output_filename,
                                mime="text/plain",
                            )
                
                # 一時ファイルの削除
                try:
                    os.unlink(temp_file)
                except:
                    pass
        
        except Exception as e:
            handle_error(e)
    else:
        st.info("ULKESフォーマットのExcelファイルをアップロードしてください。")

if __name__ == "__main__":
    app()