import re
import unicodedata
from datetime import datetime, timezone, timedelta
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.extensions import db

def utc_now():
    return datetime.now(timezone.utc)

def slugify(text: str) -> str:
    """Converte um título em um slug legível e seguro para URL."""
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')
    text = re.sub(r'[^\w\s-]', '', text.lower()).strip()
    return re.sub(r'[-\s]+', '-', text)[:100]

class ArticlePage(db.Model):
    """
    Representa a página interna de uma notícia armazenada no SQLite.
    Não é um arquivo HTML físico em disco: sua existência e URL dinâmica
    são controladas por este registro no banco de dados SQLite.
    Caso seja excluída por falta de acessos (5 dias), será recriada automaticamente
    quando um leitor clicar novamente no card da notícia.
    """
    __tablename__ = 'article_pages'

    id = Column(Integer, primary_key=True, autoincrement=True)
    slug = Column(String(160), unique=True, nullable=False, index=True)
    news_id = Column(Integer, ForeignKey('news_articles.id', ondelete='CASCADE'), nullable=False, unique=True, index=True)
    created_at = Column(DateTime, nullable=False, default=utc_now)
    last_accessed_at = Column(DateTime, nullable=False, default=utc_now, index=True)
    access_count = Column(Integer, nullable=False, default=1)
    is_active = Column(Boolean, nullable=False, default=True)

    # Relacionamento com o artigo original
    article = relationship('NewsArticle', back_populates='page')

    # Registros auxiliares de acesso anônimo (excluídos em cascata se a página for removida)
    access_logs = relationship(
        'AccessLog',
        back_populates='page',
        cascade='all, delete-orphan',
        order_by='desc(AccessLog.accessed_at)'
    )

    __table_args__ = (
        Index('idx_page_last_access', 'last_accessed_at'),
        Index('idx_page_slug', 'slug'),
    )

    @classmethod
    def create_for_article(cls, article) -> 'ArticlePage':
        """Gera ou obtém o registro de página para a notícia."""
        base_slug = slugify(article.title) or 'noticia'
        slug = f"{base_slug}-{article.id}"
        
        page = cls(
            slug=slug,
            news_id=article.id,
            created_at=utc_now(),
            last_accessed_at=utc_now(),
            access_count=1,
            is_active=True
        )
        return page

    def register_access(self):
        """Atualiza a data do último acesso para UTC atual e incrementa o contador."""
        self.last_accessed_at = utc_now()
        self.access_count = (self.access_count or 0) + 1

    def days_since_last_access(self) -> float:
        """Calcula quantos dias se passaram desde o último acesso."""
        now = utc_now()
        # Garantir timezone UTC compatível
        last_acc = self.last_accessed_at
        if last_acc.tzinfo is None:
            last_acc = last_acc.replace(tzinfo=timezone.utc)
        diff = now - last_acc
        return diff.total_seconds() / 86400.0

    def is_expired(self, max_days: int = 5) -> bool:
        """Determina se a página completou 5 dias consecutivos sem nenhum acesso."""
        return self.days_since_last_access() >= max_days

    def to_dict(self):
        return {
            'id': self.id,
            'slug': self.slug,
            'news_id': self.news_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_accessed_at': self.last_accessed_at.isoformat() if self.last_accessed_at else None,
            'access_count': self.access_count,
            'days_since_last_access': round(self.days_since_last_access(), 2),
            'is_active': self.is_active
        }

    def __repr__(self):
        return f"<ArticlePage id={self.id} slug={self.slug!r} news_id={self.news_id}>"
