import streamlit as st
import pandas as pd
import io
import tempfile
import os
import sys
import traceback

# モジュールのインポート
from utils.extract_labels import extract_labels, get_layers_from_dxf
from utils.analyze_structure import analyze_dxf_structure, get_default_output_filename
from utils.extract_hierarchy import extract_hierarchy
from utils.compare_dxf import compare_dxf_files_and_generate_dxf
from utils.compare_labels import compare_labels
from utils.extract_symbols import extract_circuit_symbols
from utils.compare_partslist import compare_parts_list, normalize_label

def save_uploadedfile(uploadedfile):
    """アップロードされたファイルを一時ディレクトリに保存する"""
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploadedfile.name)[1]) as f:
        f.write(uploadedfile.getbuffer())
        return f.name

def create_download_link(data, filename, text="Download file"):
    """ダウンロード用のリンクを生成する"""
    from base64 import b64encode
    b64 = b64encode(data).decode()
    href = f'<a href="data:file/octet-stream;base64,{b64}" download="{filename}">{text}</a>'
    return href

def main():
    st.set_page_config(
        page_title="DXF file Analysis Tools",
        page_icon="📊",
        layout="wide",
    )
    
    st.title('DXF file Analysis Tools')
    st.write('CADのDXFファイルを分析・比較するツールです。')
    
    # メニュー順序を元の順序に合わせる
    tool_selection = st.sidebar.radio(
        'ツールを選択',
        [
            '図面ラベル抽出', 
            '構造分析（Excel出力）', 
            '構造分析（テキスト出力）', 
            '図面差分抽出', 
            '図面ラベル差分抽出',
            'Excel回路記号抽出',
            '回路記号リスト差分抽出'
        ]
    )

    if tool_selection == '図面ラベル抽出':
	    st.header('DXFファイルからラベルを抽出')
	    uploaded_file = st.file_uploader("DXFファイルをアップロード", type="dxf", key="label_extractor")
	    
	    # デフォルトのファイル名を設定
	    default_filename = "labels.txt"
	    if uploaded_file is not None:
	        default_filename = os.path.splitext(uploaded_file.name)[0] + ".txt"
	        
	    output_filename = st.text_input("出力ファイル名", default_filename)
	    if not output_filename.endswith('.txt'):
	        output_filename += '.txt'
	    
	    # 新しいオプション
	    col1, col2 = st.columns(2)
	    with col1:
	        filter_option = st.checkbox(
	            "回路記号（候補）のみ抽出", 
	            value=False, 
	            help="以下の条件に合致するラベルは回路記号でないと判断して除外します："
	                 "\n- 最初の文字が「(」（例：(BK), (M5)）"
	                 "\n- 最初の文字が数字（例：2.1+, 500DJ）"
	                 "\n- 英大文字だけで2文字以下（E, L, PE）"
	                 "\n- 英大文字１文字に続いて数字（例：R1, T2）"
	                 "\n- 英大文字１文字に続いて数字と「.」からなる文字列（例：L1.1, P01）"
	                 "\n- 英字と「+」もしくは「-」の組み合わせ（例：P+, VCC-）"
	                 "\n- 「GND」を含む（例：GND, GND(M4)）"
	                 "\n- 「AWG」ではじまるラベル（例：AWG14, AWG18）"
	                 "\n- 英単語（＋数字）と空白からなるラベル（例：on ..., CB BOX FX3）"
	                 "\n- 「☆」ではじまるラベル"
	                 "\n- 「注」ではじまるラベル"
	                 "\n- ラベルの文字列中の「(」ではじまり「)」で閉じる文字列部分を削除"
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
	        
	    debug_option = st.checkbox("デバッグ情報を表示", value=False, help="フィルタリングの詳細情報を表示します。")
	        
	    if uploaded_file is not None:
	        try:
	            # ファイルを一時ディレクトリに保存
	            temp_file = save_uploadedfile(uploaded_file)
	            
	            # レイヤー一覧を取得
	            with st.spinner('レイヤー情報を読み込み中...'):
	                layers = get_layers_from_dxf(temp_file)
	            
	            if layers:
	                st.subheader("レイヤー選択")
	                
	                # 全選択/全解除のトグルスイッチ
	                col3, col4 = st.columns([1, 3])
	                with col3:
	                    select_all = st.button("全選択")
	                    
	                with col4:
	                    deselect_all = st.button("全解除")
	                
	                # セッション状態の初期化と更新
	                if 'layer_states' not in st.session_state:
	                    st.session_state.layer_states = {}
	                
	                # 現在のレイヤーをセッション状態に追加（存在しない場合のみ）
	                for layer in layers:
	                    if layer not in st.session_state.layer_states:
	                        st.session_state.layer_states[layer] = True  # デフォルトで選択状態
	                
	                # 全選択/全解除ボタンの処理
	                if select_all:
	                    for layer in layers:
	                        st.session_state.layer_states[layer] = True
	                elif deselect_all:
	                    for layer in layers:
	                        st.session_state.layer_states[layer] = False
	                
	                # 各レイヤーのチェックボックス
	                selected_layers = []
	                
	                # 3列表示に変更
	                layer_cols = st.columns(3)
	                
	                for i, layer in enumerate(layers):
	                    col_index = i % 3
	                    with layer_cols[col_index]:
	                        # チェックボックスを表示
	                        is_selected = st.checkbox(layer, value=st.session_state.layer_states[layer], key=f"layer_{layer}")
	                        st.session_state.layer_states[layer] = is_selected
	                        
	                        if is_selected:
	                            selected_layers.append(layer)
	            
	            if st.button("ラベルを抽出"):
	                if not layers or not selected_layers:
	                    st.warning("レイヤーが選択されていないか、DXFファイルにレイヤーが存在しません。")
	                else:
	                    with st.spinner('ラベルを抽出中...'):
	                        labels, info = extract_labels(
	                            temp_file, 
	                            filter_non_parts=filter_option, 
	                            sort_order=sort_value, 
	                            debug=debug_option,
	                            selected_layers=selected_layers  # 選択されたレイヤーを渡す
	                        )
	                        
	                        # 結果を表示
	                        st.subheader("抽出されたラベル")
	                        
	                        # レイヤー処理情報の表示
	                        st.info(f"処理対象レイヤー: {info['processed_layers']} / {info['total_layers']}")
	                        
	                        # 処理情報の表示
	                        st.info(f"元の抽出ラベル総数: {info['total_extracted']}")
	                        
	                        if filter_option:
	                            st.info(f"フィルタリングで除外したラベル数: {info['filtered_count']}")
	                        
	                        st.info(f"最終的なラベル数: {info['final_count']}")
	                        
	                        if sort_value != "none":
	                            sort_text = "昇順" if sort_value == "asc" else "逆順"
	                            st.info(f"ラベルを{sort_text}で並び替えました")
	                        
	                        # ラベル一覧
	                        st.text_area("ラベル一覧", "\n".join(labels), height=300)
	                        
	                        # ダウンロードボタンを作成
	                        if labels:
	                            txt_str = "\n".join(labels)
	                            st.download_button(
	                                label="テキストファイルをダウンロード",
	                                data=txt_str.encode('utf-8'),
	                                file_name=output_filename,
	                                mime="text/plain",
	                            )
	                
	                # 一時ファイルの削除
	                os.unlink(temp_file)
	        
	        except Exception as e:
	            st.error(f"エラーが発生しました: {str(e)}")
	            st.error(traceback.format_exc())

    elif tool_selection == '構造分析（Excel出力）':
            st.header('DXFデータ構造を分析しExcelファイルに出力')
            uploaded_file = st.file_uploader("DXFファイルをアップロード", type="dxf", key="structure_analyzer")
            
            # デフォルトのファイル名を設定
            default_filename = "structure.xlsx"
            if uploaded_file is not None:
                default_filename = get_default_output_filename(uploaded_file.name, 'xlsx')
                    
            output_filename = st.text_input("出力ファイル名", default_filename)
            if not output_filename.endswith('.xlsx') and not output_filename.endswith('.csv'):
                output_filename += '.xlsx'
            
            # セクション分割オプション
            use_split = st.checkbox("セクションごとに分割して保存", value=False, 
                                  help="ONにすると、HEADER, BLOCKS, ENTITIES などのセクションごとに別ファイルに分割されます。")
            
            # CSV強制オプション
            use_csv = st.checkbox("CSV形式で保存", value=False, 
                                help="ONにすると、Excel形式ではなくCSV形式で保存されます。")
                    
            if uploaded_file is not None:
                try:
                    # ファイルを一時ディレクトリに保存
                    temp_file = save_uploadedfile(uploaded_file)
                    
                    if st.button("構造を分析"):
                        # セッションステートに保存して分析結果を保持
                        if 'structure_data' not in st.session_state:
                            st.session_state.structure_data = None
                        if 'structure_sections' not in st.session_state:
                            st.session_state.structure_sections = None
                        if 'structure_df' not in st.session_state:
                            st.session_state.structure_df = None
                        
                        with st.spinner('DXFデータ構造を分析中...'):
                            data = analyze_dxf_structure(temp_file)
                            # 全ての列が適切なデータ型であることを確認
                            df = pd.DataFrame(data, columns=['Section', 'Entity Marker', 'Entity', 'GroupCode', 'GroupCode Definition', 'Value'])
                            
                            # GroupCode 列のデータ型を確認して、必要に応じて文字列に変換
                            df['GroupCode'] = df['GroupCode'].astype(str)
                            
                            # セッションステートに保存
                            st.session_state.structure_data = data
                            st.session_state.structure_df = df
                            
                            # セクション情報を取得して保存
                            sections = df['Section'].unique()
                            st.session_state.structure_sections = sections
                            
                            # 結果をデータフレームとして表示
                            st.subheader("構造分析結果")
                            st.dataframe(df, height=400)
                            
                            # データのサイズをチェック
                            row_count = len(df)
                            st.info(f"抽出されたデータ: {row_count} 行")
                            
                            # Excel行数制限をチェック
                            EXCEL_ROW_LIMIT = 1000000
                            if row_count > EXCEL_ROW_LIMIT and not use_csv:
                                st.warning(f"データが大きすぎるため ({row_count} 行 > {EXCEL_ROW_LIMIT} 行制限)、Excel形式での保存が難しい場合があります。CSV形式での保存をお勧めします。")
                        
                        # 一時ファイルの削除
                        os.unlink(temp_file)
                    
                    # 分析結果が存在する場合、ダウンロードオプションを表示
                    if hasattr(st.session_state, 'structure_df') and st.session_state.structure_df is not None:
                        df = st.session_state.structure_df
                        
                        # 出力形式を決定
                        file_ext = os.path.splitext(output_filename)[1].lower()
                        is_csv_output = use_csv or file_ext == '.csv' or len(df) > 1000000  # Excel行数制限
                        
                        if use_split:
                            # セクションごとに分割して保存
                            st.subheader("セクション選択")
                            st.info("選択したセクションをまとめてダウンロードします。2つ以上選択するとZIPアーカイブになります。")
                            
                            # セクション情報を取得
                            sections = st.session_state.structure_sections
                            
                            # セクション選択用のチェックボックス（デフォルトですべてON）
                            col1, col2 = st.columns([1, 3])
                            
                            with col1:
                                select_all = st.button("全選択")
                            
                            with col2:
                                deselect_all = st.button("全解除")
                            
                            # セッションステートでチェックボックスの状態を管理
                            if 'section_states' not in st.session_state:
                                st.session_state.section_states = {section: True for section in sections}
                            
                            if select_all:
                                for section in sections:
                                    st.session_state.section_states[section] = True
                            
                            if deselect_all:
                                for section in sections:
                                    st.session_state.section_states[section] = False
                            
                            # セクション選択用チェックボックスを3列で表示
                            section_cols = st.columns(3)
                            
                            selected_sections = {}
                            for i, section in enumerate(sections):
                                col_index = i % 3
                                with section_cols[col_index]:
                                    selected = st.checkbox(
                                        f"{section}", 
                                        value=st.session_state.section_states.get(section, True),
                                        key=f"section_{section}"
                                    )
                                    selected_sections[section] = selected
                                    st.session_state.section_states[section] = selected
                            
                            # 選択されたセクションのリスト
                            sections_to_download = [section for section, selected in selected_sections.items() if selected]
                            
                            if sections_to_download:
                                # ダウンロードセクション
                                st.subheader("ダウンロード")
                                
                                # ファイル形式表示
                                file_format = "CSV" if is_csv_output else "Excel"
                                base_name = os.path.splitext(output_filename)[0]
                                
                                # 選択セクション数を表示
                                st.info(f"選択されたセクション: {len(sections_to_download)}/{len(sections)}")
                                
                                # 一括ダウンロード処理
                                if len(sections_to_download) > 0:
                                    if len(sections_to_download) == 1:
                                        # 1つのセクションのみの場合は単一ファイルでダウンロード
                                        section = sections_to_download[0]
                                        section_safe = section.replace('(', '_').replace(')', '').replace(' ', '_')
                                        
                                        if is_csv_output:
                                            section_filename = f"{base_name}_{section_safe}.csv"
                                            # ダウンロードボタンが押されたらCSVを生成してダウンロード
                                            download_button_key = f"csv_dl_{section_safe}"
                                            
                                            # 単一ボタンでCSVファイルを生成・ダウンロード
                                            if st.download_button(
                                                label=f"{section} - CSVファイルをダウンロード",
                                                data=df[df['Section'] == section].to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig'),
                                                file_name=section_filename,
                                                mime="text/csv",
                                                key=download_button_key
                                            ):
                                                st.success(f"{section}のCSVファイルをダウンロードしました")
                                        else:
                                            section_filename = f"{base_name}_{section_safe}.xlsx"
                                            
                                            # Excelファイルを生成
                                            try:
                                                section_df = df[df['Section'] == section]
                                                output = io.BytesIO()
                                                
                                                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                                                    section_df.to_excel(writer, index=False, sheet_name=f'{section}'[:31])  # シート名の長さ制限
                                                
                                                # 単一ボタンでExcelファイルをダウンロード
                                                if st.download_button(
                                                    label=f"{section} - Excelファイルをダウンロード",
                                                    data=output.getvalue(),
                                                    file_name=section_filename,
                                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                                    key=f"excel_dl_{section_safe}"
                                                ):
                                                    st.success(f"{section}のExcelファイルをダウンロードしました")
                                            except Exception as e:
                                                st.error(f"Excelファイルの作成中にエラーが発生しました: {str(e)}")
                                                # エラー時にはCSVでの代替方法を提供
                                                alt_section_filename = f"{base_name}_{section_safe}.csv"
                                                if st.download_button(
                                                    label=f"{section} - 代替CSVファイルをダウンロード",
                                                    data=df[df['Section'] == section].to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig'),
                                                    file_name=alt_section_filename,
                                                    mime="text/csv",
                                                    key=f"alt_csv_dl_{section_safe}"
                                                ):
                                                    st.success(f"{section}のCSVファイルをダウンロードしました")
                                    else:
                                        # 複数のセクションが選択されている場合はZIPアーカイブを作成
                                        # ZIPファイル名を設定
                                        zip_filename = f"{base_name}_sections.zip"
                                        
                                        # ZIPアーカイブ生成とダウンロードを1ステップで行う
                                        if st.button(f"選択した {len(sections_to_download)} セクションをZIPアーカイブで作成・ダウンロード"):
                                            # ボタン押下時にZIPアーカイブを作成
                                            import zipfile
                                            
                                            # 進捗表示のコンテナ
                                            progress_container = st.container()
                                            
                                            # ステータスバーの表示
                                            with progress_container:
                                                status_text = st.empty()
                                                progress_bar = st.progress(0)
                                                status_text.text("ZIPアーカイブの作成を開始します...")
                                            
                                            try:
                                                # ZIPファイル用のメモリバッファを作成
                                                zip_buffer = io.BytesIO()
                                                
                                                # ZIPファイルを作成
                                                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
                                                    for i, section in enumerate(sections_to_download):
                                                        # 進捗状況の更新
                                                        progress = (i + 1) / len(sections_to_download)
                                                        progress_bar.progress(progress)
                                                        status_text.text(f"処理中... {i+1}/{len(sections_to_download)}: {section}")
                                                        
                                                        # セクションデータの取得
                                                        section_df = df[df['Section'] == section]
                                                        
                                                        # セクション名から括弧などを取り除いてファイル名に適した形式に変換
                                                        section_safe = section.replace('(', '_').replace(')', '').replace(' ', '_')
                                                        
                                                        if is_csv_output:
                                                            # CSVファイルを作成
                                                            section_filename = f"{base_name}_{section_safe}.csv"
                                                            csv_data = section_df.to_csv(index=False, encoding='utf-8-sig')
                                                            zf.writestr(section_filename, csv_data)
                                                        else:
                                                            # Excelファイルを作成
                                                            section_filename = f"{base_name}_{section_safe}.xlsx"
                                                            excel_buffer = io.BytesIO()
                                                            try:
                                                                with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
                                                                    section_df.to_excel(writer, index=False, sheet_name=f'{section}'[:31])
                                                                excel_buffer.seek(0)
                                                                zf.writestr(section_filename, excel_buffer.getvalue())
                                                            except Exception as e:
                                                                # Excel保存に失敗した場合はCSVとして保存
                                                                status_text.warning(f"セクション '{section}' のExcelファイル作成に失敗しました。CSV形式で保存します。")
                                                                csv_filename = f"{base_name}_{section_safe}.csv"
                                                                csv_data = section_df.to_csv(index=False, encoding='utf-8-sig')
                                                                zf.writestr(csv_filename, csv_data)
                                                
                                                # 進捗表示を完了状態にする
                                                progress_bar.progress(1.0)
                                                status_text.text("ZIPアーカイブの作成が完了しました！")
                                                
                                                # ZIPファイルのダウンロードを自動的に行う
                                                st.success(f"ZIPアーカイブを作成しました（{len(sections_to_download)}個のファイルが含まれています）")
                                                
                                                # ダウンロードボタンを表示（直接ダウンロードさせる）
                                                st.download_button(
                                                    label="ZIPアーカイブをダウンロード",
                                                    data=zip_buffer.getvalue(),
                                                    file_name=zip_filename,
                                                    mime="application/zip",
                                                    key="zip_download"
                                                )
                                            except Exception as e:
                                                st.error(f"ZIPアーカイブ作成中にエラーが発生しました: {str(e)}")
                                                st.error(traceback.format_exc())
                            else:
                                st.warning("ダウンロードするセクションを選択してください。")
                        else:
                            # 全データを1つのファイルに保存
                            st.subheader("ダウンロード")
                            
                            if is_csv_output:
                                # CSV形式で保存 - 直接ダウンロードボタンを表示
                                csv_filename = output_filename if output_filename.endswith('.csv') else os.path.splitext(output_filename)[0] + '.csv'
                                csv_data = df.to_csv(index=False, encoding='utf-8-sig')
                                
                                # 1ステップでCSVファイルをダウンロード
                                if st.download_button(
                                    label="CSVファイルをダウンロード",
                                    data=csv_data.encode('utf-8-sig'),
                                    file_name=csv_filename,
                                    mime="text/csv",
                                    key="csv_download_all"
                                ):
                                    st.success("CSVファイルをダウンロードしました")
                            else:
                                # Excel形式で保存
                                excel_filename = output_filename if output_filename.endswith('.xlsx') else os.path.splitext(output_filename)[0] + '.xlsx'
                                
                                # データサイズが大きい場合は警告
                                if len(df) > 1000000:
                                    st.warning("データサイズが大きいため、Excel形式での保存に失敗する可能性があります。CSV形式での保存をお勧めします。")
                                
                                try:
                                    # Excelファイルを生成
                                    output = io.BytesIO()
                                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                                        df.to_excel(writer, index=False, sheet_name='DXF構造')
                                    
                                    # 1ステップでExcelファイルをダウンロード
                                    if st.download_button(
                                        label="Excelファイルをダウンロード",
                                        data=output.getvalue(),
                                        file_name=excel_filename,
                                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                        key="excel_download_all"
                                    ):
                                        st.success("Excelファイルをダウンロードしました")
                                except Exception as e:
                                    st.error(f"Excelファイルの作成中にエラーが発生しました: {str(e)}")
                                    
                                    # 代替のCSVダウンロードを提供
                                    alt_csv_filename = os.path.splitext(output_filename)[0] + '.csv'
                                    csv_data = df.to_csv(index=False, encoding='utf-8-sig')
                                    
                                    st.info("代わりにCSV形式で保存してください。")
                                    if st.download_button(
                                        label="代替CSVファイルをダウンロード",
                                        data=csv_data.encode('utf-8-sig'),
                                        file_name=alt_csv_filename,
                                        mime="text/csv",
                                        key="alt_csv_download_all"
                                    ):
                                        st.success("CSVファイルをダウンロードしました")
                
                except Exception as e:
                    st.error(f"エラーが発生しました: {str(e)}")
                    st.error(traceback.format_exc())

    elif tool_selection == '構造分析（テキスト出力）':
        st.header('DXFデータ構造を分析しマークダウン形式のテキストファイルで出力')
        uploaded_file = st.file_uploader("DXFファイルをアップロード", type="dxf", key="hierarchy_extractor")
        
        # デフォルトのファイル名を設定
        default_filename = "hierarchy.md"
        if uploaded_file is not None:
            default_filename = os.path.splitext(uploaded_file.name)[0] + ".md"
            
        output_filename = st.text_input("出力ファイル名", default_filename)
        if not output_filename.endswith('.md'):
            output_filename += '.md'
            
        if uploaded_file is not None:
            try:
                # ファイルを一時ディレクトリに保存
                temp_file = save_uploadedfile(uploaded_file)
                
                if st.button("構造を分析"):
                    with st.spinner('DXFデータ構造を分析中...'):
                        try:
                            hierarchy_lines = extract_hierarchy(temp_file)
                            
                            # 結果を表示
                            st.subheader("構造分析結果")
                            st.text_area("マークダウン形式テキスト", "\n".join(hierarchy_lines), height=300)
                            
                            # ダウンロードボタンを作成
                            md_str = "\n".join(hierarchy_lines)
                            st.download_button(
                                label="マークダウン形式テキストファイルをダウンロード",
                                data=md_str.encode('utf-8'),
                                file_name=output_filename,
                                mime="text/markdown",
                            )
                        except Exception as e:
                            st.error(f"構造分析中にエラーが発生しました: {str(e)}")
                            st.error(traceback.format_exc())
                    
                    # 一時ファイルの削除
                    try:
                        os.unlink(temp_file)
                    except:
                        pass
            
            except Exception as e:
                st.error(f"エラーが発生しました: {str(e)}")
                st.error(traceback.format_exc())

    elif tool_selection == '図面差分抽出':
        st.header('2つのDXFファイルを比較し差分を抽出しDXFフォーマットで出力')
        col1, col2 = st.columns(2)
        
        with col1:
            uploaded_file_a = st.file_uploader("基準DXFファイル (A)", type="dxf", key="dxf_a")
        
        with col2:
            uploaded_file_b = st.file_uploader("比較対象DXFファイル (B)", type="dxf", key="dxf_b")
        
        # デフォルトのファイル名を設定
        default_filename = "diff.dxf"
        if uploaded_file_a is not None and uploaded_file_b is not None:
            file_a_base = os.path.splitext(uploaded_file_a.name)[0]
            file_b_base = os.path.splitext(uploaded_file_b.name)[0]
            default_filename = f"{file_a_base}_vs_{file_b_base}.dxf"
            
        output_filename = st.text_input("出力ファイル名", default_filename)
        if not output_filename.endswith('.dxf'):
            output_filename += '.dxf'
        
        tolerance = st.slider("許容誤差", min_value=1e-8, max_value=1e-1, value=1e-6, format="%.8f")
        
        if uploaded_file_a is not None and uploaded_file_b is not None:
            try:
                # ファイルを一時ディレクトリに保存
                temp_file_a = save_uploadedfile(uploaded_file_a)
                temp_file_b = save_uploadedfile(uploaded_file_b)
                temp_output = tempfile.NamedTemporaryFile(delete=False, suffix=".dxf").name
                
                if st.button("差分を比較"):
                    with st.spinner('DXFファイルを比較中...'):
                        result = compare_dxf_files_and_generate_dxf(temp_file_a, temp_file_b, temp_output, tolerance)
                        
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
                        else:
                            st.error("DXFファイルの比較に失敗しました")
                    
                    # 一時ファイルの削除
                    os.unlink(temp_file_a)
                    os.unlink(temp_file_b)
                    os.unlink(temp_output)
            
            except Exception as e:
                st.error(f"エラーが発生しました: {str(e)}")
                st.error(traceback.format_exc())

    elif tool_selection == '図面ラベル差分抽出':
        st.header('2つのDXFファイルのラベルを比較し、差分をマークダウン形式テキストファイルで出力')
        col1, col2 = st.columns(2)
        
        with col1:
            uploaded_file_a = st.file_uploader("基準DXFファイル (A)", type="dxf", key="label_a")
        
        with col2:
            uploaded_file_b = st.file_uploader("比較対象DXFファイル (B)", type="dxf", key="label_b")
        
        # デフォルトのファイル名を設定
        default_filename = "label_diff.md"
        if uploaded_file_a is not None and uploaded_file_b is not None:
            file_a_base = os.path.splitext(uploaded_file_a.name)[0]
            file_b_base = os.path.splitext(uploaded_file_b.name)[0]
            default_filename = f"{file_a_base}_vs_{file_b_base}_label_diff.md"
            
        output_filename = st.text_input("出力ファイル名", default_filename)
        if not output_filename.endswith('.md'):
            output_filename += '.md'
        
        if uploaded_file_a is not None and uploaded_file_b is not None:
            try:
                # ファイルを一時ディレクトリに保存
                temp_file_a = save_uploadedfile(uploaded_file_a)
                temp_file_b = save_uploadedfile(uploaded_file_b)
                
                if st.button("ラベル差分を比較"):
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
                    os.unlink(temp_file_a)
                    os.unlink(temp_file_b)
            
            except Exception as e:
                st.error(f"エラーが発生しました: {str(e)}")
                st.error(traceback.format_exc())
   
    elif tool_selection == 'Excel回路記号抽出':
        st.header('ULKES Excelファイルから回路記号を抽出')
        
        uploaded_file = st.file_uploader("Excelファイルをアップロード", type=["xlsx"], key="circuit_extractor")
        
        # 各種オプション設定
        col1, col2 = st.columns(2)
        
        with col1:
            # デフォルトのファイル名を設定
            default_filename = "circuit_symbols.txt"
            if uploaded_file is not None:
                default_filename = os.path.splitext(uploaded_file.name)[0] + "_symbols.txt"
                
            output_filename = st.text_input("出力ファイル名", default_filename)
            if not output_filename.endswith('.txt'):
                output_filename += '.txt'
        
        with col2:
            use_filename = st.checkbox("ファイル名にある図面番号を使用", value=True)
            assembly_number = None if use_filename else st.text_input("図面番号", "")
        
        # 追加オプション
        col3, col4 = st.columns(2)
        
        with col3:
            use_all_assemblies = st.checkbox("全ての可能な図面番号を使用", value=False, 
                                            help="Excelファイル内で検出できる部品を含む全ての図面番号に対して処理を行います。")
        
        with col4:
            include_maker_info = st.checkbox("メーカー情報を含める", value=False,
                                            help="出力にメーカー名とメーカー型式を含めます。CSVフォーマットになります。")
            
        if uploaded_file is not None:
            try:
                # ファイルを一時ディレクトリに保存
                temp_file = save_uploadedfile(uploaded_file)
                
                if st.button("回路記号を抽出"):
                    with st.spinner('回路記号を抽出中...'):
                        # ファイル名からアセンブリ番号を取得
                        if use_filename:
                            # extract_assembly_number_from_filename関数を使用
                            from utils.extract_symbols import extract_assembly_number_from_filename
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
                    os.unlink(temp_file)
            
            except Exception as e:
                st.error(f"エラーが発生しました: {str(e)}")
                st.error(traceback.format_exc())

    elif tool_selection == '回路記号リスト差分抽出':
        st.header('2つの回路記号リストを比較し差分を抽出し、マークダウン形式テキストファイルで出力')
        col1, col2 = st.columns(2)
        
        with col1:
            uploaded_file_a = st.file_uploader("回路記号リスト・ファイルA", type=["txt"], key="partslist_a")
        
        with col2:
            uploaded_file_b = st.file_uploader("回路記号リスト・ファイルB", type=["txt"], key="partslist_b")
        
        # デフォルトのファイル名を設定
        default_filename = "partslist_diff.md"
        if uploaded_file_a is not None and uploaded_file_b is not None:
            file_a_base = os.path.splitext(uploaded_file_a.name)[0]
            file_b_base = os.path.splitext(uploaded_file_b.name)[0]
            default_filename = f"{file_a_base}_vs_{file_b_base}_diff.md"
            
        output_filename = st.text_input("出力ファイル名", default_filename)
        if not output_filename.endswith('.md'):
            output_filename += '.md'
        
        if uploaded_file_a is not None and uploaded_file_b is not None:
            try:
                # ファイルを一時ディレクトリに保存
                temp_file_a = save_uploadedfile(uploaded_file_a)
                temp_file_b = save_uploadedfile(uploaded_file_b)
                
                if st.button("回路記号リストを比較"):
                    with st.spinner('回路記号リストを比較中...'):
                        try:
                            # パーツリストの比較
                            comparison_result = compare_parts_list(temp_file_a, temp_file_b)
                            
                            # 結果を表示
                            st.subheader("回路記号リスト差分抽出結果")
                            st.markdown(comparison_result)
                            
                            # ダウンロードボタンを作成
                            st.download_button(
                                label="テキストファイルをダウンロード",
                                data=comparison_result.encode('utf-8'),
                                file_name=output_filename,
                                mime="text/markdown",
                            )
                        except Exception as e:
                            st.error(f"比較処理中にエラーが発生しました: {str(e)}")
                            st.error(traceback.format_exc())
                    
                    # 一時ファイルの削除
                    try:
                        os.unlink(temp_file_a)
                        os.unlink(temp_file_b)
                    except:
                        pass
            
            except Exception as e:
                st.error(f"エラーが発生しました: {str(e)}")
                st.error(traceback.format_exc())

if __name__ == '__main__':
    main()