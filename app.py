import streamlit as st
import pandas as pd
from datetime import datetime

# --- CONFIGURATION & SESSION STATE ---
st.set_page_config(page_title="SembakoPintar POS", layout="wide")

if 'inventory' not in st.session_state:
    # Dummy Data Inventory dengan Konversi Satuan
    st.session_state.inventory = pd.DataFrame([
        {"id": 1, "nama": "Beras Premium", "stok_pcs": 100, "min_stok": 20, "harga_modal": 10000, "harga_jual": 12000, "dus_ke_pcs": 10},
        {"id": 2, "nama": "Minyak Goreng 1L", "stok_pcs": 15, "min_stok": 20, "harga_modal": 14000, "harga_jual": 16000, "dus_ke_pcs": 12}
    ])

if 'cart' not in st.session_state:
    st.session_state.cart = []

# --- FUNCTIONS ---
def update_stok(idx, jumlah, mode="tambah"):
    if mode == "tambah":
        st.session_state.inventory.at[idx, 'stok_pcs'] += jumlah
    else:
        st.session_state.inventory.at[idx, 'stok_pcs'] -= jumlah

# --- SIDEBAR NAVIGATION ---
menu = st.sidebar.selectbox("Navigasi", ["Dashboard", "Manajemen Stok", "Kasir (Transaksi)", "Laporan Laba Rugi"])

# --- 1. DASHBOARD & ALERTS ---
if menu == "Dashboard":
    st.header("🚀 Dashboard Ringkasan")
    
    # Stock Alert Logic
    low_stock = st.session_state.inventory[st.session_state.inventory['stok_pcs'] <= st.session_state.inventory['min_stok']]
    if not low_stock.empty:
        st.error(f"⚠️ **Alert Stok Menipis!** {len(low_stock)} barang butuh restock.")
        st.dataframe(low_stock[['nama', 'stok_pcs', 'min_stok']])

    col1, col2 = st.columns(2)
    col1.metric("Total Produk", len(st.session_state.inventory))
    col2.metric("Produk Kritis", len(low_stock))

# --- 2. MANAJEMEN STOK (CRUD + UoM) ---
elif menu == "Manajemen Stok":
    st.header("📦 Manajemen Stok & Konversi Satuan")
    
    tab1, tab2 = st.tabs(["Daftar Barang", "Tambah/Edit Barang"])
    
    with tab1:
        st.subheader("Data Inventori")
        edited_df = st.data_editor(st.session_state.inventory, num_rows="dynamic", key="inv_editor")
        if st.button("Simpan Perubahan"):
            st.session_state.inventory = edited_df
            st.success("Data diperbarui!")

    with tab2:
        with st.form("form_barang"):
            nama = st.text_input("Nama Barang")
            col_a, col_b = st.columns(2)
            dus_ke_pcs = col_a.number_input("Konversi (1 Dus isi berapa Pcs?)", min_value=1, value=1)
            stok_dus = col_b.number_input("Input Stok (Dalam Dus)", min_value=0)
            
            h_modal = st.number_input("Harga Modal per Pcs")
            h_jual = st.number_input("Harga Jual per Pcs")
            min_s = st.number_input("Batas Stok Minimum", value=10)
            
            if st.form_submit_button("Tambah Barang"):
                new_id = st.session_state.inventory['id'].max() + 1
                new_data = {
                    "id": new_id, "nama": nama, "stok_pcs": stok_dus * dus_ke_pcs, 
                    "min_stok": min_s, "harga_modal": h_modal, "harga_jual": h_jual, 
                    "dus_ke_pcs": dus_ke_pcs
                }
                st.session_state.inventory = pd.concat([st.session_state.inventory, pd.DataFrame([new_data])], ignore_index=True)
                st.success(f"Berhasil input {stok_dus} Dus ({stok_dus * dus_ke_pcs} Pcs)")

# --- 3. KASIR (TRANSAKSI) ---
elif menu == "Kasir (Transaksi)":
    st.header("🛒 Kasir Sembako")
    
    col_kiri, col_kanan = st.columns([2, 1])
    
    with col_kiri:
        search = st.text_input("🔍 Scan Barcode atau Cari Nama Barang")
        items = st.session_state.inventory[st.session_state.inventory['nama'].str.contains(search, case=False)]
        
        st.dataframe(items[['id', 'nama', 'stok_pcs', 'harga_jual']], use_container_width=True)
        
        selected_id = st.number_input("Masukkan ID Barang", step=1, min_value=0)
        qty = st.number_input("Jumlah Beli", min_value=1, value=1)
        
        if st.button("Tambah ke Keranjang"):
            item_data = st.session_state.inventory[st.session_state.inventory['id'] == selected_id].iloc[0]
            # Logika Harga Bertingkat (Grosir)
            harga_final = item_data['harga_jual']
            if qty >= 12: # Misal beli 1 lusin
                harga_final -= 500
                st.info("Harga Grosir Diaktifkan!")
                
            st.session_state.cart.append({
                "id": selected_id, "nama": item_data['nama'], 
                "qty": qty, "harga": harga_final, "subtotal": qty * harga_final
            })

    with col_kanan:
        st.subheader("Struk Belanja")
        if st.session_state.cart:
            cart_df = pd.DataFrame(st.session_state.cart)
            st.table(cart_df[['nama', 'qty', 'subtotal']])
            total = cart_df['subtotal'].sum()
            st.markdown(f"### Total: Rp {total:,}")
            
            metode = st.selectbox("Metode Bayar", ["Tunai", "QRIS", "Kasbon/Utang"])
            
            if st.button("Selesaikan Transaksi"):
                # Potong Stok Otomatis
                for _, row in cart_df.iterrows():
                    idx = st.session_state.inventory.index[st.session_state.inventory['id'] == row['id']][0]
                    update_stok(idx, row['qty'], mode="kurang")
                
                st.session_state.cart = []
                st.success("Transaksi Berhasil & Stok Terupdate!")
                st.balloons()
        else:
            st.write("Keranjang kosong")

# --- 4. LABA RUGI REAL-TIME ---
elif menu == "Laporan Laba Rugi":
    st.header("📈 Laporan Keuangan")
    # Logika sederhana: Nilai Aset vs Potensi Margin
    inv = st.session_state.inventory
    total_modal = (inv['stok_pcs'] * inv['harga_modal']).sum()
    total_potensi_jual = (inv['stok_pcs'] * inv['harga_jual']).sum()
    margin = total_potensi_jual - total_modal
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Modal Aset", f"Rp {total_modal:,}")
    c2.metric("Potensi Omzet", f"Rp {total_potensi_jual:,}")
    c3.metric("Estimasi Laba", f"Rp {margin:,}", delta=f"{(margin/total_modal)*100:.1f}%")