import streamlit as st
import couchdb
import pandas as pd
from datetime import datetime

# --- CONFIG & CONNECTION ---
st.set_page_config(page_title="SekejapHadir Pro", layout="wide", page_icon="⚡")

COUCHDB_URL = 'http://admin:tik@172.27.0.1:5984/' 
DB_NAME = 'elearning_db'

def get_db():
    try:
        couch = couchdb.Server(COUCHDB_URL)
        return couch[DB_NAME] if DB_NAME in couch else couch.create(DB_NAME)
    except:
        return None

db = get_db()

# --- DB HELPERS ---
def query_docs(doc_type, extra_selector=None):
    if not db: return []
    selector = {'type': doc_type}
    if extra_selector:
        selector.update(extra_selector)
    return [doc for doc in db.find({'selector': selector})]

# --- UI APP ---
def main():
    if not db:
        st.error("Koneksi CouchDB Bermasalah.")
        return

    st.sidebar.title("⚡ SekejapHadir")
    
    # Update Menu Sidebar: Tambah Rekap
    menu = ["🏠 Beranda", "📝 Absensi", "📊 Rekap Kehadiran", "⚙️ Kelola Data"]
    
    if 'current_page' not in st.session_state:
        st.session_state.current_page = "🏠 Beranda"

    choice = st.sidebar.radio("Navigasi", menu, index=menu.index(st.session_state.current_page))

    # --- 1. BERANDA ---
    if choice == "🏠 Beranda":
        st.header("Jadwal Mengajar")
        tgl_str = st.date_input("Pilih Tanggal", datetime.now()).strftime("%Y-%m-%d")
        schedules = query_docs("schedule", {"date": tgl_str})
        
        if not schedules:
            st.info(f"Tidak ada jadwal pada {tgl_str}.")
        else:
            for sch in schedules:
                with st.container(border=True):
                    c1, c2 = st.columns([3, 1])
                    c1.markdown(f"### {sch['class_name']}\n**Mapel:** {sch['subject_name']}")
                    if c2.button("Mulai Absen", key=f"go_{sch['_id']}"):
                        st.session_state.active_sch = sch
                        st.session_state.current_page = "📝 Absensi"
                        st.rerun()

    # --- 2. ABSENSI (HANYA SIMPAN DATA) ---
    elif choice == "📝 Absensi":
        st.header("Input Presensi Siswa")
        active_sch = st.session_state.get('active_sch', None)

        if active_sch:
            st.success(f"Kelas: **{active_sch['class_name']}** | Mapel: **{active_sch['subject_name']}**")
            students = query_docs("student", {"class_id": active_sch['class_id']})
            
            if not students:
                st.warning("Belum ada siswa di kelas ini.")
            else:
                attendance_results = {}
                for s in students:
                    col_n, col_s = st.columns([2, 1])
                    col_n.write(f"👤 **{s['name']}**")
                    status = col_s.segmented_control(
                        "Status", ["Hadir", "Telat", "Alfa"], 
                        default="Hadir", key=f"att_{s['_id']}"
                    )
                    attendance_results[s['_id']] = {"name": s['name'], "status": status}

                if st.button("💾 Simpan Kehadiran", type="primary", use_container_width=True):
                    db.save({
                        "type": "attendance",
                        "date": active_sch['date'],
                        "class_id": active_sch['class_id'],
                        "class_name": active_sch['class_name'],
                        "subject_id": active_sch['subject_id'],
                        "subject_name": active_sch['subject_name'],
                        "records": attendance_results,
                        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })
                    st.success("Data kehadiran berhasil disimpan ke database!")
                    del st.session_state.active_sch # Reset setelah simpan
        else:
            st.info("Pilih jadwal di menu **🏠 Beranda** untuk mulai absen.")

    # --- 3. MENU BARU: REKAP KEHADIRAN ---
    elif choice == "📊 Rekap Kehadiran":
        st.header("Rekap Presensi Siswa")
        
        # Filter Rekap
        all_attendance = query_docs("attendance")
        
        if not all_attendance:
            st.warning("Belum ada data absensi yang tersimpan.")
        else:
            # Mengubah list doc menjadi DataFrame untuk kemudahan filter
            df_rekap = pd.DataFrame(all_attendance)
            
            col1, col2 = st.columns(2)
            filter_kelas = col1.multiselect("Filter Kelas", options=df_rekap['class_name'].unique())
            filter_mapel = col2.multiselect("Filter Mapel", options=df_rekap['subject_name'].unique())

            # Logika Filtering
            filtered_df = df_rekap
            if filter_kelas:
                filtered_df = filtered_df[filtered_df['class_name'].isin(filter_kelas)]
            if filter_mapel:
                filtered_df = filtered_df[filtered_df['subject_name'].isin(filter_mapel)]

            st.divider()

            for _, row in filtered_df.iterrows():
                with st.expander(f"📅 {row['date']} - {row['class_name']} ({row['subject_name']})"):
                    # Tampilkan Statistik Singkat
                    records = row['records']
                    stats = pd.Series([v['status'] for v in records.values()]).value_counts()
                    
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Hadir", stats.get("Hadir", 0))
                    c2.metric("Telat", stats.get("Telat", 0))
                    c3.metric("Alfa", stats.get("Alfa", 0))

                    # Tampilkan Tabel Detail Siswa
                    detail_data = [{"Nama Siswa": v['name'], "Status": v['status']} for v in records.values()]
                    st.table(pd.DataFrame(detail_data))
                    
                    if st.button("🗑️ Hapus Rekap Ini", key=f"del_rec_{row['_id']}"):
                        db.delete(row)
                        st.rerun()

    # --- 4. KELOLA DATA (CRUD) ---
    elif choice == "⚙️ Kelola Data":
        st.header("Manajemen Data")
        # ... (Logika CRUD Kelas, Siswa, Mapel, Jadwal tetap sama seperti sebelumnya)
        st.info("Gunakan tab di bawah untuk mengelola entitas database.")
        # [Tambahkan kembali kode CRUD Tab Kelas, Siswa, Mapel, Jadwal di sini]

if __name__ == "__main__":
    main()