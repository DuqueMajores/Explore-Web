import pytest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from app import create_app
from app.extensions import db
from app.models.news import NewsArticle
from app.models.page import ArticlePage
from app.services.news_service import NewsService
from app.tasks.cleanup import clean_expired_pages

@pytest.fixture
def app(tmp_path):
    app = create_app('testing')
    app.config['STATIC_ARTICLES_DIR'] = str(tmp_path / 'noticia')
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

def test_opened_page_becomes_permanent_static_html(app, client):
    """
    Testa a criação do HTML no primeiro acesso e sua retenção após períodos longos.
    """
    with app.app_context():
        art = NewsArticle(
            article_hash='hash_recreate_test',
            title='Matéria que será Excluída e Recriada',
            original_url='https://teste.com/recreate',
            category='ciencia'
        )
        db.session.add(art)
        db.session.commit()
        article_id = art.id

        news_svc = NewsService('test-key')

        # O primeiro acesso cria os metadados e o arquivo HTML permanente.
        page, was_recreated = news_svc.get_or_create_page_for_article(art, reader_id='joao-sp')
        assert was_recreated is True
        assert page.id is not None
        initial_page_id = page.id
        slug = page.slug

        response = client.get(f'/noticia/abrir/{article_id}', follow_redirects=True)
        assert response.status_code == 200
        snapshot = Path(app.config['STATIC_ARTICLES_DIR']) / slug / 'index.html'
        assert snapshot.is_file()
        assert snapshot.read_bytes() == response.data

        # Mesmo após seis dias, a manutenção não remove os metadados nem o HTML.
        page.last_accessed_at = datetime.now(timezone.utc) - timedelta(days=6)
        db.session.commit()

        # A rotina de manutenção verifica, mas preserva a página.
        checked, deleted, _ = clean_expired_pages(app, execution_type='test')
        assert checked == 1
        assert deleted == 0
        assert ArticlePage.query.filter_by(id=initial_page_id).first() is not None
        assert snapshot.is_file()

        # Um novo acesso serve o mesmo arquivo estático, sem recriar seu conteúdo.
        response = client.get(f'/noticia/abrir/{article_id}', follow_redirects=True)
        assert response.status_code == 200
        assert snapshot.read_bytes() == response.data

        # O registro original permanece e os novos acessos continuam contabilizados.
        new_page = ArticlePage.query.filter_by(news_id=article_id).first()
        assert new_page is not None
        assert new_page.id == initial_page_id
        assert new_page.access_count >= 1

        # Mesmo sem os metadados no SQLite, a URL serve o snapshot já criado.
        db.session.delete(new_page)
        db.session.commit()
        response = client.get(f'/noticia/{slug}')
        assert response.status_code == 200
        assert response.data == snapshot.read_bytes()
