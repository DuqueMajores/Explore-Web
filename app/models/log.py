import hashlib
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.extensions import db

def utc_now():
    return datetime.now(timezone.utc)

class AccessLog(db.Model):
    """
    Registros auxiliares necessários para determinar atividade anônima de leitores.
    Cada leitor anônimo recebe um identificador aleatório via cookie (UUID),
    garantindo que saibamos a frequência de acesso sem exigir cadastro pessoal.
    """
    __tablename__ = 'access_logs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    page_id = Column(Integer, ForeignKey('article_pages.id', ondelete='CASCADE'), nullable=False, index=True)
    reader_id = Column(String(64), nullable=False, index=True)
    accessed_at = Column(DateTime, nullable=False, default=utc_now, index=True)
    user_agent = Column(String(255), nullable=True)
    ip_hash = Column(String(64), nullable=True)

    page = relationship('ArticlePage', back_populates='access_logs')

    __table_args__ = (
        Index('idx_reader_page_access', 'reader_id', 'page_id'),
    )

    @staticmethod
    def hash_ip(ip: str) -> str:
        """Anonimiza o IP do leitor com SHA-256 para preservar privacidade."""
        if not ip:
            return 'unknown'
        return hashlib.sha256(ip.encode('utf-8')).hexdigest()[:16]

    def to_dict(self):
        return {
            'id': self.id,
            'page_id': self.page_id,
            'reader_id': self.reader_id,
            'accessed_at': self.accessed_at.isoformat() if self.accessed_at else None,
            'user_agent': self.user_agent,
            'ip_hash': self.ip_hash
        }

class MaintenanceLog(db.Model):
    """
    Histórico das execuções da rotina de limpeza automática e manutenção do SQLite.
    Permite auditar quando a verificação dos 5 dias foi realizada e quantas páginas foram excluídas.
    """
    __tablename__ = 'maintenance_logs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    executed_at = Column(DateTime, nullable=False, default=utc_now, index=True)
    execution_type = Column(String(50), nullable=False, default='automatic')  # 'automatic' ou 'manual'
    pages_checked = Column(Integer, nullable=False, default=0)
    pages_deleted = Column(Integer, nullable=False, default=0)
    details = Column(Text, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'executed_at': self.executed_at.isoformat() if self.executed_at else None,
            'execution_type': self.execution_type,
            'pages_checked': self.pages_checked,
            'pages_deleted': self.pages_deleted,
            'details': self.details
        }
