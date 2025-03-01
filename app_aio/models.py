from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime
from werkzeug.security import check_password_hash


class User(Base):
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True)
    email = Column(String(80), unique=True, nullable=False)
    password = Column(String(120), nullable=False)

    def verify_password(self, password):
        return check_password_hash(self.password, password)


class Adventure(Base):
    __tablename__ = 'adventure'
    id = Column(Integer, primary_key=True)
    title = Column(String(80), nullable=False)
    description = Column(String(120), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    owner_id = Column(Integer, ForeignKey('user.id'))

    owner = relationship('User', backref='adventures')