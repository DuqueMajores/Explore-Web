import os
from datetime import datetime, timezone
from flask import Blueprint, jsonify, current_app, request, url_for
from app.models.news import NewsArticle
from app.models.page import ArticlePage
from app.models.log import AccessLog, MaintenanceLog
from app.services.backup_service import BackupService
from app.tasks.cleanup import clean_expired_pages

api_bp = Blueprint('api', __name__, url_prefix='/api')

def format_time_ago(dt):
    if dt is None:
        return '—'
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    diff = now - dt
    seconds = diff.total_seconds()
    if seconds < 60:
        return 'agora mesmo'
    elif seconds < 3600:
        mins = int(seconds // 60)
        return f'há {mins} min' if mins > 1 else 'há 1 min'
    elif seconds < 86400:
        hours = int(seconds // 3600)
        return f'há {hours} h' if hours > 1 else 'há 1 h'
    elif seconds < 172800:
        return 'ontem'
    else:
        days = int(seconds // 86400)
        return f'há {days} dias'


def unique_articles(articles):
    """Remove matérias repetidas por título ou imagem antes da paginação."""
    seen_titles, seen_images, unique = set(), set(), []
    for article in articles:
        title_key = ' '.join((article.title or '').lower().split())
        image_key = (article.image_url or '').strip().lower()
        if title_key and title_key in seen_titles:
            continue
        if image_key and image_key in seen_images:
            continue
        if title_key:
            seen_titles.add(title_key)
        if image_key:
            seen_images.add(image_key)
        unique.append(article)
    return unique

@api_bp.route('/noticias')
def get_articles_feed():
    """
    Endpoint para rolagem infinita.
    Retorna os próximos cards de notícias em JSON com paginação,
    permitindo ao cliente carregar novidades dinamicamente conforme rola a página.
    """
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 12, type=int)
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

    ordered_articles = query.order_by(
        NewsArticle.published_at.desc().nullslast(),
        NewsArticle.id.desc()
    ).all()
    unique = unique_articles(ordered_articles)
    total = len(unique)
    offset = (page - 1) * per_page
    articles = unique[offset:offset + per_page]

    # Se o leitor estiver se aproximando do fim dos artigos salvos localmente,
    # busca automaticamente novas matérias em tempo real da NewsAPI e persiste no SQLite
    if (offset + len(articles)) >= total:
        try:
            from app.services.news_service import NewsService
            api_key = current_app.config.get('NEWS_API_KEY')
            base_url = current_app.config.get('NEWS_API_BASE_URL')
            if api_key and api_key != 'sua_chave_newsapi_aqui':
                news_svc = NewsService(api_key, base_url)
                if search_query:
                    news_svc.fetch_and_store_from_api(query=search_query)
                elif category and category != 'todas':
                    news_svc.fetch_and_store_from_api(category=category)
                else:
                    news_svc.fetch_and_store_from_api()

                # Re-executa query com novos artigos
                ordered_articles = query.order_by(
                    NewsArticle.published_at.desc().nullslast(),
                    NewsArticle.id.desc()
                ).all()
                unique = unique_articles(ordered_articles)
                total = len(unique)
                articles = unique[offset:offset + per_page]
        except Exception as e:
            current_app.logger.warning(f"Auto-fetch NewsAPI no scroll: {e}")

    items = []
    seen_titles = set()
    seen_urls = set()
    seen_images = set()

    for a in articles:
        clean_u = NewsArticle.clean_url(a.original_url) if hasattr(NewsArticle, 'clean_url') else a.original_url
        norm_t = (a.title or '').strip().lower()
        if clean_u in seen_urls or norm_t in seen_titles:
            continue
        seen_urls.add(clean_u)
        seen_titles.add(norm_t)

        current_img = a.image_url or ''
        if not current_img or current_img in seen_images or 'photo-1504711434969-e33886168f5c' in current_img:
            cover_img = NewsArticle.get_diverse_cover(a.category, seed=f"{a.id}-{a.title}")
        else:
            cover_img = current_img
        seen_images.add(cover_img)

        slug = a.page.slug if a.page else f"noticia-{a.id}"
        items.append({
            'id': a.id,
            'slug': slug,
            'title': a.title,
            'category': a.category,
            'author': a.author or a.source_name or 'Explore',
            'description': a.description or '',
            'clean_description': a.clean_description,
            'short_summary': a.short_summary,
            'image_url': cover_img,
            'time_ago': format_time_ago(a.published_at),
            'open_url': url_for('news.open_by_id', article_id=a.id)
        })

    has_more = (offset + len(articles)) < total

    return jsonify({
        'articles': items,
        'page': page,
        'has_more': has_more,
        'total': total
    })

@api_bp.route('/stats')
def stats():
    """Retorna dados de monitoramento do banco SQLite e da aplicação."""
    db_path = BackupService.get_db_path()
    size_bytes = os.path.getsize(db_path) if os.path.exists(db_path) else 0

    return jsonify({
        'database': {
            'type': 'SQLite (Local Baseado em Arquivo)',
            'path': db_path,
            'exists': os.path.exists(db_path),
            'size_kb': round(size_bytes / 1024, 2),
            'cloud_dependencies': 'Nenhuma (Zero Firebase, Zero Nuvem)'
        },
        'counts': {
            'news_articles': NewsArticle.query.count(),
            'article_pages': ArticlePage.query.count(),
            'access_logs': AccessLog.query.count()
        },
        'policy': {
            'expiration_days': current_app.config.get('PAGE_EXPIRATION_DAYS', 5),
            'auto_cleanup_rule': 'Páginas sem acesso por 5 dias consecutivos são excluídas do SQLite e recriadas dinamicamente se acessadas novamente.'
        }
    })

@api_bp.route('/cleanup', methods=['POST'])
def run_cleanup():
    """Aciona a limpeza via requisição de API."""
    checked, deleted, msg = clean_expired_pages(current_app, execution_type='api')
    return jsonify({
        'status': 'success',
        'pages_checked': checked,
        'pages_deleted': deleted,
        'message': msg
    })
