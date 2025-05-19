import os
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash
from werkzeug.utils import secure_filename
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders



load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY") or '43214321'

# Konfiguracija baze (promeni username/password/dbname po potrebi)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///vesti.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Upload folder i dozvoljeni formati
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_IMAGE_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}
app.config['ALLOWED_VIDEO_EXTENSIONS'] = {'mp4', 'mov', 'avi'}

# Model za vest
class Vest(db.Model):
    __tablename__ = 'vest'   # baš da tabela bude 'vest'
    id = db.Column(db.Integer, primary_key=True)
    naslov = db.Column(db.String(200), nullable=False)
    sadrzaj = db.Column(db.Text, nullable=False)
    datum_vreme = db.Column(db.String(100), nullable=False)
    slike = db.Column(db.PickleType)
    video = db.Column(db.PickleType)
    target_pages = db.Column(db.PickleType)

# Login kredencijali
USERNAME = "root"
PASSWORD = "root"

# Provera ekstenzije
def allowed_file(filename, allowed_extensions):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions



@app.route('/login', methods=['POST'])
def login_post():
    username = request.form['username']
    password = request.form['password']
    if username == USERNAME and password == PASSWORD:
        return redirect(url_for('dashboard'))
    return "Pogrešno korisničko ime ili šifra."

@app.route('/dashboard')

def dashboard():
    search_query = request.args.get('search', '').lower()
    if search_query:
        vesti = Vest.query.filter(
            db.or_(
                db.func.lower(Vest.naslov).contains(search_query),
                db.func.lower(Vest.sadrzaj).contains(search_query)
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
        target_pages = request.form.getlist('target_pages')
        datum_vreme = datetime.now().strftime('%Y-%m-%dT%H:%M')

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

        return redirect(url_for('dashboard'))

    return render_template('postavi_vest.html')

@app.route('/BorzaniOnline')
def sve_vesti():
    search_query = request.args.get('search', '').lower()
    if search_query:
        vesti = Vest.query.filter(
            db.and_(
                db.or_(
                    db.func.lower(Vest.naslov).contains(search_query),
                    db.func.lower(Vest.sadrzaj).contains(search_query)
                ),
                Vest.target_pages.contains(['Naslovna'])
            )
        ).order_by(Vest.datum_vreme.desc()).all()
    else:
        vesti = Vest.query.filter(Vest.target_pages.contains(['Naslovna'])).order_by(Vest.datum_vreme.desc()).all()
    return render_template('sve_vesti.html', vesti=vesti)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/prikazi_vest/<int:id>')
def prikazi_vest(id):
    vest = Vest.query.get_or_404(id)
    return render_template('prikazi_vest.html', vest=vest)

@app.route('/delete_vest/<int:id>')
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
        db.session.commit()
        return redirect(url_for('dashboard'))
    return render_template('edit_vest.html', vest=vest)


@app.route('/vesti')
def vesti():
    search_query = request.args.get('search', '').lower()
    if search_query:
        vesti = Vest.query.filter(
            db.or_(
                db.func.lower(Vest.naslov).contains(search_query),
                db.func.lower(Vest.sadrzaj).contains(search_query)
            )
        ).order_by(Vest.datum_vreme.desc()).all()
    else:
        vesti = Vest.query.filter(Vest.target_pages.contains(['vesti'])).order_by(Vest.datum_vreme.desc()).all()
    return render_template('vesti.html', vesti=vesti)



@app.route('/najnovije')
def najnovije():
    vesti = Vest.query.filter(Vest.target_pages.contains(['najnovije'])).order_by(Vest.datum_vreme.desc()).all()
    return render_template('najnovije.html', vesti=vesti)

@app.route('/lokalne_vesti')
def lokalne_vesti():
    vesti = Vest.query.filter(Vest.target_pages.contains(['lokalne_vesti'])).order_by(Vest.datum_vreme.desc()).all()
    return render_template('lokalne_vesti.html', vesti=vesti)

@app.route('/sport')
def sport():
    search_query = request.args.get('search', '').lower()
    if search_query:
        vesti = Vest.query.filter(
            db.and_(
                db.or_(
                    db.func.lower(Vest.naslov).contains(search_query),
                    db.func.lower(Vest.sadrzaj).contains(search_query)
                ),
                Vest.target_pages.contains(['sport'])
            )
        ).order_by(Vest.datum_vreme.desc()).all()
    else:
        vesti = Vest.query.filter(Vest.target_pages.contains(['sport'])).order_by(Vest.datum_vreme.desc()).all()
    return render_template('sport.html', vesti=vesti, search_query=search_query)

@app.route('/vremenska')
def vremenska_prognoza():
    search_query = request.args.get('search', '').lower()
    if search_query:
        vesti = Vest.query.filter(
            db.and_(
                db.or_(
                    db.func.lower(Vest.naslov).contains(search_query),
                    db.func.lower(Vest.sadrzaj).contains(search_query)
                ),
                Vest.target_pages.contains(['vremenska'])
            )
        ).order_by(Vest.datum_vreme.desc()).all()
    else:
        vesti = Vest.query.filter(Vest.target_pages.contains(['vremenska'])).order_by(Vest.datum_vreme.desc()).all()
    return render_template('vremenska_prognoza.html', vesti=vesti, search_query=search_query)

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
            # Direktno upiši svoje email adrese i lozinku ovde:
            from_addr = "dstanisavljevic579@gmail.com"            # odakle šalješ
            to_addr = "stanisavljevic30@icloud.com"            # kome šalješ
            password = "acmi ojiz pnxi dueu"   # lozinka ili app password

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

    # Ako je GET metoda, samo prikaži formu
    return render_template('ostavi_vest.html')
@app.route('/')
def home_redirect():
    return render_template('sve_vesti.html')

if __name__ == '__main__':
    print("Pokrećem Flask server...")
    with app.app_context():
        db.create_all()
    app.run(debug=True)  