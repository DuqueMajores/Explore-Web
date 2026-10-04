import hashlib
import re
from typing import Optional, List
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, Index
from sqlalchemy.orm import relationship
from app.extensions import db

def utc_now():
    return datetime.now(timezone.utc)

class NewsArticle(db.Model):
    """
    Representa uma notícia obtida da NewsAPI ou inserida no sistema.
    Armazenada localmente no banco SQLite.
    """
    __tablename__ = 'news_articles'

    id = Column(Integer, primary_key=True, autoincrement=True)
    article_hash = Column(String(64), unique=True, nullable=False, index=True)
    title = Column(String(500), nullable=False)
    author = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    content = Column(Text, nullable=True)
    original_url = Column(Text, nullable=False)
    image_url = Column(Text, nullable=True)
    source_name = Column(String(255), nullable=True)
    category = Column(String(100), nullable=False, default='geral', index=True)
    published_at = Column(DateTime, nullable=True, index=True)
    created_at = Column(DateTime, nullable=False, default=utc_now)

    # Relacionamento 1 para 1 com a página interna correspondente
    page = relationship(
        'ArticlePage',
        back_populates='article',
        uselist=False,
        cascade='all, delete-orphan'
    )

    __table_args__ = (
        Index('idx_news_category_pub', 'category', 'published_at'),
    )

    @staticmethod
    def clean_url(url: str) -> str:
        if not url:
            return ""
        # Remove query params e âncoras para chave canônica
        u = url.split('#')[0].split('?')[0].rstrip('/')
        return u.strip()

    @staticmethod
    def generate_hash(url: str, title: str = '') -> str:
        """Gera um hash único SHA256 para evitar duplicações da mesma matéria."""
        clean_u = NewsArticle.clean_url(url)
        norm_title = re.sub(r'^(siga|ao vivo|urgente|veja|v[ií]deos?|leia mais):\s*', '', title or '', flags=re.IGNORECASE).strip().lower()
        norm_title = re.sub(r'\s+', ' ', norm_title)
        
        # Se for link canônico conhecido de portal (ex: g1, ge, uol, terra), o link canônico é o identificador
        if clean_u and ('.ghtml' in clean_u or '.html' in clean_u or '/noticia/' in clean_u):
            raw = f"url::{clean_u}"
        else:
            raw = f"{clean_u}::{norm_title}"
        return hashlib.sha256(raw.encode('utf-8')).hexdigest()

    CATEGORY_COVERS = {
        'tecnologia': [
            'https://images.unsplash.com/photo-1518770660439-4636190af475?w=800&q=80',
            'https://images.unsplash.com/photo-1488590528505-98d2b5aba04b?w=800&q=80',
            'https://images.unsplash.com/photo-1531297484001-80022131f5a1?w=800&q=80',
            'https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?w=800&q=80',
            'https://images.unsplash.com/photo-1519389950473-47ba0277781c?w=800&q=80',
            'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=800&q=80',
            'https://images.unsplash.com/photo-1550751827-4bd374c3f58b?w=800&q=80',
            'https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=800&q=80',
            'https://images.unsplash.com/photo-1504384308090-c894fdcc538d?w=800&q=80',
            'https://images.unsplash.com/photo-1620712943543-bcc4688e7485?w=800&q=80',
        ],
        'negocios': [
            'https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=800&q=80',
            'https://images.unsplash.com/photo-1578575437130-527eed3abbec?w=800&q=80',
            'https://images.unsplash.com/photo-1590283603385-17ffb3a7f29f?w=800&q=80',
            'https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?w=800&q=80',
            'https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?w=800&q=80',
            'https://images.unsplash.com/photo-1559526324-4b87b5e36e44?w=800&q=80',
            'https://images.unsplash.com/photo-1563986768609-322da13575f3?w=800&q=80',
            'https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=800&q=80',
            'https://images.unsplash.com/photo-1526304640581-d334cdbbf45e?w=800&q=80',
            'https://images.unsplash.com/photo-1579532537598-459ecdaf39cc?w=800&q=80',
        ],
        'ciencia': [
            'https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=800&q=80',
            'https://images.unsplash.com/photo-1635070041078-e363dbe005cb?w=800&q=80',
            'https://images.unsplash.com/photo-1507668077129-56e32842fceb?w=800&q=80',
            'https://images.unsplash.com/photo-1532094349884-543bc11b234d?w=800&q=80',
            'https://images.unsplash.com/photo-1446776811953-b23d57bd21aa?w=800&q=80',
            'https://images.unsplash.com/photo-1518152006812-edab29b069ac?w=800&q=80',
            'https://images.unsplash.com/photo-1507413245164-6160d8298b31?w=800&q=80',
            'https://images.unsplash.com/photo-1614728894747-a83421e2b9c9?w=800&q=80',
            'https://images.unsplash.com/photo-1564325724739-bae0bd08762c?w=800&q=80',
            'https://images.unsplash.com/photo-1581093458791-9f3c3900df4b?w=800&q=80',
        ],
        'saude': [
            'https://images.unsplash.com/photo-1505751172876-fa1923c5c528?w=800&q=80',
            'https://images.unsplash.com/photo-1584515979956-d9f6e5d09982?w=800&q=80',
            'https://images.unsplash.com/photo-1576091160399-112ba8d25d1d?w=800&q=80',
            'https://images.unsplash.com/photo-1532938911079-1b06ac7ceec7?w=800&q=80',
            'https://images.unsplash.com/photo-1506126613408-eca07ce68773?w=800&q=80',
            'https://images.unsplash.com/photo-1498837167922-ddd27525d352?w=800&q=80',
            'https://images.unsplash.com/photo-1579684385127-1ef15d508118?w=800&q=80',
            'https://images.unsplash.com/photo-1588776814546-1ffcf47267a5?w=800&q=80',
            'https://images.unsplash.com/photo-1535914254981-b5012eebbd15?w=800&q=80',
            'https://images.unsplash.com/photo-1512069772995-ec65ed45afd6?w=800&q=80',
        ],
        'esportes': [
            'https://images.unsplash.com/photo-1508098682722-e99c43a406b2?w=800&q=80',
            'https://images.unsplash.com/photo-1574629810360-7efbbe195018?w=800&q=80',
            'https://images.unsplash.com/photo-1530549387789-4c1017266635?w=800&q=80',
            'https://images.unsplash.com/photo-1461896836934-ffe607ba8211?w=800&q=80',
            'https://images.unsplash.com/photo-1546519638-68e109498ffc?w=800&q=80',
            'https://images.unsplash.com/photo-1517649763962-0c623266ddc0?w=800&q=80',
            'https://images.unsplash.com/photo-1568605117036-5fe5e7bab0b7?w=800&q=80',
            'https://images.unsplash.com/photo-1534438327276-14e5300c3a48?w=800&q=80',
            'https://images.unsplash.com/photo-1552674605-db6ffd4facb5?w=800&q=80',
            'https://images.unsplash.com/photo-1519766304817-4f37bda74a29?w=800&q=80',
        ],
        'entretenimento': [
            'https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?w=800&q=80',
            'https://images.unsplash.com/photo-1514525253161-7a46d19cd819?w=800&q=80',
            'https://images.unsplash.com/photo-1470225620780-dba8ba36b745?w=800&q=80',
            'https://images.unsplash.com/photo-1492684223066-81342ee5ff30?w=800&q=80',
            'https://images.unsplash.com/photo-1460723237483-7a6dc9d0b212?w=800&q=80',
            'https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?w=800&q=80',
            'https://images.unsplash.com/photo-1524712245354-2c4e5e7121c0?w=800&q=80',
            'https://images.unsplash.com/photo-1457369804613-52c61a468e7d?w=800&q=80',
            'https://images.unsplash.com/photo-1518929458119-e5bf444c30f4?w=800&q=80',
            'https://images.unsplash.com/photo-1501386761578-eac5c94b800a?w=800&q=80',
        ],
        'geral': [
            'https://images.unsplash.com/photo-1585829365295-ab7cd400c167?w=800&q=80',
            'https://images.unsplash.com/photo-1588681664899-f142ff2dc9b1?w=800&q=80',
            'https://images.unsplash.com/photo-1477959858617-67f30bc75b82?w=800&q=80',
            'https://images.unsplash.com/photo-1444723121867-7a241cacace9?w=800&q=80',
            'https://images.unsplash.com/photo-1526778548025-fa2f459cd5c1?w=800&q=80',
            'https://images.unsplash.com/photo-1523961131990-5ea7c61b2107?w=800&q=80',
            'https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=800&q=80',
            'https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=800&q=80',
            'https://images.unsplash.com/photo-1521737604893-d14cc237f11d?w=800&q=80',
            'https://images.unsplash.com/photo-1476820865390-c52aeebb9891?w=800&q=80',
        ]
    }

    @classmethod
    def get_diverse_cover(cls, category: str, seed: str = '') -> str:
        cat = (category or 'geral').lower()
        pool = cls.CATEGORY_COVERS.get(cat, cls.CATEGORY_COVERS['geral'])
        idx = abs(hash(seed or 'cover')) % len(pool)
        return pool[idx]

    @staticmethod
    def clean_text(text: Optional[str]) -> str:
        """
        Remove resquícios indesejados de scraping da NewsAPI,
        como HTML residual (ex: <ul>, <li>, Article Information), metadados de agências,
        avisos de assinatura, publicidade, sufixos [+1234 chars] e cortes/truncamentos de texto.
        """
        if not text:
            return ""

        import re
        import html
        t = str(text)

        # Remove sufixos de truncamento da NewsAPI [+123 chars]
        t = re.sub(r'\[\+\d+\s+chars\]', '', t, flags=re.IGNORECASE)

        # Remove parênteses ou colchetes incompletos no final do texto (ex: "(Para comp..." ou "[Leia mais...")
        t = re.sub(r'[\(\[\{][^\)\]\}]*$', '', t)

        # Remove 'Article Information' e blocos de listas aninhadas
        t = re.sub(r'Article\s+Information(?:\s*<[^>]+>.*?</[^>]+>)*', '', t, flags=re.IGNORECASE)
        t = re.sub(r'Article\s+Information', '', t, flags=re.IGNORECASE)

        # Remove listas HTML completas <ul>...</ul> ou tags avulsas
        t = re.sub(r'<ul\b[^>]*>.*?</ul>', '', t, flags=re.IGNORECASE | re.DOTALL)
        t = re.sub(r'<ol\b[^>]*>.*?</ol>', '', t, flags=re.IGNORECASE | re.DOTALL)
        t = re.sub(r'<li\b[^>]*>.*?</li>', '', t, flags=re.IGNORECASE | re.DOTALL)

        # Remove quaisquer outras tags HTML residuais
        t = re.sub(r'<[^>]+>', ' ', t)

        # Remove chamadas de publicidade e avisos comuns de portais
        junk_patterns = [
            r'Pular para o conteúdo[^\.\n]*',
            r'ASSINE\s+[A-Z\s]+',
            r'Continua após publicidade',
            r'Adicione\s+GD\s+às suas fontes preferidas no Google\.?',
            r'Principais destaques',
            r'Crédito,\s*[^.\n]+',
            r'Legenda da foto,\s*[^.\n]+',
            r'The post .*? appeared first on .*',
            r'Leia a versão original em inglês aqui\.?',
            r'© \d{4}-\d{4} [^.\n]+'
        ]
        for pattern in junk_patterns:
            t = re.sub(pattern, '', t, flags=re.IGNORECASE)

        # Decodifica entidades HTML (ex: &nbsp;)
        t = html.unescape(t)
        t = t.replace('\xa0', ' ')

        # Normaliza espaços múltiplos
        t = re.sub(r'[ \t]+', ' ', t)
        t = re.sub(r'\n\s*\n', '\n', t)
        t = t.strip()

        # Remove palavras truncadas ou dangling ellipses no final (ex: ", inform…", " ras…")
        t = re.sub(r'[,;\s]+[a-zA-ZáàâãéèêíïóôõöúçñÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑ]{1,10}[…\.]*$', '.', t)

        # Se terminar em elipse ou pontuação incompleta, busca o último encerramento de frase válido
        if t.endswith(('…', '...', '..')) or (t and t[-1] not in '.!?"\''):
            last_period = max(t.rfind('.'), t.rfind('!'), t.rfind('?'))
            if last_period > 35:
                t = t[:last_period + 1].strip()
            else:
                t = re.sub(r'[\.\s…]+$', '', t).strip()
                words = t.split()
                if len(words) > 5 and len(words[-1]) <= 3 and words[-1].islower():
                    words = words[:-1]
                    t = ' '.join(words)
                if t and t[-1] not in '.!?"\'':
                    t += '.'

        return t.strip()

    @property
    def clean_description(self) -> str:
        """Retorna a descrição higienizada, sem cortes abruptos."""
        return self.clean_text(self.description)

    @property
    def short_summary(self) -> str:
        """
        Retorna no máximo uma pequena frase de resumo concisa e limpa
        especialmente formatada para as prévias de cards do Facebook (og:description).
        """
        import re
        raw = self.clean_text(self.description or self.content or '')
        if not raw:
            return f"Confira a matéria completa sobre '{self.title}' no Explore."

        # Extrai a primeira frase com sentido completo
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', raw) if len(s.strip()) > 15]
        first_sentence = sentences[0] if sentences else raw.strip()

        if len(first_sentence) > 155:
            return first_sentence[:152].rstrip() + '...'
        if len(first_sentence) < 30 and len(sentences) > 1:
            combined = f"{first_sentence} {sentences[1]}".strip()
            if len(combined) <= 155:
                return combined
            return combined[:152].rstrip() + '...'

        return first_sentence

    def get_reading_paragraphs(self) -> list[str]:
        """
        Retorna somente parágrafos presentes no conteúdo real recebido da fonte.
        Nunca completa uma notícia com texto editorial inventado ou reutilizado.
        """
        import unicodedata
        import re

        paragraphs = []
        clean_desc = self.clean_text(self.description)
        clean_raw = self.clean_text(self.content)

        def is_duplicate(candidate: str, reference: str) -> bool:
            if not candidate or not reference:
                return False
            def norm_tokens(s):
                s = unicodedata.normalize('NFKD', s or '').encode('ASCII', 'ignore').decode('utf-8').lower()
                return set(re.findall(r'[a-z0-9]{3,}', s))
            t1 = norm_tokens(candidate)
            t2 = norm_tokens(reference)
            if not t1 or not t2:
                return False
            intersection = t1 & t2
            smaller = min(len(t1), len(t2))
            if smaller == 0:
                return False
            return (len(intersection) / smaller) > 0.60

        # Usa os parágrafos reais do conteúdo, quando a fonte os fornece.
        if clean_raw:
            parts = [p.strip() for p in clean_raw.split('\n') if len(p.strip()) > 35]
            for part in parts:
                cleaned_part = self.clean_text(part)
                if len(cleaned_part) > 40:
                    if not any(is_duplicate(cleaned_part, existing) for existing in paragraphs):
                        if cleaned_part[0].isupper() or any(c in '.!?' for c in cleaned_part[-2:]):
                            paragraphs.append(cleaned_part)

        # RSS e algumas APIs entregam apenas um resumo, sem quebras de linha.
        # Nesse caso, preserva o resumo real em vez de fabricar parágrafos.
        if not paragraphs:
            fallback = clean_raw or clean_desc
            if fallback and len(fallback) > 20:
                paragraphs.append(fallback)

        return paragraphs

    def to_dict(self):
        return {
            'id': self.id,
            'article_hash': self.article_hash,
            'title': self.title,
            'author': self.author,
            'description': self.description,
            'content': self.content,
            'original_url': self.original_url,
            'image_url': self.image_url,
            'source_name': self.source_name,
            'category': self.category,
            'published_at': self.published_at.isoformat() if self.published_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'has_page': self.page is not None
        }

    def __repr__(self):
        return f"<NewsArticle id={self.id} title={self.title[:30]!r}>"
