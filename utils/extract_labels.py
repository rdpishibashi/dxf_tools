import ezdxf
import re
import os
import sys

# 共通ユーティリティをインポート
try:
    from common_utils import process_circuit_symbol_labels
except ImportError:
    # common_utils.pyが見つからない場合のフォールバック
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from common_utils import process_circuit_symbol_labels

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

def extract_labels(dxf_file, filter_non_parts=False, sort_order="asc", debug=False, selected_layers=None, validate_ref_designators=False):
    """
    DXFファイルからテキストラベルを抽出する
    
    Args:
        dxf_file: DXFファイルパス
        filter_non_parts: 回路記号以外のラベルをフィルタリングするかどうか
        sort_order: ソート順 ("asc"=昇順, "desc"=降順, "none"=ソートなし)
        debug: デバッグ情報を表示するかどうか
        selected_layers: 処理対象とするレイヤー名のリスト。Noneの場合は全レイヤーを対象とする
        validate_ref_designators: 回路記号の妥当性をチェックするかどうか
        
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
        "filename": os.path.basename(dxf_file),
        "invalid_ref_designators": []  # 妥当性チェック用
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
        
        # 回路記号処理（フィルタリング、妥当性チェック）
        symbol_result = process_circuit_symbol_labels(
            labels,
            filter_non_parts=filter_non_parts,
            validate_ref_designators=validate_ref_designators,
            debug=debug
        )
        
        # 処理結果を取得
        labels = symbol_result['labels']
        info["filtered_count"] = symbol_result['filtered_count']
        info["invalid_ref_designators"] = symbol_result['invalid_ref_designators']
        
        # ソート
        if sort_order == "asc":
            labels.sort()
        elif sort_order == "desc":
            labels.sort(reverse=True)
        
        # 最終的なラベル数を記録
        info["final_count"] = len(labels)
        
        return labels, info
        
    except Exception as e:
        print(f"エラー: {str(e)}")
        info["error"] = str(e)
        return [], info

def process_multiple_dxf_files(dxf_files, filter_non_parts=False, sort_order="asc", debug=False, selected_layers=None, validate_ref_designators=False):
    """
    複数のDXFファイルからラベルを抽出する
    
    Args:
        dxf_files: DXFファイルパスのリスト
        filter_non_parts: 回路記号以外のラベルをフィルタリングするかどうか
        sort_order: ソート順 ("asc"=昇順, "desc"=降順, "none"=ソートなし)
        debug: デバッグ情報を表示するかどうか
        selected_layers: 処理対象とするレイヤー名のリスト。Noneの場合は全レイヤーを対象とする
        validate_ref_designators: 回路記号の妥当性をチェックするかどうか
        
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
                        labels, info = extract_labels(file_path, filter_non_parts, sort_order, debug, selected_layers, validate_ref_designators)
                        results[file_path] = (labels, info)
        # 単一のDXFファイルの場合
        elif os.path.isfile(dxf_file) and dxf_file.lower().endswith('.dxf'):
            labels, info = extract_labels(dxf_file, filter_non_parts, sort_order, debug, selected_layers, validate_ref_designators)
            results[dxf_file] = (labels, info)
    
    return results