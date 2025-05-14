import ezdxf
import re

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
        "total_layers": 0
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
                
                # 括弧内の部分を一時的に削除するための正規表現
                temp_label = re.sub(r'\([^)]*\)', '', label).strip()
                
                # 以下の条件に合致するラベルは回路記号でないと判断
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
                elif re.match(r'^[a-z]+( [a-z]+)+$', label):  # on ..., to ... など
                    is_filtered = True
                    reason = "英小文字だけの単語と空白を複数含む"
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
        return [], info