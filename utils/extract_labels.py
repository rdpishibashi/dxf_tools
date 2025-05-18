import ezdxf
import re
import os

def get_layers_from_dxf(dxf_file):
    """
    DXFファイルからレイヤー一覧を取得する
    
    Args:
        dxf_file: DXFファイルパス
        
    Returns:
        list: レイヤー名のリスト
    """
    try:
        doc = ezdxf.readfile(dxf_file)
        # レイヤーテーブルからすべてのレイヤー名を取得
        layer_names = [layer.dxf.name for layer in doc.layers]
        return sorted(layer_names)  # アルファベット順にソート
    except Exception as e:
        print(f"レイヤー一覧の取得中にエラーが発生しました: {str(e)}")
        return []

def extract_labels(dxf_file, filter_non_parts=False, sort_order="asc", debug=False, selected_layers=None):
    """
    DXFファイルからテキストラベルを抽出する
    
    Args:
        dxf_file: DXFファイルパス
        filter_non_parts: 回路記号以外のラベルをフィルタリングするかどうか
        sort_order: ソート順 ("asc"=昇順, "desc"=降順, "none"=ソートなし)
        debug: デバッグ情報を表示するかどうか
        selected_layers: 処理対象とするレイヤー名のリスト。Noneの場合は全レイヤーを対象とする
        
    Returns:
        tuple: (ラベルリスト, 情報辞書)
    """
    # 処理情報を格納する辞書
    info = {
        "total_extracted": 0,
        "filtered_count": 0,
        "final_count": 0,
        "processed_layers": 0,
        "total_layers": 0,
        "filename": os.path.basename(dxf_file)
    }
    
    try:
        # DXFファイルを読み込む
        doc = ezdxf.readfile(dxf_file)
        msp = doc.modelspace()
        
        # 全レイヤー数を記録
        all_layers = [layer.dxf.name for layer in doc.layers]
        info["total_layers"] = len(all_layers)
        
        # 選択されたレイヤーの処理
        if selected_layers is None:
            # 選択されたレイヤーが指定されていない場合は全レイヤーを対象とする
            selected_layers = all_layers
        
        # 処理対象のレイヤー数を記録
        info["processed_layers"] = len(selected_layers)
        
        # すべてのテキストエンティティを抽出（選択されたレイヤーのみ）
        labels = []
        for e in msp:
            if e.dxftype() in ['TEXT', 'MTEXT']:
                # エンティティのレイヤーが選択されたレイヤーに含まれているか確認
                if e.dxf.layer in selected_layers:
                    if e.dxftype() == 'TEXT':
                        text = e.dxf.text
                    else:  # MTEXT
                        text = e.text
                    
                    # フォーマットコードを削除
                    cleaned_text = re.sub(r'\\[A-Za-z0-9.]+;', '', text)
                    cleaned_text = cleaned_text.replace('\\P', ' ').strip()
                    
                    if cleaned_text:
                        labels.append(cleaned_text)
        
        # 総抽出数を記録
        info["total_extracted"] = len(labels)
        
        # フィルタリング
        if filter_non_parts:
            filtered_labels = []
            filtered_out = []
            
            for label in labels:
                # フィルタリング条件
                is_filtered = False
                reason = ""
                
                # 空白を含むかどうかをチェック
                if ' ' in label:
                    # 次の条件のいずれかに該当する場合にフィルタリング
                    
                    # 1. 空白を含み、英数字のみで構成されているラベル
                    if re.match(r'^[A-Za-z0-9 ]+$', label):
                        is_filtered = True
                        reason = "空白を含む英数字のみのラベル"
                    
                    # 2. 空白を含み、単語や短い説明のようなラベル
                    # 単語間にスペースがあり、記号が少ないもの（一般的な説明テキスト）
                    words = label.split()
                    if len(words) > 1:
                        # 括弧や記号を除いた部分の長さを計算
                        clean_part = re.sub(r'[^\w\s]', '', label)
                        special_chars = [c for c in label if not (c.isalnum() or c.isspace())]
                        
                        # 記号が少ない（全体の25%未満）または一般的な記号パターン（括弧など）
                        if len(special_chars) < len(label) * 0.25 or '(' in label:
                            # 最初の単語が "to" や短い場合
                            if len(words[0]) <= 3 or words[0].lower() == 'to' or words[0].lower() == 'on':
                                is_filtered = True
                                reason = "説明的なテキスト"
                
                # その他のフィルタリング条件
                if not is_filtered:
                    if re.match(r'^\(', label):  # (BK), (M5) など
                        is_filtered = True
                        reason = "括弧で始まる"
                    elif re.match(r'^\d', label):  # 2.1+, 500DJ など
                        is_filtered = True
                        reason = "数字で始まる"
                    elif re.match(r'^[A-Z]{1,2}$', label):  # E, L, PE など
                        is_filtered = True
                        reason = "英大文字だけで2文字以下"
                    elif re.match(r'^[A-Z]\d+$', label):  # R1, T2 など
                        is_filtered = True
                        reason = "英大文字1文字に続いて数字"
                    elif re.match(r'^[A-Z]\d+\.\d+$', label):  # L1.1, P01 など
                        is_filtered = True
                        reason = "英大文字1文字に続いて数字と「.」からなる文字列"
                    elif re.match(r'^[A-Za-z]+[\+\-]$', label):  # P+, VCC- など
                        is_filtered = True
                        reason = "英字と「+」もしくは「-」の組み合わせ"
                    elif 'GND' in label:  # GND, GND(M4) など
                        is_filtered = True
                        reason = "「GND」を含む"
                    elif label.startswith('AWG'):  # AWG14, AWG18 など
                        is_filtered = True
                        reason = "「AWG」ではじまる"
                    elif label.startswith('☆'):
                        is_filtered = True
                        reason = "「☆」ではじまる"
                    elif label.startswith('注'):
                        is_filtered = True
                        reason = "「注」ではじまる"
                
                if is_filtered:
                    if debug:
                        filtered_out.append(f"{label} (理由: {reason})")
                    continue
                
                # 括弧で囲まれた部分を削除する
                clean_label = re.sub(r'\([^)]*\)', '', label).strip()
                
                if clean_label:
                    filtered_labels.append(clean_label)
                    
            # フィルタリング結果を記録
            info["filtered_count"] = info["total_extracted"] - len(filtered_labels)
            labels = filtered_labels
        
        # ソート
        if sort_order == "asc":
            labels.sort()
        elif sort_order == "desc":
            labels.sort(reverse=True)
        
        # 最終的なラベル数を記録
        info["final_count"] = len(labels)
        
        # デバッグ情報
        if debug and filter_non_parts:
            print(f"フィルタリングで除外されたラベル: {filtered_out}")
        
        return labels, info
        
    except Exception as e:
        print(f"エラー: {str(e)}")
        info["error"] = str(e)
        return [], info

def process_multiple_dxf_files(dxf_files, filter_non_parts=False, sort_order="asc", debug=False, selected_layers=None):
    """
    複数のDXFファイルからラベルを抽出する
    
    Args:
        dxf_files: DXFファイルパスのリスト
        filter_non_parts: 回路記号以外のラベルをフィルタリングするかどうか
        sort_order: ソート順 ("asc"=昇順, "desc"=降順, "none"=ソートなし)
        debug: デバッグ情報を表示するかどうか
        selected_layers: 処理対象とするレイヤー名のリスト。Noneの場合は全レイヤーを対象とする
        
    Returns:
        dict: ファイルパスをキー、(ラベルリスト, 情報辞書)をバリューとする辞書
    """
    results = {}
    
    for dxf_file in dxf_files:
        # ディレクトリの場合は、中のDXFファイルを処理
        if os.path.isdir(dxf_file):
            for root, _, files in os.walk(dxf_file):
                for file in files:
                    if file.lower().endswith('.dxf'):
                        file_path = os.path.join(root, file)
                        labels, info = extract_labels(file_path, filter_non_parts, sort_order, debug, selected_layers)
                        results[file_path] = (labels, info)
        # 単一のDXFファイルの場合
        elif os.path.isfile(dxf_file) and dxf_file.lower().endswith('.dxf'):
            labels, info = extract_labels(dxf_file, filter_non_parts, sort_order, debug, selected_layers)
            results[dxf_file] = (labels, info)
    
    return results