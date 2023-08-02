from extensions import db
from sqlalchemy.sql import func


class Candidate(db.Model):
    email = db.Column(db.String(100), primary_key=True)
    resume_path = db.Column(db.String(500), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True),
                           server_default=func.now())

    def __repr__(self):
        return f'<Candidate {self.email}>'
