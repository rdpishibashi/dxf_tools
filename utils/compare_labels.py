import ezdxf
import re
from collections import Counter

def extract_labels(dxf_file):
    """
    DXFファイルからラベル（MTEXTエンティティ）を抽出する
    
    Args:
        dxf_file: DXFファイルパス
        
    Returns:
        list: 抽出されたラベルのリスト
    """
    doc = ezdxf.readfile(dxf_file)
    msp = doc.modelspace()
    labels = []
    for e in msp:
        if e.dxftype() == 'MTEXT':
            text = e.dxf.text
            # フォーマットコードを削除
            cleaned_text = re.sub(r'\\[A-Za-z0-9.]+;', '', text)
            cleaned_text = cleaned_text.replace('\\P', ' ').strip()
            if cleaned_text:
                labels.append(cleaned_text)
    return labels

def compare_labels(dxf_file_a, dxf_file_b):
    """
    2つのDXFファイルのラベル差分をマークダウン形式で出力する
    
    Args:
        dxf_file_a: 基準DXFファイルパス
        dxf_file_b: 比較対象DXFファイルパス
        
    Returns:
        str: マークダウン形式の差分結果
    """
    # ラベルを抽出
    labels_a = Counter(extract_labels(dxf_file_a))
    labels_b = Counter(extract_labels(dxf_file_b))
    
    # マークダウン形式の出力を生成
    output = []
    output.append("## DXFラベル差分比較結果\n")
    
    output.append("### 追加されたラベル (added)")
    for label, count in (labels_b - labels_a).items():
        output.append(f"- {label} (+{count})")
    
    output.append("\n### 削除されたラベル (deleted)")
    for label, count in (labels_a - labels_b).items():
        output.append(f"- {label} (-{count})")
    
    return "\n".join(output)