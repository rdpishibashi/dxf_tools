import os
import tempfile
import base64
import sys
import traceback

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