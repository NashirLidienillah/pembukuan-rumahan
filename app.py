import os
from flask import Flask, render_template, request, redirect, url_for, make_response, flash
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
from sqlalchemy import extract, func
from datetime import datetime
from fpdf import FPDF

# Muat environment variables
load_dotenv()

# Inisialisasi Aplikasi Flask
app = Flask(__name__)

# Konfigurasi
app.config['SECRET_KEY'] = 'kunci_rahasia_super_aman'
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {'pool_pre_ping': True}
db = SQLAlchemy(app)

# Model untuk tabel transaksi
class Transaksi(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tanggal = db.Column(db.Date, nullable=False)
    kategori = db.Column(db.String(50), nullable=False)
    jumlah = db.Column(db.Integer, nullable=False)
    tipe = db.Column(db.String(20), nullable=False)
    keterangan = db.Column(db.Text, nullable=True)
    pemilik = db.Column(db.String(50), nullable=True) # -> [BARU] Kolom pemilik

# Daftar master untuk dropdown
pemilik_list = ["Saya", "Ayah", "Ibu", "Keluarga", "Lainnya"]
kategori_list = ["Gaji", "Makanan & Minuman", "Transportasi", "Tagihan", "Hiburan", "Belanja", "Lainnya"]

# --- Route Utama dan Transaksi ---
@app.route('/', methods=['GET', 'POST'])
def index():
    bulan = datetime.now().month
    tahun = datetime.now().year

    if request.method == 'POST':
        bulan = int(request.form.get('bulan'))
        tahun = int(request.form.get('tahun'))
    
    transaksi_terfilter = Transaksi.query.filter(
        extract('year', Transaksi.tanggal) == tahun,
        extract('month', Transaksi.tanggal) == bulan
    ).order_by(Transaksi.tanggal.desc()).all()

    pemasukan_periode = sum(t.jumlah for t in transaksi_terfilter if t.tipe == 'Pemasukan')
    pengeluaran_periode = sum(t.jumlah for t in transaksi_terfilter if t.tipe == 'Pengeluaran')
    saldo_periode = pemasukan_periode - pengeluaran_periode

    return render_template(
        'index.html',
        transaksi_list=transaksi_terfilter,
        pemasukan=pemasukan_periode,
        pengeluaran=pengeluaran_periode,
        saldo=saldo_periode,
        bulan=bulan,
        tahun=tahun,
        kategori_list=kategori_list,
        pemilik_list=pemilik_list # -> [BARU] Kirim daftar pemilik
    )

@app.route('/tambah', methods=['POST'])
def tambah_transaksi():
    tanggal_str = request.form.get('tanggal')
    tanggal = datetime.strptime(tanggal_str, '%Y-%m-%d').date()
    tipe = request.form.get('tipe')
    jumlah = request.form.get('jumlah')
    kategori = request.form.get('kategori')
    keterangan = request.form.get('keterangan')
    pemilik = request.form.get('pemilik') # -> [BARU] Ambil data pemilik

    transaksi_baru = Transaksi(
        tanggal=tanggal, tipe=tipe, jumlah=int(jumlah), 
        kategori=kategori, keterangan=keterangan, 
        pemilik=pemilik # -> [BARU] Simpan data pemilik
    )
    db.session.add(transaksi_baru)
    db.session.commit()
    flash('Transaksi baru berhasil ditambahkan!', 'success')
    return redirect(url_for('index'))

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_transaksi(id):
    trx_untuk_diedit = Transaksi.query.get_or_404(id)

    if request.method == 'POST':
        trx_untuk_diedit.tanggal = datetime.strptime(request.form.get('tanggal'), '%Y-%m-%d').date()
        trx_untuk_diedit.tipe = request.form.get('tipe')
        trx_untuk_diedit.jumlah = int(request.form.get('jumlah'))
        trx_untuk_diedit.kategori = request.form.get('kategori')
        trx_untuk_diedit.keterangan = request.form.get('keterangan')
        trx_untuk_diedit.pemilik = request.form.get('pemilik') # -> [BARU] Update pemilik

        db.session.commit()
        flash('Transaksi berhasil diperbarui!', 'success')
        return redirect(url_for('index'))

    return render_template(
        'edit_transaksi.html', 
        trx=trx_untuk_diedit, 
        kategori_list=kategori_list, 
        pemilik_list=pemilik_list # -> [BARU] Kirim daftar pemilik
    )

@app.route('/hapus/<int:id>')
def hapus_transaksi(id):
    transaksi_untuk_dihapus = Transaksi.query.get_or_404(id)
    try:
        db.session.delete(transaksi_untuk_dihapus)
        db.session.commit()
        flash('Transaksi berhasil dihapus!', 'success')
    except:
        flash('Terjadi kesalahan saat menghapus transaksi.', 'danger')
    return redirect(url_for('index'))

# --- Route Laporan & Ekspor ---
@app.route('/laporan', methods=['GET', 'POST'])
def laporan():
    current_year = datetime.now().year
    bulan = datetime.now().month
    tahun = current_year
    pemilik_terpilih = 'Semua' # Default

    if request.method == 'POST':
        bulan = int(request.form.get('bulan'))
        tahun = int(request.form.get('tahun'))
        pemilik_terpilih = request.form.get('pemilik')

    query = Transaksi.query.filter(
        extract('year', Transaksi.tanggal) == tahun,
        extract('month', Transaksi.tanggal) == bulan
    )

    if pemilik_terpilih != 'Semua':
        query = query.filter(Transaksi.pemilik == pemilik_terpilih)

    transaksi_periode_ini = query.order_by(Transaksi.tanggal.asc()).all()
    
    total_pemasukan = sum(t.jumlah for t in transaksi_periode_ini if t.tipe == 'Pemasukan')
    total_pengeluaran = sum(t.jumlah for t in transaksi_periode_ini if t.tipe == 'Pengeluaran')
    sisa_uang = total_pemasukan - total_pengeluaran

    hasil = {'pemasukan': total_pemasukan, 'pengeluaran': total_pengeluaran, 'laba_rugi': sisa_uang}
    
    return render_template(
        'laporan.html', 
        hasil=hasil, 
        bulan=bulan, 
        tahun=tahun, 
        current_year=current_year,
        transaksi_list=transaksi_periode_ini,
        pemilik_list=pemilik_list,
        pemilik_terpilih=pemilik_terpilih
    )

# ... (kode ekspor_pdf tidak perlu diubah) ...

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)