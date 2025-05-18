import ezdxf
import os
from io import StringIO

# バージョンに応じた TagWriter のインポート
try:
    from ezdxf.lldxf.writer import TagWriter  # ezdxf >= 0.19
except ImportError:
    from ezdxf.lldxf.tagwriter import TagWriter  # ezdxf < 0.19

def get_group_code_meaning(code):
    """
    DXFのグループコードの意味を返す
    
    Args:
        code: グループコード
        
    Returns:
        str: グループコードの意味
    """
    code_meanings = {
        0: "Entity Type", 1: "Primary Text String", 2: "Name", 3: "Additional Text",
        5: "Handle", 6: "Linetype", 7: "Text Style Name", 8: "Layer Name", 9: "Variable Name",
        10: "X Coordinate (Main)", 20: "Y Coordinate (Main)", 30: "Z Coordinate (Main)",
        40: "Double Precision Value", 50: "Angle", 62: "Color Number", 70: "Integer Value",
        210: "X Direction Vector", 220: "Y Direction Vector", 230: "Z Direction Vector", 999: "Comment"
    }
    return code_meanings.get(code, "Other")

def extract_entity_data(section_name, entity, blocks_dict=None):
    """
    エンティティのデータを抽出する
    
    Args:
        section_name: セクション名
        entity: DXFエンティティ
        blocks_dict: ブロック名をキーとした辞書（オプション）
        
    Returns:
        list: 抽出されたデータのリスト
    """
    rows = []
    entity_type = entity.dxftype()

    # エンティティの開始を示す行を追加
    rows.append([section_name, "Start", entity_type, 0, "Entity Type", entity_type])
    
    # BLOCKエンティティの場合、名前を取得して表示
    if entity_type == 'INSERT' and blocks_dict and hasattr(entity, 'dxf') and hasattr(entity.dxf, 'name'):
        block_name = entity.dxf.name
        rows.append([section_name, "", entity_type, "N/A", "Block Name", block_name])
    
    buffer = StringIO()
    tagwriter = TagWriter(buffer)
    entity.export_dxf(tagwriter)
    buffer.seek(0)
    lines = buffer.readlines()

    for i in range(0, len(lines)-1, 2):
        code_line = lines[i].strip()
        value_line = lines[i+1].strip()
        if code_line.isdigit():
            code = int(code_line)
            meaning = get_group_code_meaning(code)
            # code は整数型のまま保存
            rows.append([section_name, "", entity_type, code, meaning, value_line])

    # エンティティの終了を示す行を追加
    rows.append([section_name, "End", entity_type, 0, "Entity Type", entity_type])

    return rows

def extract_table_data(section_name, table_entry):
    """
    テーブルエントリのデータを抽出する
    
    Args:
        section_name: セクション名
        table_entry: テーブルエントリ
        
    Returns:
        list: 抽出されたデータのリスト
    """
    rows = []
    entry_type = table_entry.dxftype()
    
    # テーブルエントリの開始を示す行を追加
    rows.append([section_name, "Start", entry_type, "N/A", "TABLE Entry", entry_type])
    
    for key, value in table_entry.dxf.all_existing_dxf_attribs().items():
        # ここでは GroupCode を文字列 "N/A" として保存（一貫性を保つため）
        rows.append([section_name, "", entry_type, "N/A", "TABLE Entry", f"{key} = {value}"])
    
    # テーブルエントリの終了を示す行を追加
    rows.append([section_name, "End", entry_type, "N/A", "TABLE Entry", entry_type])
    
    return rows

def analyze_dxf_structure(dxf_file):
    """
    DXFファイルの構造を分析する
    
    Args:
        dxf_file: DXFファイルパス
        
    Returns:
        list: 構造データのリスト
        
    Note:
        戻り値のリストは、DataFrameの列として以下の順に格納される:
        [Section, Entity Marker, Entity, GroupCode, GroupCode Definition, Value]
    """
    doc = ezdxf.readfile(dxf_file)
    all_rows = []

    # HEADER
    all_rows.append(['HEADER', "Start", 'HEADER_SECTION', 0, "Section Start", "HEADER"])
    for varname in doc.header.varnames():
        value = doc.header.get(varname)
        all_rows.append(['HEADER', "", 'HEADER_VAR', 9, "Variable Name", f"{varname} = {value}"])
    all_rows.append(['HEADER', "End", 'HEADER_SECTION', 0, "Section End", "HEADER"])

    # TABLES
    all_rows.append(['TABLES', "Start", 'TABLES_SECTION', 0, "Section Start", "TABLES"])
    for table_name, table in {
        'LAYERS': doc.layers,
        'LTYPE': doc.linetypes,
        'STYLES': doc.styles,
        'DIMSTYLES': doc.dimstyles,
        'UCS': doc.ucs
    }.items():
        table_section = f"TABLES({table_name})"
        all_rows.append([table_section, "Start", 'TABLE', 0, "Table Start", table_name])
        for entry in table:
            all_rows.extend(extract_table_data(table_section, entry))
        all_rows.append([table_section, "End", 'TABLE', 0, "Table End", table_name])
    all_rows.append(['TABLES', "End", 'TABLES_SECTION', 0, "Section End", "TABLES"])

    # ブロック名をキーとした辞書を作成
    blocks_dict = {block.name: block for block in doc.blocks}

    # BLOCKS
    all_rows.append(['BLOCKS', "Start", 'BLOCKS_SECTION', 0, "Section Start", "BLOCKS"])
    for block in doc.blocks:
        block_name = block.name
        all_rows.append(['BLOCKS', "Start", 'BLOCK', 0, "Block Start", block_name])
        for entity in block:
            all_rows.extend(extract_entity_data('BLOCKS', entity, blocks_dict))
        all_rows.append(['BLOCKS', "End", 'BLOCK', 0, "Block End", block_name])
    all_rows.append(['BLOCKS', "End", 'BLOCKS_SECTION', 0, "Section End", "BLOCKS"])

    # ENTITIES
    all_rows.append(['ENTITIES', "Start", 'ENTITIES_SECTION', 0, "Section Start", "ENTITIES"])
    msp = doc.modelspace()
    for entity in msp:
        all_rows.extend(extract_entity_data('ENTITIES', entity, blocks_dict))
    all_rows.append(['ENTITIES', "End", 'ENTITIES_SECTION', 0, "Section End", "ENTITIES"])

    # OBJECTS
    all_rows.append(['OBJECTS', "Start", 'OBJECTS_SECTION', 0, "Section Start", "OBJECTS"])
    for obj in doc.objects:
        all_rows.extend(extract_entity_data('OBJECTS', obj))
    all_rows.append(['OBJECTS', "End", 'OBJECTS_SECTION', 0, "Section End", "OBJECTS"])

    # CLASSES コメント行
    all_rows.append(['CLASSES', "Start", 'CLASSES_SECTION', 0, "Section Start", "CLASSES"])
    # CLASSESコメント行のGroupCodeをN/Aから文字列に変換
    all_rows.append(['CLASSES', "", 'INFO', "N/A", 'Info', 'CLASSES セクションは存在すればファイル内に含まれます'])
    all_rows.append(['CLASSES', "End", 'CLASSES_SECTION', 0, "Section End", "CLASSES"])

    return all_rows

def get_default_output_filename(input_dxf, output_format='xlsx'):
    """
    入力DXFファイル名から適切な出力ファイル名を生成する
    
    Args:
        input_dxf: 入力DXFファイル名
        output_format: 出力形式 ('xlsx' または 'csv')
        
    Returns:
        str: デフォルトの出力ファイル名
    """
    base_name = os.path.splitext(input_dxf)[0]
    if output_format.lower() == 'csv':
        return f"{base_name}.csv"
    else:
        return f"{base_name}.xlsx"
