import logging
from datetime import datetime, timezone, timedelta
from typing import Tuple
from app.extensions import db
from app.models.page import ArticlePage
from app.models.log import MaintenanceLog

logger = logging.getLogger(__name__)

def clean_expired_pages(app=None, execution_type: str = 'automatic') -> Tuple[int, int, str]:
    """
    Examina os registros de páginas no SQLite e compara a data do último acesso com o UTC atual.
    Qualquer página que permaneça durante 5 dias consecutivos sem receber acesso válido
    é removida automaticamente do SQLite juntamente com seus registros auxiliares de log.
    
    A exclusão afeta apenas a tabela 'article_pages' (e 'access_logs' via CASCADE).
    A matéria em 'news_articles' permanece preservada para que, quando um leitor clicar
    novamente no card, a página seja recriada instantaneamente.
    
    Retorna (total_verificadas, total_excluidas, mensagem_resumo).
    """
    def _execute():
        now = datetime.now(timezone.utc)
        # Limite exato de 5 dias consecutivos (120 horas)
        threshold = now - timedelta(days=5)

        all_pages = ArticlePage.query.all()
        total_checked = len(all_pages)
        deleted_count = 0
        deleted_titles = []

        for page in all_pages:
            # Normalizar timezone se necessário
            last_acc = page.last_accessed_at
            if last_acc.tzinfo is None:
                last_acc = last_acc.replace(tzinfo=timezone.utc)

            if last_acc < threshold:
                title = page.article.title if page.article else f"Página #{page.id}"
                deleted_titles.append(f"#{page.id} - {title[:40]}")
                db.session.delete(page)
                deleted_count += 1

        details = ""
        if deleted_count > 0:
            details = f"Páginas removidas por inatividade (>5 dias): {'; '.join(deleted_titles)}"
        else:
            details = "Nenhuma página atingiu o limite de 5 dias sem acesso. Banco íntegro."

        # Registrar no histórico de manutenção do SQLite
        log_entry = MaintenanceLog(
            executed_at=now,
            execution_type=execution_type,
            pages_checked=total_checked,
            pages_deleted=deleted_count,
            details=details
        )
        db.session.add(log_entry)

        try:
            db.session.commit()
            msg = f"Manutenção ({execution_type}) concluída: {total_checked} páginas verificadas, {deleted_count} excluídas por inatividade (>= 5 dias)."
            logger.info(msg)
            return total_checked, deleted_count, msg
        except Exception as e:
            db.session.rollback()
            err_msg = f"Erro ao executar limpeza de páginas expiradas no SQLite: {str(e)}"
            logger.error(err_msg)
            return total_checked, 0, err_msg

    if app:
        with app.app_context():
            return _execute()
    return _execute()

def simulate_age_page(page_id: int, days_to_age: int = 6) -> Tuple[bool, str]:
    """
    Ferramenta de teste e demonstração:
    Retrocede artificialmente a data do último acesso da página no SQLite
    para permitir testar a exclusão automática dos 5 dias e a subsequente
    recriação dinâmica quando acessada novamente.
    """
    page = db.session.get(ArticlePage, page_id)
    if not page:
        return False, f"Página #{page_id} não encontrada no SQLite."

    past_date = datetime.now(timezone.utc) - timedelta(days=days_to_age)
    page.last_accessed_at = past_date
    try:
        db.session.commit()
        return True, f"Página #{page_id} retrocedida em {days_to_age} dias (último acesso: {past_date.strftime('%d/%m/%Y %H:%M:%S UTC')}). Agora ela está elegível para a rotina de exclusão!"
    except Exception as e:
        db.session.rollback()
        return False, f"Erro ao envelhecer página: {str(e)}"
