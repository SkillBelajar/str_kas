# Gunakan image Python yang ringan
FROM python:3.11-slim

# Set folder kerja di dalam container
WORKDIR /app

# Install dependensi minimal
RUN pip install streamlit

# Salin file aplikasi ke container
COPY app.py .

# Buka port default Streamlit
EXPOSE 8501

# Jalankan aplikasi
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]