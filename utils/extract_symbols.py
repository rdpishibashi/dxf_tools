import pandas as pd
import os
import re

def extract_alphabetic_part(symbol):
    """
    回路記号からアルファベット部分を抽出する
    
    Args:
        symbol (str): 回路記号
        
    Returns:
        str: アルファベット部分
    """
    # アルファベット部分（先頭の連続したアルファベット）を抽出
    match = re.match(r'^([A-Za-z]+)', symbol)
    if match:
        return match.group(1)
    return ""

def extract_circuit_symbols(input_excel, assembly_number=None):
    """
    Excelファイルから回路記号リストを抽出する。
    
    Args:
        input_excel (str): 入力Excelファイルのパス
        assembly_number (str, optional): 図面番号（指定しない場合はファイル名から抽出）
        
    Returns:
        tuple: (回路記号リスト, 処理情報)
    """
    # 情報を格納する辞書を先に初期化
    info = {
        "assembly_number": assembly_number if assembly_number else os.path.splitext(os.path.basename(input_excel))[0],
        "total_rows": 0,
        "processed_rows": 0,
        "total_symbols": 0,
        "error": None
    }
    
    try:
        # アセンブリ番号がない場合は入力ファイル名から抽出
        if not assembly_number:
            filename = os.path.basename(input_excel)
            assembly_number = os.path.splitext(filename)[0]  # 拡張子を除いた部分
            info["assembly_number"] = assembly_number
        
        try:
            # Excelファイルを読み込む（1行目をヘッダーとして）
            df = pd.read_excel(input_excel, engine='openpyxl')
        except ImportError:
            # openpyxlがインストールされていない場合は代替エンジンを試す
            try:
                df = pd.read_excel(input_excel)
            except Exception as e:
                info["error"] = f"Excelファイルの読み込みに失敗しました: {str(e)}。依存関係 'openpyxl' をインストールしてください。"
                return [], info
        
        info["total_rows"] = len(df)
        
        # ファイルが存在し、必要な列があるか確認
        required_columns = ["符号", "構成コメント", "構成数", "図面番号"]
        for col in required_columns:
            if col not in df.columns:
                info["error"] = f"'{col}'列がExcelファイルに見つかりません"
                return [], info
        
        # 処理対象の行を特定
        start_processing = False
        processing_rows = []
        
        for i, row in df.iterrows():
            # アセンブリ番号と一致する図面番号を探す
            if not start_processing and pd.notna(row["図面番号"]) and str(row["図面番号"]) == assembly_number:
                start_processing = True
                continue  # 一致した行は処理対象外
            
            # 処理開始後、図面番号が空白の行を処理対象とする
            if start_processing:
                if pd.isna(row["図面番号"]) or str(row["図面番号"]).strip() == "":
                    processing_rows.append(i)
                else:
                    # 図面番号が空白でなくなったら処理終了
                    break
        
        info["processed_rows"] = len(processing_rows)
        
        if not processing_rows:
            info["error"] = f"処理対象となる行が見つかりません。図面番号 '{assembly_number}' が図面番号列に存在するか確認してください。"
            return [], info
        
        # 回路記号リストを格納するリスト
        circuit_symbols = []
        
        # 処理対象の行だけを処理
        for idx in processing_rows:
            row = df.iloc[idx]
            
            # 符号または構成コメントからシンボルを取得
            if pd.notna(row["構成コメント"]) and "_" in str(row["構成コメント"]):
                # 構成コメントに"_"が含まれる場合はそちらを使用
                base_symbols = str(row["構成コメント"]).split("_")
            else:
                # そうでなければ符号を使用
                symbol_str = str(row["符号"]) if pd.notna(row["符号"]) else ""
                base_symbols = symbol_str.split("_") if "_" in symbol_str else [symbol_str]
            
            # 数値型の場合は整数に変換する
            qty = int(row["構成数"]) if pd.notna(row["構成数"]) else 0
            
            # 空文字列を除外
            base_symbols = [s for s in base_symbols if s.strip()]
            
            # 回路記号の個数を取得
            symbol_count = len(base_symbols)
            
            # 最終的なシンボルリスト
            final_symbols = base_symbols.copy()
            
            # 回路記号の個数と構成数を比較
            if symbol_count < qty:
                # 最後の回路記号のアルファベット部分を取得
                last_alpha = ""
                if base_symbols:
                    last_alpha = extract_alphabetic_part(base_symbols[-1])
                
                # 不足分は"rrrrr-Xddd"で補完
                # rrrrrはアルファベット部分、dddは行ごとに001からのシーケンス番号
                for i in range(qty - symbol_count):
                    final_symbols.append(f"{last_alpha}-X{i+1:03d}")
            elif symbol_count > qty:
                # 超過分は最後から?をつける
                final_symbols = final_symbols[:qty]
                for i in range(symbol_count - qty):
                    if i < len(final_symbols):
                        final_symbols[qty-i-1] = final_symbols[qty-i-1] + "?"
            
            # 回路記号リストに追加
            circuit_symbols.extend(final_symbols)
        
        # 空文字列を削除
        circuit_symbols = [symbol for symbol in circuit_symbols if symbol]
        
        info["total_symbols"] = len(circuit_symbols)
        return circuit_symbols, info
        
    except Exception as e:
        info["error"] = str(e)
        return [], info