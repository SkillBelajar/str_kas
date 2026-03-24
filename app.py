import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="KasCepat Ketapang", page_icon="💰", layout="centered")

# --- DATABASE SETUP (SQLITE - OFFLINE) ---
def init_db():
    conn = sqlite3.connect('kas_ketapang.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS transaksi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tanggal TEXT,
            tipe TEXT,
            nominal REAL,
            catatan TEXT
        )
    ''')
    conn.commit()
    conn.close()

def tambah_data(tipe, nominal, catatan):
    conn = sqlite3.connect('kas_ketapang.db')
    c = conn.cursor()
    tanggal_sekarang = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute('INSERT INTO transaksi (tanggal, tipe, nominal, catatan) VALUES (?,?,?,?)',
              (tanggal_sekarang, tipe, nominal, catatan))
    conn.commit()
    conn.close()

def ambil_data_hari_ini():
    conn = sqlite3.connect('kas_ketapang.db')
    hari_ini = datetime.now().strftime("%Y-%m-%d")
    df = pd.read_sql_query(f"SELECT * FROM transaksi WHERE tanggal LIKE '{hari_ini}%' ORDER BY id DESC", conn)
    conn.close()
    return df

# Inisialisasi DB saat aplikasi jalan
init_db()

# --- UI APP ---
st.title("💰 KasCepat Ketapang")
st.markdown("Pencatatan kas pasar & koperasi desa. *Mudah, Cepat, Offline.*")
st.divider()

# --- BAGIAN INPUT (3 TOMBOL BESAR) ---
col1, col2 = st.columns(2)

with col1:
    if st.button("➕ UANG MASUK", use_container_width=True, type="primary"):
        st.session_state.mode = "Masuk"

with col2:
    if st.button("➖ UANG KELUAR", use_container_width=True):
        st.session_state.mode = "Keluar"

# Form Input jika tombol ditekan
if 'mode' in st.session_state:
    with st.expander(f"Input Transaksi {st.session_state.mode}", expanded=True):
        with st.form("form_transaksi", clear_on_submit=True):
            nom = st.number_input("Nominal (Rp)", min_value=0, step=500, format="%d")
            cat = st.text_input("Catatan Singkat (Contoh: Jual Beras, Beli Es)", placeholder="Ketik di sini...")
            
            submit = st.form_submit_button(f"Simpan Uang {st.session_state.mode}")
            if submit:
                if nom > 0:
                    tambah_data(st.session_state.mode, nom, cat)
                    st.success(f"Berhasil simpan Rp {nom:,}")
                    del st.session_state.mode
                    st.rerun()
                else:
                    st.error("Isi nominal dulu!")

st.divider()

# --- RINGKASAN HARI INI ---
df_hari_ini = ambil_data_hari_ini()

# Hitung Total
total_masuk = df_hari_ini[df_hari_ini['tipe'] == 'Masuk']['nominal'].sum()
total_keluar = df_hari_ini[df_hari_ini['tipe'] == 'Keluar']['nominal'].sum()
saldo_bersih = total_masuk - total_keluar

st.subheader("📊 Ringkasan Hari Ini")
m1, m2, m3 = st.columns(3)
m1.metric("Pemasukan", f"Rp {total_masuk:,.0f}")
m2.metric("Pengeluaran", f"Rp {total_keluar:,.0f}")
m3.metric("Saldo Bersih", f"Rp {saldo_bersih:,.0f}")

# --- RIWAYAT SEDERHANA ---
st.subheader("📜 Riwayat Transaksi")
if not df_hari_ini.empty:
    # Formatting untuk tampilan tabel
    display_df = df_hari_ini.copy()
    display_df['nominal'] = display_df.apply(
        lambda x: f"+ Rp {x['nominal']:,.0f}" if x['tipe'] == 'Masuk' else f"- Rp {x['nominal']:,.0f}", axis=1
    )
    st.table(display_df[['tanggal', 'catatan', 'nominal']])
    
    # Fitur Ekspor (CSV sebagai pengganti PDF yang ringan)
    csv = df_hari_ini.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download Laporan Hari Ini (CSV)",
        data=csv,
        file_name=f'Laporan_Kas_{datetime.now().strftime("%d%m%Y")}.csv',
        mime='text/csv',
    )
else:
    st.info("Belum ada transaksi hari ini.")

# --- FOOTER ---
st.sidebar.title("Tentang KasCepat")
st.sidebar.info(
    "Dirancang khusus untuk pedagang di Ketapang. "
    "Data tersimpan di perangkat ini (Offline)."
)