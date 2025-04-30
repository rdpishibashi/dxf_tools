import pandas as pd
import os
import re
import traceback

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

def extract_assembly_number_from_filename(filename):
    """
    ファイル名からアセンブリ番号を抽出する
    '_'以降がアセンブリ番号として扱われる
    例: 'ULKES構成_EE6312-000-01A.xlsx' → 'EE6312-000-01A'
    
    Args:
        filename (str): ファイル名
        
    Returns:
        str: アセンブリ番号
    """
    # 拡張子を除いたファイル名を取得
    base_name = os.path.splitext(os.path.basename(filename))[0]
    
    # '_'で分割し、'_'以降の部分をアセンブリ番号として返す
    parts = base_name.split('_', 1)
    if len(parts) > 1:
        return parts[1]  # '_'以降の部分を返す
    
    # '_'がない場合はファイル名全体をアセンブリ番号として返す
    return base_name

def find_all_possible_assembly_numbers(df):
    """
    Excelファイル内の全ての可能なアセンブリ番号（図面番号）を抽出する
    図面番号の下に空白行がある図面番号のみを対象とする
    
    Args:
        df (pandas.DataFrame): Excelファイルから読み込んだデータフレーム
        
    Returns:
        list: 可能なアセンブリ番号のリスト
    """
    possible_assemblies = []
    
    for i in range(len(df) - 1):  # 最後の行は次の行がないので対象外
        current_row = df.iloc[i]
        next_row = df.iloc[i + 1]
        
        # 現在の行に図面番号があり、次の行の図面番号が空白の場合
        if (pd.notna(current_row["図面番号"]) and 
            (pd.isna(next_row["図面番号"]) or str(next_row["図面番号"]).strip() == "")):
            possible_assemblies.append(str(current_row["図面番号"]))
    
    return possible_assemblies

def extract_circuit_symbols(input_excel, assembly_number=None, use_all_assemblies=False, include_maker_info=False):
    """
    Excelファイルから回路記号リストを抽出する。
    
    Args:
        input_excel (str): 入力Excelファイルのパス
        assembly_number (str, optional): 図面番号（指定しない場合はファイル名から抽出）
        use_all_assemblies (bool): 全ての可能なアセンブリ番号を使用するかどうか
        include_maker_info (bool): メーカー名とメーカー型式を出力に含めるかどうか
        
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
            suggested_assembly_number = extract_assembly_number_from_filename(filename)
            info["assembly_number"] = suggested_assembly_number
        else:
            suggested_assembly_number = assembly_number
        
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
        
        # メーカー情報を含める場合は追加の列が必要
        if include_maker_info:
            required_columns.extend(["メーカ名", "メーカ型式"])
        
        for col in required_columns:
            if col not in df.columns:
                info["error"] = f"'{col}'列がExcelファイルに見つかりません"
                return [], info
        
        # 使用するアセンブリ番号のリストを初期化
        assembly_numbers = []
        
        # 全てのアセンブリを使用するオプションが有効な場合
        if use_all_assemblies:
            possible_assemblies = find_all_possible_assembly_numbers(df)
            if possible_assemblies:
                assembly_numbers = possible_assemblies
                info["assembly_number"] = ",".join(assembly_numbers)
            else:
                # アセンブリ番号が見つからなかった場合でも、ファイル名から抽出したものを使用
                assembly_numbers = [suggested_assembly_number]
        else:
            # 抽出されたアセンブリ番号が図面番号に存在するか確認
            assembly_found = False
            for i, row in df.iterrows():
                if pd.notna(row["図面番号"]) and str(row["図面番号"]) == suggested_assembly_number:
                    assembly_numbers = [suggested_assembly_number]
                    assembly_found = True
                    break
            
            # アセンブリ番号が見つからなかった場合は、ファイル名全体を使用
            if not assembly_found:
                assembly_number = os.path.splitext(os.path.basename(input_excel))[0]
                info["assembly_number"] = assembly_number
                assembly_numbers = [assembly_number]
        
        # すべての回路記号を格納するリスト
        all_circuit_symbols = []
        total_processed_rows = 0
        
        # 各アセンブリ番号について処理を実行
        for assembly_number in assembly_numbers:
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
            
            total_processed_rows += len(processing_rows)
            
            if not processing_rows:
                continue  # 処理対象の行がない場合は次のアセンブリ番号へ
            
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
                
                # メーカー情報を含める場合
                if include_maker_info:
                    maker_name = str(row["メーカ名"]) if pd.notna(row["メーカ名"]) else ""
                    maker_model = str(row["メーカ型式"]) if pd.notna(row["メーカ型式"]) else ""
                    
                    # 各シンボルにメーカー情報を追加
                    symbols_with_info = []
                    for symbol in final_symbols:
                        if symbol:  # 空文字列でない場合
                            symbols_with_info.append(f"{symbol},{maker_name},{maker_model}")
                    
                    # 回路記号リストに追加
                    circuit_symbols.extend(symbols_with_info)
                else:
                    # メーカー情報を含めない場合は、シンボルのみを追加
                    circuit_symbols.extend([s for s in final_symbols if s])  # 空文字列を除外
            
            # 全てのシンボルリストに追加
            all_circuit_symbols.extend(circuit_symbols)
        
        # 処理情報の更新
        info["processed_rows"] = total_processed_rows
        info["total_symbols"] = len(all_circuit_symbols)
        
        # 空文字列を削除
        all_circuit_symbols = [symbol for symbol in all_circuit_symbols if symbol]
        
        return all_circuit_symbols, info
        
    except Exception as e:
        traceback.print_exc()
        info["error"] = str(e)
        return [], info