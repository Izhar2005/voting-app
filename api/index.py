from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import psycopg2
from typing import List
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles # TAMBAHKAN INI

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
# GANTI URL DI BAWAH INI dengan Connection String yang didapat dari Neon.tech
DATABASE_URL = "postgresql://neondb_owner:npg_GnmFrphlz8f4@ep-falling-sun-aobmq2l0-pooler.c-2.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

# Model data untuk menerima kiriman (Request) dari Frontend
class VoteRequest(BaseModel):
    token: str
    kandidat_id: str

# Fungsi untuk membuka koneksi ke database Neon.tech
def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

@app.get("/api/kandidat")
def get_kandidat():
    """Endpoint untuk mengambil daftar kandidat yang ada"""
    return [
        {"id": "1", "nama": "Kandidat Alpha"},
        {"id": "2", "nama": "Kandidat Beta"}
    ]

@app.post("/api/vote")
def submit_vote(request: VoteRequest):
    """Endpoint utama untuk memproses voting anonim"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # 1. Cek apakah token valid dan aktif di database
        cur.execute("SELECT status FROM tokens WHERE token_code = %s", (request.token,))
        result = cur.fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="Token tidak ditemukan/tidak valid!")
        
        if result[0] == 'USED':
            raise HTTPException(status_code=400, detail="Token ini sudah pernah digunakan!")
        
        # 2. Jika valid, ubah status token menjadi 'USED' agar tidak bisa dipakai lagi
        cur.execute("UPDATE tokens SET status = 'USED' WHERE token_code = %s", (request.token,))
        
        # 3. Tambahkan suara ke kandidat pilihan
        cur.execute("UPDATE kandidat SET suara = suara + 1 WHERE id = %s", (request.kandidat_id,))
        
        # Simpan perubahan secara permanen di database (Commit)
        conn.commit()
        return {"message": "Suara berhasil dikirim secara anonim!"}
    
    except Exception as e:
        # Jika ada error di tengah jalan, batalkan semua perubahan demi integritas data
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Pastikan koneksi ke database selalu ditutup setelah selesai
        cur.close()
        conn.close()
        # Endpoint untuk Quick Count
@app.get("/api/results")
def get_results():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT nama, suara FROM kandidat ORDER BY id ASC")
    results = cur.fetchall()
    cur.close()
    conn.close()
    return [{"nama": r[0], "suara": r[1]} for r in results]

# Endpoint untuk Admin Reset (Gunakan password sederhana untuk keamanan)
@app.post("/api/admin/reset")
def reset_system(password: str):
    if password != "admin123": # Ganti password ini sesuai keinginan
        raise HTTPException(status_code=401, detail="Password Admin Salah!")
    
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("UPDATE kandidat SET suara = 0")
        cur.execute("UPDATE tokens SET status = 'ACTIVE'")
        conn.commit()
        return {"message": "Sistem berhasil direset ke kondisi awal!"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()