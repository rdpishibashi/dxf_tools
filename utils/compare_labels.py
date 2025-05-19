import pandas as pd
import io
from collections import Counter
import os
from utils.extract_labels import extract_labels

def compare_labels_multi(file_pairs, filter_non_parts=False, sort_order="asc"):
    """
    複数のDXFファイルペアのラベル比較結果をExcelとして出力する
    
    Args:
        file_pairs: ファイルペアのリスト[(fileA_path, fileB_path, pair_name), ...]
        filter_non_parts: 回路記号（候補）のみを抽出するかどうか
        sort_order: ソート順（"asc"=昇順, "desc"=降順, "none"=ソートなし）
        
    Returns:
        bytes: 生成されたExcelファイルのバイナリデータ
    """
    # Excelファイルを作成するためのライターオブジェクト
    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    
    # 各ペアを処理
    for idx, (file_a, file_b, pair_name) in enumerate(file_pairs):
        # ラベルを抽出（extract_labelsを再利用）
        labels_a, info_a = extract_labels(file_a, filter_non_parts=filter_non_parts, sort_order=sort_order)
        labels_b, info_b = extract_labels(file_b, filter_non_parts=filter_non_parts, sort_order=sort_order)
        
        # ラベルの出現回数をカウント
        counter_a = Counter(labels_a)
        counter_b = Counter(labels_b)
        
        # すべてのユニークなラベルを取得
        all_labels = sorted(set(list(counter_a.keys()) + list(counter_b.keys())))
        
        # ファイルのファイル名を取得（パスから）
        file_a_name = os.path.basename(file_a)
        file_b_name = os.path.basename(file_b)
        
        # シート名を決定（最大31文字）
        if pair_name:
            # カスタム名がある場合
            sheet_name = f"Pair{idx+1}_{pair_name}"[:31]
        else:
            # ファイル名からシート名を生成
            sheet_name = f"Pair{idx+1}"[:31]
            
        # データフレームの作成
        df = pd.DataFrame({
            'Label': all_labels,
            file_a_name: [counter_a.get(label, 0) for label in all_labels],
            file_b_name: [counter_b.get(label, 0) for label in all_labels]
        })
        
        # ラベルがファイルAにのみ存在する（Aのみ）、ファイルBにのみ存在する（Bのみ）、
        # または両方に存在するが異なる回数（差異あり）、完全に一致（完全一致）を示す列を追加
        df['Status'] = df.apply(lambda row: 
            'A Only' if row[file_a_name] > 0 and row[file_b_name] == 0 else
            'B Only' if row[file_a_name] == 0 and row[file_b_name] > 0 else
            'Different Count' if row[file_a_name] != row[file_b_name] else
            'Same', axis=1)
        
        # 差分情報の列を追加（B - A）
        df['Diff (B-A)'] = df[file_b_name] - df[file_a_name]
        
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
        
        # ヘッダー行の書式を設定
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, format_header)
        
        # 条件付き書式の適用
        # 'Status'列が'A Only'の場合、行全体を淡い赤で表示
        # 'Status'列が'B Only'の場合、行全体を淡い緑で表示
        # 'Status'列が'Different Count'の場合、行全体を淡い黄で表示
        worksheet.conditional_format(1, 0, len(df), len(df.columns)-1, {
            'type': 'formula',
            'criteria': '=$D2="A Only"',
            'format': format_a_only
        })
        
        worksheet.conditional_format(1, 0, len(df), len(df.columns)-1, {
            'type': 'formula',
            'criteria': '=$D2="B Only"',
            'format': format_b_only
        })
        
        worksheet.conditional_format(1, 0, len(df), len(df.columns)-1, {
            'type': 'formula',
            'criteria': '=$D2="Different Count"',
            'format': format_different
        })
        
        # ヘッダー行を固定
        worksheet.freeze_panes(1, 0)
        
        # サマリー情報をシートの上部に追加
        summary_data = [
            [f"ファイルA: {file_a_name}", f"ラベル総数: {len(labels_a)}", f"ユニークラベル数: {len(counter_a)}"],
            [f"ファイルB: {file_b_name}", f"ラベル総数: {len(labels_b)}", f"ユニークラベル数: {len(counter_b)}"],
            ["", "", ""],
            ["差分サマリー:", "", ""],
            [f"Aのみのラベル: {sum(1 for s in df['Status'] if s == 'A Only')}", 
             f"Bのみのラベル: {sum(1 for s in df['Status'] if s == 'B Only')}", 
             f"異なる個数のラベル: {sum(1 for s in df['Status'] if s == 'Different Count')}"]
        ]
        
        # サマリーシートを追加
        if idx == 0:
            summary_sheet = workbook.add_worksheet("Summary")
            writer.sheets["Summary"] = summary_sheet
            
            # サマリーシートのタイトル
            title_format = workbook.add_format({
                'bold': True,
                'font_size': 14,
                'align': 'center',
                'valign': 'vcenter'
            })
            summary_sheet.merge_range('A1:D1', 'ラベル差分比較サマリー', title_format)
            
            # 各ペアの情報を追加
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
            summary_sheet.write(summary_row, 7, "ラベル総数", pair_header_format)
            
            summary_row += 1
            
        # サマリーシートにこのペアの情報を追加
        summary_sheet = writer.sheets["Summary"]
        summary_sheet.write(idx+3, 0, f"ペア{idx+1}")
        summary_sheet.write(idx+3, 1, sheet_name)
        summary_sheet.write(idx+3, 2, file_a_name)
        summary_sheet.write(idx+3, 3, file_b_name)
        summary_sheet.write(idx+3, 4, sum(1 for s in df['Status'] if s == 'A Only'))
        summary_sheet.write(idx+3, 5, sum(1 for s in df['Status'] if s == 'B Only'))
        summary_sheet.write(idx+3, 6, sum(1 for s in df['Status'] if s == 'Different Count'))
        summary_sheet.write(idx+3, 7, len(all_labels))
    
    # Excelファイルを保存
    writer.close()
    output.seek(0)
    
    return output.getvalue()
