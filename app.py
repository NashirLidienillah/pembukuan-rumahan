import os
from flask import Flask, render_template, request, redirect, url_for, make_response, flash
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
from sqlalchemy import extract, func
from datetime import datetime
from fpdf import FPDF # -> [BARU] Import library PDF

# Muat environment variables
load_dotenv()

# Inisialisasi Aplikasi Flask
app = Flask(__name__)
app.config['SECRET_KEY'] = 'sabar'

# Konfigurasi Database
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Model untuk tabel transaksi
class Transaksi(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tanggal = db.Column(db.Date, nullable=False)
    kategori = db.Column(db.String(50), nullable=False)
    jumlah = db.Column(db.Integer, nullable=False)
    tipe = db.Column(db.String(10), nullable=False)
    keterangan = db.Column(db.Text, nullable=True)

# [PERBAIKAN] Ganti seluruh fungsi index() dengan ini
@app.route('/', methods=['GET', 'POST'])
def index():
    # Tentukan periode default (bulan dan tahun saat ini)
    bulan = datetime.now().month
    tahun = datetime.now().year

    # Jika ada filter yang dikirim dari form, gunakan nilai dari form
    if request.method == 'POST':
        bulan = int(request.form.get('bulan'))
        tahun = int(request.form.get('tahun'))
    
    # Ambil data transaksi HANYA untuk periode yang dipilih
    transaksi_terfilter = Transaksi.query.filter(
        extract('year', Transaksi.tanggal) == tahun,
        extract('month', Transaksi.tanggal) == bulan
    ).order_by(Transaksi.tanggal.desc()).all()

    # Hitung total untuk kartu ringkasan berdasarkan periode yang dipilih
    pemasukan_periode = db.session.query(func.sum(Transaksi.jumlah)).filter(
        extract('year', Transaksi.tanggal) == tahun,
        extract('month', Transaksi.tanggal) == bulan,
        Transaksi.tipe == 'Pemasukan'
    ).scalar() or 0

    pengeluaran_periode = db.session.query(func.sum(Transaksi.jumlah)).filter(
        extract('year', Transaksi.tanggal) == tahun,
        extract('month', Transaksi.tanggal) == bulan,
        Transaksi.tipe == 'Pengeluaran'
    ).scalar() or 0
    
    saldo_periode = pemasukan_periode - pengeluaran_periode

    return render_template(
        'index.html',
        transaksi_list=transaksi_terfilter, # Kirim data yang sudah terfilter
        pemasukan=pemasukan_periode,
        pengeluaran=pengeluaran_periode,
        saldo=saldo_periode,
        bulan=bulan, # Kirim bulan & tahun terpilih kembali ke template
        tahun=tahun
    )

@app.route('/tambah', methods=['POST'])
def tambah_transaksi():
    tanggal_str = request.form.get('tanggal')
    tanggal = datetime.strptime(tanggal_str, '%Y-%m-%d').date()
    tipe = request.form.get('tipe')
    jumlah = request.form.get('jumlah')
    kategori = request.form.get('kategori')
    keterangan = request.form.get('keterangan')
    transaksi_baru = Transaksi(tanggal=tanggal, tipe=tipe, jumlah=int(jumlah), kategori=kategori, keterangan=keterangan)
    db.session.add(transaksi_baru)
    db.session.commit()
    flash('Transaksi baru berhasil ditambahkan!', 'success')
    return redirect(url_for('index'))

# --- Route Laporan ---
@app.route('/laporan', methods=['GET', 'POST'])
def laporan():
    current_year = datetime.now().year
    # Atur periode default ke bulan dan tahun saat ini
    bulan = datetime.now().month
    tahun = current_year

    # Jika ada filter yang dikirim dari form, gunakan nilai dari form
    if request.method == 'POST':
        bulan = int(request.form.get('bulan'))
        tahun = int(request.form.get('tahun'))
    
    # Ambil daftar transaksi HANYA untuk periode yang dipilih
    transaksi_periode_ini = Transaksi.query.filter(
        extract('year', Transaksi.tanggal) == tahun,
        extract('month', Transaksi.tanggal) == bulan
    ).order_by(Transaksi.tanggal.asc()).all()

    # Hitung total untuk kartu ringkasan
    total_pemasukan = sum(t.jumlah for t in transaksi_periode_ini if t.tipe == 'Pemasukan')
    total_pengeluaran = sum(t.jumlah for t in transaksi_periode_ini if t.tipe == 'Pengeluaran')
    
    laba_rugi = total_pemasukan - total_pengeluaran

    hasil = {
        'pemasukan': total_pemasukan,
        'pengeluaran': total_pengeluaran,
        'laba_rugi': laba_rugi
    }
    
    return render_template(
        'laporan.html', 
        hasil=hasil, 
        bulan=bulan, 
        tahun=tahun, 
        current_year=current_year,
        transaksi_list=transaksi_periode_ini # -> [BARU] Kirim daftar transaksi ke template
    )

# -> [FITUR BARU] Route untuk membuat dan mengirim file PDF
@app.route('/ekspor-pdf')
def ekspor_pdf():
    bulan_str = request.args.get('bulan')
    tahun_str = request.args.get('tahun')

    if not bulan_str or not tahun_str:
        return "Error: Parameter bulan dan tahun dibutuhkan.", 400

    try:
        bulan = int(bulan_str)
        tahun = int(tahun_str)
    except ValueError:
        return "Error: Parameter bulan dan tahun harus berupa angka.", 400

    transaksi_periode_ini = Transaksi.query.filter(
        extract('year', Transaksi.tanggal) == tahun,
        extract('month', Transaksi.tanggal) == bulan
    ).order_by(Transaksi.tanggal.asc()).all()

    total_pemasukan = sum(t.jumlah for t in transaksi_periode_ini if t.tipe == 'Pemasukan')
    total_pengeluaran = sum(t.jumlah for t in transaksi_periode_ini if t.tipe == 'Pengeluaran')
    laba_rugi = total_pemasukan - total_pengeluaran

    pdf = FPDF()
    pdf.add_page()

    # Header Laporan
    pdf.set_font('Helvetica', 'B', 16) # -> [PERBAIKAN] Menggunakan Helvetica
    pdf.cell(0, 10, f'Laporan Keuangan - Bulan {bulan}/{tahun}', 0, 1, 'C')
    pdf.ln(10)

    # Ringkasan Laporan
    pdf.set_font('Helvetica', '', 12) # -> [PERBAIKAN] Menggunakan Helvetica
    pdf.cell(0, 10, f'Total Pemasukan: Rp {total_pemasukan:,.0f}', 0, 1)
    pdf.cell(0, 10, f'Total Pengeluaran: Rp {total_pengeluaran:,.0f}', 0, 1)
    pdf.set_font('Helvetica', 'B', 12) # -> [PERBAIKAN] Menggunakan Helvetica
    pdf.cell(0, 10, f'Sisa Uang: Rp {laba_rugi:,.0f}', 0, 1) # Mengganti Laba/Rugi menjadi Sisa Uang
    pdf.ln(10)

    # Tabel Detail Transaksi
    pdf.set_font('Helvetica', 'B', 10) # -> [PERBAIKAN] Menggunakan Helvetica
    pdf.cell(25, 10, 'Tanggal', 1)
    pdf.cell(35, 10, 'Kategori', 1)
    pdf.cell(60, 10, 'Keterangan', 1)
    pdf.cell(35, 10, 'Pemasukan', 1)
    pdf.cell(35, 10, 'Pengeluaran', 1)
    pdf.ln()

    pdf.set_font('Helvetica', '', 10) # -> [PERBAIKAN] Menggunakan Helvetica
    for trx in transaksi_periode_ini:
        pdf.cell(25, 10, trx.tanggal.strftime('%d-%m-%Y'), 1)
        pdf.cell(35, 10, trx.kategori, 1)
        pdf.cell(60, 10, trx.keterangan or '', 1)
        if trx.tipe == 'Pemasukan':
            pdf.cell(35, 10, f'Rp {trx.jumlah:,.0f}', 1, 0, 'R')
            pdf.cell(35, 10, '', 1)
        else:
            pdf.cell(35, 10, '', 1)
            pdf.cell(35, 10, f'Rp {trx.jumlah:,.0f}', 1, 0, 'R')
        pdf.ln()

    response = make_response(bytes(pdf.output()))
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=laporan_{bulan}_{tahun}.pdf'
    
    return response

# -> [TAMBAHKAN FUNGSI INI] Route untuk mengedit transaksi
@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_transaksi(id):
    trx_untuk_diedit = Transaksi.query.get_or_404(id)

    if request.method == 'POST':
        trx_untuk_diedit.tanggal = datetime.strptime(request.form.get('tanggal'), '%Y-%m-%d').date()
        trx_untuk_diedit.tipe = request.form.get('tipe')
        trx_untuk_diedit.jumlah = int(request.form.get('jumlah'))
        trx_untuk_diedit.kategori = request.form.get('kategori')
        trx_untuk_diedit.keterangan = request.form.get('keterangan')

        db.session.commit()
        flash('Transaksi berhasil diperbarui!', 'success')
        return redirect(url_for('index'))

    return render_template('edit_transaksi.html', trx=trx_untuk_diedit)


# -> [TAMBAHKAN FUNGSI INI] Route untuk menghapus transaksi
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

# Menjalankan aplikasi
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)