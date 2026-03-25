import streamlit as st
import couchdb
import pandas as pd
from datetime import datetime

# --- 1. KONFIGURASI & KONEKSI ---
st.set_page_config(page_title="SekejapHadir Ultra", layout="wide", page_icon="⚡")

COUCHDB_URL = 'http://admin:tik@172.27.0.1:5984/' 
DB_NAME = 'elearning_db'

def get_db():
    try:
        couch = couchdb.Server(COUCHDB_URL)
        return couch[DB_NAME] if DB_NAME in couch else couch.create(DB_NAME)
    except:
        return None

db = get_db()

# --- 2. HELPER FUNCTIONS ---
def query_docs(doc_type, extra_selector=None):
    if not db: return []
    selector = {'type': doc_type}
    if extra_selector:
        selector.update(extra_selector)
    return [doc for doc in db.find({'selector': selector})]

def delete_doc(doc_id):
    try:
        doc = db.get(doc_id)
        db.delete(doc)
        st.toast("Data terhapus!", icon="🗑️")
        st.rerun()
    except:
        st.error("Gagal menghapus.")

# --- 3. STATE & NAVIGATION ---
if 'page' not in st.session_state:
    st.session_state.page = "🏠 Beranda"

def nav(page_name):
    st.session_state.page = page_name
    st.rerun()

# --- 4. UI LOGIC ---
def main():
    if not db:
        st.error("⚠️ Koneksi CouchDB Gagal. Cek kredensial Anda.")
        return

    st.sidebar.title("⚡ SekejapHadir")
    menu = ["🏠 Beranda", "📝 Absensi", "📊 Rekap Sesi", "👤 Rekap Per Siswa", "⚙️ Kelola Data"]
    choice = st.sidebar.radio("Menu", menu, index=menu.index(st.session_state.page))

    # --- TAB: BERANDA ---
    if choice == "🏠 Beranda":
        st.header("Jadwal Mengajar")
        tgl_str = st.date_input("Tanggal", datetime.now()).strftime("%Y-%m-%d")
        schs = query_docs("schedule", {"date": tgl_str})
        
        if not schs:
            st.info("Belum ada jadwal. Tambahkan di menu Kelola Data.")
        else:
            for s in schs:
                with st.container(border=True):
                    c1, c2 = st.columns([3, 1])
                    c1.markdown(f"### {s['class_name']}\n**Mapel:** {s['subject_name']}")
                    if c2.button("Mulai Absen", key=f"go_{s['_id']}", use_container_width=True):
                        st.session_state.active_sch = s
                        nav("📝 Absensi")

    # --- TAB: ABSENSI (FLOW 10 DETIK) ---
    elif choice == "📝 Absensi":
        st.header("Input Presensi")
        sch = st.session_state.get('active_sch')
        
        if not sch:
            st.warning("Pilih jadwal di Beranda dulu!")
        else:
            st.subheader(f"{sch['class_name']} - {sch['subject_name']} ({sch['date']})")
            students = query_docs("student", {"class_id": sch['class_id']})
            
            if not students:
                st.error("Siswa tidak ditemukan.")
            else:
                att_data = {}
                st.divider()
                for s in students:
                    col_n, col_s = st.columns([2, 1])
                    col_n.write(f"👤 **{s['name']}**")
                    # TAMBAH STATUS IZIN
                    status = col_s.segmented_control(
                        "Status", ["Hadir", "Izin", "Telat", "Alfa"], 
                        default="Hadir", key=f"att_{s['_id']}"
                    )
                    att_data[s['_id']] = {"name": s['name'], "status": status}

                if st.button("💾 Simpan Absensi", type="primary", use_container_width=True):
                    db.save({
                        "type": "attendance",
                        "date": sch['date'],
                        "class_id": sch['class_id'], "class_name": sch['class_name'],
                        "subject_id": sch['subject_id'], "subject_name": sch['subject_name'],
                        "records": att_data
                    })
                    st.success("Tersimpan!")
                    del st.session_state.active_sch
                    st.balloons()

    # --- TAB: REKAP PER SESI ---
    elif choice == "📊 Rekap Sesi":
        st.header("Riwayat Absensi")
        all_att = query_docs("attendance")
        for a in all_att:
            with st.expander(f"📅 {a['date']} - {a['class_name']} ({a['subject_name']})"):
                recs = a['records']
                df = pd.DataFrame([{"Nama": v['name'], "Status": v['status']} for v in recs.values()])
                st.table(df)
                if st.button("Hapus Rekap", key=f"del_{a['_id']}"):
                    delete_doc(a['_id'])

    # --- TAB BARU: REKAP PER SISWA ---
    elif choice == "👤 Rekap Per Siswa":
        st.header("Akumulasi Kehadiran Siswa")
        classes = query_docs("class")
        c_opts = {c['name']: c['_id'] for c in classes}
        
        sel_c = st.selectbox("Pilih Kelas untuk Laporan", options=list(c_opts.keys()))
        
        if sel_c:
            # Ambil semua absensi untuk kelas ini
            att_docs = query_docs("attendance", {"class_id": c_opts[sel_c]})
            # Ambil semua daftar siswa di kelas ini
            student_list = query_docs("student", {"class_id": c_opts[sel_c]})
            
            if not att_docs:
                st.info("Belum ada data absensi tercatat untuk kelas ini.")
            else:
                # Inisialisasi hitungan
                report = []
                for s in student_list:
                    s_id = s['_id']
                    counts = {"Hadir": 0, "Izin": 0, "Telat": 0, "Alfa": 0}
                    
                    # Iterasi setiap dokumen absensi
                    for doc in att_docs:
                        if s_id in doc['records']:
                            stat = doc['records'][s_id]['status']
                            counts[stat] += 1
                    
                    report.append({
                        "Nama Siswa": s['name'],
                        "✅ Hadir": counts["Hadir"],
                        "📩 Izin": counts["Izin"],
                        "⏰ Telat": counts["Telat"],
                        "❌ Alfa": counts["Alfa"],
                        "📈 Total Sesi": sum(counts.values())
                    })
                
                df_report = pd.DataFrame(report)
                st.dataframe(df_report, use_container_width=True, hide_index=True)
                
                # Highlight Siswa Bermasalah (Alfa > 3)
                st.subheader("🚩 Perhatian Khusus (Alfa > 3)")
                warning_df = df_report[df_report["❌ Alfa"] > 3]
                if not warning_df.empty:
                    st.warning(f"Ada {len(warning_df)} siswa dengan tingkat ketidakhadiran tinggi.")
                    st.table(warning_df)
                else:
                    st.success("Semua siswa masih dalam batas kehadiran aman.")

    # --- TAB: KELOLA DATA (FULL CRUD) ---
    elif choice == "⚙️ Kelola Data":
        st.header("Manajemen Database")
        t1, t2, t3, t4 = st.tabs(["🏫 Kelas", "👥 Siswa", "📖 Mapel", "📅 Jadwal"])

        # CRUD KELAS
        with t1:
            with st.form("f_k"):
                nk = st.text_input("Nama Kelas")
                if st.form_submit_button("Simpan"):
                    db.save({"type": "class", "name": nk}); st.rerun()
            for c in query_docs("class"):
                col1, col2 = st.columns([5,1])
                col1.write(f"🏫 {c['name']}")
                if col2.button("🗑️", key=f"dk_{c['_id']}"): delete_doc(c['_id'])

        # CRUD SISWA
        with t2:
            classes = query_docs("class")
            c_opts = {c['name']: c['_id'] for c in classes}
            with st.form("f_s"):
                ns = st.text_input("Nama Siswa")
                sk = st.selectbox("Kelas", options=list(c_opts.keys()))
                if st.form_submit_button("Simpan"):
                    db.save({"type": "student", "name": ns, "class_id": c_opts[sk]}); st.rerun()
            if c_opts:
                view_k = st.selectbox("Filter Kelas", options=list(c_opts.keys()))
                for s in query_docs("student", {"class_id": c_opts[view_k]}):
                    col1, col2 = st.columns([5,1])
                    col1.write(f"👤 {s['name']}")
                    if col2.button("🗑️", key=f"ds_{s['_id']}"): delete_doc(s['_id'])

        # CRUD MAPEL
        with t3:
            with st.form("f_m"):
                nm = st.text_input("Nama Mapel")
                mk = st.selectbox("Untuk Kelas", options=list(c_opts.keys()), key="mk")
                if st.form_submit_button("Simpan"):
                    db.save({"type": "subject", "name": nm, "class_id": c_opts[mk]}); st.rerun()
            for m in query_docs("subject"):
                st.write(f"📖 {m['name']} (ID Kelas: {m['class_id']})")
                if st.button("Hapus", key=f"dm_{m['_id']}"): delete_doc(m['_id'])

        # CRUD JADWAL
        with t4:
            with st.form("f_j"):
                tj = st.date_input("Tanggal")
                kj = st.selectbox("Kelas", options=list(c_opts.keys()), key="kj")
                # Dinamis mapel
                ms = query_docs("subject", {"class_id": c_opts[kj]})
                mo = {m['name']: m['_id'] for m in ms}
                mj = st.selectbox("Mapel", options=list(mo.keys()))
                if st.form_submit_button("Buat Jadwal"):
                    db.save({
                        "type": "schedule", "date": tj.strftime("%Y-%m-%d"),
                        "class_id": c_opts[kj], "class_name": kj,
                        "subject_id": mo[mj], "subject_name": mj
                    }); st.rerun()
            for j in query_docs("schedule"):
                st.write(f"📅 {j['date']} | {j['class_name']} - {j['subject_name']}")
                if st.button("Hapus", key=f"dj_{j['_id']}"): delete_doc(j['_id'])

if __name__ == "__main__":
    main()