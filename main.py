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

# 属性翻译字典 (保持不变，此处省略部分以节省篇幅，建议保留你原有的完整字典)
TRANSLATIONS = {
    # 珊瑚类 (Coral) 相关
    "coral_group": "珊瑚群组",
    "growth_form": "生长形态",
    "growth_outline_type": "生长轮廓类型",
    "coloniality": "群体性",
    "colony_size": "群体大小",
    "corallite_arrangement": "珊瑚虫排列",
    "colony_relief": "群体起伏/立体感",
    "corallite_visibility": "珊瑚虫可见度",
    "coral_preciousness_grade": "珊瑚名贵等级",
    "bleaching_state": "白化状态",
    
    # 刺胞动物 (Cnidaria) 相关
    "cnidarian_type": "刺胞动物类型",
    "tentacle_arrangement_diagnosis": "触手排列判定",
    "body_column_visibility": "体柱可见度",
    "tentacle_prominence": "触手显著度",
    "tentacle_form": "触手形态",
    "oral_arm_presence": "口腕是否存在",
    "colony_organization": "群体组织形式",
    "transparency": "透明度",
    "color_pattern": "颜色斑纹模式",
    "bell_body_integrity": "伞部完整性",
    
    # 棘皮动物 (Echinoderm) 相关
    "echinoderm_group": "棘皮动物细分群",
    "body_symmetry": "身体对称性",
    "arm_presence_form": "腕足存在形式",
    "arm_count_coarse": "腕足数量(粗略)",
    "central_disc_prominence": "中央盘显著度",
    "spine_development": "刺/棘发育情况",
    "tube_feet_visibility": "管足可见度",
    "body_inflation": "身体膨胀/充盈度",
    
    # 通用属性
    "surface_texture": "表面纹理",
    "dominant_color": "主导颜色",
    "color": "颜色",
    "substrate_attachment": "基质附着方式",
    "concept": "物种名称",
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

def save_result(student_id, entry_id, attr_results):
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        for key, val in attr_results.items():
            # 这里的 val['value'] 现在会存入 A/B/C/D
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
    
    # CSS 注入：确保图片置顶和样式美化 (已注释部分保留)
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
    if admin_code == "admin422": # 这里设置你的口令
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
    
    # 修改点：在这里拼接 IMAGE_FOLDER
    concat_path = os.path.join(IMAGE_FOLDER, item['concat_file'])
    
    if os.path.exists(concat_path):
        st.image(concat_path, use_container_width=True)
    else:
        st.warning(f"图片未找到: {concat_path}") # 这里也建议打印拼接后的路径，方便排查
        
    # --- 增加：在图片下方显示评价标准 ---
    st.info("""
    **评价标准：**
    * **A**: 属性标注基本准确，能够较好地反映视觉特征，与图片展示内容相对一致；即使存在少量瑕疵，但对目标的整体理解影响有限。
    * **B**: 属性标注大体正确，能够反映目标的主要视觉特征，与图片展示内容大体一致；虽存在一定偏差、遗漏或局部不一致，但整体仍能支持对目标的基本理解，具有参考价值。
    * **C**: 属性标注部分正确，只能反映目标的少数主要特征；存在较多偏差、遗漏或不一致，对目标理解已造成较明显影响，整体参考价值有限。
    * **D**: 属性标注整体较差，与图片展示特征不符的内容较多，存在多项明显错误、较大遗漏或严重内部冲突，已不能可靠反映该目标的真实视觉属性。
    """)
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
        for idx, (key, val) in enumerate(attr_list[i : i + cols_num]):
            with cols[idx]:
                # 使用翻译字典，找不到则显示原键名
                st.markdown(f"**{TRANSLATIONS.get(key, key)}**")
                
                # 直接获取 JSON 中的值作为初筛值
                orig = str(val)
                st.caption(f"模型初筛值: {orig}")
                
                # ABCD 评分选项
                choice = st.radio(
                    f"评分_{key}", ["A", "B", "C", "D"], 
                    horizontal=True, key=f"r_{item['entry_id']}_{key}",
                    label_visibility="collapsed"
                )
                
                # 保存结果
                temp_results[key] = {"value": choice, "modified": 0}

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
