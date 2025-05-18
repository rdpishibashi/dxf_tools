import ezdxf
import math
from ezdxf.addons.importer import Importer # Importerはブロックインポートで引き続き使用

# y_offset_for_file_b 引数を追加
def compare_dxf_files_and_generate_dxf(file_a, file_b, output_file, tolerance=1e-6, y_offset_for_file_b=0.0):
    try:
        doc_a = ezdxf.readfile(file_a)
        doc_b = ezdxf.readfile(file_b)
        doc_result = ezdxf.new('R2010')

        # --- ブロック定義のインポート (前回の修正を維持) ---
        if doc_a:
            print(f"Importing blocks from file_a...")
            try:
                importer_a = Importer(doc_a, doc_result)
                block_names_a = [block.name for block in doc_a.blocks if not block.name.lower().startswith('*')]
                if block_names_a:
                    importer_a.import_blocks(block_names_a) # block_names引数を渡す
                    print(f"Blocks imported from file_a: {len(block_names_a)} blocks processed.")
                else:
                    print(f"No user-defined blocks found in file_a to import.")
            except Exception as import_e_a:
                print(f"DXF block import (file_a) error: {str(import_e_a)}")

        if doc_b:
            print(f"Importing blocks from file_b...")
            try:
                importer_b = Importer(doc_b, doc_result)
                block_names_b = [block.name for block in doc_b.blocks if not block.name.lower().startswith('*')]
                blocks_to_import_from_b = [bn for bn in block_names_b if bn not in doc_result.blocks]
                if blocks_to_import_from_b:
                    importer_b.import_blocks(blocks_to_import_from_b) # block_names引数を渡す
                    print(f"Blocks imported from file_b: {len(blocks_to_import_from_b)} blocks processed.")
                else:
                    print(f"No new user-defined blocks found in file_b to import.")
            except Exception as import_e_b:
                print(f"DXF block import (file_b) error: {str(import_e_b)}")
        # --- インポート処理ここまで ---

        # レイヤー作成
        doc_result.layers.new(name='ADDED', dxfattribs={'color': 3})
        doc_result.layers.new(name='REMOVED', dxfattribs={'color': 1})
        doc_result.layers.new(name='MODIFIED', dxfattribs={'color': 5})
        doc_result.layers.new(name='UNCHANGED', dxfattribs={'color': 7})

        msp_a = doc_a.modelspace()
        msp_b = doc_b.modelspace()
        msp_result = doc_result.modelspace()

        entities_a = {}
        entities_b = {}

        # ファイルAのエンティティを処理 (オフセットなし)
        for entity in msp_a:
            key = get_entity_key(entity, tolerance, y_offset=0.0) # y_offset引数を追加
            entities_a[key] = entity

        # ファイルBのエンティティを処理 (指定されたYオフセットを適用)
        for entity in msp_b:
            key = get_entity_key(entity, tolerance, y_offset=y_offset_for_file_b) # y_offset引数を追加
            entities_b[key] = entity

        processed_b_keys = set()

        for key_a, entity_a_val in entities_a.items():
            if key_a in entities_b: # entities_bのキーはオフセット補正済み
                entity_b_val = entities_b[key_a]
                processed_b_keys.add(key_a) # entities_b側のキーとして記録 (key_aとkey_bは同じはず)
                # is_entity_modifiedにもオフセットを渡して比較
                if is_entity_modified(entity_a_val, entity_b_val, tolerance, y_offset_for_b=y_offset_for_file_b):
                    # 変更ありと判断された場合、file_b のエンティティを元の座標でコピー
                    copy_entity_to_result(entity_b_val, msp_result, 'MODIFIED')
                else:
                    # 変更なしと判断された場合、file_a (またはfile_bの元の座標で) のエンティティをコピー
                    copy_entity_to_result(entity_a_val, msp_result, 'UNCHANGED')
            else: # entities_a にのみ存在 (オフセット考慮後の比較で)
                copy_entity_to_result(entity_a_val, msp_result, 'REMOVED')

        # entities_b にのみ存在するものを ADDED として処理
        for key_b, entity_b_val in entities_b.items():
            if key_b not in processed_b_keys: # entities_a のキーセット(オフセット0で生成) と比較するのではなく、
                                             # processed_b_keys にないものを処理
                copy_entity_to_result(entity_b_val, msp_result, 'ADDED')

        doc_result.saveas(output_file)
        return True
    except Exception as e:
        print(f"エラーが発生しました: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

# get_entity_key 関数に y_offset 引数を追加
def get_entity_key(entity, tolerance=1e-6, y_offset=0.0): # y_offset引数を追加
    entity_type = entity.dxftype()
    layer = entity.dxf.layer
    linetype = entity.dxf.linetype # 既存のコードに合わせてlinetypeもキーに含める

    if entity_type == 'LINE':
        start_x = entity.dxf.start[0]
        start_y = entity.dxf.start[1] - y_offset # Yオフセット適用
        end_x = entity.dxf.end[0]
        end_y = entity.dxf.end[1] - y_offset   # Yオフセット適用
        return f"LINE_{round_float(start_x, tolerance)}_{round_float(start_y, tolerance)}_{round_float(end_x, tolerance)}_{round_float(end_y, tolerance)}_{layer}_{linetype}"
    elif entity_type == 'CIRCLE':
        center_x = entity.dxf.center[0]
        center_y = entity.dxf.center[1] - y_offset # Yオフセット適用
        radius = entity.dxf.radius
        # layer, linetype もキーに含めるとより厳密になる
        return f"CIRCLE_{round_float(center_x, tolerance)}_{round_float(center_y, tolerance)}_{round_float(radius, tolerance)}_{layer}_{linetype}"
    elif entity_type == 'ARC':
        center_x = entity.dxf.center[0]
        center_y = entity.dxf.center[1] - y_offset # Yオフセット適用
        radius = entity.dxf.radius
        start_angle = entity.dxf.start_angle
        end_angle = entity.dxf.end_angle
        return f"ARC_{round_float(center_x, tolerance)}_{round_float(center_y, tolerance)}_{round_float(radius, tolerance)}_{round_float(start_angle, tolerance)}_{round_float(end_angle, tolerance)}_{layer}_{linetype}"
    elif entity_type == 'TEXT':
        insert_x = entity.dxf.insert[0]
        insert_y = entity.dxf.insert[1] - y_offset # Yオフセット適用
        text_val = entity.dxf.text
        # 高さや回転などもキーに含めることを検討
        height = entity.dxf.height
        rotation = entity.dxf.get('rotation', 0.0)
        return f"TEXT_{round_float(insert_x, tolerance)}_{round_float(insert_y, tolerance)}_{text_val}_{round_float(height, tolerance)}_{round_float(rotation, tolerance)}_{layer}_{linetype}"
    elif entity_type == 'MTEXT':
        insert_x = entity.dxf.insert[0]
        insert_y = entity.dxf.insert[1] - y_offset # Yオフセット適用
        text_val = entity.text # MTEXTの場合は .text から取得
        char_height = entity.dxf.char_height
        rotation = entity.dxf.get('rotation', 0.0)
        return f"MTEXT_{round_float(insert_x, tolerance)}_{round_float(insert_y, tolerance)}_{text_val}_{round_float(char_height, tolerance)}_{round_float(rotation, tolerance)}_{layer}_{linetype}"
    elif entity_type == 'LEADER': # LEADERは元のコードを参照
        return f"LEADER_{layer}_{linetype}"
    # POINTエンティティなど、他のエンティティタイプも必要に応じてYオフセットを適用
    elif entity_type == 'POINT':
        loc_x = entity.dxf.location[0]
        loc_y = entity.dxf.location[1] - y_offset # Yオフセット適用
        return f"POINT_{round_float(loc_x, tolerance)}_{round_float(loc_y, tolerance)}_{layer}_{linetype}"
    elif entity_type == 'INSERT': # INSERTエンティティもYオフセットを適用
        insert_x = entity.dxf.insert[0]
        insert_y = entity.dxf.insert[1] - y_offset # Yオフセット適用
        block_name = entity.dxf.name
        xscale = entity.dxf.get('xscale', 1.0)
        yscale = entity.dxf.get('yscale', 1.0)
        rotation = entity.dxf.get('rotation', 0.0)
        return f"INSERT_{block_name}_{round_float(insert_x, tolerance)}_{round_float(insert_y, tolerance)}_{round_float(xscale,tolerance)}_{round_float(yscale,tolerance)}_{round_float(rotation,tolerance)}_{layer}"
    else:
        # その他のエンティティタイプの場合は、元のキー生成ロジックをベースに
        # Y座標を含む可能性のある属性があればオフセットを適用
        return f"{entity_type}_{layer}_{linetype}"

# is_entity_modified 関数に y_offset_for_b 引数を追加
def is_entity_modified(entity_a, entity_b, tolerance=1e-6, y_offset_for_b=0.0): # y_offset_for_b引数を追加
    if entity_a.dxftype() != entity_b.dxftype():
        return True

    entity_type = entity_a.dxftype()
    # 各エンティティタイプに応じて、Y座標比較時にオフセットを考慮
    if entity_type == 'LINE':
        if not math.isclose(entity_a.dxf.start[0], entity_b.dxf.start[0], rel_tol=tolerance, abs_tol=tolerance) or \
           not math.isclose(entity_a.dxf.start[1], entity_b.dxf.start[1] - y_offset_for_b, rel_tol=tolerance, abs_tol=tolerance) or \
           not math.isclose(entity_a.dxf.end[0], entity_b.dxf.end[0], rel_tol=tolerance, abs_tol=tolerance) or \
           not math.isclose(entity_a.dxf.end[1], entity_b.dxf.end[1] - y_offset_for_b, rel_tol=tolerance, abs_tol=tolerance):
            return True
    elif entity_type == 'CIRCLE':
        if not math.isclose(entity_a.dxf.center[0], entity_b.dxf.center[0], rel_tol=tolerance, abs_tol=tolerance) or \
           not math.isclose(entity_a.dxf.center[1], entity_b.dxf.center[1] - y_offset_for_b, rel_tol=tolerance, abs_tol=tolerance) or \
           not math.isclose(entity_a.dxf.radius, entity_b.dxf.radius, rel_tol=tolerance, abs_tol=tolerance):
            return True
    elif entity_type == 'ARC':
        if not math.isclose(entity_a.dxf.center[0], entity_b.dxf.center[0], rel_tol=tolerance, abs_tol=tolerance) or \
           not math.isclose(entity_a.dxf.center[1], entity_b.dxf.center[1] - y_offset_for_b, rel_tol=tolerance, abs_tol=tolerance) or \
           not math.isclose(entity_a.dxf.radius, entity_b.dxf.radius, rel_tol=tolerance, abs_tol=tolerance) or \
           not math.isclose(entity_a.dxf.start_angle, entity_b.dxf.start_angle, rel_tol=tolerance, abs_tol=tolerance) or \
           not math.isclose(entity_a.dxf.end_angle, entity_b.dxf.end_angle, rel_tol=tolerance, abs_tol=tolerance):
            return True
    elif entity_type == 'TEXT':
        # テキスト内容、高さ、回転なども比較
        if not math.isclose(entity_a.dxf.insert[0], entity_b.dxf.insert[0], rel_tol=tolerance, abs_tol=tolerance) or \
           not math.isclose(entity_a.dxf.insert[1], entity_b.dxf.insert[1] - y_offset_for_b, rel_tol=tolerance, abs_tol=tolerance) or \
           entity_a.dxf.text != entity_b.dxf.text or \
           not math.isclose(entity_a.dxf.height, entity_b.dxf.height, rel_tol=tolerance, abs_tol=tolerance) or \
           not math.isclose(entity_a.dxf.get('rotation', 0.0), entity_b.dxf.get('rotation', 0.0), rel_tol=tolerance, abs_tol=tolerance):
            return True
    elif entity_type == 'MTEXT':
        # テキスト内容、文字高さ、幅なども比較
        if not math.isclose(entity_a.dxf.insert[0], entity_b.dxf.insert[0], rel_tol=tolerance, abs_tol=tolerance) or \
           not math.isclose(entity_a.dxf.insert[1], entity_b.dxf.insert[1] - y_offset_for_b, rel_tol=tolerance, abs_tol=tolerance) or \
           entity_a.text != entity_b.text or \
           not math.isclose(entity_a.dxf.char_height, entity_b.dxf.char_height, rel_tol=tolerance, abs_tol=tolerance) or \
           not math.isclose(entity_a.dxf.get('width', 0.0), entity_b.dxf.get('width', 0.0), rel_tol=tolerance, abs_tol=tolerance): # widthはオプション
            return True
    elif entity_type == 'POINT': # POINTエンティティの比較
        if not math.isclose(entity_a.dxf.location[0], entity_b.dxf.location[0], rel_tol=tolerance, abs_tol=tolerance) or \
           not math.isclose(entity_a.dxf.location[1], entity_b.dxf.location[1] - y_offset_for_b, rel_tol=tolerance, abs_tol=tolerance):
            return True
    elif entity_type == 'INSERT':
        if entity_a.dxf.name != entity_b.dxf.name or \
           not math.isclose(entity_a.dxf.insert[0], entity_b.dxf.insert[0], rel_tol=tolerance, abs_tol=tolerance) or \
           not math.isclose(entity_a.dxf.insert[1], entity_b.dxf.insert[1] - y_offset_for_b, rel_tol=tolerance, abs_tol=tolerance) or \
           not math.isclose(entity_a.dxf.get('xscale',1.0), entity_b.dxf.get('xscale',1.0), rel_tol=tolerance, abs_tol=tolerance) or \
           not math.isclose(entity_a.dxf.get('yscale',1.0), entity_b.dxf.get('yscale',1.0), rel_tol=tolerance, abs_tol=tolerance) or \
           not math.isclose(entity_a.dxf.get('rotation',0.0), entity_b.dxf.get('rotation',0.0), rel_tol=tolerance, abs_tol=tolerance):
            return True
    # 他の共通属性の比較 (レイヤー、線種など。キーに含まれていれば冗長かもしれないが、より確実)
    if entity_a.dxf.layer != entity_b.dxf.layer or \
       entity_a.dxf.linetype != entity_b.dxf.linetype or \
       entity_a.dxf.color != entity_b.dxf.color: # 色も比較
        return True
    # XDATAなどのより詳細な比較はここに追加できます
    return False

# round_float 関数 (変更なし)
def round_float(value, tolerance=1e-6):
    if not isinstance(value, (int, float)): # 数値でない場合はそのまま返す (稀なケースだが念のため)
        return value
    return round(value / tolerance) * tolerance

# copy_entity_to_result 関数 (変更なし、XDATAコピーはコメントアウトまたはAPI確認を推奨)
def copy_entity_to_result(entity, msp_result, layer_name):
    # この関数は元のエンティティの属性（オフセット適用前の座標）でコピーします
    dxfattribs = entity.dxf.all_existing_dxf_attribs()
    dxfattribs['layer'] = layer_name
    if 'handle' in dxfattribs: del dxfattribs['handle']
    if 'owner' in dxfattribs: del dxfattribs['owner']
    if 'reactors' in dxfattribs: del dxfattribs['reactors'] # reactorsもコピーしない

    new_entity = None
    entity_type = entity.dxftype()

    if entity_type == 'LINE':
        new_entity = msp_result.add_line(
            start=entity.dxf.start, # 元の座標
            end=entity.dxf.end,     # 元の座標
            dxfattribs=dxfattribs
        )
    elif entity_type == 'POINT':
        if 'insert' in dxfattribs: del dxfattribs['insert']
        location = dxfattribs.pop('location', entity.dxf.location)
        new_entity = msp_result.add_point(location=location, dxfattribs=dxfattribs)
    elif entity_type == 'CIRCLE':
        new_entity = msp_result.add_circle(
            center=entity.dxf.center, # 元の座標
            radius=entity.dxf.radius,
            dxfattribs=dxfattribs
        )
    elif entity_type == 'ARC':
        new_entity = msp_result.add_arc(
            center=entity.dxf.center, # 元の座標
            radius=entity.dxf.radius,
            start_angle=entity.dxf.start_angle,
            end_angle=entity.dxf.end_angle,
            dxfattribs=dxfattribs
        )
    elif entity_type == 'TEXT':
        text_content = dxfattribs.pop('text', entity.dxf.text)
        insert_coord = dxfattribs.pop('insert', entity.dxf.insert)
        height = dxfattribs.pop('height', entity.dxf.height)
        current_attribs = {'insert': insert_coord, 'height': height}
        current_attribs.update(dxfattribs)
        new_entity = msp_result.add_text(text=text_content, dxfattribs=current_attribs)
    elif entity_type == 'MTEXT':
        mtext_content = entity.text
        insert_coord = dxfattribs.pop('insert', entity.dxf.insert)
        char_height = dxfattribs.pop('char_height', entity.dxf.char_height)
        current_attribs = {'insert': insert_coord, 'char_height': char_height}
        current_attribs.update(dxfattribs)
        new_entity = msp_result.add_mtext(text=mtext_content, dxfattribs=current_attribs)
    elif entity_type == 'INSERT':
        block_name = dxfattribs.pop('name', entity.dxf.name)
        insert_coord = dxfattribs.pop('insert', entity.dxf.insert) # 元の座標
        current_attribs = {'insert': insert_coord} # add_blockref のdxfattribsはinsertを含んでも良いが、引数で明示的に渡す方が安全
        current_attribs.update(dxfattribs)
        new_entity = msp_result.add_blockref(name=block_name, insert=insert_coord, dxfattribs=current_attribs)
    elif entity_type == 'LEADER': # 元の簡易コピー
        try:
            # LEADERの位置情報を取得しようと試みる (より良い方法があれば修正)
            leader_pos = entity.dxf.get('vertices', [(0,0,0)])[0] if hasattr(entity.dxf, 'vertices') and entity.dxf.vertices else \
                         entity.dxf.get('annotation_location', (0,0,0)) if hasattr(entity.dxf, 'annotation_location') else (0,0,0)

            msp_result.add_text(
                text=f"[LEADER]",
                dxfattribs={'layer': layer_name, 'insert': leader_pos, 'height': 2.5}
            )
        except Exception:
             msp_result.add_text(
                text=f"[LEADER_COPY_ERR]",
                dxfattribs={'layer': layer_name, 'insert': (0,0,0), 'height': 2.5}
            )
    else:
        # 汎用的なコピー（位置情報があれば利用）
        insert_pos = entity.dxf.get('insert', None)
        if insert_pos is None:
            if hasattr(entity.dxf, 'location'): insert_pos = entity.dxf.location
            elif hasattr(entity.dxf, 'center'): insert_pos = entity.dxf.center
            elif hasattr(entity.dxf, 'start'): insert_pos = entity.dxf.start
            else: insert_pos = (0,0,0)

        msp_result.add_text(
            text=f"[{entity_type} on {layer_name}]",
            dxfattribs={'layer': layer_name, 'insert': insert_pos, 'height': 2.5, 'color': dxfattribs.get('color', 256)}
        )

    # XDATAのコピー (APIの確認が必要なため、慎重に扱うか一時的にコメントアウト)
    # if new_entity and hasattr(entity, 'xdata') and entity.xdata is not None:
    #     try:
    #         # ezdxf 1.4.1 の XData の正しい扱い方を要確認
    #         # for appid, tags_list in entity.xdata.items(): # items() が使えるか？
    #         #    new_entity.set_xdata(appid, tags_list)
    #         print(f"Info: XDATA found for entity {entity.dxf.handle if entity.dxf.handle else 'N/A'}, copy logic needs verification for ezdxf 1.4.1.")
    #     except Exception as xdata_e:
    #         print(f"Warning: Failed to copy XDATA for entity {entity.dxf.handle if entity.dxf.handle else 'N/A'}: {xdata_e}")