# models.py
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean
from sqlalchemy.orm import declarative_base
import datetime as dt

Base = declarative_base()


class News(Base):
    __tablename__ = "news"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(300), nullable=False)
    url = Column(String(500), unique=True, nullable=False, index=True)
    summary = Column(Text, nullable=True)
    source = Column(String(50), nullable=False, index=True)  # G1, R7, CNN, etc.
    city = Column(String(100), nullable=True)
    uf = Column(String(2), index=True, nullable=True)        # SP, RJ, AL...
    category = Column(String(100), nullable=True)
    published_at = Column(DateTime, index=True, nullable=True)
    created_at = Column(DateTime, default=dt.datetime.utcnow, nullable=False)


class MonitoredURL(Base):
    __tablename__ = "monitored_urls"

    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(String(500), unique=True, nullable=False)
    media = Column(String(50), nullable=False, index=True)   # "G1", "CNN Brasil", "R7"
    uf = Column(String(2), nullable=True, index=True)
    city = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=dt.datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=dt.datetime.utcnow,
        onupdate=dt.datetime.utcnow,
        nullable=False,
    )


class Keyword(Base):
    __tablename__ = "keywords"

    id = Column(Integer, primary_key=True, autoincrement=True)
    term = Column(String(100), unique=True, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=dt.datetime.utcnow, nullable=False)
