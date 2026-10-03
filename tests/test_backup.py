import os
import sqlite3
import pytest
from app import create_app
from app.extensions import db
from app.models.news import NewsArticle
from app.services.backup_service import BackupService

@pytest.fixture
def app():
    test_db_path = '/tmp/test_backup_db.sqlite3'
    backup_dir = '/tmp/test_backups'
    
    if os.path.exists(test_db_path):
        os.remove(test_db_path)
    os.makedirs(backup_dir, exist_ok=True)

    app = create_app('testing')
    app.config['BASE_DIR'] = '/tmp'
    app.config['DEFAULT_SQLITE_PATH'] = test_db_path
    app.config['BACKUP_DIR'] = backup_dir
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{test_db_path}'

    with app.app_context():
        # Cria as tabelas fisicamente no arquivo sqlite
        conn = sqlite3.connect(test_db_path)
        conn.execute("CREATE TABLE news_articles (id INTEGER PRIMARY KEY, title TEXT);")
        conn.execute("CREATE TABLE article_pages (id INTEGER PRIMARY KEY, slug TEXT);")
        conn.commit()
        conn.close()

        yield app

        if os.path.exists(test_db_path):
            os.remove(test_db_path)

def test_create_and_list_backup(app):
    with app.app_context():
        success, filename, msg = BackupService.create_local_backup(note='unit_test')
        assert success is True
        assert 'backup_sqlite_' in filename

        backups = BackupService.list_local_backups()
        assert len(backups) >= 1
        assert any(b['filename'] == filename for b in backups)
