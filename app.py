import streamlit as st
import couchdb
import pandas as pd
from datetime import datetime

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="SekejapHadir", layout="wide", page_icon="⚡")

# --- 2. KONEKSI COUCHDB ---
COUCHDB_URL = 'http://admin:tik@172.27.0.1:5984/' 
DB_NAME = 'elearning_db'

def get_db():
    try:
        couch = couchdb.Server(COUCHDB_URL)
        if DB_NAME in couch:
            return couch[DB_NAME]
        return couch.create(DB_NAME)
    except Exception as e:
        st.error(f"Gagal terhubung ke CouchDB: {e}")
        return None

db = get_db()

# --- 3. FUNGSI PEMBANTU (CRUD CORE) ---
def query_docs(doc_type, extra_selector=None):
    if not db: return []
    selector = {'type': doc_type}
    if extra_selector:
        selector.update(extra_selector)
    return [doc for doc in db.find({'selector': selector})]

def delete_document(doc_id):
    try:
        doc = db.get(doc_id)
        db.delete(doc)
        st.toast("Data berhasil dihapus!", icon="🗑️")
        st.rerun()
    except:
        st.error("Gagal menghapus data.")

# --- 4. LOGIKA NAVIGASI ---
if 'current_page' not in st.session_state:
    st.session_state.current_page = "🏠 Beranda"

def navigate_to(page):
    st.session_state.current_page = page
    st.rerun()

# --- 5. INTERFACE UTAMA ---
def main():
    if not db: return

    st.sidebar.title("⚡ SekejapHadir")
    menu_options = ["🏠 Beranda", "📝 Absensi", "📊 Rekap Kehadiran", "⚙️ Kelola Data"]
    choice = st.sidebar.radio("Menu Utama", menu_options, index=menu_options.index(st.session_state.current_page))

    # --- MENU: BERANDA ---
    if choice == "🏠 Beranda":
        st.header("Jadwal Mengajar Hari Ini")
        tgl_pilih = st.date_input("Pilih Tanggal", datetime.now())
        tgl_str = tgl_pilih.strftime("%Y-%m-%d")

        schedules = query_docs("schedule", {"date": tgl_str})
        
        if not schedules:
            st.info(f"Tidak ada jadwal mengajar pada {tgl_str}.")
            st.caption("Tambahkan jadwal di menu 'Kelola Data' > 'Jadwal'")
        else:
            for sch in schedules:
                with st.container(border=True):
                    c1, c2 = st.columns([3, 1])
                    c1.markdown(f"### {sch['class_name']}\n**Mata Pelajaran:** {sch['subject_name']}")
                    if c2.button("Mulai Absen", key=f"btn_sch_{sch['_id']}", use_container_width=True):
                        st.session_state.active_sch = sch
                        navigate_to("📝 Absensi")

    # --- MENU: ABSENSI ---
    elif choice == "📝 Absensi":
        st.header("Input Presensi")
        active_sch = st.session_state.get('active_sch', None)

        if not active_sch:
            st.warning("Silakan pilih jadwal di menu Beranda terlebih dahulu.")
        else:
            with st.container(border=True):
                st.subheader(f"{active_sch['class_name']} — {active_sch['subject_name']}")
                st.caption(f"Tanggal: {active_sch['date']}")

            students = query_docs("student", {"class_id": active_sch['class_id']})
            
            if not students:
                st.error("Belum ada siswa di kelas ini. Daftarkan siswa di menu Kelola Data.")
            else:
                attendance_results = {}
                st.divider()
                # ALUR 10 DETIK: Default "Hadir", Guru hanya ganti yang bermasalah
                for s in students:
                    col_n, col_s = st.columns([2, 1])
                    col_n.write(f"👤 **{s['name']}**")
                    status = col_s.segmented_control(
                        "Status", ["Hadir", "Telat", "Alfa"], 
                        default="Hadir", key=f"att_{s['_id']}"
                    )
                    attendance_results[s['_id']] = {"name": s['name'], "status": status}

                st.divider()
                if st.button("💾 Simpan Kehadiran", type="primary", use_container_width=True):
                    db.save({
                        "type": "attendance",
                        "date": active_sch['date'],
                        "class_id": active_sch['class_id'],
                        "class_name": active_sch['class_name'],
                        "subject_id": active_sch['subject_id'],
                        "subject_name": active_sch['subject_name'],
                        "records": attendance_results,
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })
                    st.success("Data berhasil disimpan!")
                    st.balloons()
                    del st.session_state.active_sch
                    st.button("Kembali ke Beranda", on_click=navigate_to, args=("🏠 Beranda",))

    # --- MENU: REKAP KEHADIRAN ---
    elif choice == "📊 Rekap Kehadiran":
        st.header("Laporan Presensi")
        all_att = query_docs("attendance")
        
        if not all_att:
            st.info("Belum ada data absensi yang tersimpan.")
        else:
            df_all = pd.DataFrame(all_att)
            col_f1, col_f2 = st.columns(2)
            f_kls = col_f1.multiselect("Filter Kelas", options=df_all['class_name'].unique())
            f_mpl = col_f2.multiselect("Filter Mapel", options=df_all['subject_name'].unique())

            filtered = df_all
            if f_kls: filtered = filtered[filtered['class_name'].isin(f_kls)]
            if f_mpl: filtered = filtered[filtered['subject_name'].isin(f_mpl)]

            for _, row in filtered.iterrows():
                with st.expander(f"📅 {row['date']} | {row['class_name']} - {row['subject_name']}"):
                    recs = row['records']
                    # Hitung Statistik
                    stats = pd.Series([v['status'] for v in recs.values()]).value_counts()
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Hadir", stats.get("Hadir", 0))
                    m2.metric("Telat", stats.get("Telat", 0))
                    m3.metric("Alfa", stats.get("Alfa", 0))
                    
                    # Detail Tabel
                    df_det = pd.DataFrame([{"Nama": v['name'], "Status": v['status']} for v in recs.values()])
                    st.table(df_det)
                    
                    if st.button("🗑️ Hapus Rekap Ini", key=f"del_att_{row['_id']}"):
                        delete_document(row['_id'])

    # --- MENU: KELOLA DATA (CRUD) ---
    elif choice == "⚙️ Kelola Data":
        st.header("Manajemen Database")
        t_kls, t_sw, t_mp, t_jd = st.tabs(["🏫 Kelas", "👥 Siswa", "📖 Mapel", "📅 Jadwal"])

        # TAB KELAS
        with t_kls:
            with st.form("form_kls"):
                nk = st.text_input("Nama Kelas Baru")
                if st.form_submit_button("Simpan"):
                    db.save({"type": "class", "name": nk})
                    st.rerun()
            for c in query_docs("class"):
                col1, col2 = st.columns([5, 1])
                col1.write(f"🏫 {c['name']}")
                if col2.button("🗑️", key=f"d_k_{c['_id']}"): delete_document(c['_id'])

        # TAB SISWA
        with t_sw:
            classes = query_docs("class")
            c_opts = {c['name']: c['_id'] for c in classes}
            if c_opts:
                with st.form("form_sw"):
                    ns = st.text_input("Nama Siswa")
                    sk = st.selectbox("Pilih Kelas", options=list(c_opts.keys()))
                    if st.form_submit_button("Tambah Siswa"):
                        db.save({"type": "student", "name": ns, "class_id": c_opts[sk]})
                        st.rerun()
                
                view_k = st.selectbox("Lihat Siswa di Kelas:", options=list(c_opts.keys()))
                for s in query_docs("student", {"class_id": c_opts[view_k]}):
                    col1, col2 = st.columns([5, 1])
                    col1.write(f"👤 {s['name']}")
                    if col2.button("🗑️", key=f"d_s_{s['_id']}"): delete_document(s['_id'])

        # TAB MAPEL
        with t_mp:
            if c_opts:
                with st.form("form_mp"):
                    nm = st.text_input("Nama Mata Pelajaran")
                    mk = st.selectbox("Untuk Kelas", options=list(c_opts.keys()), key="sel_mk")
                    if st.form_submit_button("Simpan Mapel"):
                        db.save({"type": "subject", "name": nm, "class_id": c_opts[mk]})
                        st.rerun()
                
                for m in query_docs("subject"):
                    # Cari nama kelas dari ID
                    kls_nama = next((k for k, v in c_opts.items() if v == m['class_id']), "Unknown")
                    col1, col2 = st.columns([5, 1])
                    col1.write(f"📖 {m['name']} — (Kelas: {kls_nama})")
                    if col2.button("🗑️", key=f"d_m_{m['_id']}"): delete_document(m['_id'])

        # TAB JADWAL
        with t_jd:
            if c_opts:
                col_jk, col_jt = st.columns(2)
                sel_jk = col_jk.selectbox("Pilih Kelas", options=list(c_opts.keys()), key="sel_jk")
                sel_jt = col_jt.date_input("Pilih Tanggal")
                
                # Filter mapel berdasarkan kelas yang dipilih
                sub_list = query_docs("subject", {"class_id": c_opts[sel_jk]})
                s_opts = {s['name']: s['_id'] for s in sub_list}
                
                if s_opts:
                    sel_jm = st.selectbox("Pilih Mapel", options=list(s_opts.keys()))
                    if st.button("➕ Tambahkan ke Jadwal", use_container_width=True):
                        db.save({
                            "type": "schedule",
                            "date": sel_jt.strftime("%Y-%m-%d"),
                            "class_id": c_opts[sel_jk], "class_name": sel_jk,
                            "subject_id": s_opts[sel_jm], "subject_name": sel_jm
                        })
                        st.success("Jadwal Berhasil Ditambahkan!")
                        st.rerun()
                else:
                    st.warning("Buat Mata Pelajaran dulu untuk kelas ini di tab 'Mapel'.")

if __name__ == "__main__":
    main()