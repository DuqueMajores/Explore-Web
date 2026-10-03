import pytest
from datetime import datetime, timezone, timedelta
from app import create_app
from app.extensions import db
from app.models.news import NewsArticle
from app.models.page import ArticlePage
from app.models.log import AccessLog
from app.tasks.cleanup import clean_expired_pages

@pytest.fixture
def app():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

def test_cleanup_5_days_rule(app):
    """
    Testa se uma página com mais de 5 dias sem acesso é removida do SQLite,
    enquanto a página recente permanece ativa.
    """
    with app.app_context():
        # Cria matéria 1 (que ficará expirada)
        art_expired = NewsArticle(
            article_hash='hash_exp',
            title='Materia Antiga Expirada',
            original_url='https://teste.com/exp',
            category='geral'
        )
        # Cria matéria 2 (que permanecerá ativa)
        art_active = NewsArticle(
            article_hash='hash_act',
            title='Materia Recente Ativa',
            original_url='https://teste.com/act',
            category='tecnologia'
        )
        db.session.add_all([art_expired, art_active])
        db.session.commit()

        # Página 1 com último acesso há 6 dias (deve ser excluída)
        page1 = ArticlePage.create_for_article(art_expired)
        page1.last_accessed_at = datetime.now(timezone.utc) - timedelta(days=6)

        # Página 2 com último acesso há 1 dia (deve permanecer)
        page2 = ArticlePage.create_for_article(art_active)
        page2.last_accessed_at = datetime.now(timezone.utc) - timedelta(days=1)

        db.session.add_all([page1, page2])
        db.session.commit()

        # Adiciona log auxiliar na página 1
        log1 = AccessLog(page_id=page1.id, reader_id='reader-abc')
        db.session.add(log1)
        db.session.commit()

        assert ArticlePage.query.count() == 2
        assert AccessLog.query.count() == 1

        page1_id = page1.id
        page2_id = page2.id

        # Executa rotina de limpeza automática
        checked, deleted, msg = clean_expired_pages(app, execution_type='test')

        assert checked == 2
        assert deleted == 1

        # Página 1 deve ter sido removida do SQLite
        assert ArticlePage.query.filter_by(id=page1_id).first() is None
        # Registros auxiliares de log da página 1 devem ter sido removidos em cascata
        assert AccessLog.query.filter_by(page_id=page1_id).first() is None

        # Página 2 deve continuar intacta no SQLite
        assert ArticlePage.query.filter_by(id=page2_id).first() is not None

        # As matérias base continuam preservadas em news_articles
        assert NewsArticle.query.filter_by(id=art_expired.id).first() is not None
        assert NewsArticle.query.filter_by(id=art_active.id).first() is not None
