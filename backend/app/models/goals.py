from app.__init__ import db
from datetime import datetime, timezone

class Goals(db.Model):
    __tablename__ = "goals"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    system_prompt = db.Column(db.Text, nullable=False)
    avatar_url = db.Column(db.String(255), nullable=True)
    created_by = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    is_globally_hidden = db.Column(db.Boolean, nullable=True, default=False)
    short_desc = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(255), nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'system_prompt': self.system_prompt,
            'avatar_url': self.avatar_url,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_globally_hidden': self.is_globally_hidden,
            'short_desc': self.short_desc,
            'category': self.category
        }