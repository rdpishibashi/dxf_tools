import streamlit as st
import os
import tempfile
import sys

# utils モジュールをインポート可能にするためのパスの追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.compare_dxf import compare_dxf_files_and_generate_dxf
from common_utils import save_uploadedfile, get_comparison_filename, handle_error

def app():
    st.title('図面差分抽出')
    st.write('2つのDXFファイルを比較し、差分をDXFフォーマットで出力します。')
    
    # ファイルアップロードUI
    col1, col2 = st.columns(2)
    
    with col1:
        uploaded_file_a = st.file_uploader("基準DXFファイル (A)", type="dxf", key="dxf_a")
    
    with col2:
        uploaded_file_b = st.file_uploader("比較対象DXFファイル (B)", type="dxf", key="dxf_b")
    
    # デフォルトのファイル名を設定
    default_filename = "diff.dxf"
    if uploaded_file_a is not None and uploaded_file_b is not None:
        default_filename = get_comparison_filename(uploaded_file_a.name, uploaded_file_b.name, 'diff')
        
    output_filename = st.text_input("出力ファイル名", default_filename)
    if not output_filename.endswith('.dxf'):
        output_filename += '.dxf'
    
    # 許容誤差設定
    tolerance = st.slider("許容誤差", min_value=1e-8, max_value=1e-1, value=1e-6, format="%.8f",
                          help="図面の位置座標の比較における許容誤差です。大きくすると微小な違いを無視します。")
    
    # Y方向オフセット設定（必要に応じて表示）
    y_offset = st.number_input("Y方向オフセット (mm)", 
                               min_value=-1000.0, max_value=1000.0, value=0.0, step=1.0,
                               help="比較対象ファイル(B)のY座標に適用するオフセット値です。図面がY方向にずれている場合に調整できます。")
    
    if uploaded_file_a is not None and uploaded_file_b is not None:
        try:
            # ファイルが選択されたら処理ボタンを表示
            if st.button("差分を比較"):
                # ファイルを一時ディレクトリに保存
                temp_file_a = save_uploadedfile(uploaded_file_a)
                temp_file_b = save_uploadedfile(uploaded_file_b)
                temp_output = tempfile.NamedTemporaryFile(delete=False, suffix=".dxf").name
                
                with st.spinner('DXFファイルを比較中...'):
                    result = compare_dxf_files_and_generate_dxf(
                        temp_file_a, 
                        temp_file_b, 
                        temp_output,
                        tolerance=tolerance,
                        y_offset_for_file_b=y_offset
                    )
                    
                    if result:
                        st.success("DXFファイルの比較が完了しました")
                        
                        # 結果ファイルを読み込んでダウンロードボタンを作成
                        with open(temp_output, 'rb') as f:
                            dxf_data = f.read()
                            
                        st.download_button(
                            label="差分DXFファイルをダウンロード",
                            data=dxf_data,
                            file_name=output_filename,
                            mime="application/dxf",
                        )
                        
                        # 差分情報の表示
                        st.info("""
                        生成されたDXFファイルでは、以下のレイヤーで差分が表示されます：
                        - ADDED (緑色): 比較対象ファイル(B)にのみ存在する要素
                        - REMOVED (赤色): 基準ファイル(A)にのみ存在する要素
                        - MODIFIED (青色): 両方のファイルに存在するが変更がある要素
                        - UNCHANGED (白色): 両方のファイルに存在し変更がない要素
                        """)
                    else:
                        st.error("DXFファイルの比較に失敗しました")
                
                # 一時ファイルの削除
                try:
                    os.unlink(temp_file_a)
                    os.unlink(temp_file_b)
                    os.unlink(temp_output)
                except:
                    pass
                
        except Exception as e:
            handle_error(e)
    else:
        st.info("基準ファイル(A)と比較対象ファイル(B)をアップロードしてください。")

if __name__ == "__main__":
    app()