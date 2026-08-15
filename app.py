import os
from flask import Flask, render_template_string
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# Configuration PostgreSQL
database_url = os.environ.get('DATABASE_URL')
if database_url and database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Modèle simple pour tester
class Test(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(50))

@app.route('/')
def index():
    try:
        # Tester la base
        test = Test.query.first()
        return f"✅ BASE DE DONNÉES OK ! Connexion réussie !"
    except Exception as e:
        return f"❌ ERREUR : {str(e)}"

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print("✅ Tables créées avec succès !")
    app.run(debug=True, host='0.0.0.0', port=10000)