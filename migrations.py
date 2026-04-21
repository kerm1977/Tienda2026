# migrations.py
from flask_migrate import Migrate
from app import create_app
from db import db

# Archivo preparado para Flask-Migrate
app = create_app()
migrate = Migrate(app, db)

# Comandos de terminal:
# flask --app migrations.py db init
# flask --app migrations.py db migrate -m "Migración inicial"
# flask --app migrations.py db upgrade