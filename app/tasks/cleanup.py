import logging
from datetime import datetime, timezone
from typing import Tuple
from app.extensions import db
from app.models.page import ArticlePage
from app.models.log import MaintenanceLog

logger = logging.getLogger(__name__)

def clean_expired_pages(app=None, execution_type: str = 'automatic') -> Tuple[int, int, str]:
    """
    Mantém o endpoint e a tarefa agendada por compatibilidade, mas páginas abertas
    são permanentes e não são excluídas por inatividade.

    Retorna (total_verificadas, total_excluidas, mensagem_resumo); total_excluídas
    será sempre zero.
    """
    def _execute():
        now = datetime.now(timezone.utc)
        all_pages = ArticlePage.query.all()
        total_checked = len(all_pages)
        deleted_count = 0
        details = "Páginas HTML estáticas e registros preservados; a limpeza não remove páginas por inatividade."

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
            msg = f"Verificação ({execution_type}) concluída: {total_checked} páginas verificadas, nenhuma removida; páginas estáticas são permanentes."
            logger.info(msg)
            return total_checked, deleted_count, msg
        except Exception as e:
            db.session.rollback()
            err_msg = f"Erro ao verificar páginas permanentes no SQLite: {str(e)}"
            logger.error(err_msg)
            return total_checked, 0, err_msg

    if app:
        with app.app_context():
            return _execute()
    return _execute()
