import ezdxf
import math

def compare_dxf_files_and_generate_dxf(file_a, file_b, output_file, tolerance=1e-6):
    """
    2つのDXFファイルを比較して差分をDXFファイルとして出力する
    
    Args:
        file_a: 基準DXFファイルパス
        file_b: 比較対象DXFファイルパス
        output_file: 出力DXFファイルパス
        tolerance: 浮動小数点比較の許容誤差
        
    Returns:
        bool: 処理の成否
    """
    try:
        # DXFファイルを読み込む
        doc_a = ezdxf.readfile(file_a)
        doc_b = ezdxf.readfile(file_b)

        # 比較結果を格納する新しいDXFドキュメントを作成
        doc_result = ezdxf.new('R2010')

        # レイヤーを作成
        doc_result.layers.new(name='ADDED', dxfattribs={'color': 3})  # 緑色: 追加された要素
        doc_result.layers.new(name='REMOVED', dxfattribs={'color': 1})  # 赤色: 削除された要素
        doc_result.layers.new(name='MODIFIED', dxfattribs={'color': 5})  # 青色: 変更された要素
        doc_result.layers.new(name='UNCHANGED', dxfattribs={'color': 7})  # 白色: 変更なしの要素

        # モデルスペースを取得
        msp_a = doc_a.modelspace()
        msp_b = doc_b.modelspace()
        msp_result = doc_result.modelspace()

        # エンティティのハンドルをキーとした辞書を作成
        entities_a = {}
        entities_b = {}

        # ファイルAのエンティティを処理
        for entity in msp_a:
            key = get_entity_key(entity, tolerance)
            entities_a[key] = entity

        # ファイルBのエンティティを処理
        for entity in msp_b:
            key = get_entity_key(entity, tolerance)
            entities_b[key] = entity

        # 削除された要素（ファイルAにあってファイルBにない要素）
        for key, entity in entities_a.items():
            if key not in entities_b:
                # エンティティをコピーして赤色レイヤーに配置
                copy_entity_to_result(entity, msp_result, 'REMOVED')

        # 追加された要素（ファイルBにあってファイルAにない要素）
        for key, entity in entities_b.items():
            if key not in entities_a:
                # エンティティをコピーして緑色レイヤーに配置
                copy_entity_to_result(entity, msp_result, 'ADDED')
            else:
                # 両方のファイルに存在する要素
                entity_a = entities_a[key]
                if is_entity_modified(entity_a, entity, tolerance):
                    # 変更された要素は青色レイヤーに配置
                    copy_entity_to_result(entity, msp_result, 'MODIFIED')
                else:
                    # 変更なしの要素は白色レイヤーに配置
                    copy_entity_to_result(entity, msp_result, 'UNCHANGED')

        # 結果を保存
        doc_result.saveas(output_file)
        return True
    except Exception as e:
        print(f"エラーが発生しました: {str(e)}")
        return False

def get_entity_key(entity, tolerance=1e-6):
    """
    エンティティを一意に識別するためのキーを生成
    
    Args:
        entity: DXFエンティティ
        tolerance: 浮動小数点比較の許容誤差
        
    Returns:
        str: エンティティキー
    """
    entity_type = entity.dxftype()

    # エンティティタイプに応じて識別キーを生成
    if entity_type == 'LINE':
        # LINEエンティティのキーを生成
        return f"LINE_{round_float(entity.dxf.start[0], tolerance)}_{round_float(entity.dxf.start[1], tolerance)}_{round_float(entity.dxf.end[0], tolerance)}_{round_float(entity.dxf.end[1], tolerance)}_{entity.dxf.layer}_{entity.dxf.linetype}"
    elif entity_type == 'CIRCLE':
        return f"CIRCLE_{round_float(entity.dxf.center[0], tolerance)}_{round_float(entity.dxf.center[1], tolerance)}_{round_float(entity.dxf.radius, tolerance)}"
    elif entity_type == 'ARC':
        return f"ARC_{round_float(entity.dxf.center[0], tolerance)}_{round_float(entity.dxf.center[1], tolerance)}_{round_float(entity.dxf.radius, tolerance)}_{round_float(entity.dxf.start_angle, tolerance)}_{round_float(entity.dxf.end_angle, tolerance)}"
    elif entity_type == 'TEXT':
        return f"TEXT_{round_float(entity.dxf.insert[0], tolerance)}_{round_float(entity.dxf.insert[1], tolerance)}_{entity.dxf.text}"
    elif entity_type == 'MTEXT':
        return f"MTEXT_{round_float(entity.dxf.insert[0], tolerance)}_{round_float(entity.dxf.insert[1], tolerance)}_{entity.text}"
    elif entity_type == 'LEADER':
        # LEADERエンティティのキーを生成
        return f"LEADER_{entity.dxf.layer}_{entity.dxf.linetype}"  # 例：レイヤーと線種をキーにする
    else:
        # その他のエンティティタイプの場合は、最小限の属性でキーを生成
        return f"{entity_type}_{entity.dxf.layer}_{entity.dxf.linetype}"

def round_float(value, tolerance=1e-6):
    """
    浮動小数点数を丸める
    
    Args:
        value: 浮動小数点数
        tolerance: 丸め誤差
        
    Returns:
        float: 丸められた値
    """
    return round(value / tolerance) * tolerance

def is_entity_modified(entity_a, entity_b, tolerance=1e-6):
    """
    2つのエンティティが異なるかどうかを判定
    
    Args:
        entity_a: 比較元エンティティ
        entity_b: 比較先エンティティ
        tolerance: 浮動小数点比較の許容誤差
        
    Returns:
        bool: 変更があればTrue
    """
    # エンティティタイプが異なる場合は変更されたとみなす
    if entity_a.dxftype() != entity_b.dxftype():
        return True

    # 属性を比較
    entity_type = entity_a.dxftype()
    if entity_type == 'LEADER':
        # LEADERエンティティの属性を比較
        if entity_a.dxf.layer != entity_b.dxf.layer:
            return True
        if entity_a.dxf.linetype != entity_b.dxf.linetype:
            return True
    elif entity_type == 'LINE':
        # LINEエンティティの属性を比較
        if not math.isclose(entity_a.dxf.start[0], entity_b.dxf.start[0], rel_tol=tolerance, abs_tol=tolerance):
            return True
        if not math.isclose(entity_a.dxf.start[1], entity_b.dxf.start[1], rel_tol=tolerance, abs_tol=tolerance):
            return True
        if not math.isclose(entity_a.dxf.end[0], entity_b.dxf.end[0], rel_tol=tolerance, abs_tol=tolerance):
            return True
        if not math.isclose(entity_a.dxf.end[1], entity_b.dxf.end[1], rel_tol=tolerance, abs_tol=tolerance):
            return True
        if entity_a.dxf.layer != entity_b.dxf.layer:
            return True
        if entity_a.dxf.linetype != entity_b.dxf.linetype:
            return True
    elif entity_type == 'TEXT':
        if entity_a.dxf.text != entity_b.dxf.text:
            return True
        if not math.isclose(entity_a.dxf.insert[0], entity_b.dxf.insert[0], rel_tol=tolerance, abs_tol=tolerance):
            return True
        if not math.isclose(entity_a.dxf.insert[1], entity_b.dxf.insert[1], rel_tol=tolerance, abs_tol=tolerance):
            return True
    elif entity_type == 'MTEXT':
        if entity_a.text != entity_b.text:
            return True
        if not math.isclose(entity_a.dxf.insert[0], entity_b.dxf.insert[0], rel_tol=tolerance, abs_tol=tolerance):
            return True
        if not math.isclose(entity_a.dxf.insert[1], entity_b.dxf.insert[1], rel_tol=tolerance, abs_tol=tolerance):
            return True
    else:
        # その他のエンティティタイプの場合は、最小限の属性で比較
        if entity_a.dxf.layer != entity_b.dxf.layer:
            return True
        if entity_a.dxf.linetype != entity_b.dxf.linetype:
            return True

    # すべての比較をパスした場合は変更なしとみなす
    return False

def copy_entity_to_result(entity, msp_result, layer_name):
    """
    エンティティを結果のモデルスペースにコピーし、指定されたレイヤーに配置
    
    Args:
        entity: コピー元エンティティ
        msp_result: 結果のモデルスペース
        layer_name: 配置先レイヤー名
    """
    entity_type = entity.dxftype()

    # エンティティタイプに応じてコピー処理
    if entity_type == 'LINE':
        msp_result.add_line(
            start=entity.dxf.start,
            end=entity.dxf.end,
            dxfattribs={'layer': layer_name}
        )
    elif entity_type == 'CIRCLE':
        msp_result.add_circle(
            center=entity.dxf.center,
            radius=entity.dxf.radius,
            dxfattribs={'layer': layer_name}
        )
    elif entity_type == 'ARC':
        msp_result.add_arc(
            center=entity.dxf.center,
            radius=entity.dxf.radius,
            start_angle=entity.dxf.start_angle,
            end_angle=entity.dxf.end_angle,
            dxfattribs={'layer': layer_name}
        )
    elif entity_type == 'TEXT':
        msp_result.add_text(
            text=entity.dxf.text,
            dxfattribs={
                'layer': layer_name,
                'insert': entity.dxf.insert,
                'height': entity.dxf.height,
                'rotation': entity.dxf.rotation if hasattr(entity.dxf, 'rotation') else 0
            }
        )
    elif entity_type == 'MTEXT':
        msp_result.add_mtext(
            text=entity.text,
            dxfattribs={
                'layer': layer_name,
                'insert': entity.dxf.insert,
                'char_height': entity.dxf.char_height,
                'width': entity.dxf.width if hasattr(entity.dxf, 'width') else 0
            }
        )
    elif entity_type == 'LEADER':
        # LEADERエンティティのコピー処理
        # LEADERの形状を再現するために、LINEエンティティに分解してコピーする
        try:
            points = entity.get_arrow_block_insert()
            msp_result.add_line(points[0], points[1], dxfattribs={'layer': layer_name})
        except:
            msp_result.add_text(
                text=f"[LEADER]",
                dxfattribs={
                    'layer': layer_name,
                    'insert': getattr(entity.dxf, 'insert', (0, 0, 0)) if hasattr(entity.dxf, 'insert') else (0, 0, 0),
                    'height': 2.5
                }
            )
    else:
        # その他のエンティティタイプの場合は簡易的な表示
        msp_result.add_text(
            text=f"[{entity_type}]",
            dxfattribs={
                'layer': layer_name,
                'insert': getattr(entity.dxf, 'insert', (0, 0, 0)) if hasattr(entity.dxf, 'insert') else (0, 0, 0),
                'height': 2.5
            }
        )