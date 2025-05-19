import pandas as pd
import io
from collections import Counter
import os
import csv
import traceback

def normalize_label(label):
    """ラベルを正規化する（空白を削除し、大文字に変換）"""
    if label is None:
        return ""
    return label.strip().upper()

def parse_csv_line(line):
    """CSVフォーマットの行からラベル、メーカー名、製品名を抽出する"""
    try:
        # CSVフォーマットを適切に解析（カンマを含む値も適切に扱う）
        parts = list(csv.reader([line]))[0]
        
        # 最低でもラベルがある必要がある
        if not parts:
            return None, None, None
        
        label = parts[0].strip() if parts[0] else None
        
        # 2番目と3番目のデータがあれば、それぞれをメーカー名と製品名とする
        manufacturer = parts[1].strip() if len(parts) > 1 and parts[1] else None
        product_name = parts[2].strip() if len(parts) > 2 and parts[2] else None
        
        return label, manufacturer, product_name
    except Exception as e:
        print(f"CSVライン解析エラー: {str(e)}, line: {line}")
        # 解析エラーの場合はラベルのみを返し、他はNoneとする
        return line.strip(), None, None

def load_labels_from_file(file_path):
    """ファイルからラベルとメーカー情報を読み込み、正規化する"""
    labels = []
    manufacturers = []
    product_names = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:  # 空行を無視
                    continue
                
                # ラベル、メーカー名、製品名を抽出
                label, manufacturer, product_name = parse_csv_line(line)
                
                if label:
                    # ラベルを正規化（大文字変換・トリム）
                    label = normalize_label(label)
                    labels.append(label)
                    manufacturers.append(manufacturer)
                    product_names.append(product_name)
        
        return labels, manufacturers, product_names
    except Exception as e:
        print(f"エラー: ファイル '{file_path}' の読み込みに失敗しました: {str(e)}")
        traceback.print_exc()
        return [], [], []  # エラーの場合は空リストを返す

def compare_parts_list_multi(file_pairs):
    """
    複数のラベルファイルペアの比較結果をExcelとして出力する
    
    Args:
        file_pairs: ファイルペアのリスト[(fileA_path, fileB_path, pair_name), ...]
        
    Returns:
        bytes: 生成されたExcelファイルのバイナリデータ
    """
    try:
        # Excelファイルを作成するためのライターオブジェクト
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            
            # 各ペアを処理
            for idx, (file_a, file_b, pair_name) in enumerate(file_pairs):
                
                # ラベルを読み込み
                labels_a, manufacturers_a, product_names_a = load_labels_from_file(file_a)
                labels_b, manufacturers_b, product_names_b = load_labels_from_file(file_b)
                                
                # ラベルの出現回数をカウント
                counter_a = Counter(labels_a)
                counter_b = Counter(labels_b)
                
                # すべてのユニークなラベルを取得
                all_labels = sorted(set(list(counter_a.keys()) + list(counter_b.keys())))
                
                # ファイルのファイル名を取得（パスから）
                file_a_name = f"A: {os.path.basename(file_a)}"
                file_b_name = f"B: {os.path.basename(file_b)}"
                
                # メーカー情報とモデル情報をラベルごとに辞書化
                manufacturer_a_dict = {}
                product_name_a_dict = {}
                manufacturer_b_dict = {}
                product_name_b_dict = {}
                
                # ファイルAのメーカー情報とモデル情報をラベルごとに整理
                for i, label in enumerate(labels_a):
                    if i < len(manufacturers_a) and label not in manufacturer_a_dict and manufacturers_a[i]:
                        manufacturer_a_dict[label] = manufacturers_a[i]
                    if i < len(product_names_a) and label not in product_name_a_dict and product_names_a[i]:
                        product_name_a_dict[label] = product_names_a[i]
                
                # ファイルBのメーカー情報とモデル情報をラベルごとに整理
                for i, label in enumerate(labels_b):
                    if i < len(manufacturers_b) and label not in manufacturer_b_dict and manufacturers_b[i]:
                        manufacturer_b_dict[label] = manufacturers_b[i]
                    if i < len(product_names_b) and label not in product_name_b_dict and product_names_b[i]:
                        product_name_b_dict[label] = product_names_b[i]
                
                # シート名を決定（最大31文字）
                if pair_name:
                    # カスタム名がある場合
                    sheet_name = f"{pair_name}"[:31]
                else:
                    # ファイル名からシート名を生成
                    sheet_name = f"Pair{idx+1}"[:31]
                
                # 安全なシート名にする (Excelのシート名に使えない文字を置換)
                sheet_name = sheet_name.replace('/', '_').replace('\\', '_').replace('*', '_').replace('?', '_').replace('[', '_').replace(']', '_')
                
                # データフレームの作成
                data = {
                    'Label': all_labels,
                    file_a_name: [counter_a.get(label, 0) for label in all_labels],
                    file_b_name: [counter_b.get(label, 0) for label in all_labels]
                }
                
                # データフレーム作成
                df = pd.DataFrame(data)
                
                # ステータス列を追加
                df['Status'] = df.apply(lambda row: 
                    'A Only' if row[file_a_name] > 0 and row[file_b_name] == 0 else
                    'B Only' if row[file_a_name] == 0 and row[file_b_name] > 0 else
                    'Different' if row[file_a_name] != row[file_b_name] else
                    'Same', axis=1)
                
                # 差分情報の列を追加（B - A）
                df['Diff (B-A)'] = df[file_b_name] - df[file_a_name]
                
                # メーカー情報と製品名情報の列を追加
                df['Manufacturer A'] = [manufacturer_a_dict.get(label, None) for label in all_labels]
                df['Product Name A'] = [product_name_a_dict.get(label, None) for label in all_labels]
                df['Manufacturer B'] = [manufacturer_b_dict.get(label, None) for label in all_labels]
                df['Product Name B'] = [product_name_b_dict.get(label, None) for label in all_labels]
                
                # データフレームをExcelシートに出力
                df.to_excel(writer, sheet_name=sheet_name, index=False)
                
                # ワークシートとワークブックのオブジェクトを取得
                worksheet = writer.sheets[sheet_name]
                workbook = writer.book
                
                # セルの書式設定
                format_header = workbook.add_format({
                    'bold': True, 
                    'text_wrap': True, 
                    'valign': 'top', 
                    'border': 1,
                    'bg_color': '#D9E1F2'
                })
                
                format_a_only = workbook.add_format({'bg_color': '#FFC7CE'})  # 淡い赤
                format_b_only = workbook.add_format({'bg_color': '#C6EFCE'})  # 淡い緑
                format_different = workbook.add_format({'bg_color': '#FFEB9C'})  # 淡い黄
                
                # 列の幅を調整
                worksheet.set_column('A:A', 25)  # ラベル列
                worksheet.set_column('B:C', 15)  # ファイル列
                worksheet.set_column('D:D', 15)  # ステータス列
                worksheet.set_column('E:E', 10)  # 差分列
                worksheet.set_column('F:I', 20)  # メーカー情報と製品名情報
                
                # ヘッダー行の書式を設定
                for col_num, value in enumerate(df.columns.values):
                    worksheet.write(0, col_num, value, format_header)
                
                # 条件付き書式の適用
                worksheet.conditional_format(1, 0, len(df) + 1, len(df.columns) - 1, {
                    'type': 'formula',
                    'criteria': '=$D2="A Only"',
                    'format': format_a_only
                })
                
                worksheet.conditional_format(1, 0, len(df) + 1, len(df.columns) - 1, {
                    'type': 'formula',
                    'criteria': '=$D2="B Only"',
                    'format': format_b_only
                })
                
                worksheet.conditional_format(1, 0, len(df) + 1, len(df.columns) - 1, {
                    'type': 'formula',
                    'criteria': '=$D2="Different"',
                    'format': format_different
                })
                
                # ヘッダー行を固定
                worksheet.freeze_panes(1, 0)
                
                # サマリー情報を用意
                a_only_count = sum(1 for s in df['Status'] if s == 'A Only')
                b_only_count = sum(1 for s in df['Status'] if s == 'B Only')
                different_count = sum(1 for s in df['Status'] if s == 'Different')
                
                # サマリーシートを追加・更新
                if idx == 0:
                    summary_sheet = workbook.add_worksheet("Summary")
                    
                    # サマリーシートのタイトル
                    title_format = workbook.add_format({
                        'bold': True,
                        'font_size': 14,
                        'align': 'center',
                        'valign': 'vcenter'
                    })
                    summary_sheet.merge_range('A1:I1', '回路記号リスト差分比較サマリー', title_format)
                    
                    # 各ペアの情報を追加 - ヘッダー行
                    summary_row = 2
                    pair_header_format = workbook.add_format({
                        'bold': True,
                        'bg_color': '#4472C4',
                        'font_color': 'white'
                    })
                    summary_sheet.write(summary_row, 0, "ペア番号", pair_header_format)
                    summary_sheet.write(summary_row, 1, "シート名", pair_header_format)
                    summary_sheet.write(summary_row, 2, "ファイルA", pair_header_format)
                    summary_sheet.write(summary_row, 3, "ファイルB", pair_header_format)
                    summary_sheet.write(summary_row, 4, "Aのみ", pair_header_format)
                    summary_sheet.write(summary_row, 5, "Bのみ", pair_header_format)
                    summary_sheet.write(summary_row, 6, "異なる個数", pair_header_format)
                    summary_sheet.write(summary_row, 7, "共通", pair_header_format)
                    summary_sheet.write(summary_row, 8, "ラベル総数", pair_header_format)
                    
                    summary_sheet.set_column('A:A', 10)
                    summary_sheet.set_column('B:B', 15)
                    summary_sheet.set_column('C:D', 30)
                    summary_sheet.set_column('E:I', 15)
                
                # サマリーシートにこのペアの情報を追加
                summary_sheet = writer.sheets["Summary"]
                same_count = sum(1 for s in df['Status'] if s == 'Same')
                
                # ファイル名からパスを除去して表示用の名前を取得
                file_a_display = os.path.basename(file_a)
                file_b_display = os.path.basename(file_b)
                
                summary_sheet.write(idx+3, 0, f"ペア{idx+1}")
                summary_sheet.write(idx+3, 1, sheet_name)
                summary_sheet.write(idx+3, 2, file_a_display)  # 元のファイル名を表示
                summary_sheet.write(idx+3, 3, file_b_display)  # 元のファイル名を表示
                summary_sheet.write(idx+3, 4, a_only_count)
                summary_sheet.write(idx+3, 5, b_only_count)
                summary_sheet.write(idx+3, 6, different_count)
                summary_sheet.write(idx+3, 7, same_count)
                summary_sheet.write(idx+3, 8, len(all_labels))
        
        # Excelファイルのバイナリデータを返す
        output.seek(0)
        return output.getvalue()
    
    except Exception as e:
        print(f"Excel生成エラー: {str(e)}")
        traceback.print_exc()
        raise  # エラーを再スローして呼び出し元で処理できるようにする

# 後方互換性のために元のcompare_parts_list関数を残す
def compare_parts_list(dxf_labels_file, circuit_symbols_file):
    """
    2つのラベルファイルを比較し、結果をマークダウン形式で出力する
    
    Args:
        dxf_labels_file: 図面ラベルファイルのパス
        circuit_symbols_file: 回路記号ファイルのパス
        
    Returns:
        str: マークダウン形式の比較結果
    """
    try:
        dxf_labels, _, _ = load_labels_from_file(dxf_labels_file)
        circuit_symbols, _, _ = load_labels_from_file(circuit_symbols_file)

        # カウンターで集計
        dxf_counter = Counter(dxf_labels)
        circuit_counter = Counter(circuit_symbols)

        # 共通するユニークラベル数
        common_unique_labels_count = len(set(dxf_counter.keys()) & set(circuit_counter.keys()))

        # 図面に不足しているラベル（回路記号にはあるが図面にない）
        missing_in_dxf = circuit_counter - dxf_counter
        missing_in_dxf_expanded = sorted(list(missing_in_dxf.elements()))
        missing_in_dxf_total_count = len(missing_in_dxf_expanded)

        # 回路記号に不足しているラベル（図面にあるが回路記号にない）
        missing_in_circuit = dxf_counter - circuit_counter
        missing_in_circuit_expanded = sorted(list(missing_in_circuit.elements()))
        missing_in_circuit_total_count = len(missing_in_circuit_expanded)

        # マークダウン形式で出力を生成
        output = []
        output.append("## 図面ラベルと回路記号の差分比較結果\n")

        output.append("### 処理概要")
        output.append(f"- 図面ラベル数: {len(dxf_labels)} (ユニーク: {len(dxf_counter)})")
        output.append(f"- 回路記号数: {len(circuit_symbols)} (ユニーク: {len(circuit_counter)})")
        output.append(f"- 共通ユニークラベル数: {common_unique_labels_count}")
        output.append(f"- 図面に不足しているラベル総数: {missing_in_dxf_total_count}")
        output.append(f"- 回路記号に不足しているラベル総数: {missing_in_circuit_total_count}")
        output.append("")

        output.append("### 図面に不足しているラベル（回路記号リストには存在する）")
        if missing_in_dxf_expanded:
            for symbol in missing_in_dxf_expanded:
                output.append(f"- {symbol}")
        else:
            output.append("- なし")
        output.append("")

        output.append("### 回路記号リストに不足しているラベル（図面には存在する）")
        if missing_in_circuit_expanded:
            for label in missing_in_circuit_expanded:
                output.append(f"- {label}")
        else:
            output.append("- なし")
        output.append("")

        # 文字列として結果を返す
        return "\n".join(output)
    except Exception as e:
        # エラーメッセージをマークダウン形式で返す
        error_output = []
        error_output.append("## エラーが発生しました\n")
        error_output.append(f"エラー内容: {str(e)}")
        return "\n".join(error_output)