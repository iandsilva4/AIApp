from app.__init__ import db
from datetime import datetime, timezone

class SessionSentiments(db.Model):
    __tablename__ = "session_sentiments"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_email = db.Column(db.String(255), nullable=False)
    session_id = db.Column(db.Integer, nullable=False)
    sentiment = db.Column(db.String(255), nullable=False)
    sentiment_score = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'id': self.id,
            'user_email': self.user_email,
            'session_id': self.session_id,
            'sentiment': self.sentiment,
            'sentiment_score': self.sentiment_score,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }