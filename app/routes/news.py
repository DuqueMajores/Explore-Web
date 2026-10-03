import uuid
from flask import Blueprint, render_template, request, redirect, url_for, flash, make_response, current_app
from app.extensions import db
from app.models.news import NewsArticle
from app.models.page import ArticlePage
from app.services.news_service import NewsService

news_bp = Blueprint('news', __name__)

def get_or_set_reader_id(response=None) -> str:
    """
    Obtém ou gera o identificador anônimo de leitor através de um cookie HTTP.
    O leitor não precisa criar conta nem fazer login; o identificador serve
    apenas para registrar atividade única no banco SQLite do servidor.
    """
    cookie_name = current_app.config.get('READER_COOKIE_NAME', 'noticias_reader_id')
    reader_id = request.cookies.get(cookie_name)
    if not reader_id:
        reader_id = str(uuid.uuid4())
        if response:
            max_age = current_app.config.get('READER_COOKIE_MAX_AGE', 31536000)
            response.set_cookie(cookie_name, reader_id, max_age=max_age, httponly=True, samesite='Lax')
    return reader_id

@news_bp.route('/')
def index():
    """Página inicial com listagem das notícias obtidas da NewsAPI/SQLite."""
    category = request.args.get('categoria', 'todas').lower()
    search_query = request.args.get('q', '').strip()

    query = NewsArticle.query

    if category and category != 'todas':
        query = query.filter(NewsArticle.category == category)

    if search_query:
        query = query.filter(
            (NewsArticle.title.ilike(f'%{search_query}%')) |
            (NewsArticle.description.ilike(f'%{search_query}%'))
        )

    # Carrega o primeiro lote de artigos (1 destaque + 6 no grid) para renderização imediata rápida
    initial_limit = 7
    total_matching = query.count()
    articles = query.order_by(NewsArticle.published_at.desc().nullslast(), NewsArticle.id.desc()).limit(initial_limit).all()

    # Se a base estiver totalmente vazia no primeiro acesso, semeia matérias padrão
    if not articles and not search_query and category == 'todas':
        news_svc = NewsService(current_app.config['NEWS_API_KEY'], current_app.config['NEWS_API_BASE_URL'])
        news_svc.seed_initial_articles()
        total_matching = query.count()
        articles = NewsArticle.query.order_by(NewsArticle.published_at.desc()).limit(initial_limit).all()

    categories = [
        ('todas', 'Todas'),
        ('tecnologia', 'Tecnologia'),
        ('negocios', 'Negócios'),
        ('ciencia', 'Ciência'),
        ('saude', 'Saúde'),
        ('entretenimento', 'Entretenimento'),
        ('esportes', 'Esportes'),
        ('geral', 'Geral')
    ]

    # Estatísticas rápidas
    total_articles = NewsArticle.query.count()
    active_pages = ArticlePage.query.count()
    has_more_initial = total_matching > len(articles)

    response = make_response(render_template(
        'index.html',
        articles=articles,
        current_category=category,
        categories=categories,
        search_query=search_query,
        total_articles=total_articles,
        active_pages=active_pages,
        has_more_initial=has_more_initial,
        total_matching=total_matching
    ))
    # Assegura cookie de identificação anônima
    get_or_set_reader_id(response)
    return response

@news_bp.route('/noticia/<slug>')
def view_article_by_slug(slug):
    """
    Exibe a página interna da notícia.
    REQUISITO CRUCIAL:
    1. Verifica se já existe um registro correspondente em 'article_pages' no SQLite.
    2. Se não existir (ex: foi excluído após 5 dias sem acesso), busca o artigo em 'news_articles'
       pelo ID ou slug e recria o registro da página automaticamente!
    3. Registra o acesso do leitor anônimo e atualiza a data do último acesso em UTC.
    """
    cookie_name = current_app.config.get('READER_COOKIE_NAME', 'noticias_reader_id')
    reader_id = request.cookies.get(cookie_name) or str(uuid.uuid4())
    needs_cookie = request.cookies.get(cookie_name) is None

    # Tenta localizar página pelo slug
    page = ArticlePage.query.filter_by(slug=slug).first()
    was_recreated = (request.args.get('recriada') == '1')

    if page:
        article = page.article
        page.register_access()
        # Registra log de acesso
        from app.models.log import AccessLog
        log = AccessLog(
            page_id=page.id,
            reader_id=reader_id,
            user_agent=request.headers.get('User-Agent', '')[:250],
            ip_hash=AccessLog.hash_ip(request.remote_addr or '')
        )
        db.session.add(log)
        db.session.commit()
    else:
        # A página NÃO EXISTE ou foi EXCLUÍDA pela rotina de limpeza de 5 dias!
        # Extrair o ID do artigo a partir do sufixo do slug (ex: "titulo-da-materia-12")
        article_id = None
        try:
            parts = slug.split('-')
            article_id = int(parts[-1])
        except (ValueError, IndexError):
            article_id = None

        article = None
        if article_id:
            article = db.session.get(NewsArticle, article_id)

        if not article:
            flash("Matéria não encontrada no banco SQLite local.", "error")
            return redirect(url_for('news.index'))

        # RECRIA AUTOMATICAMENTE A PÁGINA A PARTIR DOS DADOS DO ARTIGO NO SQLITE!
        news_svc = NewsService(current_app.config['NEWS_API_KEY'], current_app.config['NEWS_API_BASE_URL'])
        page, was_recreated = news_svc.get_or_create_page_for_article(
            article=article,
            reader_id=reader_id,
            ip=request.remote_addr or '',
            user_agent=request.headers.get('User-Agent', '')
        )

    # Busca chamados para notícias semelhantes da mesma categoria ou recentes
    similar_articles = NewsArticle.query.filter(
        NewsArticle.id != article.id,
        NewsArticle.category == article.category
    ).order_by(NewsArticle.published_at.desc()).limit(3).all()

    if len(similar_articles) < 3:
        existing_ids = [article.id] + [a.id for a in similar_articles]
        complement = NewsArticle.query.filter(
            ~NewsArticle.id.in_(existing_ids)
        ).order_by(NewsArticle.published_at.desc()).limit(3 - len(similar_articles)).all()
        similar_articles.extend(complement)

    response = make_response(render_template(
        'article.html',
        article=article,
        page=page,
        was_recreated=was_recreated,
        reader_id=reader_id,
        similar_articles=similar_articles
    ))

    if needs_cookie:
        max_age = current_app.config.get('READER_COOKIE_MAX_AGE', 31536000)
        response.set_cookie(cookie_name, reader_id, max_age=max_age, httponly=True, samesite='Lax')

    return response

@news_bp.route('/noticia/abrir/<int:article_id>')
def open_by_id(article_id):
    """
    Ponto de entrada quando um leitor clica no card da matéria.
    Verifica se a página interna existe no SQLite. Se não existir ou tiver sido excluída,
    cria/recria o registro e redireciona para a URL amigável dinâmica.
    """
    article = db.get_or_404(NewsArticle, article_id)
    cookie_name = current_app.config.get('READER_COOKIE_NAME', 'noticias_reader_id')
    reader_id = request.cookies.get(cookie_name) or str(uuid.uuid4())

    news_svc = NewsService(current_app.config['NEWS_API_KEY'], current_app.config['NEWS_API_BASE_URL'])
    page, was_recreated = news_svc.get_or_create_page_for_article(
        article=article,
        reader_id=reader_id,
        ip=request.remote_addr or '',
        user_agent=request.headers.get('User-Agent', '')
    )

    resp = redirect(url_for('news.view_article_by_slug', slug=page.slug, recriada=1 if was_recreated else None))
    if request.cookies.get(cookie_name) is None:
        max_age = current_app.config.get('READER_COOKIE_MAX_AGE', 31536000)
        resp.set_cookie(cookie_name, reader_id, max_age=max_age, httponly=True, samesite='Lax')
    return resp

@news_bp.route('/sincronizar', methods=['POST'])
def sync_news():
    """Aciona sincronização manual com a NewsAPI buscando o máximo de matérias."""
    category = request.form.get('category')
    news_svc = NewsService(current_app.config['NEWS_API_KEY'], current_app.config['NEWS_API_BASE_URL'])
    if not category or category == 'todas':
        count, msg = news_svc.sync_all_categories()
    else:
        count, msg = news_svc.fetch_and_store_from_api(category=category)
    flash(msg, 'success' if count > 0 else 'info')
    return redirect(url_for('news.index'))
