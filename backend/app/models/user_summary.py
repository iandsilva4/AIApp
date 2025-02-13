from app.__init__ import db
from datetime import datetime, timezone

class UserSummary(db.Model):
    __tablename__ = 'user_summaries'

    id = db.Column(db.Integer, primary_key=True)
    user_email = db.Column(db.String(255), unique=True, nullable=False)
    summary = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'<UserSummary {self.user_email}>'