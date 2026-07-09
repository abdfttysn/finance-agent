# ElingCash Multi-Agent Worker

Worker ini adalah layanan Python berbasis **FastAPI** dan **LangGraph** yang berfungsi sebagai orchestrator multi-agent. Worker menerima trigger event dari client WhatsApp, merutekan pesan ke agent spesialis yang tepat, memanggil API ElingCash, dan mengembalikan jawaban akhir terformat dalam Bahasa Indonesia.

## Prasyarat

- Python 3.11+
- Pip (Python Package Installer)
- Virtual Environment (venv)
- Aplikasi **ElingCash** berjalan di local (misalnya http://localhost dengan Laragon)
- Google Gemini API Key

## Langkah Instalasi & Memulai

Ikuti langkah-langkah di bawah ini untuk menginstal dan menjalankan worker:

### 1. Buat Virtual Environment
Buka terminal/powershell di folder `worker`, lalu buat virtual environment baru:
```bash
python -m venv venv
```

### 2. Aktifkan Virtual Environment
- **Di Windows (PowerShell):**
  ```powershell
  .\venv\Scripts\Activate.ps1
  ```
- **Di Windows (CMD):**
  ```cmd
  .\venv\Scripts\activate.bat
  ```
- **Di macOS/Linux:**
  ```bash
  source venv/bin/activate
  ```

### 3. Install Dependensi
Setelah venv aktif, install pustaka yang dibutuhkan dari `requirements.txt`:
```bash
pip install -r requirements.txt
```

### 4. Konfigurasi Environment Variables (`.env`)
Salin file `.env.example` menjadi `.env`:
```bash
cp .env.example .env
```
Buka file `.env` dan isi variabel berikut:
- **`GOOGLE_API_KEY`**: API Key dari Google AI Studio (Gemini).
- **`ELINGCASH_BASE_URL`**: URL aplikasi ElingCash Anda (default: `http://localhost`).
- **`ELINGCASH_TOKEN`**: Personal Access Token (Sanctum) dari ElingCash.

> **Cara mendapatkan ELINGCASH_TOKEN:**
> Jalankan perintah berikut di folder project ElingCash Anda:
> ```bash
> php artisan tinker
> ```
> Lalu ketik:
> ```php
> $user = App\Models\User::first();
> echo $user->createToken('worker-agent')->plainTextToken;
> ```
> Salin token yang tercetak ke `.env` Anda.

### 5. Jalankan Worker
Jalankan server FastAPI menggunakan uvicorn:
```bash
uvicorn main:app --reload --port 8000
```
Server akan berjalan di `http://localhost:8000`.

---

## Menguji Integrasi End-to-End

Setelah Worker berjalan, pastikan:
1. ElingCash (API) aktif di `http://localhost` (Laragon / `php artisan serve`).
2. WhatsApp Client di folder `../client` sudah terinstall (`npm install`) dan terhubung ke WhatsApp (`npm start`).
3. Kirim pesan ke grup WhatsApp yang berisi salah satu keyword trigger (misalnya: `"bayar"`, `"tagihan"`, `"invoice"`).
4. Contoh pertanyaan:
   - *"Berapa net worth saya hari ini?"*
   - *"Berapa sisa budget uang makan bulan ini?"*
   - *"Tampilkan pengeluaran saya minggu ini"*
   - *"Berapa saldo di rekening BCA?"*
   - *"Catat pengeluaran makan siang 50000 dari rekening Dompet Tunai"* (Agent akan otomatis mencocokkan nama rekening & kategori, lalu menyimpannya).
