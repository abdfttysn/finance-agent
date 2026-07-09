"""
tools/elingcash_tools.py

Semua 7 API tools untuk ElingCash menggunakan @tool decorator LangChain.
Setiap tool melakukan HTTP request ke API menggunakan httpx.

Tools yang tersedia:
    - get_financial_profile()
    - get_transactions(...)
    - record_transaction(...)
    - get_categories(...)
    - get_dashboard_summary()
    - get_analytics()
    - get_assets(...)
"""

import os
import httpx
from typing import Optional
from langchain_core.tools import tool


# -------------------------------------------------------
# Helper: Build authenticated headers & base URL
# -------------------------------------------------------
def _get_headers() -> dict:
    token = os.environ.get("ELINGCASH_TOKEN", "")
    return {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }


def _get_base_url() -> str:
    return os.environ.get("ELINGCASH_BASE_URL", "http://localhost")


def _build_url(path: str) -> str:
    base = _get_base_url().rstrip("/")
    return f"{base}{path}"


# -------------------------------------------------------
# Tool 1: GET /api/ai/financial-profile
# -------------------------------------------------------
@tool
def get_financial_profile() -> dict:
    """
    Mengambil profil keuangan lengkap dan terkonsolidasi dari ElingCash.

    Gunakan tool ini untuk menjawab pertanyaan umum tentang kondisi keuangan
    pengguna, seperti: net worth, savings rate, financial runway, daftar aset,
    peringatan anggaran aktif, dan tagihan yang belum dibayar.

    Returns:
        dict berisi: user, kpi (net_worth, monthly_income, monthly_expense,
        savings_rate), runway, assets, budget_503020, active_warnings, unpaid_bills.
    """
    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.get(
                _build_url("/api/ai/financial-profile"),
                headers=_get_headers()
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        return {"error": f"HTTP {e.response.status_code}: {e.response.text}"}
    except Exception as e:
        return {"error": str(e)}


# -------------------------------------------------------
# Tool 2: GET /api/transactions
# -------------------------------------------------------
@tool
def get_transactions(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    type: Optional[str] = None,
    category_id: Optional[int] = None,
    asset_id: Optional[int] = None,
    target_asset_id: Optional[int] = None,
    involved_asset_id: Optional[int] = None,
    min_amount: Optional[float] = None,
    max_amount: Optional[float] = None,
    search: Optional[str] = None,
) -> dict:
    """
    Mengambil riwayat transaksi pengguna dengan filter lengkap dari ElingCash.

    Gunakan tool ini untuk menjawab pertanyaan riwayat transaksi, seperti:
    "Pengeluaran bulan ini", "Transaksi makan minggu lalu", "Pemasukan hari ini", dll.

    Args:
        start_date: Tanggal mulai format YYYY-MM-DD. Default: 1 tahun lalu.
        end_date: Tanggal akhir format YYYY-MM-DD. Default: hari ini.
                  PENTING: Rentang start_date sampai end_date maksimal 1 tahun (366 hari).
        type: Filter tipe transaksi. Nilai: 'income' atau 'expense'.
        category_id: Filter berdasarkan ID kategori (integer).
        asset_id: Filter berdasarkan ID rekening aset sumber (integer).
        target_asset_id: Filter berdasarkan ID rekening aset/kewajiban target penerima dana (integer).
        involved_asset_id: Filter transaksi yang melibatkan rekening aset tertentu baik sebagai sumber maupun target (integer). Sangat berguna untuk histori cicilan lengkap.
        min_amount: Nominal minimum transaksi.
        max_amount: Nominal maksimum transaksi.
        search: Pencarian teks pada deskripsi transaksi (LIKE).

    Returns:
        dict berisi data transaksi (list) dan meta pagination.
    """
    params = {}
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date
    if type:
        params["type"] = type
    if category_id is not None:
        params["category_id"] = category_id
    if asset_id is not None:
        params["asset_id"] = asset_id
    if target_asset_id is not None:
        params["target_asset_id"] = target_asset_id
    if involved_asset_id is not None:
        params["involved_asset_id"] = involved_asset_id
    if min_amount is not None:
        params["min_amount"] = min_amount
    if max_amount is not None:
        params["max_amount"] = max_amount
    if search:
        params["search"] = search

    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.get(
                _build_url("/api/transactions"),
                headers=_get_headers(),
                params=params
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        return {"error": f"HTTP {e.response.status_code}: {e.response.text}"}
    except Exception as e:
        return {"error": str(e)}


# -------------------------------------------------------
# Tool 3: POST /api/transactions
# -------------------------------------------------------
@tool
def record_transaction(
    asset_id: int,
    category_id: int,
    amount: float,
    type: str,
    date: str,
    target_asset_id: Optional[int] = None,
    description: Optional[str] = None,
) -> dict:
    """
    Mencatat transaksi keuangan baru (pemasukan atau pengeluaran) ke ElingCash.

    Gunakan tool ini HANYA untuk mencatat transaksi baru yang diminta pengguna.
    PENTING: Anda HARUS mengetahui asset_id dan category_id yang valid sebelum
    memanggil tool ini. Gunakan get_assets() dan get_categories() terlebih dahulu
    jika ID belum diketahui.

    Args:
        asset_id: ID rekening aset sumber yang digunakan (integer). Harus valid milik user.
        category_id: ID kategori transaksi (integer). Harus valid milik user.
        amount: Nominal transaksi. Minimal 0.01.
        type: Tipe transaksi. Nilai: 'income' (pemasukan) atau 'expense' (pengeluaran).
        date: Tanggal transaksi format YYYY-MM-DD.
        target_asset_id: ID rekening aset/kewajiban target penerima dana (integer, opsional).
        description: Keterangan tambahan (opsional, max 1000 karakter).

    Returns:
        dict berisi message dan data transaksi yang berhasil dicatat.
    """
    payload = {
        "asset_id": asset_id,
        "category_id": category_id,
        "amount": amount,
        "type": type,
        "date": date,
    }
    if target_asset_id is not None:
        payload["target_asset_id"] = target_asset_id
    if description:
        payload["description"] = description

    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.post(
                _build_url("/api/transactions"),
                headers=_get_headers(),
                json=payload
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        return {"error": f"HTTP {e.response.status_code}: {e.response.text}"}
    except Exception as e:
        return {"error": str(e)}


# -------------------------------------------------------
# Tool 4: GET /api/ai/categories
# -------------------------------------------------------
@tool
def get_categories(
    name: Optional[str] = None,
    type: Optional[str] = None,
) -> list:
    """
    Mengambil daftar kategori transaksi beserta sisa alokasi budget bulan ini.

    Gunakan tool ini untuk menjawab pertanyaan sisa budget atau alokasi kategori,
    seperti: "Berapa sisa budget makan?", "Apakah budget hobi masih ada?",
    "Sudah berapa persen budget transportasi terpakai?"

    Args:
        name: Pencarian nama kategori (LIKE). Contoh: 'makan', 'transport', 'hiburan'.
        type: Filter tipe: 'income' (pemasukan) atau 'expense' (pengeluaran).

    Returns:
        list kategori, masing-masing berisi: id, name, type, budget_limit,
        budget_type, spent_this_month, remaining_budget, percentage_spent.
    """
    params = {}
    if name:
        params["name"] = name
    if type:
        params["type"] = type

    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.get(
                _build_url("/api/ai/categories"),
                headers=_get_headers(),
                params=params
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        return [{"error": f"HTTP {e.response.status_code}: {e.response.text}"}]
    except Exception as e:
        return [{"error": str(e)}]


# -------------------------------------------------------
# Tool 5: GET /api/ai/dashboard-summary
# -------------------------------------------------------
@tool
def get_dashboard_summary() -> dict:
    """
    Mengambil ringkasan dashboard operasional bulan berjalan dari ElingCash.

    Gunakan tool ini untuk menjawab pertanyaan seputar kondisi keuangan
    bulan ini, peringatan limit anggaran yang kritis, dan tagihan bulanan
    yang akan segera jatuh tempo (H-5 atau overdue).

    Returns:
        dict berisi: stats (net_worth, monthly_income, monthly_expense,
        remaining_budget), warnings (list peringatan aktif),
        upcoming_bills (list tagihan mendekat/overdue).
    """
    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.get(
                _build_url("/api/ai/dashboard-summary"),
                headers=_get_headers()
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        return {"error": f"HTTP {e.response.status_code}: {e.response.text}"}
    except Exception as e:
        return {"error": str(e)}


# -------------------------------------------------------
# Tool 6: GET /api/ai/analytics
# -------------------------------------------------------
@tool
def get_analytics() -> dict:
    """
    Mengambil laporan historis dan analisis finansial mendalam dari ElingCash.

    Gunakan tool ini untuk menjawab pertanyaan analisis jangka panjang:
    tren 6 bulan terakhir, perkembangan net worth, rasio 50/30/20 aktual,
    savings rate, financial runway, dan saran keuangan berdasarkan data ilmiah.

    Returns:
        dict berisi: overview (income, expense, net_savings), ratio_503020,
        savings_rate, financial_runway, monthly_trend (6 bulan), 
        net_worth_trend (6 bulan), advice (list saran keuangan).
    """
    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.get(
                _build_url("/api/ai/analytics"),
                headers=_get_headers()
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        return {"error": f"HTTP {e.response.status_code}: {e.response.text}"}
    except Exception as e:
        return {"error": str(e)}


# -------------------------------------------------------
# Tool 7: GET /api/ai/assets
# -------------------------------------------------------
@tool
def get_assets(keyword: Optional[str] = None) -> list:
    """
    Mengambil daftar semua rekening aset dan kewajiban pengguna dari ElingCash.

    Gunakan tool ini untuk menjawab pertanyaan tentang saldo rekening tertentu,
    daftar semua tabungan/investasi, atau total kewajiban/utang.
    Juga digunakan untuk mencari asset_id sebelum mencatat transaksi baru.

    Args:
        keyword: Pencarian berdasarkan nama atau catatan aset (LIKE).
                 Contoh: 'BCA', 'dompet', 'kartu kredit', 'emas'.

    Returns:
        list aset, masing-masing berisi: id, name, type (liquid/non_liquid/liability),
        balance, notes.
    """
    params = {}
    if keyword:
        params["keyword"] = keyword

    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.get(
                _build_url("/api/ai/assets"),
                headers=_get_headers(),
                params=params
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        return [{"error": f"HTTP {e.response.status_code}: {e.response.text}"}]
    except Exception as e:
        return [{"error": str(e)}]


# -------------------------------------------------------
# Kumpulan tools per sub-agent
# -------------------------------------------------------
FINANCIAL_PROFILE_TOOLS = [get_financial_profile]
TRANSACTION_TOOLS = [get_transactions, get_assets]
STORE_TRANSACTION_TOOLS = [get_assets, get_categories, record_transaction]
CATEGORY_BUDGET_TOOLS = [get_categories]
DASHBOARD_TOOLS = [get_dashboard_summary]
ANALYTICS_TOOLS = [get_analytics]
ASSETS_TOOLS = [get_assets]
