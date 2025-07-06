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
pemilik_list = ["Saya", "Ayah", "Ibu", "Keluarga", "Lainnya"]
kategori_list = ["Gaji", "Makanan & Minuman", "Transportasi", "Tagihan", "Hiburan", "Belanja", "Lainnya"]

@app.before_first_request
def create_tables():
    db.create_all()

# --- Route Utama dan Transaksi ---
@app.route('/', methods=['GET', 'POST'])
def index():
    bulan = datetime.now().month
    tahun = datetime.now().year

    if request.method == 'POST':
        bulan = int(request.form.get('bulan'))
        tahun = int(request.form.get('tahun'))
    
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
    except Exception as e:
        flash(f'Terjadi error saat menambah data: {e}', 'danger')
        db.session.rollback()
    return redirect(url_for('index'))

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_transaksi(id):
    trx_untuk_diedit = Transaksi.query.get_or_404(id)

    if request.method == 'POST':
        try:
            trx_untuk_diedit.tanggal = datetime.strptime(request.form.get('tanggal'), '%Y-%m-%d').date()
            trx_untuk_diedit.tipe = request.form.get('tipe')
            trx_untuk_diedit.jumlah = int(request.form.get('jumlah'))
            trx_untuk_diedit.kategori = request.form.get('kategori')
            trx_untuk_diedit.keterangan = request.form.get('keterangan')
            trx_untuk_diedit.pemilik = request.form.get('pemilik')
            db.session.commit()
            flash('Transaksi berhasil diperbarui!', 'success')
        except Exception as e:
            flash(f'Terjadi error saat memperbarui data: {e}', 'danger')
            db.session.rollback()
        return redirect(url_for('index'))

    return render_template('edit_transaksi.html', trx=trx_untuk_diedit, kategori_list=kategori_list, pemilik_list=pemilik_list)

@app.route('/hapus/<int:id>')
def hapus_transaksi(id):
    transaksi_untuk_dihapus = Transaksi.query.get_or_404(id)
    try:
        db.session.delete(transaksi_untuk_dihapus)
        db.session.commit()
        flash('Transaksi berhasil dihapus!', 'success')
    except Exception as e:
        flash(f'Terjadi kesalahan saat menghapus transaksi: {e}', 'danger')
        db.session.rollback()
    return redirect(url_for('index'))

# --- Route Laporan & Ekspor ---
@app.route('/laporan', methods=['GET', 'POST'])
def laporan():
    current_year = datetime.now().year
    bulan = datetime.now().month
    tahun = current_year
    pemilik_terpilih = 'Semua'

    if request.method == 'POST':
        bulan = int(request.form.get('bulan'))
        tahun = int(request.form.get('tahun'))
        pemilik_terpilih = request.form.get('pemilik')

    base_query = Transaksi.query.filter(
        extract('year', Transaksi.tanggal) == tahun,
        extract('month', Transaksi.tanggal) == bulan
    )
    if pemilik_terpilih != 'Semua':
        base_query = base_query.filter(Transaksi.pemilik == pemilik_terpilih)

    transaksi_periode_ini = base_query.order_by(Transaksi.tanggal.asc()).all()
    
    total_pemasukan = sum(t.jumlah for t in transaksi_periode_ini if t.tipe == 'Pemasukan')
    total_pengeluaran = sum(t.jumlah for t in transaksi_periode_ini if t.tipe == 'Pengeluaran')
    sisa_uang = total_pemasukan - total_pengeluaran
    hasil = {'pemasukan': total_pemasukan, 'pengeluaran': total_pengeluaran, 'laba_rugi': sisa_uang}
    
    data_pie_chart = db.session.query(
        Transaksi.kategori, func.sum(Transaksi.jumlah)
    ).filter(
        extract('year', Transaksi.tanggal) == tahun,
        extract('month', Transaksi.tanggal) == bulan,
        Transaksi.tipe == 'Pengeluaran'
    )
    if pemilik_terpilih != 'Semua':
        data_pie_chart = data_pie_chart.filter(Transaksi.pemilik == pemilik_terpilih)
    
    data_pie_chart_result = data_pie_chart.group_by(Transaksi.kategori).all()

    labels_pie = [item[0] for item in data_pie_chart_result]
    data_pie = [item[1] for item in data_pie_chart_result]
    
    return render_template(
        'laporan.html', 
        hasil=hasil, bulan=bulan, tahun=tahun, current_year=current_year,
        transaksi_list=transaksi_periode_ini,
        pemilik_list=pemilik_list,
        pemilik_terpilih=pemilik_terpilih,
        labels_pie=labels_pie,
        data_pie=data_pie
    )

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
    pdf.set_font('Helvetica', 'B', 16)
    pdf.cell(0, 10, f'Laporan Keuangan - Bulan {bulan}/{tahun}', 0, 1, 'C')
    pdf.ln(10)
    pdf.set_font('Helvetica', '', 12)
    pdf.cell(0, 10, f'Total Pemasukan: Rp {total_pemasukan:,.0f}', 0, 1)
    pdf.cell(0, 10, f'Total Pengeluaran: Rp {total_pengeluaran:,.0f}', 0, 1)
    pdf.set_font('Helvetica', 'B', 12)
    pdf.cell(0, 10, f'Sisa Uang: Rp {laba_rugi:,.0f}', 0, 1)
    pdf.ln(10)
    pdf.set_font('Helvetica', 'B', 10)
    pdf.cell(25, 10, 'Tanggal', 1)
    pdf.cell(35, 10, 'Kategori', 1)
    pdf.cell(60, 10, 'Keterangan', 1)
    pdf.cell(35, 10, 'Pemasukan', 1)
    pdf.cell(35, 10, 'Pengeluaran', 1)
    pdf.ln()
    pdf.set_font('Helvetica', '', 10)
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

# Menjalankan aplikasi
if __name__ == '__main__':
    app.run(debug=True)