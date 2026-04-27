import streamlit as st
import json
import os
import sqlite3
import pandas as pd
import threading
from io import BytesIO

# --- 配置区 ---
JSON_PATH = "review_annotations.json"
IMAGE_FOLDER = ""
DB_PATH = "test_results.db"

# 属性翻译字典 (保持不变，此处省略部分以节省篇幅，建议保留你原有的完整字典)
TRANSLATIONS = {
    "sponge_growth_type": "海绵生长类型",
    "surface_channel_diagnosis": "表面通道特征判定",
    "overall_body_form": "整体形体/轮廓",
    "attachment_extent": "附着范围/程度",
    "osculum_visibility": "出水孔可见度",
    "osculum_form": "出水孔形态",
    "branch_tube_organization": "分支或管状结构组织",
    "relief_thickness": "起伏厚度/立体感",
    "surface_porosity": "表面孔隙率",
    "surface_texture": "表面纹理特征",
    "epibiont_cover": "外附生物覆盖情况",
    "substrate_relation": "与基质的关系",
    "occlusion": "遮挡/缺失情况",
    "echinoderm_group": "棘皮动物细分群",
    "body_symmetry": "身体对称性",
    "arm_presence_form": "腕足存在形式",
    "arm_count_coarse": "腕足数量(粗略计数)",
    "central_disc_prominence": "中央盘显著度",
    "spine_development": "刺/棘发育情况",
    "tube_feet_visibility": "管足可见度",
    "body_inflation": "身体膨胀/充盈度",
    "substrate_attachment": "基质附着方式",
    "crustacean_group": "甲壳类细分群",
    "body_plan": "身体结构方案",
    "carapace_shape": "头胸甲形状",
    "rostrum_prominence": "额角/额剑显著度",
    "cheliped_development": "螯足发育程度",
    "leg_form": "步足/附肢形态",
    "abdomen_exposure": "腹部暴露程度",
    "body_segmentation_visibility": "身体分节清晰度",
    "antenna_prominence": "触角显眼程度",
    "surface_armature": "表面甲胄/附属物",
    "shell_occupation": "外壳占据情况(如寄居)",
    "posture": "姿态/动作",
    "mollusk_group": "软体动物分类",
    "shell_presence": "外壳是否存在",
    "shell_configuration": "壳体构造(单壳/双壳等)",
    "shell_coiling_direction": "旋壳方向",
    "spire_height": "螺塔高度",
    "aperture_shape": "壳口形状",
    "operculum_visibility": "厣(壳盖)可见度",
    "body_extension_degree": "身体伸出程度",
    "body_shell_color": "体表/壳体颜色",
    "surface_gloss": "表面光泽度",
    "attachment_mode": "附着模式",
    "species": "物种名称",
    "diagnosis": "形态学判定特征",
    "dorsal_fin": "背鳍特征",
    "caudal_fin": "尾鳍形态",
    "pectoral_fin": "胸鳍特征",
    "pelvic_fin": "腹鳍特征",
    "anal_fin": "臀鳍特征",
    "adipose_fin": "脂鳍是否存在",
    "barbel": "口须特征",
    "body_shape_lateral": "侧面体型",
    "type_of_eyes": "眼睛类型/位置",
    "type_of_mouth_snout": "口吻部类型",
    "cross_section": "横截面形状",
    "dorsal_head_profile": "头部背侧轮廓",
    "color": "颜色表现",
    "camouflage": "伪装特征",
    "texture": "质感/纹理",
    "body_damage": "身体损伤情况",
    "interaction": "环境交互行为",
    "cnidarian_type": "刺胞动物类型",
    "tentacle_arrangement_diagnosis": "触手排列判定",
    "body_form": "体型结构",
    "symmetry_type": "对称类型",
    "bell_presence": "伞部是否存在",
    "tentacle_prominence": "触手显著度",
    "tentacle_form": "触手形态",
    "oral_arm_presence": "口腕是否存在",
    "colony_organization": "群体组织形式",
    "transparency": "透明度",
    "color_pattern": "颜色斑纹模式",
    "bell_body_integrity": "伞部整体完整性",
    "creature_type": "生物类别",
    "visual_diagnosis": "视觉识别判定",
    "body_shape": "身体形状",
    "symmetry": "对称性",
    "body_organization": "身体组织构成",
    "appendage_type": "附肢/延伸物类型",
    "hard_structure_presence": "硬质结构是否存在",
    "repetition_modularity": "重复性/模块化结构",
    "dominant_color": "主导颜色",
    "camouflage_visibility": "伪装可见度",
    "body_posture": "身体姿态",
    "surface_relief": "表面起伏特征"
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

def save_result(student_id, entry_id, attr_results):
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        for key, val in attr_results.items():
            c.execute('''INSERT OR REPLACE INTO results VALUES (?, ?, ?, ?, ?)''',
                    (student_id, entry_id, key, val['value'], val['modified']))
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

# --- 新增：管理员导出全员 Excel 函数 ---
def export_all_to_excel():
    conn = sqlite3.connect(DB_PATH)
    # 获取所有有记录的学号
    sids_df = pd.read_sql_query("SELECT DISTINCT student_id FROM results", conn)
    student_ids = sids_df['student_id'].tolist()
    
    if not student_ids:
        conn.close()
        return None

    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        for sid in student_ids:
            query = "SELECT entry_id, attr_key, final_value, is_modified FROM results WHERE student_id = ?"
            df = pd.read_sql_query(query, conn, params=(sid,))
            df['属性中文名'] = df['attr_key'].map(TRANSLATIONS)
            # 重新排序列
            df = df[['entry_id', 'attr_key', '属性中文名', 'final_value', 'is_modified']]
            df.to_excel(writer, index=False, sheet_name=str(sid))
    conn.close()
    return output.getvalue()

def main():
    st.set_page_config(page_title="水下目标属性校对系统", layout="wide")
    
    # CSS 注入：确保图片置顶和样式美化
    # st.markdown("""
    #     <style>
    #     .sticky-container {
    #         position: -webkit-sticky; position: sticky;
    #         top: 2.875rem; background-color: white; z-index: 100;
    #         padding-bottom: 10px; border-bottom: 2px solid #f0f2f6;
    #     }
    #     </style>
    #     """, unsafe_allow_html=True)

    init_db()

    # 1. 登录
    if 'student_id' not in st.session_state:
        st.title("水下目标标注校对系统")
        sid = st.text_input("请输入学号开始任务：")
        if st.button("进入系统"):
            if sid:
                st.session_state.student_id = sid
                st.rerun()
        return

    # 2. 数据加载
    if 'data' not in st.session_state:
        if not os.path.exists(JSON_PATH):
            st.error(f"缺失配置文件: {JSON_PATH}")
            return
        with open(JSON_PATH, 'r', encoding='utf-8') as f:
            st.session_state.data = json.load(f)
    
    data = st.session_state.data
    student_id = st.session_state.student_id

    # 3. 进度管理
    if 'current_idx' not in st.session_state:
        st.session_state.current_idx = get_finished_count(student_id)

    # 4. 侧边栏：导出功能与退出
    st.sidebar.title(f" {student_id}")
    st.sidebar.write(f"当前进度: {st.session_state.current_idx} / {len(data)}")
    
    # 管理员导出逻辑
    st.sidebar.divider()
    st.sidebar.subheader("数据导出 (管理员)")
    # 简单的密码保护，防止普通同学误下
    admin_code = st.sidebar.text_input("输入管理员口令下载全员数据", type="password")
    if admin_code == "admin123": # 这里设置你的口令
        xlsx_data = export_all_to_excel()
        if xlsx_data:
            st.sidebar.download_button(
                label="点击下载全员汇总.xlsx",
                data=xlsx_data,
                file_name="全员校对汇总.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.sidebar.info("数据库暂无数据")

    if st.sidebar.button("退出登录"):
        del st.session_state.student_id
        st.rerun()

    # 5. 完成检测
    if st.session_state.current_idx >= len(data):
        st.balloons()
        st.success("恭喜！你已完成所有任务。")
        return

    item = data[st.session_state.current_idx]

    # --- 6. 图片展示区 ---
    st.markdown('<div class="sticky-container">', unsafe_allow_html=True)
    st.write(f"**任务编号**: {item['entry_id']} | **当前进度**: {st.session_state.current_idx + 1}/{len(data)}")
    
    concat_path = os.path.join(IMAGE_FOLDER, item['concat_file'])
    if os.path.exists(concat_path):
        st.image(concat_path, use_container_width=True)
    else:
        st.warning(f"图片未找到: {item['concat_file']}")
    st.markdown('</div>', unsafe_allow_html=True)

    # --- 7. 属性校对区 ---
    st.write("---")
    st.subheader(f"检测目标: {item['concept']}")
    
    attrs = item['attributes']
    temp_results = {}
    
    cols_num = 3
    attr_list = list(attrs.items())
    for i in range(0, len(attr_list), cols_num):
        cols = st.columns(cols_num)
        for idx, (key, info) in enumerate(attr_list[i : i + cols_num]):
            with cols[idx]:
                st.markdown(f"**{TRANSLATIONS.get(key, key)}**")
                orig = str(info['annotated_value'])
                st.caption(f"模型初筛值: {orig}")
                
                choice = st.radio(
                    f"选择_{key}", ["保留", "修改"], 
                    horizontal=True, key=f"r_{item['entry_id']}_{key}",
                    label_visibility="collapsed"
                )
                
                if choice == "修改":
                    new_val = st.text_input("请输入修正值：", value=orig, key=f"i_{item['entry_id']}_{key}")
                    temp_results[key] = {"value": new_val, "modified": 1}
                else:
                    temp_results[key] = {"value": orig, "modified": 0}

    # --- 8. 提交按钮 ---
    st.divider()
    c1, c2, c3 = st.columns([1, 2, 1])
    with c1:
        if st.button("上一题") and st.session_state.current_idx > 0:
            st.session_state.current_idx -= 1
            st.rerun()
    with c2:
        if st.button("提交并保存，进入下一题", type="primary", use_container_width=True):
            save_result(student_id, item['entry_id'], temp_results)
            st.session_state.current_idx += 1
            st.rerun()

if __name__ == "__main__":
    main()
