import os
import tempfile
import base64
import sys
import traceback
import re

def save_uploadedfile(uploadedfile):
    """アップロードされたファイルを一時ディレクトリに保存する"""
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploadedfile.name)[1]) as f:
        f.write(uploadedfile.getbuffer())
        return f.name

def create_download_link(data, filename, text="Download file"):
    """ダウンロード用のリンクを生成する（非推奨、st.download_buttonを使用すべき）"""
    b64 = base64.b64encode(data).decode()
    href = f'<a href="data:file/octet-stream;base64,{b64}" download="{filename}">{text}</a>'
    return href

def get_output_filename(input_filename, tool_type, extension=None):
    """
    統一されたファイル名生成関数
    
    Args:
        input_filename: 入力ファイル名
        tool_type: ツールタイプの識別子
        extension: 出力ファイルの拡張子
        
    Returns:
        str: 適切な出力ファイル名
    """
    # 拡張子を除いたファイル名の基本部分を取得
    base_name = os.path.splitext(input_filename)[0]
    
    # まだ拡張子が残っている可能性があるため、再度処理
    # 例: "file.xlsx.dxf" → "file.xlsx" → "file"
    while '.' in base_name:
        base_name = os.path.splitext(base_name)[0]
    
    # ツールタイプに応じたサフィックスとファイル形式を追加
    if tool_type == 'labels':
        return f"{base_name}_labels.txt" if not extension else f"{base_name}_labels.{extension}"
    elif tool_type == 'diff':
        return f"{base_name}_diff.dxf" if not extension else f"{base_name}_diff.{extension}"
    elif tool_type == 'label_diff':
        return f"{base_name}_label_diff.md" if not extension else f"{base_name}_label_diff.{extension}"
    elif tool_type == 'symbols':
        return f"{base_name}_symbols.txt" if not extension else f"{base_name}_symbols.{extension}"
    elif tool_type == 'partslist_diff':
        return f"{base_name}_partslist_diff.md" if not extension else f"{base_name}_partslist_diff.{extension}"
    else:
        # デフォルト
        if extension:
            return f"{base_name}.{extension}"
        return f"{base_name}.{tool_type}"

def get_comparison_filename(file_a_name, file_b_name, tool_type, extension=None):
    """
    2つのファイルを比較する場合のファイル名生成関数
    
    Args:
        file_a_name: 1つ目のファイル名
        file_b_name: 2つ目のファイル名
        tool_type: ツールタイプの識別子
        extension: 出力ファイルの拡張子
        
    Returns:
        str: 比較結果を表す出力ファイル名
    """
    # 拡張子を除いたファイル名を取得
    file_a_base = os.path.splitext(file_a_name)[0]
    file_b_base = os.path.splitext(file_b_name)[0]
    
    # まだ拡張子が残っている可能性があるため、再度処理
    while '.' in file_a_base:
        file_a_base = os.path.splitext(file_a_base)[0]
    while '.' in file_b_base:
        file_b_base = os.path.splitext(file_b_base)[0]
    
    # ツールタイプに応じたファイル名を生成
    if tool_type == 'diff':
        return f"{file_a_base}_vs_{file_b_base}.dxf" if not extension else f"{file_a_base}_vs_{file_b_base}.{extension}"
    elif tool_type == 'label_diff':
        return f"{file_a_base}_vs_{file_b_base}_label_diff.md" if not extension else f"{file_a_base}_vs_{file_b_base}_label_diff.{extension}"
    elif tool_type == 'partslist_diff':
        return f"{file_a_base}_vs_{file_b_base}_partslist_diff.md" if not extension else f"{file_a_base}_vs_{file_b_base}_partslist_diff.{extension}"
    else:
        # デフォルト
        if extension:
            return f"{file_a_base}_vs_{file_b_base}.{extension}"
        return f"{file_a_base}_vs_{file_b_base}.{tool_type}"

def handle_error(e, show_traceback=True):
    """エラーを適切に処理して表示する"""
    import streamlit as st
    st.error(f"エラーが発生しました: {str(e)}")
    if show_traceback:
        st.error(traceback.format_exc())


# ========================================
# 機器符号処理関連の共通機能
# ========================================

# ref_designator_format.txt の内容を埋め込み
REF_DESIGNATOR_FORMATS = [
    "CBnnn",
    "CBnnna",
    "CPnnn",
    "CPnnna",
    "CPBnnn",
    "ELB(CB) nnn",
    "ELB(CB) nnna",
    "ELBnnn",
    "ELBnnna",
    "Fnnn",
    "Fnnna",
    "",  # 空行
    "Annn",
    "Bnnn",
    "R",
    "Rn",
    "S",
    "Sn",
    "Snnn",
    "Tn",
    "Tnnn",
    "Tnnna",
    "P",
    "Pnnn",
    "Pnnna",
    "Nnnn",
    "U",
    "V",
    "Vnnn",
    "Vnnna",
    "UPnnn",
    "UNnna",
    "Wnnna"
]

def convert_format_to_regex(format_str):
    """
    フォーマット文字列を正規表現パターンに変換する
    
    Args:
        format_str: フォーマット文字列（例: "CBnnn", "ELB(CB) nnn"）
        
    Returns:
        str: 正規表現パターン
    """
    if not format_str or format_str.strip() == "":
        return None
    
    # 特殊文字をエスケープ
    pattern = re.escape(format_str)
    
    # エスケープされた文字を元に戻して変換
    # "n" → 数字1文字
    pattern = pattern.replace('n', '\\d')
    # "a" → 大文字アルファベット1文字  
    pattern = pattern.replace('a', '[A-Z]')
    
    # 完全一致パターンとして返す
    return f"^{pattern}$"

def compile_ref_designator_patterns():
    """
    機器符号フォーマットのパターンリストをコンパイルする
    
    Returns:
        list: コンパイル済み正規表現オブジェクトのリスト
    """
    patterns = []
    for format_str in REF_DESIGNATOR_FORMATS:
        regex_pattern = convert_format_to_regex(format_str)
        if regex_pattern:
            try:
                compiled_pattern = re.compile(regex_pattern)
                patterns.append(compiled_pattern)
            except re.error:
                # 正規表現のコンパイルエラーの場合はスキップ
                continue
    return patterns

def validate_ref_designator(label, patterns):
    """
    ラベルが参考指示子フォーマットに適合するかチェックする
    
    Args:
        label: チェック対象のラベル
        patterns: コンパイル済み正規表現パターンのリスト
        
    Returns:
        bool: 適合する場合True、しない場合False
    """
    for pattern in patterns:
        if pattern.match(label):
            return True
    return False

def filter_non_circuit_symbols(labels, debug=False):
    """
    機器符号以外と判断されるラベルをフィルタリングする
    
    Args:
        labels: ラベルのリスト
        debug: デバッグ情報を出力するかどうか
        
    Returns:
        tuple: (フィルタリング後のラベルリスト, フィルタリングで除外されたラベル数)
    """
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
    
    # デバッグ情報
    if debug and filtered_out:
        print(f"フィルタリングで除外されたラベル: {filtered_out}")
    
    return filtered_labels, len(labels) - len(filtered_labels)

def validate_circuit_symbols(labels):
    """
    機器符号の妥当性をチェックし、適合しないものを返す
    
    Args:
        labels: チェック対象のラベルリスト
        
    Returns:
        list: 適合しない機器符号のリスト（ユニーク、アルファベット順）
    """
    patterns = compile_ref_designator_patterns()
    invalid_designators = []
    
    for label in labels:
        if not validate_ref_designator(label, patterns):
            invalid_designators.append(label)
    
    # ユニークかつアルファベット順でソート
    return sorted(list(set(invalid_designators)))

def process_circuit_symbol_labels(labels, filter_non_parts=False, validate_ref_designators=False, debug=False):
    """
    ラベルに対して機器符号処理を統合的に実行する
    
    Args:
        labels: 処理対象のラベルリスト
        filter_non_parts: 機器符号以外のラベルをフィルタリングするかどうか
        validate_ref_designators: 機器符号の妥当性をチェックするかどうか
        debug: デバッグ情報を表示するかどうか
        
    Returns:
        dict: 処理結果を含む辞書
            - 'labels': 処理後のラベルリスト
            - 'filtered_count': フィルタリングで除外されたラベル数
            - 'invalid_ref_designators': 適合しない機器符号のリスト（妥当性チェック有効時のみ）
    """
    result = {
        'labels': labels.copy(),
        'filtered_count': 0,
        'invalid_ref_designators': []
    }
    
    # フィルタリング処理
    if filter_non_parts:
        filtered_labels, filtered_count = filter_non_circuit_symbols(labels, debug)
        result['labels'] = filtered_labels
        result['filtered_count'] = filtered_count
    
    # 機器符号妥当性チェック（フィルタリング後のラベルに対して実行）
    if validate_ref_designators and filter_non_parts:
        invalid_designators = validate_circuit_symbols(result['labels'])
        result['invalid_ref_designators'] = invalid_designators
    
    return result