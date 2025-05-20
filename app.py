import os
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash, session
from werkzeug.utils import secure_filename
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from sqlalchemy import or_, and_, func

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY") or '43214321'

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///vesti.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_IMAGE_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}
app.config['ALLOWED_VIDEO_EXTENSIONS'] = {'mp4', 'mov', 'avi'}

class Vest(db.Model):
    __tablename__ = 'vest'
    id = db.Column(db.Integer, primary_key=True)
    naslov = db.Column(db.String(200), nullable=False)
    sadrzaj = db.Column(db.Text, nullable=False)
    datum_vreme = db.Column(db.String(100), nullable=False)
    slike = db.Column(db.PickleType)
    video = db.Column(db.PickleType)
    target_pages = db.Column(db.PickleType)

def allowed_file(filename, allowed_extensions):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

@app.route('/')
def home_redirect():
    vesti = Vest.query.order_by(Vest.datum_vreme.desc()).all()
    return render_template('sve_vesti.html', vesti=vesti)

USERNAME = 'borzani2000'
PASSWORD = 'bOrzani2000brezOvica'

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == USERNAME and password == PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('dashboard'))
        else:
            flash("Pogrešno korisničko ime ili šifra.", "danger")
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    search_query = request.args.get('search', '').lower()
    if search_query:
        vesti = Vest.query.filter(
            or_(
                func.lower(Vest.naslov).contains(search_query),
                func.lower(Vest.sadrzaj).contains(search_query)
            )
        ).order_by(Vest.datum_vreme.desc()).all()
    else:
        vesti = Vest.query.order_by(Vest.datum_vreme.desc()).all()
    return render_template('dashboard.html', vesti=vesti)

@app.route('/postavi_vest', methods=['GET', 'POST'])
def postavi_vest():
    if request.method == 'POST':
        naslov = request.form['naslov']
        sadrzaj = request.form['sadrzaj']
        target_pages = [tp.lower() for tp in request.form.getlist('target_pages')]  # mala slova
        datum_vreme = request.form['datum_vreme']

        slike_paths = []
        for slika in request.files.getlist('slike'):
            if slika and allowed_file(slika.filename, app.config['ALLOWED_IMAGE_EXTENSIONS']):
                filename = secure_filename(slika.filename)
                path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                slika.save(path)
                slike_paths.append(filename)

        video_paths = []
        for video in request.files.getlist('video'):
            if video and allowed_file(video.filename, app.config['ALLOWED_VIDEO_EXTENSIONS']):
                filename = secure_filename(video.filename)
                path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                video.save(path)
                video_paths.append(filename)

        nova_vest = Vest(
            naslov=naslov,
            sadrzaj=sadrzaj,
            datum_vreme=datum_vreme,
            slike=slike_paths,
            video=video_paths,
            target_pages=target_pages
        )
        db.session.add(nova_vest)
        db.session.commit()

        return redirect(url_for('postavi_vest'))

    return render_template('postavi_vest.html')

@app.route('/BorzaniOnline')
def sve_vesti():
    search_query = request.args.get('search', '').lower()
    vesti_sve = Vest.query.order_by(Vest.datum_vreme.desc()).all()

    # Filtriranje u Pythonu za ove target pages
    valid_pages = ['naslovna', 'vesti', 'najnovije', 'lokalne vesti', 'sport', 'vremenska prognoza']
    def filter_vest(vest):
        if not vest.target_pages:
            return False
        pages_lower = [tp.lower() for tp in vest.target_pages]
        if not any(p in pages_lower for p in valid_pages):
            return False
        if search_query:
            return search_query in vest.naslov.lower() or search_query in vest.sadrzaj.lower()
        return True

    vesti = [v for v in vesti_sve if filter_vest(v)]
    return render_template('sve_vesti.html', vesti=vesti)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/prikazi_vest/<int:id>')
def prikazi_vest(id):
    vest = Vest.query.get_or_404(id)
    return render_template('prikazi_vest.html', vest=vest)

@app.route('/delete_vest/<int:id>', methods=['POST'])
def delete_vest(id):
    vest = Vest.query.get_or_404(id)
    db.session.delete(vest)
    db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/edit_vest/<int:id>', methods=['GET', 'POST'])
def edit_vest(id):
    vest = Vest.query.get_or_404(id)
    if request.method == 'POST':
        vest.naslov = request.form['naslov']
        vest.sadrzaj = request.form['sadrzaj']
        vest.target_pages = [tp.lower() for tp in request.form.getlist('target_pages')]
        db.session.commit()
        return redirect(url_for('dashboard'))
    return render_template('edit_vest.html', vest=vest)

@app.route('/vesti')
def vesti():
    search_query = request.args.get('search', '').lower()
    sve_vesti = Vest.query.order_by(Vest.datum_vreme.desc()).all()

    def filter_vest(vest):
        if not vest.target_pages:
            return False
        pages_lower = [tp.lower() for tp in vest.target_pages]
        if 'vesti' not in pages_lower:
            return False
        if search_query:
            return search_query in vest.naslov.lower() or search_query in vest.sadrzaj.lower()
        return True

    vesti_filtered = [v for v in sve_vesti if filter_vest(v)]
    return render_template('vesti.html', vesti=vesti_filtered, search_query=search_query)

@app.route('/najnovije')
def najnovije():
    sve_vesti = Vest.query.order_by(Vest.datum_vreme.desc()).all()

    vesti_filtered = [v for v in sve_vesti if v.target_pages and 'najnovije' in [tp.lower() for tp in v.target_pages]]

    return render_template('najnovije.html', vesti=vesti_filtered)

@app.route('/lokalne_vesti')
def lokalne_vesti():
    sve_vesti = Vest.query.order_by(Vest.datum_vreme.desc()).all()

    vesti_filtered = [v for v in sve_vesti if v.target_pages and 'lokalne vesti' in [tp.lower() for tp in v.target_pages]]

    return render_template('lokalne_vesti.html', vesti=vesti_filtered)

@app.route('/sport')
def sport():
    search_query = request.args.get('search', '').lower()
    sve_vesti = Vest.query.order_by(Vest.datum_vreme.desc()).all()

    def filter_vest(vest):
        if not vest.target_pages:
            return False
        pages_lower = [tp.lower() for tp in vest.target_pages]
        if 'sport' not in pages_lower:
            return False
        if search_query:
            return search_query in vest.naslov.lower() or search_query in vest.sadrzaj.lower()
        return True

    vesti_filtered = [v for v in sve_vesti if filter_vest(v)]
    return render_template('sport.html', vesti=vesti_filtered, search_query=search_query)

@app.route('/vremenska')
def vremenska_prognoza():
    search_query = request.args.get('search', '').lower()
    sve_vesti = Vest.query.order_by(Vest.datum_vreme.desc()).all()

    def filter_vest(vest):
        if not vest.target_pages:
            return False
        pages_lower = [tp.lower() for tp in vest.target_pages]
        if 'vremenska_prognoza' not in pages_lower:
            return False
        if search_query:
            return search_query in vest.naslov.lower() or search_query in vest.sadrzaj.lower()
        return True

    vesti_filtered = [v for v in sve_vesti if filter_vest(v)]
    return render_template('vremenska_prognoza.html', vesti=vesti_filtered, search_query=search_query)

@app.route('/kontakt')
def kontakt():
    return render_template('kontakt.html')

@app.route('/ostavi_vest', methods=['GET', 'POST'])
def ostavi_vest():
    if request.method == 'POST':
        ime = request.form.get('ime')
        anonimno = request.form.get('anonimno')
        tekst = request.form.get('tekst')

        if anonimno or not ime:
            ime = "Anonimni korisnik"

        try:
            from_addr = "borzaniradio@gmail.com"
            to_addr = "radioborzanibrezovica@gmail.com"
            password = "umay uyft kcgg piqq"

            subject = "Nova vest od čitaoca"
            body = f"Ime: {ime}\n\nTekst vesti:\n{tekst}"

            msg = MIMEMultipart()
            msg['From'] = from_addr
            msg['To'] = to_addr
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))

            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(from_addr, password)
            server.send_message(msg)
            server.quit()

            flash("Vest je uspešno poslata!", "success")
        except Exception as e:
            flash(f"Došlo je do greške prilikom slanja vesti: {e}", "danger")

        return redirect(url_for('ostavi_vest'))

    return render_template('ostavi_vest.html')

if __name__ == '__main__':
    print("Pokrećem Flask server...")
    with app.app_context():
        db.create_all()
    app.run(debug=True)
