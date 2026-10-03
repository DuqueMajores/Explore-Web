import pytest
from datetime import datetime, timezone
from app import create_app
from app.extensions import db
from app.models.news import NewsArticle
from app.models.page import ArticlePage
from app.models.log import AccessLog

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

def test_create_news_article(app):
    with app.app_context():
        hash_val = NewsArticle.generate_hash('https://teste.com/materia-1', 'Título de Teste')
        art = NewsArticle(
            article_hash=hash_val,
            title='Título de Teste',
            author='Autor Teste',
            description='Descrição de Teste',
            content='Conteúdo detalhado de teste',
            original_url='https://teste.com/materia-1',
            source_name='Fonte Teste',
            category='tecnologia'
        )
        db.session.add(art)
        db.session.commit()

        saved = NewsArticle.query.filter_by(article_hash=hash_val).first()
        assert saved is not None
        assert saved.title == 'Título de Teste'
        assert saved.category == 'tecnologia'

def test_article_page_relationship_and_access(app):
    with app.app_context():
        art = NewsArticle(
            article_hash='hash123',
            title='Materia Sobre Inteligencia Artificial',
            original_url='https://teste.com/ia',
            category='tecnologia'
        )
        db.session.add(art)
        db.session.commit()

        page = ArticlePage.create_for_article(art)
        db.session.add(page)
        db.session.commit()

        assert page.id is not None
        assert page.news_id == art.id
        assert 'materia' in page.slug

        initial_count = page.access_count
        page.register_access()
        db.session.commit()

        assert page.access_count == initial_count + 1
