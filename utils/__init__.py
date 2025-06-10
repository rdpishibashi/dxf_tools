# utils パッケージ初期化ファイル

# これはPythonがutilsディレクトリをパッケージとして認識するための空ファイルです
# 特に何も実装する必要はありません

# ただし、利便性のために各モジュールの主要な関数をパッケージレベルでエクスポートします
from .extract_labels import extract_labels, get_layers_from_dxf, process_multiple_dxf_files
from .extract_hierarchy import extract_hierarchy
from .compare_dxf import compare_dxf_files_and_generate_dxf
from .compare_labels import compare_labels_multi as compare_labels
from .extract_symbols import extract_circuit_symbols, find_all_possible_assembly_numbers
from .compare_partslist import compare_parts_list_multi, normalize_label

# 共通ユーティリティから回路記号処理機能をエクスポート
try:
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from common_utils import (
        process_circuit_symbol_labels,
        filter_non_circuit_symbols,
        validate_circuit_symbols,
        validate_ref_designator,
        compile_ref_designator_patterns,
        convert_format_to_regex
    )
except ImportError:
    # common_utils.pyが見つからない場合は警告
    import warnings
    warnings.warn("共通ユーティリティ(common_utils.py)がインポートできませんでした", ImportWarning)