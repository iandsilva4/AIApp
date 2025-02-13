from app.__init__ import db
from datetime import datetime, timezone

class UserSummary(db.Model):
    __tablename__ = 'user_summaries'

    id = db.Column(db.Integer, primary_key=True)
    user_email = db.Column(db.String(255), unique=True, nullable=False)
    summary = db.Column(db.Text, nullable=False)
    session_summaries = db.Column(db.Text, nullable=True)  # JSON string of session summaries with metadata
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __init__(self, user_email, summary=None, session_summaries=None):
        self.user_email = user_email
        self.summary = summary
        self.session_summaries = session_summaries
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)

    def to_dict(self):
        return {
            'id': self.id,
            'user_email': self.user_email,
            'summary': self.summary,
            'session_summaries': self.session_summaries,  # Will be a JSON string that needs to be parsed on frontend
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

    def __repr__(self):
        return f'<UserSummary {self.user_email}>'