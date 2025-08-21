import streamlit as st
import os
import traceback
import zipfile
import io
import sys

# utils モジュールをインポート可能にするためのパスの追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.extract_labels import extract_labels, get_layers_from_dxf
from common_utils import save_uploadedfile, get_output_filename, handle_error

def app():
    st.title('図面ラベル抽出')
    st.write('DXFファイルからラベル（テキスト要素）を抽出します。')
    
    # ファイルアップロードUI
    uploaded_files = st.file_uploader(
        "DXFファイルをアップロード (複数選択可能)", 
        type="dxf", 
        accept_multiple_files=True,
        key="label_extractor"
    )
    
    # ファイルが選択されたか確認
    has_files = len(uploaded_files) > 0
    
    # オプション設定
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
                     "\n適合しない機器符号のリストを別途表示します。"
                     "\n（例：CBnnn, ELB(CB) nnn, R, Annn等の標準フォーマット）"
            )
        
        # 図面番号抽出オプション
        extract_drawing_numbers_option = st.checkbox(
            "図番・流用元図番を抽出", 
            value=False,
            help="図面番号フォーマット（例：DE5313-008-02B）に一致する文字列を抽出し、"
                 "\n座標に基づいて図番（右下）と流用元図番を判別します。"
                 "\nMTEXTフォーマットコード（\\A1;\\W0.855724;等）も適切に処理します。"
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
    
    # 出力形式オプション（複数ファイルの場合のみ表示）
    if has_files and len(uploaded_files) > 1:
        output_format = st.radio(
            "出力形式",
            options=["個別ファイル", "ZIPアーカイブ"],
            index=0,  # デフォルトで個別ファイルを選択
            help="複数ファイルの場合、個別に出力するかZIPアーカイブにまとめるかを選択できます"
        )
    else:
        output_format = "個別ファイル"
    
    
    # 結果表示用のセッション状態を初期化
    if 'label_results' not in st.session_state:
        st.session_state.label_results = None
        
    # 選択ファイルのセッション状態を初期化
    if 'selected_result_file' not in st.session_state:
        st.session_state.selected_result_file = None
        
    # レイヤー選択UI用の変数
    common_layers = []
    layer_maps = {}
    
    if has_files:
        try:
            # すべてのファイルを一時保存
            temp_files = []
            for uploaded_file in uploaded_files:
                temp_file = save_uploadedfile(uploaded_file)
                temp_files.append((uploaded_file.name, temp_file))
            
            # レイヤー情報の読み込み
            with st.spinner('レイヤー情報を読み込み中...'):
                # 各ファイルのレイヤー情報を取得
                for file_name, file_path in temp_files:
                    try:
                        layers = get_layers_from_dxf(file_path)
                        layer_maps[file_name] = layers
                        
                        # 初回は全レイヤーを共通レイヤーとする
                        if not common_layers:
                            common_layers = layers.copy()
                        else:
                            # 共通のレイヤーだけを残す
                            common_layers = [layer for layer in common_layers if layer in layers]
                    except Exception as e:
                        st.error(f"ファイル {file_name} のレイヤー情報読み込みでエラー: {str(e)}")
            
            # ファイル・レイヤー選択UI
            st.subheader("ファイル選択")
            
            # レイヤー情報を表示するためのボタン
            show_layers = st.button("レイヤー情報を表示", help="アップロードされたファイルのレイヤー情報を確認し、選択できます")
            
            # セッション状態でレイヤー表示状態を管理
            if 'show_layer_selection' not in st.session_state:
                st.session_state.show_layer_selection = False
            
            if show_layers:
                st.session_state.show_layer_selection = True
            
            if layer_maps and st.session_state.show_layer_selection:
                # 全ファイル共通のレイヤーがあるかどうか
                has_common_layers = len(common_layers) > 0
                
                # レイヤー選択モード
                st.subheader("レイヤー選択")
                
                # 共通レイヤーが存在しない場合
                if not has_common_layers and len(layer_maps) > 1:
                    st.warning("アップロードされたファイル間に共通のレイヤーが見つかりませんでした。各ファイルのレイヤーを個別に選択してください。")
                
                # タブの構成を決定
                tab_names = []
                if len(layer_maps) > 1:
                    tab_names.append("共通レイヤー")
                tab_names.extend([f"ファイル: {name}" for name, _ in temp_files])
                
                # タブを作成してファイルごとにレイヤー選択UIを表示
                tabs = st.tabs(tab_names)
                
                # セッション状態の初期化
                if 'layer_states' not in st.session_state:
                    st.session_state.layer_states = {}
                
                # 初期化: すべてのファイルとレイヤーをセッション状態に追加
                for file_name, layers in layer_maps.items():
                    if file_name not in st.session_state.layer_states:
                        st.session_state.layer_states[file_name] = {}
                    
                    for layer in layers:
                        if layer not in st.session_state.layer_states[file_name]:
                            st.session_state.layer_states[file_name][layer] = True  # デフォルトで選択状態
                
                # タブインデックス
                tab_index = 0
                
                # 共通レイヤータブ（複数ファイルの場合のみ）
                if len(layer_maps) > 1:
                    with tabs[tab_index]:
                        if has_common_layers:
                            col3, col4 = st.columns([1, 3])
                            with col3:
                                if st.button("全選択", key="common_select_all"):
                                    for file_name in layer_maps.keys():
                                        for layer in common_layers:
                                            st.session_state.layer_states[file_name][layer] = True
                            
                            with col4:
                                if st.button("全解除", key="common_deselect_all"):
                                    for file_name in layer_maps.keys():
                                        for layer in common_layers:
                                            st.session_state.layer_states[file_name][layer] = False
                            
                            # 3列表示に変更
                            layer_cols = st.columns(3)
                            
                            # 共通レイヤーのチェックボックス
                            for i, layer in enumerate(common_layers):
                                col_index = i % 3
                                with layer_cols[col_index]:
                                    # 共通レイヤータブでは、すべてのファイルの同名レイヤーを一括で選択/解除
                                    # 現在の状態を取得（複数ファイルで同じレイヤーが全て選択されている場合のみTrue）
                                    is_all_selected = all(st.session_state.layer_states[file_name].get(layer, False) 
                                                         for file_name in layer_maps.keys())
                                    
                                    # チェックボックスを表示
                                    is_selected = st.checkbox(
                                        layer, 
                                        value=is_all_selected, 
                                        key=f"common_layer_{layer}"
                                    )
                                    
                                    # 選択状態を全ファイルの同名レイヤーに反映
                                    for file_name in layer_maps.keys():
                                        if layer in layer_maps[file_name]:  # ファイルにそのレイヤーが存在する場合のみ
                                            st.session_state.layer_states[file_name][layer] = is_selected
                        else:
                            st.info("アップロードされたファイル間に共通のレイヤーがありません。各ファイルタブでレイヤーを選択してください。")
                        
                        tab_index += 1
                
                # 各ファイルのタブ
                for i, (file_name, _) in enumerate(temp_files):
                    with tabs[tab_index + i]:
                        st.write(f"ファイル: {file_name}")
                        
                        if file_name in layer_maps and layer_maps[file_name]:
                            col5, col6 = st.columns([1, 3])
                            with col5:
                                if st.button("全選択", key=f"file_{i}_select_all"):
                                    for layer in layer_maps[file_name]:
                                        st.session_state.layer_states[file_name][layer] = True
                            
                            with col6:
                                if st.button("全解除", key=f"file_{i}_deselect_all"):
                                    for layer in layer_maps[file_name]:
                                        st.session_state.layer_states[file_name][layer] = False
                            
                            # 3列表示
                            file_layer_cols = st.columns(3)
                            
                            # 各ファイルのレイヤーチェックボックス
                            for j, layer in enumerate(layer_maps[file_name]):
                                col_index = j % 3
                                with file_layer_cols[col_index]:
                                    is_selected = st.checkbox(
                                        layer, 
                                        value=st.session_state.layer_states[file_name].get(layer, True),
                                        key=f"file_{i}_layer_{layer}"
                                    )
                                    st.session_state.layer_states[file_name][layer] = is_selected
                        else:
                            st.warning(f"このファイルにはレイヤーが見つかりませんでした。")
            
            # 処理実行ボタン
            process_button = st.button("ラベルを抽出")
            
            # 処理実行または結果表示
            if process_button or st.session_state.label_results is not None:
                # ボタンが押された場合は処理を実行
                if process_button:
                    # 選択されたレイヤーを確認
                    selected_layers_by_file = {}
                    for file_name in layer_maps.keys():
                        if 'layer_states' in st.session_state and file_name in st.session_state.layer_states:
                            selected_layers_by_file[file_name] = [
                                layer for layer, is_selected in st.session_state.layer_states[file_name].items() 
                                if is_selected
                            ]
                        else:
                            # レイヤー選択が行われていない場合は全レイヤーを選択
                            selected_layers_by_file[file_name] = layer_maps[file_name]
                    
                    # レイヤーが選択されていない場合の警告
                    files_without_layers = [
                        file_name for file_name, layers in selected_layers_by_file.items() 
                        if not layers
                    ]
                    
                    if files_without_layers:
                        st.warning(f"以下のファイルではレイヤーが選択されていません。全レイヤーを対象とします: {', '.join(files_without_layers)}")
                    
                    # 処理の実行
                    with st.spinner('ラベルを抽出中...'):
                        # 結果を格納するための辞書
                        results = {}
                        
                        # 各ファイルを処理
                        for file_name, file_path in temp_files:
                            # 選択されたレイヤー
                            selected_layers = selected_layers_by_file.get(file_name, [])
                            
                            # レイヤーが選択されていない場合は全レイヤーを対象とする
                            if not selected_layers:
                                selected_layers = layer_maps.get(file_name, [])
                            
                            # ラベル抽出
                            labels, info = extract_labels(
                                file_path, 
                                filter_non_parts=filter_option, 
                                sort_order=sort_value,
                                selected_layers=selected_layers,
                                validate_ref_designators=validate_ref_designators,
                                extract_drawing_numbers_option=extract_drawing_numbers_option
                            )
                            
                            results[file_name] = (labels, info)
                        
                        # セッション状態に結果を保存
                        st.session_state.label_results = results
                        
                        # 初回は最初のファイルを選択
                        if results:
                            st.session_state.selected_result_file = list(results.keys())[0]
                        
                        # ZIPアーカイブの場合、自動的にダウンロードも実行
                        if output_format == "ZIPアーカイブ" and len(results) > 1:
                            # 出力ファイル用のデータを準備
                            output_files = {}
                            
                            # すべてのファイルの結果をZIPアーカイブ用に準備
                            for file_name, (file_labels, file_info) in results.items():
                                if file_labels:
                                    # 個別ファイルのファイル名も同じヘルパー関数で生成
                                    file_output_name = get_output_filename(file_name, 'labels')
                                    output_files[file_output_name] = "\n".join(file_labels).encode('utf-8')
                                
                                # 妥当性チェック結果がある場合、それも追加
                                if validate_ref_designators and 'invalid_ref_designators' in file_info and file_info['invalid_ref_designators']:
                                    invalid_filename = get_output_filename(file_name, 'labels', 'invalid.txt')
                                    invalid_content = "\n".join(file_info['invalid_ref_designators'])
                                    output_files[invalid_filename] = invalid_content.encode('utf-8')
                                
                                # 図面番号抽出結果がある場合、それも追加
                                if extract_drawing_numbers_option:
                                    drawing_results = []
                                    if file_info.get('main_drawing_number'):
                                        drawing_results.append(f"図番: {file_info['main_drawing_number']}")
                                    if file_info.get('source_drawing_number'):
                                        drawing_results.append(f"流用元図番: {file_info['source_drawing_number']}")
                                    if file_info.get('all_drawing_numbers'):
                                        drawing_results.append(f"全図面番号: {', '.join(file_info['all_drawing_numbers'])}")
                                    
                                    if drawing_results:
                                        drawing_filename = get_output_filename(file_name, 'labels', 'drawing_numbers.txt')
                                        drawing_content = "\n".join(drawing_results)
                                        output_files[drawing_filename] = drawing_content.encode('utf-8')
                            
                            # ZIPアーカイブのダウンロードボタン
                            if output_files:
                                # ZIPファイルを作成
                                zip_buffer = io.BytesIO()
                                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
                                    for filename, data in output_files.items():
                                        zf.writestr(filename, data)
                                
                                # ZIPファイル名を作成
                                zip_filename = get_output_filename("labels_extracted", 'labels', 'zip')
                                
                                # 総ラベル数の計算
                                total_labels = sum(len(labels) for labels, _ in results.values())
                                
                                # ダウンロードボタンを表示
                                st.success(f"抽出完了！ 合計 {len(output_files)} ファイル、{total_labels} ラベルが抽出されました。")
                                st.download_button(
                                    label=f"全ファイルのラベルをZIPでダウンロード ({len(output_files)}ファイル)",
                                    data=zip_buffer.getvalue(),
                                    file_name=zip_filename,
                                    mime="application/zip",
                                    key="download_zip"
                                )
                
                # 個別ファイルの場合のみ詳細結果表示
                if output_format == "個別ファイル":
                    results = st.session_state.label_results
                    if results:
                        st.subheader("抽出結果")
                        
                        # 結果表示用のタブ名を準備
                        result_tab_names = list(results.keys())
                        
                        # コールバック関数でファイル選択を処理
                        def on_file_change():
                            # 選択が変更されたら保存
                            st.session_state.selected_result_file = st.session_state.file_selector
                        
                        # セレクトボックスを使用して選択肢を表示
                        # デフォルト値が保存されていない場合は最初のファイルを選択
                        default_file = st.session_state.selected_result_file
                        if default_file not in result_tab_names and result_tab_names:
                            default_file = result_tab_names[0]
                            st.session_state.selected_result_file = default_file
                        
                        st.selectbox(
                            "ファイル選択", 
                            options=result_tab_names,
                            index=result_tab_names.index(default_file) if default_file in result_tab_names else 0,
                            key="file_selector",
                            on_change=on_file_change
                        )
                        
                        # 選択されたファイルの結果を表示
                        selected_file = st.session_state.selected_result_file
                        if selected_file in results:
                            labels, info = results[selected_file]
                            
                            # レイヤー処理情報の表示
                            st.info(f"処理対象レイヤー: {info['processed_layers']} / {info['total_layers']}")
                            
                            # 処理情報の表示
                            st.info(f"元の抽出ラベル総数: {info['total_extracted']}")
                            
                            if 'filtered_count' in info and info['filtered_count'] > 0:
                                st.info(f"フィルタリングで除外したラベル数: {info['filtered_count']}")
                            
                            st.info(f"最終的なラベル数: {info['final_count']}")
                            
                            # ソート情報の表示（セッションには保存されていないため条件分岐）
                            if process_button and sort_value != "none":
                                sort_text = "昇順" if sort_value == "asc" else "逆順"
                                st.info(f"ラベルを{sort_text}で並び替えました")
                            
                            # 図面番号抽出結果の表示
                            if info.get('main_drawing_number') or info.get('source_drawing_number') or info.get('all_drawing_numbers'):
                                st.subheader("図面番号抽出結果")
                                
                                if info.get('main_drawing_number') or info.get('source_drawing_number'):
                                    col1, col2 = st.columns(2)
                                    
                                    with col1:
                                        if info.get('main_drawing_number'):
                                            st.success(f"**図番**: {info['main_drawing_number']}")
                                        else:
                                            st.warning("図番: 検出されませんでした")
                                    
                                    with col2:
                                        if info.get('source_drawing_number'):
                                            st.info(f"**流用元図番**: {info['source_drawing_number']}")
                                        else:
                                            st.info("流用元図番: 検出されませんでした")
                                    
                                    # 全図面番号リスト
                                    if info.get('all_drawing_numbers'):
                                        st.write(f"**抽出された全図面番号**: {', '.join(info['all_drawing_numbers'])}")
                                    
                                else:
                                    st.warning("図面番号が検出されませんでした")
                            
                            
                            # 機器符号妥当性チェック結果の表示
                            if validate_ref_designators and 'invalid_ref_designators' in info:
                                invalid_designators = info['invalid_ref_designators']
                                if invalid_designators:
                                    st.warning(f"フォーマットに適合しない機器符号が {len(invalid_designators)} 個見つかりました")
                                    
                                    # 適合しない機器符号を表示
                                    st.text_area(
                                        f"適合しない機器符号 - {selected_file}", 
                                        "\n".join(invalid_designators), 
                                        height=150
                                    )
                                    
                                    # 適合しない機器符号のダウンロードボタン
                                    invalid_filename = get_output_filename(selected_file, 'labels', 'invalid.txt')
                                    invalid_content = "\n".join(invalid_designators)
                                    st.download_button(
                                        label=f"適合しない機器符号をダウンロード",
                                        data=invalid_content.encode('utf-8'),
                                        file_name=invalid_filename,
                                        mime="text/plain",
                                        key=f"download_invalid_{hash(selected_file)}"
                                    )
                                else:
                                    st.success("すべての機器符号がフォーマットに適合しています")
                            
                            # ラベル一覧
                            st.text_area(f"ラベル一覧 - {selected_file}", "\n".join(labels), height=300)
                            
                            # 出力ファイル名を生成
                            output_filename = get_output_filename(selected_file, 'labels')
                            
                            # 個別ファイルダウンロードボタン
                            if labels:
                                txt_str = "\n".join(labels)
                                st.download_button(
                                    label=f"{selected_file} のラベルをダウンロード",
                                    data=txt_str.encode('utf-8'),
                                    file_name=output_filename,
                                    mime="text/plain",
                                    key=f"download_{hash(selected_file)}"
                                )
            
            # 一時ファイルの削除
            for _, file_path in temp_files:
                try:
                    os.unlink(file_path)
                except:
                    pass
                    
        except Exception as e:
            handle_error(e)

if __name__ == "__main__":
    app()