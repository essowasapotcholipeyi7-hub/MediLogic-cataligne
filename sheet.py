from app import app, db
from sqlalchemy import text

with app.app_context():
    try:
        db.session.execute(text("ALTER TABLE commandes ADD COLUMN instructions TEXT"))
        db.session.commit()
        print("✅ Colonne 'instructions' ajoutée avec succès")
    except Exception as e:
        print(f"Erreur: {e}")
    exit()