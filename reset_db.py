import os
from focusflow import create_app,db

app = create_app()

# Path to your SQLite database file (adjust this if your path/config differs)
db_path = os.path.join(app.instance_path, 'focusflow.db')

# Delete the existing database file if it exists
if os.path.exists(db_path):
    print(f"Deleting existing database file at {db_path}")
    os.remove(db_path)
else:
    print(f"No existing database file found at {db_path}")

# Create all tables fresh
with app.app_context():
    db.create_all()
    print("Created all tables in the new database.")
