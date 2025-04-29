#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
from collections import Counter

def normalize_label(label):
    """ラベルを正規化する（空白を削除し、大文字に変換）"""
    if label is None:
        return ""
    return label.strip().upper()

def load_labels_from_file(file_path):
    """ファイルからラベルを読み込み、正規化する"""
    labels = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                label = line.strip()
                if label:  # 空行を無視
                    # ラベルを正規化（大文字変換・トリム）
                    label = normalize_label(label)
                    labels.append(label)
        return labels
    except Exception as e:
        print(f"エラー: ファイル '{file_path}' の読み込みに失敗しました: {str(e)}")
        return [] # エラーの場合は空リストを返す

def compare_parts_list(dxf_labels_file, circuit_symbols_file):
    """2つのラベルファイルを比較し、結果をマークダウン形式で出力する"""
    try:
        dxf_labels = load_labels_from_file(dxf_labels_file)
        circuit_symbols = load_labels_from_file(circuit_symbols_file)

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