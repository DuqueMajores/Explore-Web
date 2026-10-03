import os
import logging
from datetime import datetime, timezone
from flask import Flask
from config import config_by_name
from app.extensions import db

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

def create_app(config_name='default'):
    """Fábrica de aplicação Flask com persistência local SQLite."""
    app = Flask(__name__)
    cfg = config_by_name.get(config_name, config_by_name['default'])
    app.config.from_object(cfg)

    # Inicializar extensões
    db.init_app(app)

    # Registrar Blueprints
    from app.routes.news import news_bp
    from app.routes.admin import admin_bp
    from app.routes.api import api_bp

    app.register_blueprint(news_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)

    # Filtros úteis para os templates Jinja2
    @app.template_filter('datetime_format')
    def format_datetime(value, format='%d/%m/%Y às %H:%M'):
        if value is None:
            return '—'
        if isinstance(value, str):
            try:
                value = datetime.fromisoformat(value.replace('Z', '+00:00'))
            except Exception:
                return value
        # Converter para formato amigável
        return value.strftime(format)

    @app.template_filter('time_ago')
    def time_ago(value):
        if value is None:
            return '—'
        if isinstance(value, str):
            try:
                value = datetime.fromisoformat(value.replace('Z', '+00:00'))
            except Exception:
                return value
        now = datetime.now(timezone.utc)
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        diff = now - value
        seconds = diff.total_seconds()
        if seconds < 60:
            return 'agora mesmo'
        elif seconds < 3600:
            m = int(seconds // 60)
            return f"há {m} min"
        elif seconds < 86400:
            h = int(seconds // 3600)
            return f"há {h} hora{'s' if h > 1 else ''}"
        else:
            d = int(seconds // 86400)
            return f"há {d} dia{'s' if d > 1 else ''}"

    # Criação automática do banco SQLite e tabelas na primeira execução
    with app.app_context():
        # Importar modelos para garantir que o SQLAlchemy conheça o esquema completo
        from app.models import NewsArticle, ArticlePage, AccessLog, MaintenanceLog  # noqa: F401
        
        # Garante a existência do diretório instance/
        db_path = app.config.get('SQLITE_PATH')
        if db_path:
            dir_name = os.path.dirname(db_path)
            if dir_name:
                os.makedirs(dir_name, exist_ok=True)
                
        # Cria as tabelas diretamente no arquivo SQLite se não existirem
        db.create_all()
        logger.info(f"SQLite verificado e pronto: {app.config.get('SQLALCHEMY_DATABASE_URI')}")

        # Se o banco de notícias estiver vazio, inicializa com conteúdo padrão e tenta NewsAPI
        from app.models.news import NewsArticle
        from app.services.news_service import NewsService
        if NewsArticle.query.count() == 0:
            logger.info("Banco SQLite inicializado sem notícias. Carregando dados iniciais...")
            news_svc = NewsService(app.config['NEWS_API_KEY'], app.config['NEWS_API_BASE_URL'])
            news_svc.fetch_and_store_from_api()

    # Iniciar agendador de limpeza automática em segundo plano (se não estiver em modo de teste)
    if not app.config.get('TESTING'):
        from app.tasks.scheduler import scheduler
        scheduler.start(app)

    return app
