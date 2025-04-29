import sys
import ezdxf
import re

def normalize_label(label):
    """ラベルを正規化（大文字化、トリム、全角スペース置換）"""
    if label is None:
        return ""
    return label.replace('　', ' ').strip().upper()

def remove_all_brackets(label):
    """ラベル内の括弧とその内容を削除"""
    if label is None:
        return "", False
    original_label = label
    modified_label = label
    pattern = re.compile(r'\([^)]*\)')
    prev_label = None
    while pattern.search(modified_label):
        if prev_label == modified_label:
            # 無限ループを防止
            break
        prev_label = modified_label
        modified_label = pattern.sub('', modified_label)
    modified_label = modified_label.strip()
    bracket_found = modified_label != original_label
    return modified_label, bracket_found

def is_filtered_label(label, debug=False):
    """
    ラベルがフィルター条件に合致するか判断する
    
    Args:
        label (str): チェック対象のラベル
        debug (bool): デバッグ情報を出力するかどうか
        
    Returns:
        tuple: (除外するかどうか, 除外理由, 処理後のラベル)
    """
    original_label = label
    normalized = normalize_label(label)
    modified_label = normalized
    current_label = normalized
    final_reason = None
    bracket_found = False
    trailing_removed = False

    # デバッグ情報
    if debug > 1: 
        print(f"\n--- フィルター処理開始: '{label}' ---")

    # --- フィルター条件 (括弧削除前にチェック) ---
    # 空のラベル
    if not normalized:
        if debug: print(f"空文字列なのでフィルタリング対象: '{label}'")
        return True, "空文字列", None
        
    # 最初の文字が「(」のラベル
    if normalized.startswith('('):
        if debug: print(f"'('で始まるのでフィルタリング対象: '{label}'")
        return True, "( で始まる", None
        
    # 最初の文字が数字のラベル
    if normalized[0].isdigit():
        if debug: print(f"数字で始まるのでフィルタリング対象: '{label}'")
        return True, "数字で始まる", None
        
    # 「GND」を含むラベル
    if 'GND' in normalized:
        if debug: print(f"'GND'を含むのでフィルタリング対象: '{label}'")
        return True, "GND を含む", None
        
    # 「AWG」ではじまるラベル
    if normalized.startswith('AWG'):
        if debug: print(f"'AWG'で始まるのでフィルタリング対象: '{label}'")
        return True, "AWG で始まる", None
    
    # 英小文字で始まるラベル
    stripped_original = original_label.strip() if original_label else ""
    if stripped_original and stripped_original[0].islower():
        if debug: print(f"英小文字で始まるのでフィルタリング対象: '{label}'")
        return True, "英小文字で始まる", None
    
    # 「☆」ではじまるラベル
    if normalized.startswith('☆'):
        if debug: print(f"'☆'で始まるのでフィルタリング対象: '{label}'")
        return True, "☆ で始まる", None
    
    # 「注」ではじまるラベル
    if normalized.startswith('注'):
        if debug: print(f"'注'で始まるのでフィルタリング対象: '{label}'")
        return True, "注 で始まる", None

    # --- 括弧削除処理 ---
    modified_label, bracket_found = remove_all_brackets(normalized)
    current_label = modified_label
    if bracket_found and modified_label != normalized:
        final_reason = "括弧削除"
        if debug: print(f"括弧を削除: '{normalized}' → '{modified_label}'")

    # 空文字列になった場合は除外
    if not current_label:
        reason = "空文字列" if not normalized else "括弧削除後に空文字列"
        if debug: print(f"{reason}なのでフィルタリング対象: '{label}'")
        return True, reason, None

    # --- 括弧削除後のフィルター条件 ---
    reason_prefix = "括弧削除後、" if bracket_found and modified_label != normalized else ""
    
    # 英大文字だけで2文字以下
    if current_label.isalpha() and current_label.isupper() and len(current_label) <= 2:
        if debug: print(f"{reason_prefix}英大文字だけで2文字以下なのでフィルタリング対象: '{label}'")
        return True, reason_prefix + "英大文字だけで2文字以下", None
    
    # 英大文字１文字に続いて数字のパターン
    single_letter_number_pattern = r'^[A-Z][0-9]+$'
    if re.match(single_letter_number_pattern, current_label):
        if debug: print(f"{reason_prefix}英大文字1文字+数字パターンなのでフィルタリング対象: '{label}'")
        return True, reason_prefix + "英大文字1文字+数字", None
    
    # 英大文字１文字に続いて数字と「.」からなる文字列
    single_letter_dot_pattern_strict = r'^[A-Z][0-9]+\.[0-9]+$'
    if re.match(single_letter_dot_pattern_strict, current_label):
        if debug: print(f"{reason_prefix}英大文字1文字+数字+ドット+数字パターンなのでフィルタリング対象: '{label}'")
        return True, reason_prefix + "英大文字1文字+数字+ドット+数字", None
    
    # 英字と「+」もしくは「-」の組み合わせ
    alpha_plusminus_pattern = r'^[A-Z]+[\+\-]$'
    if re.match(alpha_plusminus_pattern, current_label):
        if debug: print(f"{reason_prefix}英字+[+/-]パターンなのでフィルタリング対象: '{label}'")
        return True, reason_prefix + "英字+[+/-]", None
    
    # 英文字列と空白を複数含むラベル
    if ' ' in current_label and len(current_label.split()) > 1:
        if debug: print(f"{reason_prefix}英文字列と空白を複数含むのでフィルタリング対象: '{label}'")
        return True, reason_prefix + "英文字列と空白を複数含む", None

    # --- 後続文字削除処理 ---
    match = re.match(r'^[A-Z0-9]+', current_label)
    if match:
        extracted_part = match.group(0)
        if extracted_part != current_label:
            trailing_removed = True
            current_label = extracted_part
            if debug: print(f"後続文字を削除: '{modified_label}' → '{current_label}'")
            
            # 再度フィルターチェック
            reason_prefix_trail = reason_prefix + "後続文字削除後、" if reason_prefix else "後続文字削除後、"
            
            # 空文字列になった場合は除外
            if not current_label:
                if debug: print(f"{reason_prefix_trail}空文字列なのでフィルタリング対象: '{label}'")
                return True, reason_prefix_trail + "空文字列", None
                
            # 英大文字だけで2文字以下
            if current_label.isalpha() and current_label.isupper() and len(current_label) <= 2:
                if debug: print(f"{reason_prefix_trail}英大文字だけで2文字以下なのでフィルタリング対象: '{label}'")
                return True, reason_prefix_trail + "英大文字だけで2文字以下", None
                
            # 英大文字１文字に続いて数字のパターン
            if re.match(single_letter_number_pattern, current_label):
                if debug: print(f"{reason_prefix_trail}英大文字1文字+数字パターンなのでフィルタリング対象: '{label}'")
                return True, reason_prefix_trail + "英大文字1文字+数字", None

    # --- 最終判断 ---
    if trailing_removed:
        final_reason = "括弧削除+後続文字削除" if final_reason == "括弧削除" else "後続文字削除"
    elif bracket_found and final_reason is None:
         final_reason = "括弧あり(変化なし)" # または None

    if debug: print(f"抽出対象と判断: '{label}' → '{current_label}'")
    if debug > 1: print(f"--- フィルター処理終了: 保持 ---")
    
    # 最終的なラベルを返す (除外されなかった場合)
    return False, final_reason, current_label

def extract_labels(input_dxf, filter_non_parts=True, sort_order='asc', debug=False):
    """
    DXFファイルからラベルを抽出する
    
    Args:
        input_dxf (str): DXFファイルパス
        filter_non_parts (bool): フィルタリングを適用するかどうか
        sort_order (str): ソート順 ('asc'=昇順, 'desc'=降順, 'none'=ソートなし)
        debug (bool): デバッグ情報を出力するかどうか
        
    Returns:
        tuple: (抽出されたラベルのリスト, 処理情報)
    """
    info = {
        "total_extracted": 0,
        "filtered_count": 0,
        "skipped_count": 0,
        "final_count": 0,
        "skipped_labels": [],
        "filtered_labels": []
    }
    
    try:
        doc = ezdxf.readfile(input_dxf)
        msp = doc.modelspace()
        
        raw_labels = []  # 元のラベル
        
        # モデルスペース内のMTEXTから4番目のセグメントを抽出
        for entity in msp:
            try:
                if entity.dxftype() == 'MTEXT':
                    text = entity.text if hasattr(entity, 'text') else entity.dxf.text
                    
                    # セミコロンで分割し、4つ目の要素（インデックス3）を取得
                    segments = text.split(';')
                    if len(segments) >= 4:  # 少なくとも4つのセグメントがあることを確認
                        label = segments[3].strip()
                        if label:
                            raw_labels.append(label)
                    else:
                        info["skipped_count"] += 1
                        if debug:
                            print(f"スキップ: セミコロン区切りの4番目の要素が存在しない: {text}")
                        info["skipped_labels"].append((entity.dxftype(), "セミコロン区切りの4番目の要素が存在しない"))
            except AttributeError:
                info["skipped_count"] += 1
                info["skipped_labels"].append((entity.dxftype(), "AttributeError"))
            except Exception as e:
                info["skipped_count"] += 1
                info["skipped_labels"].append((entity.dxftype(), str(e)))
                if debug:
                    print(f"警告: エンティティの処理をスキップしました: {entity.dxftype()} - {str(e)}")
        
        info["total_extracted"] = len(raw_labels)
        
        # デバッグ情報
        if debug:
            print(f"抽出された全ラベル数: {info['total_extracted']}")
            if debug > 1:  # 詳細デバッグ
                print("抽出された全ラベル：")
                for idx, label in enumerate(raw_labels, 1):
                    print(f"{idx}: {label}")
        
        # フィルタリングの適用
        if filter_non_parts:
            filtered_labels = []
            
            for label in raw_labels:
                try:
                    # 各ラベルをフィルタリング
                    exclude, reason, modified = is_filtered_label(label, debug)
                    
                    if not exclude:
                        # 括弧削除などで変更された場合は変更後の値を使用
                        filtered_labels.append(modified if modified else label)
                    elif debug:
                        info["filtered_labels"].append((label, reason))
                        print(f"フィルタリングで除外: '{label}' ({reason})")
                except Exception as e:
                    info["skipped_count"] += 1
                    info["skipped_labels"].append((label, str(e)))
                    if debug:
                        print(f"警告: ラベルのフィルタリング中にエラーが発生しました: '{label}' - {str(e)}")
            
            info["filtered_count"] = info["total_extracted"] - len(filtered_labels)
            labels = filtered_labels
        else:
            # フィルターしない場合でも正規化は行う
            normalized_labels = []
            for label in raw_labels:
                normalized = normalize_label(label)
                if normalized:
                    normalized_labels.append(normalized)
            
            if debug:
                print("フィルターは適用しませんが、ラベルを正規化しました（大文字変換・トリミング）")
            
            labels = normalized_labels
        
        # ソートオプションに応じてソート
        if sort_order == 'asc':
            labels.sort()
        elif sort_order == 'desc':
            labels.sort(reverse=True)
        
        info["final_count"] = len(labels)
        
        return labels, info
        
    except Exception as e:
        print(f"エラーが発生しました: {str(e)}")
        if debug:
            import traceback
            traceback.print_exc()
        raise