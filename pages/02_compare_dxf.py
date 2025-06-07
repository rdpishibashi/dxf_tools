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
    
    # 出力ファイル名の設定
    # 推奨ファイル名の生成
    suggested_filename = None
    if uploaded_file_a is not None and uploaded_file_b is not None:
        suggested_filename = get_comparison_filename(uploaded_file_a.name, uploaded_file_b.name, 'diff')
    
    # ファイル名オプション
    if suggested_filename:
        use_suggested = st.checkbox(f"推奨ファイル名を使用: {suggested_filename}", value=False)
        if use_suggested:
            output_filename = suggested_filename
        else:
            output_filename = st.text_input("出力ファイル名", "diff.dxf")
    else:
        output_filename = st.text_input("出力ファイル名", "diff.dxf")
    if not output_filename.endswith('.dxf'):
        output_filename += '.dxf'
    
    # オプション設定
    with st.expander("オプション設定", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            # 許容誤差設定
            tolerance = st.number_input(
                "座標許容誤差", 
                min_value=1e-8, 
                max_value=1e-1, 
                value=0.01,
                format="%.8f",
                help="図面の位置座標の比較における許容誤差です。大きくすると微小な違いを無視します。"
            )
        
        with col2:
            st.write("**レイヤー色設定**")
            deleted_color = st.selectbox(
                "削除エンティティの色",
                options=[(1, "1 - 赤"), (2, "2 - 黄"), (3, "3 - 緑"), (4, "4 - シアン"), (5, "5 - 青"), (6, "6 - マゼンタ"), (7, "7 - 白/黒")],
                index=0,  # デフォルト: 赤
                format_func=lambda x: x[1]
            )[0]
            
            added_color = st.selectbox(
                "追加エンティティの色",
                options=[(1, "1 - 赤"), (2, "2 - 黄"), (3, "3 - 緑"), (4, "4 - シアン"), (5, "5 - 青"), (6, "6 - マゼンタ"), (7, "7 - 白/黒")],
                index=2,  # デフォルト: 緑
                format_func=lambda x: x[1]
            )[0]
            
            unchanged_color = st.selectbox(
                "変更なしエンティティの色",
                options=[(1, "1 - 赤"), (2, "2 - 黄"), (3, "3 - 緑"), (4, "4 - シアン"), (5, "5 - 青"), (6, "6 - マゼンタ"), (7, "7 - 白/黒")],
                index=3,  # デフォルト: シアン
                format_func=lambda x: x[1]
            )[0]
    
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
                        deleted_color=deleted_color,
                        added_color=added_color,
                        unchanged_color=unchanged_color
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
                        st.info(f"""
                        生成されたDXFファイルでは、以下のレイヤーで差分が表示されます：
                        - ADDED (色{added_color}): 比較対象ファイル(B)にのみ存在する要素
                        - DELETED (色{deleted_color}): 基準ファイル(A)にのみ存在する要素
                        - UNCHANGED (色{unchanged_color}): 両方のファイルに存在し変更がない要素
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
        
        # 機能説明
        with st.expander("機能の詳細", expanded=False):
            st.markdown("""
            ### 高精度DXF差分検出の特徴
            
            **1. INSERTエンティティ（ブロック）の自動展開**
            - ブロック参照を絶対座標に展開して比較
            - 挿入点、回転、スケールを考慮した変換
            - 階層構造を平坦化して正確な比較を実現
            
            **2. 高精度座標正規化**
            - 指定した許容誤差内の微小な違いを無視
            - エンティティタイプごとに最適化された許容誤差
            - テキスト位置、接続点などの特別処理
            
            **3. 包括的なエンティティ比較**
            - 座標だけでなく、レイヤー、色、サイズなども比較
            - エンティティの固有属性を考慮
            - テキスト内容の変更も検出
            """)

if __name__ == "__main__":
    app()