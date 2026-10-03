import pytest
from datetime import datetime, timezone, timedelta
from app import create_app
from app.extensions import db
from app.models.news import NewsArticle
from app.models.page import ArticlePage
from app.services.news_service import NewsService
from app.tasks.cleanup import clean_expired_pages

@pytest.fixture
def app():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

def test_page_auto_recreation_after_deletion(app, client):
    """
    Testa o ciclo completo:
    1. Criação inicial da página
    2. Exclusão automática após 5 dias sem acesso
    3. Detecção de ausência e recriação automática transparente ao novo acesso do leitor
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

        # 1. Primeiro acesso de João: cria a página no SQLite
        page, was_recreated = news_svc.get_or_create_page_for_article(art, reader_id='joao-sp')
        assert was_recreated is True
        assert page.id is not None
        initial_page_id = page.id
        slug = page.slug

        # Simula passagem de 6 dias sem acesso (excede os 5 dias)
        page.last_accessed_at = datetime.now(timezone.utc) - timedelta(days=6)
        db.session.commit()

        # 2. Rotina de limpeza executa e remove o registro do SQLite
        checked, deleted, _ = clean_expired_pages(app, execution_type='test')
        assert deleted == 1
        assert ArticlePage.query.filter_by(id=initial_page_id).first() is None

        # 3. Agora Maria no Rio clica novamente no card da mesma notícia!
        # Requisição HTTP simulada para a rota de abertura
        response = client.get(f'/noticia/abrir/{article_id}', follow_redirects=True)
        assert response.status_code == 200

        # Verifica que um novo registro de página foi criado automaticamente no SQLite!
        new_page = ArticlePage.query.filter_by(news_id=article_id).first()
        assert new_page is not None
        assert new_page.access_count >= 1
        assert b"P\xc3\xa1gina Interna Recriada Dinamicamente no SQLite" in response.data or b"Recriada" in response.data
