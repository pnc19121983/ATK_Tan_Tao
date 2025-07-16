import streamlit as st
st.set_page_config(page_title="Phân tích điểm theo lớp", layout="wide")

import pandas as pd
import matplotlib.pyplot as plt
import socket
import google.generativeai as genai
import gdown
import os

# === THÔNG SỐ CẤU HÌNH ===
FILE_ID = '1KB8QtOo9XtrJTMTGXNh9pHVMTt3hSELo' #Copy ID của file excel chia sẻ vào đây
FILE_NAME = 'du_lieu_mau.xlsx'
OWNER_HOSTNAME = 'TEN_MAY_CUA_BAN'

is_owner = socket.gethostname() == OWNER_HOSTNAME

if is_owner:
    uploaded_file = st.file_uploader("📤 Tải file Excel", type=["xlsx", "xls"])
    if uploaded_file:
        with open(FILE_NAME, "wb") as f:
            f.write(uploaded_file.read())
        st.success("✅ Đã cập nhật dữ liệu thành công!")

if not os.path.exists(FILE_NAME):
    try:
        url = f"https://drive.google.com/uc?id={FILE_ID}"
        st.info("🔽 Đang tải dữ liệu từ Google Drive...")
        gdown.download(url, FILE_NAME, quiet=False)
        st.success("✅ Tải dữ liệu thành công!")
    except Exception as e:
        st.error(f"❌ Không thể tải file từ Google Drive: {e}")
        st.stop()

try:
    df = pd.read_excel(FILE_NAME)
    #st.success("✅ Dữ liệu đã được đọc thành công.")
except Exception as e:
    st.error(f"❌ Lỗi khi đọc file Excel: {e}")
    st.stop()

# === TIỀN XỬ LÝ ===
df.columns = df.columns.str.strip()
score_columns = ['Toán', 'Văn', 'Anh', 'Lý', 'Hóa', 'Sinh', 'Sử', 'Địa', 'KTPL', 'Tin', 'CN (NN)', 'CN (CN)','ĐTB cac nam','KK','UT','TN']
for col in score_columns:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')
df['Điểm TB'] = df[score_columns].mean(axis=1, skipna=True)

# === AI CẤU HÌNH ===
genai.configure(api_key="AIzaSyAWXS7wjLXSUQVWa8e9k2MD1hjrL6rEkYU")

def generate_analysis(prompt_text):
    try:
        with st.spinner("🔍 Đang phân tích và đánh giá"):
            model = genai.GenerativeModel("gemini-1.5-flash")
            default_instruction = (
                "Hãy phân tích dữ liệu dưới đây theo cấu trúc:\n"
                "- Căn cứ vào điểm trung bình, phương sai, độ lệch chuẩn, số trung vị, mốt, khoảng biến thiên, khoản tứ phân vị đưa ra nhận xét đánh giá\n"
                "- Nguyên nhân của Chưa đạt là gì?\n"
                "- Đề xuất hướng khắc phục cho các đối tượng Chưa đạt đó.\n\n"
            )
            full_prompt = default_instruction + str(prompt_text)
            response = model.generate_content(full_prompt)
            return response.text
    except Exception as e:
        return f"❌ Lỗi khi gọi Google AI: {e}"

# === GIAO DIỆN ===
col1, col2 = st.columns([1, 15])
with col1:
    st.image("logo.png", width=80)
with col2:
    st.markdown("## TRƯỜNG THPT NGUYỄN VĂN HUYÊN")
st.title("📘 Phân tích điểm thi")

st.sidebar.header("🔎 Bộ lọc dữ liệu")
school_options = ["Toàn trường"] + sorted(df['Lớp'].dropna().unique().tolist())
selected_school = st.sidebar.selectbox("Chọn phạm vi phân tích:", school_options)
df_filtered = df if selected_school == "Toàn trường" else df[df['Lớp'] == selected_school]

# === BIỂU ĐỒ: ĐIỂM TB THEO LỚP ===
st.subheader("🏫 Biểu đồ điểm trung bình theo Lớp")

avg_by_school = df_filtered.groupby("Lớp")['Điểm TB'].mean()
avg_all = df_filtered['Điểm TB'].mean()
avg_by_school["Điểm TB toàn bộ"] = avg_all
avg_by_school = avg_by_school.sort_values(ascending=False)

ranked_labels = []
rank = 1
for name in avg_by_school.index:
    if name == "Điểm TB toàn bộ":
        ranked_labels.append("Trung bình")
    else:
        ranked_labels.append(f"{rank}. {name}")
        rank += 1

colors = ['orange' if name == "Điểm TB toàn bộ" else 'skyblue' for name in avg_by_school.index]

fig1, ax1 = plt.subplots(figsize=(12, 6))
bars = ax1.bar(ranked_labels, avg_by_school.values, color=colors)

for bar in bars:
    height = bar.get_height()
    ax1.text(bar.get_x() + bar.get_width()/2, height + 0.2, f"{height:.2f}", ha='center', va='bottom', fontsize=9, rotation=90)

ax1.set_ylabel("Điểm trung bình")
ax1.set_title("Biểu đồ điểm trung bình theo Lớp")
ax1.set_ylim(0, 10)
plt.xticks(rotation=45, ha='right')

xtick_labels = ax1.get_xticklabels()
for label in xtick_labels:
    if label.get_text() == "Trung bình":
        label.set_color("orange")

plt.tight_layout()
st.pyplot(fig1)

if st.checkbox("📌 Đánh giá bằng AI", key="ai1"):
    st.markdown("### 🧠 Nhận định & đề xuất từ AI:")
    st.markdown(generate_analysis(f"Dữ liệu điểm trung bình các lớp: {avg_by_school.to_dict()}"))

# ======= PHẦN 7: Thống kê số lượng thí sinh chọn môn tổ hợp (trừ Toán, Văn) =======
st.subheader("📈 Thống kê số lượng thí sinh lựa chọn các môn tổ hợp")

# Loại bỏ các môn bắt buộc
excluded_subjects = ["Toán", "Văn"]
optional_subjects = [col for col in score_columns if col not in excluded_subjects and col in df.columns]

# Đếm số thí sinh có điểm, chỉ giữ môn có ít nhất 1 thí sinh chọn
subject_counts = {
    subject: df_filtered[subject].notna().sum()
    for subject in optional_subjects
    if df_filtered[subject].notna().sum() > 0
}

if not subject_counts:
    st.warning("❗ Không có dữ liệu môn tự chọn nào để thống kê.")
else:
    # Dữ liệu cho biểu đồ
    labels = list(subject_counts.keys())
    sizes = list(subject_counts.values())
    colors = plt.get_cmap("tab20")(range(len(labels)))

    # Tạo biểu đồ tròn rõ nét
    fig7, ax7 = plt.subplots(figsize=(6, 3), dpi=200)
    wedges, texts, autotexts = ax7.pie(
        sizes,
        labels=labels,
        autopct='%1.1f%%',
        startangle=140,
        colors=colors,
        textprops=dict(color="black", fontsize=6)
    )

    ax7.axis('equal')
    ax7.set_title("Tỷ lệ lựa chọn các môn tổ hợp", fontsize=8)

    # Canh lề đẹp
    plt.tight_layout()
    st.pyplot(fig7)

    # Đánh giá AI
    if st.checkbox("📌 Đánh giá bằng AI", key="ai7"):
        st.markdown("### 🧠 Nhận định & đề xuất từ AI:")
        st.markdown(generate_analysis(
            f"Số lượng thí sinh chọn thi từng môn tổ hợp (trừ Toán, Văn): {subject_counts}"
        ))


# ======= PHẦN 2: Biểu đồ điểm trung bình theo Môn =======
st.subheader("📊 Biểu đồ điểm trung bình theo Môn")
available_subjects = [col for col in score_columns if col in df.columns]
selected_subject = st.selectbox("🎯 Chọn môn:", options=available_subjects)

if selected_subject:
    subject_avg_by_school = df_filtered.groupby("Lớp")[selected_subject].mean()
    overall_subject_avg = df_filtered[selected_subject].mean()

    subject_avg_by_school["TB toàn bộ"] = overall_subject_avg
    subject_avg_by_school = subject_avg_by_school.sort_values(ascending=False)

    # Đánh số thứ tự, bỏ qua dòng "TB toàn bộ"
    ranked_labels_sub = []
    rank_sub = 1
    for name in subject_avg_by_school.index:
        if name == "TB toàn bộ":
            ranked_labels_sub.append("Trung bình")
        else:
            ranked_labels_sub.append(f"{rank_sub}. {name}")
            rank_sub += 1

    colors = ['orange' if idx == "TB toàn bộ" else 'lightgreen' for idx in subject_avg_by_school.index]

    fig2, ax2 = plt.subplots(figsize=(12, 6))
    bars2 = ax2.bar(ranked_labels_sub, subject_avg_by_school.values, color=colors)
    for bar in bars2:
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2, height + 0.2, f"{height:.2f}", ha='center', va='bottom', fontsize=9, rotation=90)

    ax2.set_ylabel(f"Điểm TB môn {selected_subject}")
    ax2.set_title(f"Biểu đồ điểm trung bình môn {selected_subject} theo Lớp")
    ax2.set_ylim(0, 10)
    plt.xticks(rotation=45, ha='right')

    # 👉 Tô màu chữ "Trung bình" trên trục X thành cam
    xtick_labels_sub = ax2.get_xticklabels()
    for label in xtick_labels_sub:
        if label.get_text() == "Trung bình":
            label.set_color("orange")

    plt.tight_layout()
    st.pyplot(fig2)

    if st.checkbox("📌 Đánh giá bằng AI", key="ai2"):
        st.markdown("### 🧠 Nhận định & đề xuất từ AI:")
        st.markdown(generate_analysis(f"Dữ liệu điểm trung bình môn {selected_subject} theo từng trường: {subject_avg_by_school.to_dict()}"))



# ======= PHẦN 3: Phổ điểm môn =======
st.subheader("📉 Phổ điểm từng môn")
selected_subject_hist = st.selectbox("🧪 Chọn môn để xem phổ điểm:", options=available_subjects, key="hist")
bins = st.slider("🎯 Số cột trong phổ điểm:", min_value=5, max_value=30, value=30)

if selected_subject_hist:
    data = df_filtered[selected_subject_hist].dropna()
    fig_hist, ax_hist = plt.subplots(figsize=(10, 5))
    counts, bin_edges, patches = ax_hist.hist(data, bins=bins, color='steelblue', edgecolor='black')

    for count, patch in zip(counts, patches):
        bar_x = patch.get_x() + patch.get_width() / 2
        bar_height = patch.get_height()
        ax_hist.text(bar_x, bar_height + 0.5, f"{int(count)}", ha='center', va='bottom', fontsize=9)

    bin_centers = 0.5 * (bin_edges[1:] + bin_edges[:-1])
    for center in bin_centers:
        ax_hist.text(center, -0.5, f"{center:.1f}", ha='center', va='top', fontsize=9)

    ax_hist.set_title(f"Phổ điểm môn {selected_subject_hist}")
    ax_hist.set_xlabel("Điểm số")
    ax_hist.set_ylabel("Số học sinh")
    ax_hist.set_xlim(0, 10)
    ax_hist.set_ylim(bottom=0)
    plt.tight_layout()
    st.pyplot(fig_hist)
    st.info(f"🔍 Có {len(data)} học sinh có điểm môn {selected_subject_hist}")

    if st.checkbox("📌 Đánh giá bằng AI", key="ai3"):
        st.markdown("### 🧠 Nhận định & đề xuất từ AI:")
        st.markdown(generate_analysis(f"Phổ điểm môn {selected_subject_hist}: {counts.tolist()}"))

# ======= PHẦN 4: Điểm trung bình từng môn =======
st.subheader("📚 Điểm trung bình các môn thi")
subject_means_filtered = df_filtered[score_columns].mean()
subject_means_all = df[score_columns].mean()

fig4, ax4 = plt.subplots(figsize=(10, 5))
x = range(len(score_columns))
bar_width = 0.35

bars_filtered = ax4.bar([i - bar_width/2 for i in x], subject_means_filtered.values, width=bar_width, label="Lớp đã chọn", color='mediumseagreen')
bars_all = ax4.bar([i + bar_width/2 for i in x], subject_means_all.values, width=bar_width, label="Toàn trường", color='orange')

for i, (bar1, bar2) in enumerate(zip(bars_filtered, bars_all)):
    ax4.text(bar1.get_x() + bar1.get_width()/2, bar1.get_height() + 0.2, f"{bar1.get_height():.2f}", ha='center', va='bottom', fontsize=9, rotation=90)
    ax4.text(bar2.get_x() + bar2.get_width()/2, bar2.get_height() + 0.2, f"{bar2.get_height():.2f}", ha='center', va='bottom', fontsize=9, rotation=90)

ax4.set_xticks(list(x))
ax4.set_xticklabels(score_columns, rotation=0)
ax4.set_title("Biểu đồ điểm trung bình các môn học")
ax4.set_ylabel("Điểm trung bình")
ax4.set_ylim(0, 10)
ax4.legend()
plt.tight_layout()
st.pyplot(fig4)

if st.checkbox("📌 Đánh giá bằng AI", key="ai4"):
    st.markdown("### 🧠 Nhận định & đề xuất từ AI:")
    st.markdown(generate_analysis(f"So sánh điểm trung bình các môn thi giữa trường '{selected_school}' và toàn tỉnh.\nLớp: {subject_means_filtered.to_dict()}\nToàn trường: {subject_means_all.to_dict()}"))

st.info("ℹ️ Hãy chọn một lớp cụ thể để xem thêm thống kê học sinh.")

# ======= PHẦN 8 & 9: Chỉ hiển thị khi đã chọn lớp cụ thể =======
if selected_school != "Toàn trường":

    # ======= PHẦN 8: Biểu đồ điểm trung bình từng học sinh =======
    st.subheader("👨‍🎓 Biểu đồ điểm trung bình từng học sinh")

    student_avg_scores = df_filtered[['Họ tên', 'Điểm TB']].dropna().copy()
    overall_avg = student_avg_scores['Điểm TB'].mean()

    avg_row = pd.DataFrame([{'Họ tên': 'Trung bình', 'Điểm TB': overall_avg}])
    student_avg_scores = pd.concat([student_avg_scores, avg_row], ignore_index=True)

    student_avg_scores = student_avg_scores.sort_values(by='Điểm TB', ascending=False).reset_index(drop=True)

    ranked_labels_students = []
    rank_s = 1
    for name in student_avg_scores['Họ tên']:
        if name == "Trung bình":
            ranked_labels_students.append("Trung bình")
        else:
            ranked_labels_students.append(f"{rank_s}. {name}")
            rank_s += 1

    colors = ['orange' if name == "Trung bình" else 'violet' for name in student_avg_scores['Họ tên']]

    fig8, ax8 = plt.subplots(figsize=(12, 6))
    bars8 = ax8.bar(ranked_labels_students, student_avg_scores['Điểm TB'], color=colors)

    for bar in bars8:
        height = bar.get_height()
        ax8.text(bar.get_x() + bar.get_width()/2, height + 0.2, f"{height:.2f}", ha='center', va='bottom', fontsize=8, rotation=90)

    ax8.set_ylabel("Điểm trung bình")
    ax8.set_title("Biểu đồ điểm trung bình từng học sinh")
    ax8.set_ylim(0, 10)
    plt.xticks(rotation=90, ha='right')

    xtick_labels_s = ax8.get_xticklabels()
    for label in xtick_labels_s:
        if label.get_text() == "Trung bình":
            label.set_color("orange")

    plt.tight_layout()
    st.pyplot(fig8)

    if st.checkbox("📌 Đánh giá bằng AI", key="ai8"):
        st.markdown("### 🧠 Nhận định & đề xuất từ AI:")
        st.markdown(generate_analysis(f"Dữ liệu điểm trung bình từng học sinh (đã sắp xếp): {student_avg_scores.set_index('Họ tên')['Điểm TB'].to_dict()}"))

    # ======= PHẦN 9: Biểu đồ điểm môn theo từng học sinh =======
    st.subheader("📊 Biểu đồ điểm từng môn theo học sinh")
    available_subjects_9 = [col for col in score_columns if col in df.columns]
    selected_subject_9 = st.selectbox("🎯 Chọn môn:", options=available_subjects_9, key="mon_ph9")

    if selected_subject_9:
        df_subject = df_filtered[['Họ tên', selected_subject_9]].dropna().copy()
        subject_avg_overall = df_subject[selected_subject_9].mean()

        avg_row_9 = pd.DataFrame([{'Họ tên': 'Trung bình', selected_subject_9: subject_avg_overall}])
        df_subject = pd.concat([df_subject, avg_row_9], ignore_index=True)

        df_subject = df_subject.sort_values(by=selected_subject_9, ascending=False).reset_index(drop=True)

        ranked_labels_sub9 = []
        rank_sub9 = 1
        for name in df_subject['Họ tên']:
            if name == "Trung bình":
                ranked_labels_sub9.append("Trung bình")
            else:
                ranked_labels_sub9.append(f"{rank_sub9}. {name}")
                rank_sub9 += 1

        colors_9 = ['orange' if name == "Trung bình" else '#0099CC' for name in df_subject['Họ tên']]

        fig9, ax9 = plt.subplots(figsize=(12, 6))
        bars9 = ax9.bar(ranked_labels_sub9, df_subject[selected_subject_9], color=colors_9)

        for bar in bars9:
            height = bar.get_height()
            ax9.text(bar.get_x() + bar.get_width()/2, height + 0.2, f"{height:.2f}", ha='center', va='bottom', fontsize=9, rotation=90)

        ax9.set_ylabel(f"Điểm môn {selected_subject_9}")
        ax9.set_title(f"Biểu đồ điểm môn {selected_subject_9} theo từng học sinh")
        ax9.set_ylim(0, 10)
        plt.xticks(rotation=90, ha='right')

        xtick_labels_9 = ax9.get_xticklabels()
        for label in xtick_labels_9:
            if label.get_text() == "Trung bình":
                label.set_color("orange")

        plt.tight_layout()
        st.pyplot(fig9)

        if st.checkbox("📌 Đánh giá bằng AI", key="ai9"):
            st.markdown("### 🧠 Nhận định & đề xuất từ AI:")
            st.markdown(generate_analysis(f"Điểm môn {selected_subject_9} theo từng học sinh: {df_subject.set_index('Họ tên')[selected_subject_9].to_dict()}"))




# ====== CHÂN TRANG ======
st.markdown("---")
st.markdown("©️ **Bản quyền thuộc về iTeX-Teams**", unsafe_allow_html=True)