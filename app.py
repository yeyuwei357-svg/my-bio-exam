import streamlit as st
import pandas as pd
import os
import re
import math

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
    .stCheckbox { font-size: 18px !important; }
    .stRadio > label { font-size: 18px !important; font-weight: 500; }
    .result-box { padding: 15px; border-radius: 10px; margin-top: 10px; font-weight: bold; }
    .correct { background-color: #e8f5e9; color: #2e7d32; border: 1px solid #c8e6c9; }
    .wrong { background-color: #ffebee; color: #c62828; border: 1px solid #ffcdd2; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 基础配置与文件初始化 ---
st.set_page_config(page_title="生物工程·考研刷题宝", layout="wide", page_icon="🧬")
local_css()

FILE_NAME = 'bio_bank_v2.csv'
WRONG_FILE = 'wrong_questions.csv'
CATEGORIES = ["绪论与基因工程", "细胞工程", "发酵工程", "蛋白质工程与酶工程", "应用", "微生物生物技术"]
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

# --- 3. 核心工具：精准切分题干与选项 ---
def split_q_and_opts(raw_q):
    opt_marks = list(re.finditer(r'(?:^|\s)([A-G][\.、\s])', raw_q))
    if not opt_marks:
        return raw_q.strip(), []
    clean_q = raw_q[:opt_marks[0].start()].strip()
    opts = []
    for i in range(len(opt_marks)):
        start = opt_marks[i].start()
        end = opt_marks[i+1].start() if i+1 < len(opt_marks) else len(raw_q)
        opts.append(raw_q[start:end].strip())
    return clean_q, opts

# --- 4. 导入逻辑 ---
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
            q_raw = q_match.group(1).strip()
            ans_raw = a_match.group(1).strip().upper()
            p_content = p_match.group(1).strip() if p_match else "无"
            
            _, temp_opts = split_q_and_opts(q_raw)
            if any(x in ans_raw for x in ["正确", "错误", "对", "错", "√", "×"]):
                t_type = "判断"
            elif len(re.findall(r'[A-G]', ans_raw)) > 1:
                t_type = "多选"
            elif temp_opts:
                t_type = "单选"
            else:
                t_type = "大题"
            new_rows.append([category, t_type, q_raw, ans_raw, p_content, ""])
    if new_rows:
        pd.DataFrame(new_rows, columns=COLUMNS).to_csv(FILE_NAME, mode='a', header=False, index=False)
        return len(new_rows)
    return 0

# --- 5. 侧边栏及导航 ---
with st.sidebar:
    st.title("🧬 考研复习系统")
    df_all = load_data(FILE_NAME)
    df_wrong = load_data(WRONG_FILE)
    st.markdown(f"**题库总数：{len(df_all)}** | **错题数：{len(df_wrong)}**")
    st.divider()
    mode = st.radio("📍 核心功能", ["🎯 刷题模式", "📝 批量导入", "📂 题库整理中心"])

# --- 6. 题库整理中心 ---
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
                st.write(f"**答案:** {row['答案']} | **解析:** {row['解析']}")
        
        if st.sidebar.button(f"🗑️ 永久删除选中 ({len(selected_ids)})", type="primary"):
            df_m.drop(selected_ids).to_csv(FILE_NAME, index=False)
            st.rerun()
    else:
        st.info("题库为空。")

# --- 7. 批量导入模块 ---
elif mode == "📝 批量导入":
    st.title("📝 批量导入新题目")
    cat = st.selectbox("选择归属模块", CATEGORIES)
    raw_text = st.text_area("粘贴文本...", height=400)
    if st.button("🚀 确认导入"):
        num = smart_import(raw_text, cat)
        if num > 0:
            st.success(f"导入成功！新增 {num} 道题目。")
            st.rerun()

# --- 8. 刷题模式 ---
else:
    st.title("🎯 刷题强化训练")
    with st.sidebar:
        st.subheader("刷题配置")
        scope = st.radio("1. 刷题范围", ["全部", "仅错题"])
        m_f = st.selectbox("2. 选择刷题模块", ["全部模块"] + CATEGORIES)
        t_f = st.selectbox("3. 筛选特定题型", ["全部题型"] + TYPE_LIST)

    work_df = df_wrong if scope == "仅错题" else df_all
    if m_f != "全部模块": work_df = work_df[work_df['模块'] == m_f]
    if t_f != "全部题型": work_df = work_df[work_df['题型'] == t_f]

    if work_df.empty:
        st.warning(f"当前筛选条件下无题目。")
    else:
        total_len = len(work_df)
        step = 25
        num_ranges = math.ceil(total_len / step)
        range_options = [f"{i*step+1} - {min((i+1)*step, total_len)}" for i in range(num_ranges)]
        selected_range = st.sidebar.selectbox("4. 题号区间", range_options)
        
        range_idx = range_options.index(selected_range)
        current_work_df = work_df.iloc[range_idx*step : (range_idx+1)*step]
        
        if 'study_idx' not in st.session_state: st.session_state.study_idx = 0
        cur_idx = st.session_state.study_idx % len(current_work_df)
        item = current_work_df.iloc[cur_idx]
        
        st.progress((cur_idx + 1) / len(current_work_df))
        
        clean_q, opts = split_q_and_opts(str(item["题目"]))
        st.markdown(f'<div class="question-card"><div class="question-text">【{item["模块"]}】 第 {range_idx*step + cur_idx + 1} 题<br>{clean_q}</div></div>', unsafe_allow_html=True)
        
        nav_col1, nav_col2, _ = st.columns([1, 1, 2])
        if nav_col1.button("⬅️ 上一题"): 
            st.session_state.study_idx -= 1; st.rerun()
        if nav_col2.button("➡️ 下一题"): 
            st.session_state.study_idx += 1; st.rerun()
        st.write("---")

        # --- 核心修改：判题逻辑 ---
        show_ans = False
        user_correct = False
        
        # 预处理标准答案（转大写、去空格）
        std_ans = str(item['答案']).strip().upper()

        if item['题型'] == "判断":
            # 判断题逻辑映射
            u_ans = st.radio("请判断：", ["尚未作答", "正确", "错误"], horizontal=True, key=f"j_{cur_idx}")
            if u_ans != "尚未作答":
                show_ans = True
                # 处理各种可能的正确答案写法
                positives = ["正确", "对", "√", "T", "TRUE"]
                negatives = ["错误", "错", "×", "F", "FALSE"]
                is_std_positive = any(p in std_ans for p in positives)
                user_correct = (u_ans == "正确" and is_std_positive) or (u_ans == "错误" and not is_std_positive)

        elif opts:
            if item['题型'] == "多选":
                u_sel = [st.checkbox(o, key=f"m_{cur_idx}_{i}") for i, o in enumerate(opts)]
                if st.button("提交答案"):
                    show_ans = True
                    # 提取选中的字母，如 ['A', 'B'] -> "AB"
                    selected_letters = "".join(sorted([opts[i].strip()[0].upper() for i, checked in enumerate(u_sel) if checked]))
                    # 清理标准答案中的非大写字母（如逗号、空格）
                    std_letters = "".join(sorted(re.findall(r'[A-G]', std_ans)))
                    user_correct = (selected_letters == std_letters)
            else:
                # 单选逻辑
                choice = st.radio("请选择：", opts, index=None, key=f"s_{cur_idx}")
                if choice:
                    show_ans = True
                    user_choice_letter = choice.strip()[0].upper()
                    std_letter = std_ans[0] if std_ans else ""
                    user_correct = (user_choice_letter == std_letter)
        else:
            if st.button("查看答案与解析"):
                show_ans = True
                user_correct = None # 大题无法自动判断

        # 显示判断结果
        if show_ans:
            if user_correct is True:
                st.markdown('<div class="result-box correct">✅ 回答正确！</div>', unsafe_allow_html=True)
            elif user_correct is False:
                st.markdown(f'<div class="result-box wrong">❌ 回答错误！正确答案是：{item["答案"]}</div>', unsafe_allow_html=True)
            
            st.info(f"**【解析】**：{item['解析']}")
            
            if st.button("💔 记入错题本"):
                pd.DataFrame([item]).to_csv(WRONG_FILE, mode='a', header=False, index=False)
                st.toast("已同步至错题本")