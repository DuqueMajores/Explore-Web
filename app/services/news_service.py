import logging
import requests
from datetime import datetime, timezone
from typing import List, Dict, Optional, Tuple
from sqlalchemy.exc import IntegrityError
from app.extensions import db
from app.models.news import NewsArticle
from app.models.page import ArticlePage
from app.models.log import AccessLog
from app.services.classifier import classify_text

logger = logging.getLogger(__name__)

SAMPLE_ARTICLES = [
    {
        'title': 'Nova geração de modelos neurais acelera processamento de dados e miniaturização',
        'author': 'Redação Tecnologia',
        'description': 'Pesquisadores revelam arquiteturas capazes de operar localmente em dispositivos móveis e sistemas embarcados sem depender de servidores em nuvem.',
        'content': 'A busca por maior privacidade e latência reduzida impulsionou o desenvolvimento de novas técnicas de quantização e poda de pesos em redes neurais. Os novos modelos conseguem executar inferência veloz utilizando apenas memória RAM e armazenamento local, dispensando conexões constantes à internet e eliminando os custos de hospedagem centralizada.',
        'original_url': 'https://exemplo.com.br/tecnologia/geracao-modelos-locais',
        'image_url': 'https://images.unsplash.com/photo-1518770660439-4636190af475?w=800&q=80',
        'source_name': 'Tech Local Brasil',
        'category': 'tecnologia',
        'published_at': '2026-10-01T14:30:00Z'
    },
    {
        'title': 'Bancos centrais ampliam testes de liquidação digital com bancos de dados relacionais distribuídos',
        'author': 'Carlos Albuquerque',
        'description': 'Mercado financeiro avalia resiliência de soluções que combinam consistência ACID clássica com alta disponibilidade local.',
        'content': 'Em um cenário de volatilidade cambial e novas diretrizes de segurança da informação, instituições financeiras reforçam a importância de bancos de dados que garantem transações completas e auditabilidade local imediata. O estudo destaca a confiabilidade de esquemas bem indexados e transações atômicas.',
        'original_url': 'https://exemplo.com.br/negocios/bancos-centrais-liquidacao-digital',
        'image_url': 'https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=800&q=80',
        'source_name': 'Gazeta Econômica',
        'category': 'negocios',
        'published_at': '2026-10-01T12:00:00Z'
    },
    {
        'title': 'Telescópio orbital identifica compostos orgânicos na atmosfera de exoplaneta rochoso',
        'author': 'Dra. Mariana Santos',
        'description': 'Descoberta astronômica traz pistas valiosas sobre a formação de atmosferas estáveis em sistemas estelares vizinhos.',
        'content': 'A espectroscopia de alta resolução permitiu mapear moléculas de metano e dióxido de carbono em concentrações que intrigam astrofísicos. As observações continuarão nos próximos meses para confirmar se a presença desses compostos decorre de processos vulcânicos ou fotoquímicos.',
        'original_url': 'https://exemplo.com.br/ciencia/exoplaneta-atmosfera-organica',
        'image_url': 'https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=800&q=80',
        'source_name': 'Observatório Científico',
        'category': 'ciencia',
        'published_at': '2026-09-30T18:45:00Z'
    },
    {
        'title': 'Estudo clínico comprova benefícios do sono regular e dieta balanceada no sistema imunológico',
        'author': 'Equipe de Saúde Coletiva',
        'description': 'Pesquisa longitudinal com mais de 10 mil participantes demonstra redução de 40% em infecções virais sazonais.',
        'content': 'Manter horários consistentes de repouso e priorizar alimentos ricos em antioxidantes modula positivamente a produção de linfócitos T e citocinas protetoras. Especialistas reforçam que a prevenção cotidiana é a ferramenta mais custo-efetiva para a saúde pública.',
        'original_url': 'https://exemplo.com.br/saude/estudo-sono-imunidade',
        'image_url': 'https://images.unsplash.com/photo-1505751172876-fa1923c5c528?w=800&q=80',
        'source_name': 'Portal Saúde & Vida',
        'category': 'saude',
        'published_at': '2026-09-29T09:15:00Z'
    },
    {
        'title': 'Festival internacional de cinema independente premia obras que discutem memória e tecnologia',
        'author': 'Beatriz Lima',
        'description': 'Cineastas de mais de trinta países apresentam narrativas visuais sobre o impacto das redes nas relações familiares.',
        'content': 'A mostra competitiva destacou produções que exploram o arquivo fotográfico, a passagem do tempo e as transformações urbanas. O grande vencedor da noite foi um documentário filmado integralmente com equipamentos leves de baixo consumo.',
        'original_url': 'https://exemplo.com.br/entretenimento/festival-cinema-independente',
        'image_url': 'https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?w=800&q=80',
        'source_name': 'CineRevista',
        'category': 'entretenimento',
        'published_at': '2026-09-28T21:10:00Z'
    },
    {
        'title': 'Final emocionante do campeonato nacional mobiliza torcedores em arenas pelo país',
        'author': 'Lucas Ferreira',
        'description': 'Com virada nos acréscimos, equipe garante o título em jogo de ritmo intenso e defesas espetaculares.',
        'content': 'A partida decisiva foi marcada por disciplina tática e apoio fervoroso das arquibancadas. O gol decisivo aos 49 minutos do segundo tempo consagrou a melhor campanha do torneio e levou a torcida ao delírio.',
        'original_url': 'https://exemplo.com.br/esportes/final-campeonato-emocionante',
        'image_url': 'https://images.unsplash.com/photo-1508098682722-e99c43a406b2?w=800&q=80',
        'source_name': 'Esporte em Foco',
        'category': 'esportes',
        'published_at': '2026-09-27T17:00:00Z'
    },
    {
        'title': 'Avanço na computação quântica reduz taxas de erro térmico em qubits de silício',
        'author': 'Rodrigo Valente',
        'description': 'Engenheiros de semicondutores demonstram portas lógicas quânticas estáveis acima de 1 Kelvin, facilitando refrigeração industrial.',
        'content': 'A nova abordagem utiliza dopagem precisa de fósforo em matriz de silício cristalino purificado, operando a temperaturas significativamente superiores ao zero absoluto clássico. A redução de custos com hélio líquido deve acelerar protótipos industriais em até quatro anos.',
        'original_url': 'https://exemplo.com.br/tecnologia/computacao-quantica-silicio',
        'image_url': 'https://images.unsplash.com/photo-1635070041078-e363dbe005cb?w=800&q=80',
        'source_name': 'Quantum Insights',
        'category': 'tecnologia',
        'published_at': '2026-09-26T15:20:00Z'
    },
    {
        'title': 'Comércio exterior brasileiro bate recorde com expansão de produtos manufaturados de alto valor',
        'author': 'Renata Carvalho',
        'description': 'Balança comercial encerra o trimestre com superávit histórico impulsionado por maquinário de precisão e insumos agrícolas.',
        'content': 'A diversificação das exportações para mercados da América Latina e do Sudeste Asiático mitigou oscilações pontuais em commodities primárias. O setor fabril nacional reportou incremento de 18% em contratos bilaterais de longo prazo.',
        'original_url': 'https://exemplo.com.br/negocios/balanca-comercial-recorde',
        'image_url': 'https://images.unsplash.com/photo-1578575437130-527eed3abbec?w=800&q=80',
        'source_name': 'Comércio & Indústria',
        'category': 'negocios',
        'published_at': '2026-09-25T11:40:00Z'
    },
    {
        'title': 'Pesquisa revela regeneração acelerada de tecidos cartilaginosos com biopolímeros marinhos',
        'author': 'Dra. Gabriela Fontes',
        'description': 'Bioengenharia celular desenvolve hidrogel bioativo derivado de algas que acelera cicatrização pós-traumática.',
        'content': 'Em testes de laboratório, a estrutura tridimensional do hidrogel serviu como arcabouço ideal para a proliferação de condrócitos humanos. O tratamento demonstrou zero rejeição imunológica e restauração funcional em menos de 8 semanas.',
        'original_url': 'https://exemplo.com.br/saude/biopolimeros-regeneracao-tecidual',
        'image_url': 'https://images.unsplash.com/photo-1532187863486-abf9dbad1b69?w=800&q=80',
        'source_name': 'BioMed Journal',
        'category': 'saude',
        'published_at': '2026-09-24T10:15:00Z'
    },
    {
        'title': 'Missão espacial robótica colhe amostras inéditas do manto lunar no polo sul',
        'author': 'Prof. Arthur Nogueira',
        'description': 'Módulo não tripulado perfura cinco metros abaixo da superfície lunar em busca de água fóssil e minerais raros.',
        'content': 'Os dados telemétricos confirmaram a integridade das brocas de diamante e o acondicionamento seguro em cápsulas criogênicas. A carga retornará à Terra para datação isotópica nos principais laboratórios globais.',
        'original_url': 'https://exemplo.com.br/ciencia/missao-lunar-polo-sul',
        'image_url': 'https://images.unsplash.com/photo-1614728894747-a83421e2b9c9?w=800&q=80',
        'source_name': 'Cosmos Brasil',
        'category': 'ciencia',
        'published_at': '2026-09-23T14:50:00Z'
    },
    {
        'title': 'Novos centros culturais revitalizam patrimônio histórico em capitais brasileiras',
        'author': 'Juliana Paes',
        'description': 'Edifícios centenários são restaurados e convertidos em espaços de convivência, galerias de arte e teatros abertos.',
        'content': 'A integração de arquitetura bioclimática e tecnologias interativas permitiu criar polos de atração turística e artística. O modelo de gestão cooperativa assegura sustentabilidade financeira e programação gratuita continuada.',
        'original_url': 'https://exemplo.com.br/entretenimento/revitalizacao-centros-culturais',
        'image_url': 'https://images.unsplash.com/photo-1513694203232-719a280e022f?w=800&q=80',
        'source_name': 'Arte & Cidade',
        'category': 'entretenimento',
        'published_at': '2026-09-22T19:30:00Z'
    },
    {
        'title': 'Inovações em aerodinâmica e biometria elevam rendimento de atletas nos esportes aquáticos',
        'author': 'Thiago Mendonça',
        'description': 'Sensores subaquáticos de pressão e trajes desenvolvidos com fluidodinâmica computacional redefinem recordes.',
        'content': 'A captura de movimento em tempo real sob a água permitiu que nadadores e remadores corrigissem microdesvios na braçada instantaneamente. Especialistas apontam que a tecnologia democratizou análises que antes demandavam túneis de vento dispendiosos.',
        'original_url': 'https://exemplo.com.br/esportes/aerodinamica-esportes-aquaticos',
        'image_url': 'https://images.unsplash.com/photo-1530549387789-4c1017266635?w=800&q=80',
        'source_name': 'Ciência do Esporte',
        'category': 'esportes',
        'published_at': '2026-09-21T08:00:00Z'
    }
]

class NewsService:
    """Gerencia a coleta e sincronização de notícias no SQLite local."""

    def __init__(self, api_key: str, base_url: str = 'https://newsapi.org/v2'):
        self.api_key = api_key
        self.base_url = base_url

    def fetch_and_store_from_api(self, category: Optional[str] = None, query: Optional[str] = None) -> Tuple[int, str]:
        """
        Consulta a NewsAPI e salva/atualiza as matérias diretamente no SQLite.
        Retorna (quantidade_salva, mensagem_status).
        """
        if not self.api_key or self.api_key == 'sua_chave_newsapi_aqui':
            # Sem chave válida, semeia matérias padrão
            count = self.seed_initial_articles()
            return count, "Chave NewsAPI ausente; dados demonstrativos locais sincronizados no SQLite."

        try:
            # Consultar top headlines do Brasil ou busca por query
            if query:
                url = f"{self.base_url}/everything"
                params = {
                    'q': query,
                    'language': 'pt',
                    'sortBy': 'publishedAt',
                    'pageSize': 100,
                    'apiKey': self.api_key
                }
            else:
                url = f"{self.base_url}/top-headlines"
                params = {
                    'country': 'br',
                    'pageSize': 100,
                    'apiKey': self.api_key
                }
                if category and category != 'todas' and category != 'geral':
                    # Mapear para categorias aceitas pela NewsAPI
                    api_cat_map = {
                        'tecnologia': 'technology',
                        'negocios': 'business',
                        'ciencia': 'science',
                        'saude': 'health',
                        'entretenimento': 'entertainment',
                        'esportes': 'sports'
                    }
                    if category in api_cat_map:
                        params['category'] = api_cat_map[category]

            response = requests.get(url, params=params, timeout=12)
            data = response.json()

            if response.status_code != 200 or data.get('status') != 'ok':
                err_msg = data.get('message', f'HTTP {response.status_code}')
                logger.warning(f"NewsAPI erro: {err_msg}. Utilizando base local.")
                count = self.seed_initial_articles()
                return count, f"Aviso NewsAPI: {err_msg}. Matérias locais preservadas no SQLite."

            raw_articles = data.get('articles', [])
            
            # Se top-headlines retornar vazio, busca no endpoint everything com notícias em tempo real em português
            if not raw_articles and not query:
                cat_query = category if category and category != 'todas' else 'notícias Brasil mundo'
                everything_url = f"{self.base_url}/everything"
                ev_params = {
                    'q': cat_query,
                    'language': 'pt',
                    'sortBy': 'publishedAt',
                    'pageSize': 100,
                    'apiKey': self.api_key
                }
                ev_resp = requests.get(everything_url, params=ev_params, timeout=12)
                if ev_resp.status_code == 200:
                    ev_data = ev_resp.json()
                    raw_articles = ev_data.get('articles', [])

            saved_count = 0

            for item in raw_articles:
                title = item.get('title')
                original_url = item.get('url')
                if not title or not original_url or '[Removed]' in title:
                    continue

                clean_orig_url = NewsArticle.clean_url(original_url)
                article_hash = NewsArticle.generate_hash(clean_orig_url, title)
                existing = NewsArticle.query.filter(
                    (NewsArticle.article_hash == article_hash) |
                    (NewsArticle.original_url == clean_orig_url) |
                    (NewsArticle.original_url == original_url) |
                    (NewsArticle.title == title)
                ).first()

                pub_at = None
                pub_str = item.get('publishedAt')
                if pub_str:
                    try:
                        pub_at = datetime.fromisoformat(pub_str.replace('Z', '+00:00'))
                    except Exception:
                        pub_at = None

                src_name = item.get('source', {}).get('name', 'Fonte Externa')
                desc = NewsArticle.clean_text(item.get('description') or '')
                raw_content = NewsArticle.clean_text(item.get('content') or desc)
                cat = category or classify_text(title, desc, src_name)
                assigned_img = item.get('urlToImage') or NewsArticle.get_diverse_cover(cat, seed=title)

                if existing:
                    # Atualiza dados se necessário
                    existing.title = title
                    existing.description = desc
                    existing.content = raw_content or existing.content
                    if item.get('urlToImage'):
                        existing.image_url = item.get('urlToImage')
                    elif not existing.image_url:
                        existing.image_url = assigned_img
                    existing.category = cat
                else:
                    new_art = NewsArticle(
                        article_hash=article_hash,
                        title=title,
                        author=item.get('author') or 'Redação',
                        description=desc,
                        content=raw_content,
                        original_url=clean_orig_url,
                        image_url=assigned_img,
                        source_name=src_name,
                        category=cat,
                        published_at=pub_at or datetime.now(timezone.utc)
                    )
                    db.session.add(new_art)
                    saved_count += 1

            db.session.commit()
            return saved_count, f"{saved_count} novas notícias salvas com sucesso no SQLite."

        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao consultar NewsAPI: {e}")
            count = self.seed_initial_articles()
            return count, f"Falha na conexão com NewsAPI ({str(e)}). Carregadas notícias locais do SQLite."

    G1_RSS_FEEDS = {
        'geral': 'https://g1.globo.com/rss/g1/',
        'tecnologia': 'https://g1.globo.com/rss/g1/tecnologia/',
        'negocios': 'https://g1.globo.com/rss/g1/economia/',
        'ciencia': 'https://g1.globo.com/rss/g1/ciencia-e-saude/',
        'saude': 'https://g1.globo.com/rss/g1/ciencia-e-saude/',
        'entretenimento': 'https://g1.globo.com/rss/g1/pop-arte/',
        'esportes': 'https://ge.globo.com/rss/ge/'
    }

    def fetch_and_store_from_rss(self, category: Optional[str] = None) -> Tuple[int, str]:
        """
        Coleta notícias em tempo real diretamente dos feeds RSS oficiais em português
        (G1 Globo / GE Esportes), garantindo atualização contínua, sem limites de cota
        e matérias 100% categorizadas para cada seção do Explore.
        """
        import xml.etree.ElementTree as ET
        import re
        from email.utils import parsedate_to_datetime

        cat_key = (category or 'geral').lower()
        rss_url = self.G1_RSS_FEEDS.get(cat_key, 'https://g1.globo.com/rss/g1/')

        try:
            resp = requests.get(rss_url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}, timeout=8)
            if resp.status_code != 200:
                return 0, f"RSS HTTP {resp.status_code}"

            root = ET.fromstring(resp.content)
            items = root.findall('.//item')
            saved_count = 0

            for item in items:
                title_el = item.find('title')
                link_el = item.find('link')
                desc_el = item.find('description')
                pub_el = item.find('pubDate')

                title = title_el.text.strip() if title_el is not None and title_el.text else ''
                original_url = link_el.text.strip() if link_el is not None and link_el.text else ''

                if not title or not original_url:
                    continue

                # Extrai capa em alta resolução do item
                img_url = None
                for child in item:
                    if 'content' in child.tag and 'url' in child.attrib:
                        img_url = child.attrib['url']
                        break
                if not img_url and desc_el is not None and desc_el.text:
                    m = re.search(r'<img[^>]+src=[\"\']([^\"\']+)[\"\']', desc_el.text)
                    if m:
                        img_url = m.group(1)

                # Limpa descrição
                raw_desc = desc_el.text if desc_el is not None and desc_el.text else ''
                clean_desc = NewsArticle.clean_text(raw_desc)

                pub_at = None
                if pub_el is not None and pub_el.text:
                    try:
                        pub_dt = parsedate_to_datetime(pub_el.text)
                        if pub_dt.tzinfo is None:
                            pub_at = pub_dt.replace(tzinfo=timezone.utc)
                        else:
                            pub_at = pub_dt.astimezone(timezone.utc)
                    except Exception:
                        pub_at = None

                clean_orig_url = NewsArticle.clean_url(original_url)
                article_hash = NewsArticle.generate_hash(clean_orig_url, title)
                existing = NewsArticle.query.filter(
                    (NewsArticle.article_hash == article_hash) |
                    (NewsArticle.original_url == clean_orig_url) |
                    (NewsArticle.original_url == original_url) |
                    (NewsArticle.title == title)
                ).first()

                src_name = 'GE Esportes' if cat_key == 'esportes' else 'G1 Globo'
                assigned_img = img_url or NewsArticle.get_diverse_cover(cat_key, seed=title)

                if existing:
                    existing.title = title
                    existing.description = clean_desc or existing.description
                    if img_url:
                        existing.image_url = img_url
                    elif not existing.image_url:
                        existing.image_url = assigned_img
                    existing.category = cat_key
                else:
                    new_art = NewsArticle(
                        article_hash=article_hash,
                        title=title,
                        author=src_name,
                        description=clean_desc,
                        content=clean_desc,
                        original_url=clean_orig_url,
                        image_url=assigned_img,
                        source_name=src_name,
                        category=cat_key,
                        published_at=pub_at or datetime.now(timezone.utc)
                    )
                    db.session.add(new_art)
                    saved_count += 1

            db.session.commit()
            return saved_count, f"{saved_count} matérias atualizadas via RSS na categoria {cat_key}."
        except Exception as e:
            db.session.rollback()
            logger.warning(f"Erro ao buscar RSS para {cat_key}: {e}")
            return 0, str(e)

    def sync_all_categories(self) -> Tuple[int, str]:
        """
        Sincroniza múltiplos lotes de notícias de todas as categorias tanto via
        RSS em tempo real quanto via NewsAPI, garantindo atualização instantânea 24/7.
        """
        categories = ['geral', 'tecnologia', 'negocios', 'ciencia', 'saude', 'esportes', 'entretenimento']
        total_saved = 0

        # 1. Sincroniza via RSS (em tempo real, zero limites de cota)
        for cat in categories:
            try:
                saved_rss, _ = self.fetch_and_store_from_rss(category=cat)
                total_saved += saved_rss
            except Exception as ex:
                logger.warning(f"Erro RSS na categoria {cat}: {ex}")

        # 2. Sincroniza via NewsAPI se chave disponível
        if self.api_key and self.api_key != 'sua_chave_newsapi_aqui':
            for cat in categories:
                try:
                    saved, _ = self.fetch_and_store_from_api(category=cat)
                    total_saved += saved
                except Exception as ex:
                    logger.warning(f"Erro NewsAPI na categoria {cat}: {ex}")

        return total_saved, f"{total_saved} matérias sincronizadas com sucesso em todas as categorias."

    def seed_initial_articles(self) -> int:
        """Garante que haja matérias iniciais no SQLite para visualização e testes."""
        inserted = 0
        for item in SAMPLE_ARTICLES:
            art_hash = NewsArticle.generate_hash(item['original_url'], item['title'])
            existing = NewsArticle.query.filter_by(article_hash=art_hash).first()
            if not existing:
                try:
                    pub_at = datetime.fromisoformat(item['published_at'].replace('Z', '+00:00'))
                except Exception:
                    pub_at = datetime.now(timezone.utc)

                art = NewsArticle(
                    article_hash=art_hash,
                    title=item['title'],
                    author=item['author'],
                    description=item['description'],
                    content=item['content'],
                    original_url=item['original_url'],
                    image_url=item['image_url'],
                    source_name=item['source_name'],
                    category=item['category'],
                    published_at=pub_at
                )
                db.session.add(art)
                inserted += 1

        if inserted > 0:
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()

        return inserted

    def get_or_create_page_for_article(self, article: NewsArticle, reader_id: str, ip: str = '', user_agent: str = '') -> Tuple[ArticlePage, bool]:
        """
        Cria ou atualiza os metadados da página e registra o acesso anônimo.
        A rota Flask materializa o HTML no primeiro acesso; os registros não expiram.
        Retorna (página, foi_criada).
        """
        was_recreated = False
        page = ArticlePage.query.filter_by(news_id=article.id).first()

        if page is None:
            # Metadados ainda não existem para esta matéria.
            page = ArticlePage.create_for_article(article)
            db.session.add(page)
            was_recreated = True
        else:
            # Página já existe: atualiza o último acesso para UTC atual
            page.register_access()

        # Cria registro anônimo de acesso associado à página
        log = AccessLog(
            reader_id=reader_id,
            user_agent=user_agent[:250] if user_agent else 'Unknown',
            ip_hash=AccessLog.hash_ip(ip)
        )
        page.access_logs.append(log)

        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            page = ArticlePage.query.filter_by(news_id=article.id).first()

        return page, was_recreated
