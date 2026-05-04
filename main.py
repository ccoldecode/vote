import streamlit as st
import json
import os
import sqlite3
import pandas as pd
import threading
from io import BytesIO

# --- 配置区 ---
JSON_PATH = "sample_annotations.json"
IMAGE_FOLDER = "concat_images"
DB_PATH = "test_results.db"

# 属性翻译字典 (已补全)
TRANSLATIONS = {
    "overall_rating": "整体评分",
    "species": "物种名称",
    "diagnosis": "识别特征描述",
    "dorsal_fin": "背鳍",
    "caudal_fin": "尾鳍",
    "pectoral_fin": "胸鳍",
    "pelvic_fin": "腹鳍",
    "anal_fin": "臀鳍",
    "adipose_fin": "脂鳍",
    "barbel": "口须",
    "body_shape_lateral": "侧面体型",
    "type_of_eyes": "眼睛类型",
    "type_of_mouth_snout": "口吻类型",
    "cross_section": "身体横截面",
    "dorsal_head_profile": "头部背侧轮廓",
    "type_of_scales": "鳞片类型",
    "color": "颜色",
    "camouflage": "伪装程度",
    "texture": "表面纹理",
    "body_damage": "身体损伤",
    "interaction": "交互行为",
    "coral_group": "珊瑚群组",
    "growth_form": "生长形态",
    "growth_outline_type": "生长轮廓类型",
    "coloniality": "群体性",
    "colony_size": "群体大小",
    "corallite_arrangement": "珊瑚虫排列",
    "corallite_opening_shape": "珊瑚虫开口形状",
    "colony_relief": "群体起伏",
    "corallite_visibility": "珊瑚虫可见度",
    "coral_preciousness_grade": "珊瑚名贵等级",
    "bleaching_state": "白化状态",
    "tissue_condition": "组织状态",
    "algal_overgrowth": "藻类覆盖",
    "sediment_cover": "沉积物覆盖",
    "neighboring_contact": "邻近接触",
    "cephalopod_group": "头足类群组",
    "body_form": "身体形态",
    "mantle_shape": "外套膜形状",
    "fin_presence_placement": "鳍的存在与位置",
    "arm_configuration": "腕足配置",
    "tentacle_presence": "触腕是否存在",
    "sucker_visibility_type": "吸盘可见性与类型",
    "webbing_extent": "腕间膜程度",
    "head_to_mantle_proportion": "头与外套膜比例",
    "dominant_color": "主导颜色",
    "skin_pattern": "皮肤斑纹",
    "skin_relief": "皮肤起伏",
    "camouflage_visibility": "伪装可见性",
    "posture": "姿态",
    "crustacean_group": "甲壳类群组",
    "body_plan": "身体结构",
    "carapace_shape": "头胸甲形状",
    "rostrum_prominence": "额角显著度",
    "cheliped_development": "螯足发育情况",
    "leg_form": "步足形态",
    "abdomen_exposure": "腹部暴露情况",
    "body_segmentation_visibility": "身体分节可见度",
    "antenna_prominence": "触角显著度",
    "surface_armature": "表面甲胄/刺瘤",
    "pattern_type": "斑纹类型",
    "shell_occupation": "寄居情况",
    "echinoderm_group": "棘皮动物群组",
    "body_symmetry": "身体对称性",
    "overall_body_form": "整体体型",
    "arm_presence_form": "腕足存在形式",
    "arm_count_coarse": "腕足数量(粗略)",
    "central_disc_prominence": "中央盘显著度",
    "spine_development": "棘刺发育",
    "tube_feet_visibility": "管足可见度",
    "body_inflation": "身体膨胀度",
    "substrate_attachment": "基质附着方式",
    "mollusk_group": "软体动物群组",
    "shell_presence": "贝壳存在情况",
    "shell_configuration": "贝壳构造",
    "shell_coiling_direction": "螺壳旋向",
    "spire_height": "螺塔高度",
    "aperture_shape": "壳口形状",
    "operculum_visibility": "厣/口盖可见度",
    "shell_sculpture": "贝壳雕纹",
    "body_extension_degree": "身体伸出程度",
    "body_shell_color": "体/壳颜色",
    "surface_gloss": "表面光泽",
    "attachment_mode": "附着方式",
    "cnidarian_type": "刺胞动物类型",
    "tentacle_arrangement_diagnosis": "触手排列判定",
    "symmetry_type": "对称类型",
    "bell_presence": "伞部是否存在",
    "tentacle_form": "触手形态",
    "oral_arm_presence": "口腕是否存在",
    "colony_organization": "群体组织形式",
    "transparency": "透明度",
    "color_pattern": "颜色模式",
    "bell_body_integrity": "伞部/身体完整性",
    "sponge_growth_type": "海绵生长类型",
    "surface_channel_diagnosis": "表面孔道判定",
    "attachment_extent": "附着程度",
    "osculum_visibility": "出水孔可见度",
    "osculum_form": "出水孔形态",
    "branch_tube_organization": "分枝/管状组织",
    "relief_thickness": "起伏厚度",
    "surface_porosity": "表面孔隙度",
    "edge_form": "边缘形态",
    "epibiont_cover": "附生生物覆盖",
    "substrate_relation": "基质关系",
    "creature_type": "生物类型",
    "visual_diagnosis": "视觉判定",
    "body_shape": "体型",
    "symmetry": "对称性",
    "body_organization": "身体组织",
    "appendage_type": "附肢类型",
    "hard_structure_presence": "硬质结构是否存在",
    "repetition_modularity": "重复性/模块化",
    "surface_relief": "表面起伏",
    "body_posture": "身体姿态",
    "object_category": "物体类别",
    "material_type": "材料类型",
    "object_form": "物体形态",
    "shape": "形状",
    "size": "大小",
    "entanglement_potential": "缠绕风险",
    "damage_state": "损伤状态",
    "biofouling_level": "生物附着程度",
    "sediment_embedment": "沉积物埋没程度",
    "functional_status": "功能状态",
    "spatial_state": "空间状态",
    "diver_presence_type": "潜水员呈现类型",
    "tank_presence": "气瓶是否存在",
    "fin_presence": "脚蹼是否存在",
    "mask_presence": "面镜是否存在",
    "light_tool_presence": "照明/工具是否存在",
    "suit_type": "潜水服类型",
    "suit_description": "潜水服功能描述",
    "motion_state": "运动状态",
    "task_role": "任务角色",
    "body_orientation": "身体朝向",
    "swimming_posture": "游泳姿势",
    "hand_gesture_type": "手势类型",
    "pose_visibility": "姿态可见度",
    "attention_direction": "注意力方向",
    "buddy_proximity": "同伴距离",
    "occlusion": "遮挡程度",
    "surface_texture": "表面纹理",
    "dominant_color": "主导颜色",
    "concept": "物种/概念名称",
    "entry_id": "条目ID"
}

# --- 数据库与锁配置 ---
db_lock = threading.Lock()

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS results 
                 (student_id TEXT, entry_id TEXT, attr_key TEXT, 
                  final_value TEXT, is_modified INTEGER, 
                  PRIMARY KEY (student_id, entry_id, attr_key))''')
    conn.commit()
    conn.close()

def save_result(student_id, entry_id, final_choice):
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        # 将整体评分存入特殊的 attr_key: 'overall_rating'
        c.execute('''INSERT OR REPLACE INTO results VALUES (?, ?, ?, ?, ?)''',
                  (student_id, entry_id, 'overall_rating', final_choice, 0))
        conn.commit()
        conn.close()

def get_finished_count(student_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(DISTINCT entry_id) FROM results WHERE student_id=?", (student_id,))
    res = c.fetchone()
    count = res[0] if res else 0
    conn.close()
    return count

def export_all_to_excel():
    conn = sqlite3.connect(DB_PATH)
    sids_df = pd.read_sql_query("SELECT DISTINCT student_id FROM results", conn)
    student_ids = sids_df['student_id'].tolist()
    if not student_ids:
        conn.close()
        return None
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        for sid in student_ids:
            query = "SELECT entry_id, attr_key, final_value FROM results WHERE student_id = ?"
            df = pd.read_sql_query(query, conn, params=(sid,))
            df['评分含义'] = df['attr_key'].map(TRANSLATIONS)
            df = df[['entry_id', 'attr_key', '评分含义', 'final_value']]
            df.to_excel(writer, index=False, sheet_name=str(sid))
    conn.close()
    return output.getvalue()

def main():
    st.set_page_config(page_title="水下目标属性校对系统", layout="wide")
    init_db()

    # 1. 登录
    if 'student_id' not in st.session_state:
        st.title("水下目标标注质量评估")
        sid = st.text_input("请输入学号：")
        if st.button("开始评审"):
            if sid:
                st.session_state.student_id = sid
                st.rerun()
        return

    # 2. 数据加载
    if 'data' not in st.session_state:
        if not os.path.exists(JSON_PATH):
            st.error(f"缺失文件: {JSON_PATH}")
            return
        with open(JSON_PATH, 'r', encoding='utf-8') as f:
            st.session_state.data = json.load(f)
    
    data = st.session_state.data
    student_id = st.session_state.student_id

    # 3. 进度管理
    if 'current_idx' not in st.session_state:
        st.session_state.current_idx = get_finished_count(student_id)

    # 4. 侧边栏
    st.sidebar.title(f"{student_id}")
    st.sidebar.write(f"进度: {st.session_state.current_idx} / {len(data)}")
    st.sidebar.divider()
    admin_code = st.sidebar.text_input("管理员导出", type="password")
    if admin_code == "admin422":
        xlsx_data = export_all_to_excel()
        if xlsx_data:
            st.sidebar.download_button("下载汇总报表", xlsx_data, "quality_check.xlsx")

    if st.sidebar.button("退出"):
        del st.session_state.student_id
        st.rerun()

    # 5. 完成
    if st.session_state.current_idx >= len(data):
        st.balloons()
        st.success("全部评估已完成！")
        return

    item = data[st.session_state.current_idx]

    # --- 6. 图片展示与标准 ---
    st.write(f"**任务编号**: {item['entry_id']} | **当前进度**: {st.session_state.current_idx + 1}/{len(data)}")
    
    concat_path = os.path.join(IMAGE_FOLDER, item['concat_file'])
    if os.path.exists(concat_path):
        st.image(concat_path, use_container_width=True)
    else:
        st.warning(f"图片未找到: {concat_path}")

    st.info("""
    **评分标准：**
    * **A**: 标注基本准确，与图片展示高度一致。
    * **B**: 大体正确，存在微小偏差或遗漏，但仍有参考价值。
    * **C**: 部分正确，偏差较多，对理解有明显影响。
    * **D**: 整体较差，存在严重错误或冲突。
    """)

    # --- 7. 属性内容展示区 ---
    st.write("---")
    st.subheader(f"标注详情 (目标: {item['concept']})")
    
    attrs = item['attributes']
    cols_num = 4
    attr_list = list(attrs.items())
    
    # 这里只做展示
    for i in range(0, len(attr_list), cols_num):
        cols = st.columns(cols_num)
        for idx, (key, val) in enumerate(attr_list[i : i + cols_num]):
            with cols[idx]:
                name = TRANSLATIONS.get(key, key)
                st.markdown(f"**{name}**")
                st.text(f"{val}")

    # --- 8. 整体打分区 ---
    st.divider()
    st.subheader("整体质量评估")
    # 唯一的单选框
    overall_choice = st.radio(
        "请结合图片，对上述所有属性的标注准确性进行综合打分：",
        ["A", "B", "C", "D"],
        horizontal=True,
        key=f"overall_{item['entry_id']}"
    )

    # --- 9. 导航按钮 ---
    c1, c2, c3 = st.columns([1, 2, 1])
    with c1:
        if st.button("上一题") and st.session_state.current_idx > 0:
            st.session_state.current_idx -= 1
            st.rerun()
    with c2:
        if st.button("保存评估，进入下一题", type="primary", use_container_width=True):
            # 保存唯一的评分
            save_result(student_id, item['entry_id'], overall_choice)
            st.session_state.current_idx += 1
            st.rerun()

if __name__ == "__main__":
    main()
