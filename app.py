from flask import Flask, request, render_template_string, redirect, url_for, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from datetime import datetime
import os
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER

app = Flask(__name__)
app.secret_key = 'votre_cle_secrete'  # À changer en production

# --- Configuration base de données (PostgreSQL) ---
# Pour Render, la variable d'environnement DATABASE_URL est fournie
database_url = os.environ.get('DATABASE_URL', 'postgresql://user:pass@localhost/school_db')
# Render utilise souvent 'postgres' au lieu de 'postgresql' dans l'URL
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- Modèles ---
class AnneeScolaire(db.Model):
    __tablename__ = 'annees'
    id = db.Column(db.Integer, primary_key=True)
    libelle = db.Column(db.String(20), unique=True, nullable=False)
    active = db.Column(db.Boolean, default=True)
    classes = db.relationship('Classe', backref='annee', lazy='dynamic', cascade='all, delete-orphan')
    trimestres = db.relationship('Trimestre', backref='annee', lazy='dynamic', cascade='all, delete-orphan')

class Classe(db.Model):
    __tablename__ = 'classes'
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(50), nullable=False)
    annee_id = db.Column(db.Integer, db.ForeignKey('annees.id'), nullable=False)
    eleves = db.relationship('Eleve', backref='classe', lazy='dynamic', cascade='all, delete-orphan')
    coeffs = db.relationship('Coefficient', backref='classe', lazy='dynamic', cascade='all, delete-orphan')
    devoirs = db.relationship('Devoir', backref='classe', lazy='dynamic', cascade='all, delete-orphan')
    examens = db.relationship('Examen', backref='classe', lazy='dynamic', cascade='all, delete-orphan')

class Discipline(db.Model):
    __tablename__ = 'disciplines'
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), unique=True, nullable=False)
    coeffs = db.relationship('Coefficient', backref='discipline', lazy='dynamic', cascade='all, delete-orphan')
    devoirs = db.relationship('Devoir', backref='discipline', lazy='dynamic', cascade='all, delete-orphan')
    examens = db.relationship('Examen', backref='discipline', lazy='dynamic', cascade='all, delete-orphan')

class Coefficient(db.Model):
    __tablename__ = 'coefficients'
    id = db.Column(db.Integer, primary_key=True)
    classe_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False)
    discipline_id = db.Column(db.Integer, db.ForeignKey('disciplines.id'), nullable=False)
    valeur = db.Column(db.Float, nullable=False)
    __table_args__ = (db.UniqueConstraint('classe_id', 'discipline_id', name='unique_coeff'),)

class Eleve(db.Model):
    __tablename__ = 'eleves'
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(50), nullable=False)
    prenom = db.Column(db.String(50), nullable=False)
    matricule = db.Column(db.String(20), unique=True, nullable=False)
    classe_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False)
    notes_devoir = db.relationship('NoteDevoir', backref='eleve', lazy='dynamic', cascade='all, delete-orphan')
    notes_examen = db.relationship('NoteExamen', backref='eleve', lazy='dynamic', cascade='all, delete-orphan')

class Trimestre(db.Model):
    __tablename__ = 'trimestres'
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(20), nullable=False)  # ex: "T1", "T2", "T3"
    ordre = db.Column(db.Integer, nullable=False)
    annee_id = db.Column(db.Integer, db.ForeignKey('annees.id'), nullable=False)
    devoirs = db.relationship('Devoir', backref='trimestre', lazy='dynamic', cascade='all, delete-orphan')
    examens = db.relationship('Examen', backref='trimestre', lazy='dynamic', cascade='all, delete-orphan')
    __table_args__ = (db.UniqueConstraint('annee_id', 'ordre', name='unique_ordre'),)

class Devoir(db.Model):
    __tablename__ = 'devoirs'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, default=datetime.utcnow)
    discipline_id = db.Column(db.Integer, db.ForeignKey('disciplines.id'), nullable=False)
    classe_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False)
    trimestre_id = db.Column(db.Integer, db.ForeignKey('trimestres.id'), nullable=False)
    notes = db.relationship('NoteDevoir', backref='devoir', lazy='dynamic', cascade='all, delete-orphan')

class Examen(db.Model):
    __tablename__ = 'examens'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, default=datetime.utcnow)
    discipline_id = db.Column(db.Integer, db.ForeignKey('disciplines.id'), nullable=False)
    classe_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False)
    trimestre_id = db.Column(db.Integer, db.ForeignKey('trimestres.id'), nullable=False)
    notes = db.relationship('NoteExamen', backref='examen', lazy='dynamic', cascade='all, delete-orphan')

class NoteDevoir(db.Model):
    __tablename__ = 'notes_devoir'
    id = db.Column(db.Integer, primary_key=True)
    valeur = db.Column(db.Float, nullable=False)
    eleve_id = db.Column(db.Integer, db.ForeignKey('eleves.id'), nullable=False)
    devoir_id = db.Column(db.Integer, db.ForeignKey('devoirs.id'), nullable=False)
    __table_args__ = (db.UniqueConstraint('eleve_id', 'devoir_id', name='unique_note_devoir'),)

class NoteExamen(db.Model):
    __tablename__ = 'notes_examen'
    id = db.Column(db.Integer, primary_key=True)
    valeur = db.Column(db.Float, nullable=False)
    eleve_id = db.Column(db.Integer, db.ForeignKey('eleves.id'), nullable=False)
    examen_id = db.Column(db.Integer, db.ForeignKey('examens.id'), nullable=False)
    __table_args__ = (db.UniqueConstraint('eleve_id', 'examen_id', name='unique_note_examen'),)

# --- Fonctions de calcul ---
def get_notes_trimestre(eleve_id, classe_id, discipline_id, trimestre_id):
    """Retourne (moyenne_devoirs, note_examen) pour un élève, une discipline, un trimestre."""
    # Devoirs
    devoir_notes = db.session.query(NoteDevoir.valeur).join(Devoir).filter(
        NoteDevoir.eleve_id == eleve_id,
        Devoir.classe_id == classe_id,
        Devoir.discipline_id == discipline_id,
        Devoir.trimestre_id == trimestre_id
    ).all()
    notes = [n[0] for n in devoir_notes]
    moyenne = sum(notes)/len(notes) if notes else None

    # Examen
    exam_note = db.session.query(NoteExamen.valeur).join(Examen).filter(
        NoteExamen.eleve_id == eleve_id,
        Examen.classe_id == classe_id,
        Examen.discipline_id == discipline_id,
        Examen.trimestre_id == trimestre_id
    ).first()
    note_exam = exam_note[0] if exam_note else None
    return moyenne, note_exam

def calculer_moyenne_trimestre(eleve_id, classe_id, trimestre_id):
    """Calcule la moyenne générale d'un élève pour un trimestre donné."""
    disciplines = Discipline.query.all()
    total_coeff = 0
    total_note_coeff = 0
    for disc in disciplines:
        coeff_obj = Coefficient.query.filter_by(classe_id=classe_id, discipline_id=disc.id).first()
        if not coeff_obj:
            continue
        coeff = coeff_obj.valeur
        note_classe, note_exam = get_notes_trimestre(eleve_id, classe_id, disc.id, trimestre_id)
        if note_classe is not None and note_exam is not None:
            note_finale = (note_classe + 2 * note_exam) / 3
            total_note_coeff += note_finale * coeff
            total_coeff += coeff
    if total_coeff == 0:
        return None
    return total_note_coeff / total_coeff

def get_bulletin_trimestre(eleve_id, trimestre_id):
    """Renvoie un dict avec les infos pour le bulletin trimestriel."""
    eleve = Eleve.query.get(eleve_id)
    if not eleve:
        return None
    classe = eleve.classe
    annee = classe.annee
    trimestre = Trimestre.query.get(trimestre_id)
    if not trimestre or trimestre.annee_id != annee.id:
        return None

    lignes = []
    for disc in Discipline.query.all():
        coeff_obj = Coefficient.query.filter_by(classe_id=classe.id, discipline_id=disc.id).first()
        if not coeff_obj:
            continue
        coeff = coeff_obj.valeur
        note_classe, note_exam = get_notes_trimestre(eleve.id, classe.id, disc.id, trimestre.id)
        if note_classe is not None and note_exam is not None:
            note_finale = (note_classe + 2 * note_exam) / 3
            note_coeff = note_finale * coeff
            lignes.append({
                'discipline': disc.nom,
                'note_classe': round(note_classe, 2),
                'note_exam': round(note_exam, 2),
                'note_finale': round(note_finale, 2),
                'coeff': coeff,
                'note_coeff': round(note_coeff, 2)
            })
    moyenne = calculer_moyenne_trimestre(eleve.id, classe.id, trimestre.id)
    return {
        'eleve': eleve,
        'classe': classe,
        'annee': annee,
        'trimestre': trimestre,
        'lignes': lignes,
        'moyenne': round(moyenne, 2) if moyenne is not None else None
    }

def get_bulletin_annuel(eleve_id):
    """Renvoie la moyenne annuelle (moyenne des trois trimestres) et les détails."""
    eleve = Eleve.query.get(eleve_id)
    if not eleve:
        return None
    classe = eleve.classe
    annee = classe.annee
    trimestres = Trimestre.query.filter_by(annee_id=annee.id).order_by(Trimestre.ordre).all()
    moyennes = []
    details = []
    for trim in trimestres:
        moy = calculer_moyenne_trimestre(eleve.id, classe.id, trim.id)
        if moy is not None:
            moyennes.append(moy)
            details.append({'trimestre': trim.nom, 'moyenne': round(moy, 2)})
    if not moyennes:
        moyenne_annuelle = None
    else:
        moyenne_annuelle = sum(moyennes) / len(moyennes)
    return {
        'eleve': eleve,
        'classe': classe,
        'annee': annee,
        'details': details,
        'moyenne_annuelle': round(moyenne_annuelle, 2) if moyenne_annuelle is not None else None
    }

# --- Génération PDF ---
def generer_pdf_bulletin(data, type_bulletin='trimestre'):
    """Génère un PDF pour le bulletin (trimestriel ou annuel)."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    style_title = ParagraphStyle('Title', parent=styles['Title'], alignment=TA_CENTER, fontSize=16)
    style_normal = styles['Normal']
    elements = []

    if type_bulletin == 'trimestre':
        titre = f"Bulletin trimestriel - {data['trimestre'].nom}"
        sous_titre = f"{data['eleve'].prenom} {data['eleve'].nom} - {data['classe'].nom} ({data['annee'].libelle})"
        elements.append(Paragraph(titre, style_title))
        elements.append(Spacer(1, 0.5*cm))
        elements.append(Paragraph(sous_titre, style_normal))
        elements.append(Spacer(1, 0.5*cm))
        # Tableau
        table_data = [['Discipline', 'Note classe', 'Note examen', 'Note finale', 'Coef.', 'Note coef.']]
        for ligne in data['lignes']:
            table_data.append([
                ligne['discipline'],
                str(ligne['note_classe']),
                str(ligne['note_exam']),
                str(ligne['note_finale']),
                str(ligne['coeff']),
                str(ligne['note_coeff'])
            ])
        table_data.append(['', '', '', '', 'Moyenne', str(data['moyenne']) if data['moyenne'] is not None else '---'])
        t = Table(table_data, colWidths=[4*cm, 2*cm, 2*cm, 2*cm, 1.5*cm, 2*cm])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.grey),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0,0), (-1,0), 12),
            ('BACKGROUND', (0,1), (-1,-2), colors.beige),
            ('GRID', (0,0), (-1,-1), 1, colors.black)
        ]))
        elements.append(t)
    else:  # annuel
        titre = f"Bulletin annuel - {data['annee'].libelle}"
        sous_titre = f"{data['eleve'].prenom} {data['eleve'].nom} - {data['classe'].nom}"
        elements.append(Paragraph(titre, style_title))
        elements.append(Spacer(1, 0.5*cm))
        elements.append(Paragraph(sous_titre, style_normal))
        elements.append(Spacer(1, 0.5*cm))
        table_data = [['Trimestre', 'Moyenne']]
        for d in data['details']:
            table_data.append([d['trimestre'], str(d['moyenne'])])
        table_data.append(['', 'Moyenne annuelle'])
        table_data.append(['', str(data['moyenne_annuelle']) if data['moyenne_annuelle'] is not None else '---'])
        t = Table(table_data, colWidths=[6*cm, 6*cm])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.grey),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('GRID', (0,0), (-1,-1), 1, colors.black)
        ]))
        elements.append(t)

    doc.build(elements)
    buffer.seek(0)
    return buffer

# --- Routes HTML (templates intégrés) ---

BASE_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Gestion Scolaire</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f4f4f4; }
        h1 { color: #333; }
        nav a { margin-right: 15px; text-decoration: none; color: #2a7; font-weight: bold; }
        nav a:hover { text-decoration: underline; }
        .container { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
        .flash { padding: 10px; background: #d4edda; border: 1px solid #c3e6cb; margin-bottom: 10px; }
        ul { list-style-type: none; padding: 0; }
        li { margin: 8px 0; }
        a { color: #1a73e8; text-decoration: none; }
        a:hover { text-decoration: underline; }
        .btn { background: #28a745; color: white; padding: 6px 12px; border: none; border-radius: 4px; cursor: pointer; }
        .btn-danger { background: #dc3545; }
        input, select { padding: 6px; margin: 4px; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: center; }
        th { background: #f2f2f2; }
        .form-inline { display: flex; flex-wrap: wrap; align-items: center; gap: 10px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>📚 Gestion du Lycée</h1>
        <nav>
            <a href="{{ url_for('index') }}">Accueil</a>
            <a href="{{ url_for('annees') }}">Années</a>
            <a href="{{ url_for('classes') }}">Classes</a>
            <a href="{{ url_for('disciplines') }}">Disciplines</a>
            <a href="{{ url_for('coefficients') }}">Coefficients</a>
            <a href="{{ url_for('eleves') }}">Élèves</a>
            <a href="{{ url_for('notes') }}">Saisie notes</a>
            <a href="{{ url_for('bulletins') }}">Bulletins</a>
        </nav>
        <hr>
        {% with messages = get_flashed_messages() %}
          {% if messages %}
            <div class="flash">{{ messages[0] }}</div>
          {% endif %}
        {% endwith %}
        {% block content %}{% endblock %}
    </div>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(BASE_TEMPLATE, content='''
        <h2>Bienvenue !</h2>
        <p>Utilisez le menu ci-dessus pour gérer votre établissement.</p>
    ''')

# --- Années ---
@app.route('/annees', methods=['GET', 'POST'])
def annees():
    if request.method == 'POST':
        libelle = request.form.get('libelle')
        if libelle:
            annee = AnneeScolaire(libelle=libelle)
            db.session.add(annee)
            db.session.commit()
            flash('Année ajoutée.')
        return redirect(url_for('annees'))
    annees = AnneeScolaire.query.all()
    content = '''
        <h2>Années scolaires</h2>
        <form method="post" class="form-inline">
            <input type="text" name="libelle" placeholder="Ex: 2024-2025" required>
            <button type="submit" class="btn">Ajouter</button>
        </form>
        <ul>
        {% for a in annees %}
            <li>
                {{ a.libelle }} {% if a.active %} (active) {% endif %}
                <a href="{{ url_for('supprimer_annee', id=a.id) }}" class="btn btn-danger" onclick="return confirm('Confirmer ?')">Supprimer</a>
                <a href="{{ url_for('basculer_annee', id=a.id) }}">{% if a.active %}Désactiver{% else %}Activer{% endif %}</a>
            </li>
        {% endfor %}
        </ul>
    '''
    return render_template_string(BASE_TEMPLATE.replace('{% block content %}{% endblock %}', '{{ content|safe }}'), content=content, annees=annees)

@app.route('/annee/supprimer/<int:id>')
def supprimer_annee(id):
    annee = AnneeScolaire.query.get_or_404(id)
    db.session.delete(annee)
    db.session.commit()
    flash('Année supprimée.')
    return redirect(url_for('annees'))

@app.route('/annee/basculer/<int:id>')
def basculer_annee(id):
    annee = AnneeScolaire.query.get_or_404(id)
    annee.active = not annee.active
    db.session.commit()
    flash('Statut modifié.')
    return redirect(url_for('annees'))

# --- Classes ---
@app.route('/classes', methods=['GET', 'POST'])
def classes():
    if request.method == 'POST':
        nom = request.form.get('nom')
        annee_id = request.form.get('annee_id')
        if nom and annee_id:
            classe = Classe(nom=nom, annee_id=int(annee_id))
            db.session.add(classe)
            db.session.commit()
            flash('Classe ajoutée.')
        return redirect(url_for('classes'))
    annees = AnneeScolaire.query.all()
    classes = Classe.query.all()
    content = '''
        <h2>Classes</h2>
        <form method="post" class="form-inline">
            <input type="text" name="nom" placeholder="Ex: 3ème A" required>
            <select name="annee_id" required>
                <option value="">Choisir une année</option>
                {% for a in annees %}
                    <option value="{{ a.id }}">{{ a.libelle }}</option>
                {% endfor %}
            </select>
            <button type="submit" class="btn">Ajouter</button>
        </form>
        <ul>
        {% for c in classes %}
            <li>{{ c.nom }} ({{ c.annee.libelle }}) 
                <a href="{{ url_for('supprimer_classe', id=c.id) }}" class="btn btn-danger" onclick="return confirm('Confirmer ?')">Supprimer</a>
            </li>
        {% endfor %}
        </ul>
    '''
    return render_template_string(BASE_TEMPLATE.replace('{% block content %}{% endblock %}', '{{ content|safe }}'), content=content, annees=annees, classes=classes)

@app.route('/classe/supprimer/<int:id>')
def supprimer_classe(id):
    classe = Classe.query.get_or_404(id)
    db.session.delete(classe)
    db.session.commit()
    flash('Classe supprimée.')
    return redirect(url_for('classes'))

# --- Disciplines ---
@app.route('/disciplines', methods=['GET', 'POST'])
def disciplines():
    if request.method == 'POST':
        nom = request.form.get('nom')
        if nom:
            disc = Discipline(nom=nom)
            db.session.add(disc)
            db.session.commit()
            flash('Discipline ajoutée.')
        return redirect(url_for('disciplines'))
    disciplines = Discipline.query.all()
    content = '''
        <h2>Disciplines</h2>
        <form method="post" class="form-inline">
            <input type="text" name="nom" placeholder="Ex: Mathématiques" required>
            <button type="submit" class="btn">Ajouter</button>
        </form>
        <ul>
        {% for d in disciplines %}
            <li>{{ d.nom }} 
                <a href="{{ url_for('supprimer_discipline', id=d.id) }}" class="btn btn-danger" onclick="return confirm('Confirmer ?')">Supprimer</a>
            </li>
        {% endfor %}
        </ul>
    '''
    return render_template_string(BASE_TEMPLATE.replace('{% block content %}{% endblock %}', '{{ content|safe }}'), content=content, disciplines=disciplines)

@app.route('/discipline/supprimer/<int:id>')
def supprimer_discipline(id):
    disc = Discipline.query.get_or_404(id)
    db.session.delete(disc)
    db.session.commit()
    flash('Discipline supprimée.')
    return redirect(url_for('disciplines'))

# --- Coefficients ---
@app.route('/coefficients', methods=['GET', 'POST'])
def coefficients():
    if request.method == 'POST':
        classe_id = request.form.get('classe_id')
        discipline_id = request.form.get('discipline_id')
        valeur = request.form.get('valeur')
        if classe_id and discipline_id and valeur:
            coeff = Coefficient(classe_id=int(classe_id), discipline_id=int(discipline_id), valeur=float(valeur))
            db.session.add(coeff)
            db.session.commit()
            flash('Coefficient ajouté.')
        return redirect(url_for('coefficients'))
    classes = Classe.query.all()
    disciplines = Discipline.query.all()
    coeffs = Coefficient.query.all()
    content = '''
        <h2>Coefficients par classe</h2>
        <form method="post" class="form-inline">
            <select name="classe_id" required>
                <option value="">Classe</option>
                {% for c in classes %}
                    <option value="{{ c.id }}">{{ c.nom }}</option>
                {% endfor %}
            </select>
            <select name="discipline_id" required>
                <option value="">Discipline</option>
                {% for d in disciplines %}
                    <option value="{{ d.id }}">{{ d.nom }}</option>
                {% endfor %}
            </select>
            <input type="number" step="0.1" name="valeur" placeholder="Coef" required>
            <button type="submit" class="btn">Ajouter</button>
        </form>
        <table>
            <tr><th>Classe</th><th>Discipline</th><th>Coefficient</th><th>Action</th></tr>
            {% for c in coeffs %}
            <tr>
                <td>{{ c.classe.nom }}</td>
                <td>{{ c.discipline.nom }}</td>
                <td>{{ c.valeur }}</td>
                <td><a href="{{ url_for('supprimer_coefficient', id=c.id) }}" class="btn btn-danger" onclick="return confirm('Confirmer ?')">Supprimer</a></td>
            </tr>
            {% endfor %}
        </table>
    '''
    return render_template_string(BASE_TEMPLATE.replace('{% block content %}{% endblock %}', '{{ content|safe }}'), content=content, classes=classes, disciplines=disciplines, coeffs=coeffs)

@app.route('/coefficient/supprimer/<int:id>')
def supprimer_coefficient(id):
    coeff = Coefficient.query.get_or_404(id)
    db.session.delete(coeff)
    db.session.commit()
    flash('Coefficient supprimé.')
    return redirect(url_for('coefficients'))

# --- Élèves ---
@app.route('/eleves', methods=['GET', 'POST'])
def eleves():
    if request.method == 'POST':
        nom = request.form.get('nom')
        prenom = request.form.get('prenom')
        classe_id = request.form.get('classe_id')
        if nom and prenom and classe_id:
            # génération matricule simple
            count = Eleve.query.filter_by(classe_id=int(classe_id)).count() + 1
            matricule = f"{classe_id}-{count:04d}"
            eleve = Eleve(nom=nom, prenom=prenom, classe_id=int(classe_id), matricule=matricule)
            db.session.add(eleve)
            db.session.commit()
            flash('Élève ajouté.')
        return redirect(url_for('eleves'))
    classes = Classe.query.all()
    eleves = Eleve.query.all()
    content = '''
        <h2>Élèves</h2>
        <form method="post" class="form-inline">
            <input type="text" name="nom" placeholder="Nom" required>
            <input type="text" name="prenom" placeholder="Prénom" required>
            <select name="classe_id" required>
                <option value="">Classe</option>
                {% for c in classes %}
                    <option value="{{ c.id }}">{{ c.nom }}</option>
                {% endfor %}
            </select>
            <button type="submit" class="btn">Ajouter</button>
        </form>
        <table>
            <tr><th>Matricule</th><th>Nom</th><th>Prénom</th><th>Classe</th><th>Action</th></tr>
            {% for e in eleves %}
            <tr>
                <td>{{ e.matricule }}</td>
                <td>{{ e.nom }}</td>
                <td>{{ e.prenom }}</td>
                <td>{{ e.classe.nom }}</td>
                <td><a href="{{ url_for('supprimer_eleve', id=e.id) }}" class="btn btn-danger" onclick="return confirm('Confirmer ?')">Supprimer</a></td>
            </tr>
            {% endfor %}
        </table>
    '''
    return render_template_string(BASE_TEMPLATE.replace('{% block content %}{% endblock %}', '{{ content|safe }}'), content=content, classes=classes, eleves=eleves)

@app.route('/eleve/supprimer/<int:id>')
def supprimer_eleve(id):
    eleve = Eleve.query.get_or_404(id)
    db.session.delete(eleve)
    db.session.commit()
    flash('Élève supprimé.')
    return redirect(url_for('eleves'))

# --- Saisie des notes ---
@app.route('/notes', methods=['GET', 'POST'])
def notes():
    # Sélectionner année, classe, trimestre, discipline
    annees = AnneeScolaire.query.all()
    classes = Classe.query.all()
    trimestres = Trimestre.query.all()
    disciplines = Discipline.query.all()
    eleves = []

    annee_id = request.args.get('annee_id', type=int)
    classe_id = request.args.get('classe_id', type=int)
    trimestre_id = request.args.get('trimestre_id', type=int)
    discipline_id = request.args.get('discipline_id', type=int)

    if request.method == 'POST':
        # Récupérer les données du formulaire
        annee_id = request.form.get('annee_id', type=int)
        classe_id = request.form.get('classe_id', type=int)
        trimestre_id = request.form.get('trimestre_id', type=int)
        discipline_id = request.form.get('discipline_id', type=int)
        # S'il y a des notes devoir et examen
        if annee_id and classe_id and trimestre_id and discipline_id:
            # Vérifier s'il existe un devoir et un examen pour ce couple; sinon en créer.
            # On va chercher ou créer le devoir pour cette combinaison.
            devoir = Devoir.query.filter_by(classe_id=classe_id, discipline_id=discipline_id, trimestre_id=trimestre_id).first()
            if not devoir:
                devoir = Devoir(classe_id=classe_id, discipline_id=discipline_id, trimestre_id=trimestre_id)
                db.session.add(devoir)
                db.session.commit()
            examen = Examen.query.filter_by(classe_id=classe_id, discipline_id=discipline_id, trimestre_id=trimestre_id).first()
            if not examen:
                examen = Examen(classe_id=classe_id, discipline_id=discipline_id, trimestre_id=trimestre_id)
                db.session.add(examen)
                db.session.commit()
            # Traiter les notes des élèves
            eleves_classe = Eleve.query.filter_by(classe_id=classe_id).all()
            for eleve in eleves_classe:
                note_devoir = request.form.get(f'dev_{eleve.id}')
                note_exam = request.form.get(f'exam_{eleve.id}')
                if note_devoir:
                    nd = NoteDevoir.query.filter_by(eleve_id=eleve.id, devoir_id=devoir.id).first()
                    if nd:
                        nd.valeur = float(note_devoir)
                    else:
                        nd = NoteDevoir(eleve_id=eleve.id, devoir_id=devoir.id, valeur=float(note_devoir))
                        db.session.add(nd)
                if note_exam:
                    ne = NoteExamen.query.filter_by(eleve_id=eleve.id, examen_id=examen.id).first()
                    if ne:
                        ne.valeur = float(note_exam)
                    else:
                        ne = NoteExamen(eleve_id=eleve.id, examen_id=examen.id, valeur=float(note_exam))
                        db.session.add(ne)
            db.session.commit()
            flash('Notes enregistrées.')
            return redirect(url_for('notes', annee_id=annee_id, classe_id=classe_id, trimestre_id=trimestre_id, discipline_id=discipline_id))

    # Préparer la liste des élèves pour affichage
    if classe_id:
        eleves = Eleve.query.filter_by(classe_id=classe_id).all()

    content = '''
        <h2>Saisie des notes</h2>
        <form method="get" class="form-inline" action="{{ url_for('notes') }}">
            <select name="annee_id" required>
                <option value="">Année</option>
                {% for a in annees %}
                    <option value="{{ a.id }}" {% if a.id == annee_id %}selected{% endif %}>{{ a.libelle }}</option>
                {% endfor %}
            </select>
            <select name="classe_id" required>
                <option value="">Classe</option>
                {% for c in classes %}
                    <option value="{{ c.id }}" {% if c.id == classe_id %}selected{% endif %}>{{ c.nom }}</option>
                {% endfor %}
            </select>
            <select name="trimestre_id" required>
                <option value="">Trimestre</option>
                {% for t in trimestres %}
                    <option value="{{ t.id }}" {% if t.id == trimestre_id %}selected{% endif %}>{{ t.nom }}</option>
                {% endfor %}
            </select>
            <select name="discipline_id" required>
                <option value="">Discipline</option>
                {% for d in disciplines %}
                    <option value="{{ d.id }}" {% if d.id == discipline_id %}selected{% endif %}>{{ d.nom }}</option>
                {% endfor %}
            </select>
            <button type="submit" class="btn">Charger</button>
        </form>

        {% if classe_id and trimestre_id and discipline_id %}
            <form method="post" action="{{ url_for('notes') }}">
                <input type="hidden" name="annee_id" value="{{ annee_id }}">
                <input type="hidden" name="classe_id" value="{{ classe_id }}">
                <input type="hidden" name="trimestre_id" value="{{ trimestre_id }}">
                <input type="hidden" name="discipline_id" value="{{ discipline_id }}">
                <table>
                    <tr><th>Élève</th><th>Note devoir(s) (moyenne)</th><th>Note examen</th></tr>
                    {% for eleve in eleves %}
                    <tr>
                        <td>{{ eleve.prenom }} {{ eleve.nom }}</td>
                        <td><input type="number" step="0.5" name="dev_{{ eleve.id }}" 
                               value="{% set nd = eleve.notes_devoir.filter_by(devoir_id=devoir.id).first() %}{% if nd %}{{ nd.valeur }}{% endif %}"></td>
                        <td><input type="number" step="0.5" name="exam_{{ eleve.id }}"
                               value="{% set ne = eleve.notes_examen.filter_by(examen_id=examen.id).first() %}{% if ne %}{{ ne.valeur }}{% endif %}"></td>
                    </tr>
                    {% endfor %}
                </table>
                <button type="submit" class="btn">Enregistrer</button>
            </form>
        {% endif %}
    '''
    # On doit passer les variables 'devoir' et 'examen' pour les valeurs pré-remplies
    devoir = None
    examen = None
    if classe_id and trimestre_id and discipline_id:
        devoir = Devoir.query.filter_by(classe_id=classe_id, discipline_id=discipline_id, trimestre_id=trimestre_id).first()
        examen = Examen.query.filter_by(classe_id=classe_id, discipline_id=discipline_id, trimestre_id=trimestre_id).first()
    return render_template_string(BASE_TEMPLATE.replace('{% block content %}{% endblock %}', '{{ content|safe }}'),
                                   content=content, annees=annees, classes=classes, trimestres=trimestres,
                                   disciplines=disciplines, eleves=eleves, annee_id=annee_id, classe_id=classe_id,
                                   trimestre_id=trimestre_id, discipline_id=discipline_id, devoir=devoir, examen=examen)

# --- Bulletins ---
@app.route('/bulletins', methods=['GET'])
def bulletins():
    annees = AnneeScolaire.query.all()
    classes = Classe.query.all()
    trimestres = Trimestre.query.all()
    eleves = []
    annee_id = request.args.get('annee_id', type=int)
    classe_id = request.args.get('classe_id', type=int)
    trimestre_id = request.args.get('trimestre_id', type=int)
    type_bulletin = request.args.get('type', 'trimestre')  # 'trimestre' ou 'annuel'
    if classe_id:
        eleves = Eleve.query.filter_by(classe_id=classe_id).all()

    content = '''
        <h2>Bulletins</h2>
        <form method="get" class="form-inline" action="{{ url_for('bulletins') }}">
            <select name="annee_id" required>
                <option value="">Année</option>
                {% for a in annees %}
                    <option value="{{ a.id }}" {% if a.id == annee_id %}selected{% endif %}>{{ a.libelle }}</option>
                {% endfor %}
            </select>
            <select name="classe_id" required>
                <option value="">Classe</option>
                {% for c in classes %}
                    <option value="{{ c.id }}" {% if c.id == classe_id %}selected{% endif %}>{{ c.nom }}</option>
                {% endfor %}
            </select>
            <select name="trimestre_id" {% if type_bulletin == 'trimestre' %}required{% endif %}>
                <option value="">Trimestre</option>
                {% for t in trimestres %}
                    <option value="{{ t.id }}" {% if t.id == trimestre_id %}selected{% endif %}>{{ t.nom }}</option>
                {% endfor %}
            </select>
            <select name="type">
                <option value="trimestre" {% if type_bulletin == 'trimestre' %}selected{% endif %}>Trimestriel</option>
                <option value="annuel" {% if type_bulletin == 'annuel' %}selected{% endif %}>Annuel</option>
            </select>
            <button type="submit" class="btn">Afficher</button>
        </form>
        {% if classe_id %}
            <h3>Élèves de la classe</h3>
            <ul>
            {% for eleve in eleves %}
                <li>
                    {{ eleve.prenom }} {{ eleve.nom }}
                    {% if type_bulletin == 'trimestre' and trimestre_id %}
                        <a href="{{ url_for('generer_bulletin_pdf', eleve_id=eleve.id, trimestre_id=trimestre_id) }}" target="_blank">PDF trimestriel</a>
                    {% elif type_bulletin == 'annuel' %}
                        <a href="{{ url_for('generer_bulletin_annuel_pdf', eleve_id=eleve.id) }}" target="_blank">PDF annuel</a>
                    {% endif %}
                </li>
            {% endfor %}
            </ul>
        {% endif %}
    '''
    return render_template_string(BASE_TEMPLATE.replace('{% block content %}{% endblock %}', '{{ content|safe }}'),
                                   content=content, annees=annees, classes=classes, trimestres=trimestres,
                                   eleves=eleves, annee_id=annee_id, classe_id=classe_id, trimestre_id=trimestre_id,
                                   type_bulletin=type_bulletin)

@app.route('/bulletin_pdf/<int:eleve_id>/<int:trimestre_id>')
def generer_bulletin_pdf(eleve_id, trimestre_id):
    data = get_bulletin_trimestre(eleve_id, trimestre_id)
    if not data:
        flash('Données manquantes pour ce bulletin.')
        return redirect(url_for('bulletins'))
    pdf_buffer = generer_pdf_bulletin(data, 'trimestre')
    return send_file(pdf_buffer, as_attachment=True, download_name=f"bulletin_{eleve_id}_{trimestre_id}.pdf", mimetype='application/pdf')

@app.route('/bulletin_annuel_pdf/<int:eleve_id>')
def generer_bulletin_annuel_pdf(eleve_id):
    data = get_bulletin_annuel(eleve_id)
    if not data or not data['details']:
        flash('Données manquantes pour le bulletin annuel.')
        return redirect(url_for('bulletins'))
    pdf_buffer = generer_pdf_bulletin(data, 'annuel')
    return send_file(pdf_buffer, as_attachment=True, download_name=f"bulletin_annuel_{eleve_id}.pdf", mimetype='application/pdf')

# --- Initialisation de la base (création des trimestres par défaut) ---
# --- Supprimer complètement ces lignes :
# @app.before_first_request
# def create_trimestres():
#     ...

# --- Et les remplacer par ceci :

def init_trimestres():
    """Crée les trimestres par défaut pour toutes les années existantes."""
    with app.app_context():
        annees = AnneeScolaire.query.all()
        for annee in annees:
            for ordre, nom in [(1, 'T1'), (2, 'T2'), (3, 'T3')]:
                if not Trimestre.query.filter_by(annee_id=annee.id, ordre=ordre).first():
                    trim = Trimestre(nom=nom, ordre=ordre, annee_id=annee.id)
                    db.session.add(trim)
            db.session.commit()
        print("Trimestres initialisés avec succès.")
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)