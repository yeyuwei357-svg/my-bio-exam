import streamlit as st
import pandas as pd
import os
import re
import random

# --- 1. 样式美化 ---
def local_css():
    st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .question-card {
        background-color: white; padding: 30px; border-radius: 15px;
        border-left: 8px solid #4CAF50; box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 25px;
    }
    .question-text { font-size: 22px !important; font-weight: 600; line-height: 1.6; color: #1a1a1a; }
    .stat-card { background-color: #ffffff; padding: 10px; border-radius: 10px; border: 1px solid #e0e0e0; text-align: center; }
    .stCheckbox { font-size: 18px !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 基础配置与文件初始化 ---
st.set_page_config(page_title="生物工程·考研刷题宝", layout="wide", page_icon="🧬")
local_css()

FILE_NAME = 'bio_bank_v2.csv'
WRONG_FILE = 'wrong_questions.csv'
CATEGORIES = ["绪论与基因工程", "细胞工程", "发酵工程", "蛋白质工程与酶工程", "应用"]
TYPE_LIST = ["单选", "多选", "判断", "填空", "大题"]
COLUMNS = ['模块', '题型', '题目', '答案', '解析', '我的笔记']

def init_files():
    for f in [FILE_NAME, WRONG_FILE]:
        if not os.path.exists(f):
            pd.DataFrame(columns=COLUMNS).to_csv(f, index=False)
        else:
            df = pd.read_csv(f).fillna("")
            for col in COLUMNS:
                if col not in df.columns: df[col] = ""
            df[COLUMNS].to_csv(f, index=False)

init_files()
def load_data(f): return pd.read_csv(f).fillna("")

# --- 3. 导入逻辑 ---
def smart_import(text, category):
    text = re.sub(r'#+.*?\n', '', text) 
    blocks = text.split("---")
    new_rows = []
    for block in blocks:
        block = block.strip()
        if not block: continue
        q_match = re.search(r'题目[:：]\s*(.*?)(?=答案[:：]|$)', block, re.S)
        a_match = re.search(r'答案[:：]\s*(.*?)(?=解析[:：]|$)', block, re.S)
        p_match = re.search(r'解析[:：]\s*(.*)', block, re.S)
        if q_match and a_match:
            q_raw = q_match.group(1).strip().replace('● ', '').replace('●', '')
            ans_raw = a_match.group(1).strip().replace('●', '').replace(' ', '').upper()
            p_content = p_match.group(1).strip() if p_match else "无"
            t_type = "单选"
            if "判断" in q_raw or ans_raw in ["正确", "错误", "对", "错", "√", "×"]:
                t_type = "判断"
            elif "多选" in q_raw or (len(ans_raw) > 1 and all(c in "ABCDEFG" for c in ans_raw)):
                t_type = "多选"
            elif not re.search(r'[A-G][\.、\s]', q_raw):
                t_type = "大题"
            new_rows.append([category, t_type, q_raw, ans_raw, p_content, ""])
    if new_rows:
        pd.DataFrame(new_rows, columns=COLUMNS).to_csv(FILE_NAME, mode='a', header=False, index=False)
        return len(new_rows)
    return 0

# --- 4. 侧边栏及导航 ---
with st.sidebar:
    st.title("🧬 考研复习系统")
    df_all = load_data(FILE_NAME)
    df_wrong = load_data(WRONG_FILE)
    st.markdown(f"**题库总数：{len(df_all)}** | **错题数：{len(df_wrong)}**")
    st.divider()
    mode = st.radio("📍 核心功能", ["🎯 刷题模式", "📝 批量导入", "📂 题库整理中心"])

# --- 5. 题库整理中心 ---
if mode == "📂 题库整理中心":
    st.title("📂 题库维护与管理")
    df_m = load_data(FILE_NAME)
    if not df_m.empty:
        col_f1, col_f2 = st.columns([1, 2])
        m_f = col_f1.selectbox("按模块筛选", ["全部"] + CATEGORIES)
        s_f = col_f2.text_input("🔍 关键字搜索")
        f_df = df_m.copy()
        if m_f != "全部": f_df = f_df[f_df['模块'] == m_f]
        if s_f: f_df = f_df[f_df['题目'].str.contains(s_f, na=False)]
        def toggle_all():
            for idx in f_df.index: st.session_state[f"sel_{idx}"] = st.session_state.ms
        st.checkbox("✅ 全选当前显示的题目", key="ms", on_change=toggle_all)
        selected_ids = []
        for idx, row in f_df.iterrows():
            cb, ct = st.columns([0.05, 0.95])
            if cb.checkbox("", key=f"sel_{idx}"):
                selected_ids.append(idx)
            with ct.expander(f"【{row['题型']}】 {row['题目'][:60]}..."):
                st.write(f"**模块:** {row['模块']} | **答案:** {row['答案']}")
                st.write(f"**解析:** {row['解析']}")
        if st.sidebar.button(f"🗑️ 永久删除选中 ({len(selected_ids)})", type="primary"):
            df_m.drop(selected_ids).to_csv(FILE_NAME, index=False)
            st.rerun()
    else:
        st.info("题库为空。")

# --- 6. 批量导入模块 ---
elif mode == "📝 批量导入":
    st.title("📝 批量导入新题目")
    cat = st.selectbox("选择归属模块", CATEGORIES)
    raw_text = st.text_area("粘贴文本...", height=400)
    if st.button("🚀 确认导入"):
        num = smart_import(raw_text, cat)
        if num > 0:
            st.success(f"导入成功！新增 {num} 道题目。")
            st.rerun()

# --- 7. 刷题模式（新增：分类别刷题功能） ---
else:
    st.title("🎯 刷题强化训练")
    
    # 侧边栏刷题配置
    with st.sidebar:
        st.subheader("刷题配置")
        scope = st.radio("1. 刷题范围", ["全部", "仅错题"])
        # 【新增功能】：模块筛选
        m_f = st.selectbox("2. 选择刷题模块", ["全部模块"] + CATEGORIES)
        t_f = st.selectbox("3. 筛选特定题型", ["全部题型"] + TYPE_LIST)
        if st.button("🔄 重置进度/乱序"):
            st.session_state.study_idx = 0
            st.rerun()

    # 数据过滤逻辑
    work_df = df_wrong if scope == "仅错题" else df_all
    if m_f != "全部模块":
        work_df = work_df[work_df['模块'] == m_f]
    if t_f != "全部题型":
        work_df = work_df[work_df['题型'] == t_f]
    
    if work_df.empty:
        st.warning(f"当前筛选条件下（{scope} - {m_f} - {t_f}）暂无题目。")
    else:
        if 'study_idx' not in st.session_state: st.session_state.study_idx = 0
        # 确保索引不越界
        cur_idx = st.session_state.study_idx % len(work_df)
        item = work_df.iloc[cur_idx]
        
        st.progress((cur_idx + 1) / len(work_df), text=f"当前进度: {cur_idx+1}/{len(work_df)}")
        st.markdown(f'<div class="question-card"><div class="question-text">【{item["模块"]}】<br>{item["题目"]}</div></div>', unsafe_allow_html=True)
        
        opt_regex = r'([A-G][\.、\s]\s*[^A-G]+?)(?=[A-G][\.、\s]|$)'
        opts = re.findall(opt_regex, str(item['题目']), re.S)
        show_result = False
        
        if item['题型'] == "判断":
            ans_map = {"对": "正确", "√": "正确", "正确": "正确", "错": "错误", "×": "错误", "错误": "错误"}
            correct_ans = ans_map.get(str(item['答案']).strip(), "正确")
            u_ans = st.radio("判断：", ["尚未作答", "正确", "错误"], horizontal=True, key=f"j_{cur_idx}")
            if u_ans != "尚未作答":
                show_result = True
                if u_ans == correct_ans: st.success("✅ 正确！")
                else: st.error(f"❌ 错误！正确答案是：{correct_ans}")

        elif item['题型'] == "多选" and opts:
            u_sel = [st.checkbox(o.strip(), key=f"m_{cur_idx}_{i}") for i, o in enumerate(opts)]
            if st.button("提交答案"):
                show_result = True
                u_str = "".join(sorted([opts[i][0].upper() for i, v in enumerate(u_sel) if v]))
                c_str = "".join(sorted([char for char in str(item['答案']).upper() if char in "ABCDEFG"]))
                if u_str == c_str: st.success(f"✅ 正确！您的选择：{u_str}")
                else: st.error(f"❌ 错误！正确答案是：{c_str}")

        else: # 单选或其它
            if opts:
                choice = st.radio("请选择：", [o.strip() for o in opts], index=None, key=f"s_{cur_idx}")
                if choice:
                    show_result = True
                    if choice[0].upper() == str(item['答案'])[0].upper(): st.success("✅ 正确")
                    else: st.error(f"❌ 错误！答案是：{item['答案']}")
            else:
                if st.button("查看答案与解析"): show_result = True

        if show_result:
            st.divider()
            st.info(f"**【标准答案】**: {item['答案']}\n\n**【解析】**: {item['解析']}")
            if st.button("💔 记入错题本"):
                pd.DataFrame([item]).to_csv(WRONG_FILE, mode='a', header=False, index=False)
                st.toast("已记入")

        st.write("---")
        b1, b2 = st.columns(2)
        if b1.button("⬅️ 上一题"): st.session_state.study_idx -= 1; st.rerun()
        if b2.button("➡️ 下一题"): st.session_state.study_idx += 1; st.rerun()