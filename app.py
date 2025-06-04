from flask import Flask, render_template, request, redirect, url_for, send_file
import sqlite3
from datetime import datetime
from io import BytesIO
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from fpdf import FPDF

app = Flask(__name__)
DB_NAME = 'denda.db'
DENDA_PER_KESALAHAN = 5000
NAMA_TERDAFTAR = ['Tias', 'Bambang', 'Seto', 'Tiwi', 'Vini', 'Nina','Annisa','Saqya','Gusti', 'Sukma', 'Zainal', 'Adit', 'Otoy']

# Inisialisasi DB
def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS denda (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nama TEXT NOT NULL,
                kesalahan INTEGER DEFAULT 0,
                sudah_dibayar INTEGER DEFAULT 0,
                tanggal TEXT NOT NULL
            )
        ''')
        conn.commit()

@app.route('/')
def index():
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        # Ambil data semua transaksi
        c.execute('''
            SELECT id, nama, kesalahan, sudah_dibayar, tanggal,
            (kesalahan * ?) - sudah_dibayar AS sisa_denda
            FROM denda
            ORDER BY tanggal DESC
        ''', (DENDA_PER_KESALAHAN,))
        data = c.fetchall()

        # Ambil total denda per orang
        c.execute('''
            SELECT nama, SUM((kesalahan * ?) - sudah_dibayar) AS total_denda
            FROM denda
            GROUP BY nama
        ''', (DENDA_PER_KESALAHAN,))
        total_per_nama = c.fetchall()

    return render_template('index.html', data=data, nama_terdaftar=NAMA_TERDAFTAR, total_per_nama=total_per_nama)


@app.route('/tambah', methods=['POST'])
def tambah():
    nama = request.form['nama']
    kesalahan = int(request.form['kesalahan'])
    tanggal = datetime.now().strftime("%Y-%m-%d")

    if nama not in NAMA_TERDAFTAR:
        return "Nama tidak terdaftar.", 400

    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("INSERT INTO denda (nama, kesalahan, tanggal) VALUES (?, ?, ?)", (nama, kesalahan, tanggal))
        conn.commit()
    return redirect(url_for('index'))

@app.route('/bayar/<int:id>', methods=['GET', 'POST'])
def bayar(id):
    if request.method == 'POST':
        jumlah_bayar = int(request.form['jumlah'])
        with sqlite3.connect(DB_NAME) as conn:
            c = conn.cursor()
            c.execute("UPDATE denda SET sudah_dibayar = sudah_dibayar + ? WHERE id = ?", (jumlah_bayar, id))
            conn.commit()
        return redirect(url_for('index'))
    else:
        with sqlite3.connect(DB_NAME) as conn:
            c = conn.cursor()
            c.execute("SELECT id, nama FROM denda WHERE id = ?", (id,))
            data = c.fetchone()
        return render_template('bayar.html', data=data)

@app.route('/hapus/<int:id>', methods=['POST'])
def hapus(id):
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM denda WHERE id = ?", (id,))
        conn.commit()
    return redirect(url_for('index'))

@app.route('/export-pdf')
def export_pdf():
    nama = request.args.get('nama')
    bulan = request.args.get('bulan')
    tahun = request.args.get('tahun')

    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        query = '''SELECT nama, kesalahan, sudah_dibayar, tanggal, (kesalahan * ?) - sudah_dibayar AS sisa_denda
                   FROM denda WHERE nama = ? AND strftime('%m', tanggal) = ? AND strftime('%Y', tanggal) = ?'''
        c.execute(query, (DENDA_PER_KESALAHAN, nama, bulan.zfill(2), tahun))
        data = c.fetchall()

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"Laporan Denda Bulan {bulan}-{tahun} - {nama}", ln=True, align='C')

    for row in data:
        pdf.cell(200, 10, txt=f"{row[3]} - Kesalahan: {row[1]}, Bayar: {row[2]}, Sisa: {row[4]}", ln=True)

    output = BytesIO()
    pdf.output(output)
    output.seek(0)

    return send_file(output, as_attachment=True, download_name=f"laporan_denda_{nama}_{bulan}_{tahun}.pdf")

@app.route('/grafik')
def grafik():
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute('''SELECT nama, SUM((kesalahan * ?) - sudah_dibayar) as total_denda FROM denda GROUP BY nama''', (DENDA_PER_KESALAHAN,))
        result = c.fetchall()

    nama = [row[0] for row in result]
    denda = [row[1] for row in result]

    fig, ax = plt.subplots()
    ax.bar(nama, denda, color='skyblue')
    ax.set_ylabel('Total Denda (Rp)')
    ax.set_title('Statistik Denda per Orang')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()

    output = BytesIO()
    FigureCanvas(fig).print_png(output)
    output.seek(0)

    return send_file(output, mimetype='image/png')

if __name__ == '__main__':
    init_db()
    app.run(debug=True)