import streamlit as st
from db_manager import CouchDBManager

# Konfigurasi Koneksi (Sesuaikan dengan kredensialmu)
DB_URL = "http://admin:tik@172.27.0.1:5984/"
DB_NAME = "elearning_db"

db = CouchDBManager(DB_URL, DB_NAME)

st.title("📦 Streamlit CRUD - CouchDB Edition")

# --- Form Input (Create) ---
with st.expander("Tambah Data Baru"):
    with st.form("create_form", clear_on_submit=True):
        name = st.text_input("Nama Barang")
        qty = st.number_input("Jumlah", min_value=0)
        submitted = st.form_submit_button("Simpan")
        
        if submitted:
            res = db.create_record({"name": name, "qty": qty})
            st.success(f"Data tersimpan! ID: {res[0]}")
            st.rerun()

# --- Tampilan Data (Read, Update, Delete) ---
st.subheader("Daftar Inventaris")
records = db.read_all()

if not records:
    st.info("Belum ada data.")
else:
    for doc in records:
        with st.container(border=True):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                # Mode Edit Sederhana
                new_name = st.text_input("Nama", doc['name'], key=f"n_{doc.id}")
                new_qty = st.number_input("Qty", value=doc['qty'], key=f"q_{doc.id}")
            
            with col2:
                st.write("Aksi")
                if st.button("Update", key=f"upd_{doc.id}"):
                    db.update_record(doc.id, {"name": new_name, "qty": new_qty})
                    st.toast("Data diperbarui!")
                    st.rerun()
                
                if st.button("Hapus", key=f"del_{doc.id}", type="primary"):
                    db.delete_record(doc.id)
                    st.warning("Data dihapus!")
                    st.rerun()