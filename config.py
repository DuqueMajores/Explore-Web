import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    """Configuração principal da aplicação Flask."""
    BASE_DIR = BASE_DIR
    SECRET_KEY = os.getenv('SECRET_KEY', 'noticias-sqlite-secret-key-prod-2026')
    
    # Caminho dedicado para o SQLite no servidor
    # Por padrão salvo em instance/database.sqlite3
    INSTANCE_DIR = os.path.join(BASE_DIR, 'instance')
    BACKUP_DIR = os.path.join(BASE_DIR, 'backups')
    
    # Garantir que os diretórios existam
    os.makedirs(INSTANCE_DIR, exist_ok=True)
    os.makedirs(BACKUP_DIR, exist_ok=True)
    
    DEFAULT_SQLITE_PATH = os.path.join(INSTANCE_DIR, 'database.sqlite3')
    raw_sqlite_path = os.getenv('SQLITE_PATH', DEFAULT_SQLITE_PATH)
    if not os.path.isabs(raw_sqlite_path):
        SQLITE_PATH = os.path.abspath(os.path.join(BASE_DIR, raw_sqlite_path))
    else:
        SQLITE_PATH = raw_sqlite_path

    os.makedirs(os.path.dirname(SQLITE_PATH), exist_ok=True)

    # Snapshots HTML permanentes; em produção, aponte para um volume persistente.
    STATIC_ARTICLES_DIR = os.getenv('STATIC_ARTICLES_DIR', os.path.join(BASE_DIR, 'noticia'))

    raw_db_url = os.getenv('DATABASE_URL')
    if raw_db_url:
        if raw_db_url.startswith('sqlite:///') and not raw_db_url.startswith('sqlite:////') and not raw_db_url.startswith('sqlite:///:memory:'):
            rel_path = raw_db_url.replace('sqlite:///', '', 1)
            abs_path = os.path.abspath(os.path.join(BASE_DIR, rel_path))
            SQLALCHEMY_DATABASE_URI = f'sqlite:///{abs_path}'
        else:
            SQLALCHEMY_DATABASE_URI = raw_db_url
    else:
        SQLALCHEMY_DATABASE_URI = f'sqlite:///{SQLITE_PATH}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Configurações de pool e timeout para SQLite
    SQLALCHEMY_ENGINE_OPTIONS = {
        'connect_args': {
            'check_same_thread': False,
            'timeout': 30
        }
    }
    
    # NewsAPI
    NEWS_API_KEY = os.getenv('NEWS_API_KEY', 'dde2b5709e25424c9d31a5ebd0c60287')
    NEWS_API_BASE_URL = 'https://newsapi.org/v2'
    
    CLEANUP_INTERVAL_MINUTES = int(os.getenv('CLEANUP_INTERVAL_MINUTES', '60'))
    # Atualiza o catálogo automaticamente mesmo sem interação do leitor.
    NEWS_SYNC_INTERVAL_MINUTES = int(os.getenv('NEWS_SYNC_INTERVAL_MINUTES', '15'))
    
    # Nome do cookie anônimo de leitor
    READER_COOKIE_NAME = 'noticias_reader_id'
    READER_COOKIE_MAX_AGE = int(timedelta(days=365).total_seconds())

class DevelopmentConfig(Config):
    DEBUG = True

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

class ProductionConfig(Config):
    DEBUG = False

config_by_name = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
