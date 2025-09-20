from focusflow import create_app, db
from focusflow.models import Category

app = create_app()

with app.app_context():
    categories = [
        'Academic',
        'Research',
        'Assignments',
        'Exams',
        'Meetings',
        'Projects',
        'Events',
        'Personal',
        'Health & Fitness',
        'Social',
        'Volunteering',
        'Finance',
        'Later'
    ]

    for name in categories:
        if not Category.query.filter_by(name=name).first():
            cat = Category(name=name)
            db.session.add(cat)

    db.session.commit()
    print("Initial categories created successfully.")

