import streamlit as st
import pandas as pd
import os
import uuid
import json
import hashlib
from streamlit_quill import st_quill

# =========================
# CONFIG
# =========================
st.set_page_config(layout="wide")

DB_FILES = {
    "users": "users.csv",
    "classes": "classes.csv",
    "materials": "materials.csv",
    "progress": "progress.csv",
    "enrollments": "enrollments.csv"
}

# =========================
# UTIL
# =========================
def hash_pw(p):
    return hashlib.sha256(p.encode()).hexdigest()

@st.cache_data
def load_df(key):
    return pd.read_csv(DB_FILES[key])

def save_df(df, key):
    df.to_csv(DB_FILES[key], index=False)
    load_df.clear()

# =========================
# INIT DB
# =========================
def init_db():
    for key, file in DB_FILES.items():
        if not os.path.exists(file):
            if key == "users":
                df = pd.DataFrame(
                    [["guru", hash_pw("guru"), "Master Guru", "teacher"]],
                    columns=["username", "password", "name", "role"]
                )
            elif key == "classes":
                df = pd.DataFrame(columns=["id", "name", "desc", "code"])
            elif key == "materials":
                df = pd.DataFrame(columns=["id", "class_id", "order", "title", "content", "questions", "passing_grade"])
            elif key == "progress":
                df = pd.DataFrame(columns=["username", "class_id", "order", "score", "status"])
            elif key == "enrollments":
                df = pd.DataFrame(columns=["username", "class_id"])
            df.to_csv(file, index=False)

# =========================
# AUTH
# =========================
def login_page():
    st.title("🛡️ E-Learning Pro")

    tab1, tab2 = st.tabs(["Login", "Daftar"])

    with tab1:
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")

        if st.button("Login"):
            users = load_df("users")
            user = users[(users['username'] == u) & (users['password'] == hash_pw(p))]

            if not user.empty:
                st.session_state.user = user.iloc[0].to_dict()
                st.rerun()
            else:
                st.error("Login gagal")

    with tab2:
        name = st.text_input("Nama")
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")

        if st.button("Daftar"):
            users = load_df("users")

            if u in users['username'].values:
                st.error("Username sudah ada")
            elif not u or not p:
                st.error("Harus isi semua")
            else:
                new = pd.DataFrame([[u, hash_pw(p), name, "student"]], columns=users.columns)
                save_df(pd.concat([users, new]), "users")
                st.success("Berhasil daftar")

# =========================
# TEACHER
# =========================
def teacher_dashboard():
    st.sidebar.header(f"👨‍🏫 {st.session_state.user['name']}")
    menu = st.sidebar.radio("Menu", ["Kelas", "Materi", "Monitoring"])

    # ===== KELAS =====
    if menu == "Kelas":
        st.header("Manajemen Kelas")

        with st.form("kelas"):
            name = st.text_input("Nama")
            desc = st.text_area("Deskripsi")
            code = st.text_input("Kode")

            if st.form_submit_button("Tambah"):
                if not name:
                    st.error("Nama wajib")
                else:
                    df = load_df("classes")
                    new = pd.DataFrame({
                        "id": [str(uuid.uuid4())[:8]],
                        "name": [name],
                        "desc": [desc],
                        "code": [code]
                    })
                    save_df(pd.concat([df, new]), "classes")
                    st.success("Berhasil")
                    st.rerun()

        df = load_df("classes")
        st.dataframe(df)

    # ===== MATERI =====
    elif menu == "Materi":
        st.header("Materi")

        classes = load_df("classes")
        if classes.empty:
            st.warning("Buat kelas dulu")
            return

        class_map = {r['name']: r['id'] for _, r in classes.iterrows()}
        selected = st.selectbox("Kelas", list(class_map.keys()))
        cid = class_map[selected]

        title = st.text_input("Judul")
        order = st.number_input("Level", min_value=1)
        content = st_quill()
        passing = st.slider("Passing", 0, 100, 75)

        # STATE
        if "builder_q" not in st.session_state:
            st.session_state.builder_q = []

        # ===== SOAL =====
        st.subheader("Soal")

        with st.form("soal"):
            q = st.text_input("Pertanyaan")
            a = st.text_input("A")
            b = st.text_input("B")
            c = st.text_input("C")
            d = st.text_input("D")
            ans = st.selectbox("Jawaban", ["A","B","C","D"])

            if st.form_submit_button("Tambah"):
                if not all([q,a,b,c,d]):
                    st.error("Lengkapi")
                else:
                    st.session_state.builder_q.append({
                        "question": q,
                        "options": {"A":a,"B":b,"C":c,"D":d},
                        "answer": ans
                    })
                    st.rerun()

        for i, soal in enumerate(st.session_state.builder_q):
            st.write(f"{i+1}. {soal['question']} ({soal['answer']})")

        if st.button("Simpan Materi"):
            if not title or not st.session_state.builder_q:
                st.error("Isi lengkap")
            else:
                df = load_df("materials")
                new = pd.DataFrame([[
                    str(uuid.uuid4())[:8],
                    cid,
                    order,
                    title,
                    content,
                    json.dumps(st.session_state.builder_q),
                    passing
                ]], columns=df.columns)

                save_df(pd.concat([df, new]), "materials")
                st.session_state.builder_q = []
                st.success("Tersimpan")
                st.rerun()

    # ===== MONITORING =====
    elif menu == "Monitoring":
        df = load_df("progress")
        st.dataframe(df)

        if not df.empty:
            st.metric("User", df['username'].nunique())
            st.metric("Rata-rata", int(df['score'].mean()))

# =========================
# STUDENT
# =========================
def student_dashboard():
    u = st.session_state.user['username']
    st.sidebar.header(f"🎓 {st.session_state.user['name']}")

    classes = load_df("classes")
    enroll = load_df("enrollments")

    my = enroll[enroll['username']==u]['class_id']
    classes = classes[classes['id'].isin(my)]

    if classes.empty:
        st.title("Gabung Kelas")
        code = st.text_input("Kode")

        if st.button("Gabung"):
            allc = load_df("classes")
            c = allc[allc['code']==code]

            if not c.empty:
                cid = c.iloc[0]['id']
                new = pd.DataFrame([[u, cid]], columns=["username","class_id"])
                save_df(pd.concat([enroll, new]), "enrollments")
                st.success("Masuk kelas")
                st.rerun()
            else:
                st.error("Kode salah")
        return

    class_map = {r['name']: r['id'] for _, r in classes.iterrows()}
    selected = st.selectbox("Kelas", list(class_map.keys()))
    cid = class_map[selected]

    mats = load_df("materials")
    mats = mats[mats['class_id']==cid]
    mats = mats.sort_values("order").reset_index(drop=True)

    progs = load_df("progress")
    user_prog = progs[(progs['username']==u)&(progs['class_id']==cid)]

    status_map = dict(zip(user_prog['order'], user_prog['status']))

    st.title(selected)

    # Progress bar
    if not mats.empty:
        progress = len(user_prog[user_prog['status']=="LULUS"]) / len(mats)
        st.progress(progress)

    # LIST
    for i in range(len(mats)):
        row = mats.iloc[i]
        order = row['order']

        if i == 0:
            unlocked = True
        else:
            prev = mats.iloc[i-1]['order']
            unlocked = status_map.get(prev) == "LULUS"

        if st.button(f"{'🔓' if unlocked else '🔒'} Level {order} - {row['title']}",
                     disabled=not unlocked):
            st.session_state.selected = row.to_dict()

    # DETAIL
    if "selected" in st.session_state:
        item = st.session_state.selected

        st.header(item['title'])
        st.markdown(item['content'], unsafe_allow_html=True)

        questions = json.loads(item['questions'])

        with st.form("quiz"):
            benar = 0
            answers = {}

            for i, q in enumerate(questions):
                answers[i] = st.radio(q['question'], ["A","B","C","D"], key=i)

            if st.form_submit_button("Submit"):
                for i, q in enumerate(questions):
                    if answers[i] == q['answer']:
                        benar += 1

                score = int(benar/len(questions)*100)
                status = "LULUS" if score >= item['passing_grade'] else "GAGAL"

                df = load_df("progress")
                df = df[~(
                    (df['username']==u)&
                    (df['class_id']==cid)&
                    (df['order']==item['order'])
                )]

                new = pd.DataFrame([[u,cid,item['order'],score,status]],
                                   columns=df.columns)

                save_df(pd.concat([df,new]), "progress")

                st.success(f"{status} ({score}%)")
                st.rerun()

# =========================
# MAIN
# =========================
init_db()

if "user" not in st.session_state:
    login_page()
else:
    if st.sidebar.button("Logout"):
        st.session_state.clear()
        st.rerun()

    if st.session_state.user['role']=="teacher":
        teacher_dashboard()
    else:
        student_dashboard()