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
app.config['SECRET_KEY'] = 'kunci_rahasia_super_aman_untuk_flash'
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
    pemilik = db.Column(db.String(50), nullable=True)

# Daftar master untuk dropdown
pemilik_list = ["Abi", "Umi", "Anas", "Nida", "Lainnya"]
kategori_list = ["Gaji", "Makanan & Minuman", "Transportasi", "Tagihan", "Hiburan", "Belanja", "Lainnya"]

# --- Route Utama dan Transaksi ---
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Jika ada filter dari form, gunakan itu
        bulan = int(request.form.get('bulan'))
        tahun = int(request.form.get('tahun'))
    else:
        # Jika tidak, coba ambil dari URL (untuk redirect). Jika tidak ada juga, baru pakai bulan sekarang.
        bulan = request.args.get('bulan', default=datetime.now().month, type=int)
        tahun = request.args.get('tahun', default=datetime.now().year, type=int)
    
    query = Transaksi.query.filter(
        extract('year', Transaksi.tanggal) == tahun,
        extract('month', Transaksi.tanggal) == bulan
    )
    
    transaksi_terfilter = query.order_by(Transaksi.tanggal.desc()).all()

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
        pemilik_list=pemilik_list
    )

@app.route('/tambah', methods=['POST'])
def tambah_transaksi():
    try:
        tanggal_str = request.form.get('tanggal')
        tanggal = datetime.strptime(tanggal_str, '%Y-%m-%d').date()
        tipe = request.form.get('tipe')
        jumlah = int(request.form.get('jumlah'))
        kategori = request.form.get('kategori')
        keterangan = request.form.get('keterangan')
        pemilik = request.form.get('pemilik')
        
        transaksi_baru = Transaksi(tanggal=tanggal, tipe=tipe, jumlah=jumlah, kategori=kategori, keterangan=keterangan, pemilik=pemilik)
        db.session.add(transaksi_baru)
        db.session.commit()
        flash('Transaksi baru berhasil ditambahkan!', 'success')
        # Setelah menambah, kembali ke bulan di mana transaksi ditambahkan
        return redirect(url_for('index', bulan=tanggal.month, tahun=tanggal.year))
    except Exception as e:
        flash(f'Terjadi error saat menambah data: {e}', 'danger')
        db.session.rollback()
        return redirect(url_for('index'))

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_transaksi(id):
    trx_untuk_diedit = Transaksi.query.get_or_404(id)

    if request.method == 'POST':
        try:
            tanggal_str = request.form.get('tanggal')
            tanggal_baru = datetime.strptime(tanggal_str, '%Y-%m-%d').date()
            trx_untuk_diedit.tanggal = tanggal_baru
            trx_untuk_diedit.tipe = request.form.get('tipe')
            trx_untuk_diedit.jumlah = int(request.form.get('jumlah'))
            trx_untuk_diedit.kategori = request.form.get('kategori')
            trx_untuk_diedit.keterangan = request.form.get('keterangan')
            trx_untuk_diedit.pemilik = request.form.get('pemilik')
            db.session.commit()
            flash('Transaksi berhasil diperbarui!', 'success')
            # Kembali ke bulan di mana transaksi diedit
            return redirect(url_for('index', bulan=tanggal_baru.month, tahun=tanggal_baru.year))
        except Exception as e:
            flash(f'Error saat memperbarui data: {e}', 'danger')
            db.session.rollback()
            return redirect(url_for('index'))

    return render_template('edit_transaksi.html', trx=trx_untuk_diedit, kategori_list=kategori_list, pemilik_list=pemilik_list)


@app.route('/hapus/<int:id>')
def hapus_transaksi(id):
    # Ambil bulan dan tahun dari URL sebelum menghapus
    bulan = request.args.get('bulan', type=int)
    tahun = request.args.get('tahun', type=int)
    
    transaksi_untuk_dihapus = Transaksi.query.get_or_404(id)
    try:
        db.session.delete(transaksi_untuk_dihapus)
        db.session.commit()
        flash('Transaksi berhasil dihapus!', 'success')
    except Exception as e:
        flash(f'Error saat menghapus: {e}', 'danger')
        db.session.rollback()
    
    # Redirect kembali ke bulan dan tahun yang sama
    return redirect(url_for('index', bulan=bulan, tahun=tahun))


# (Fungsi laporan dan ekspor_pdf tidak berubah dari versi final sebelumnya)
# ...

if __name__ == '__main__':
    app.run(debug=True)