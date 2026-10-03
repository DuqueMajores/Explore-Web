import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, current_app
from app.extensions import db
from app.models.news import NewsArticle
from app.models.page import ArticlePage
from app.models.log import AccessLog, MaintenanceLog
from app.tasks.cleanup import clean_expired_pages, simulate_age_page
from app.services.backup_service import BackupService

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/')
def dashboard():
    """Painel de controle do banco SQLite e das páginas internas."""
    db_path = BackupService.get_db_path()
    db_exists = os.path.exists(db_path)
    db_size_kb = 0
    if db_exists:
        try:
            db_size_kb = round(os.path.getsize(db_path) / 1024, 2)
        except Exception:
            pass

    total_articles = NewsArticle.query.count()
    total_pages = ArticlePage.query.count()
    total_logs = AccessLog.query.count()
    maintenance_history = MaintenanceLog.query.order_by(MaintenanceLog.executed_at.desc()).limit(10).all()

    # Listagem de todas as páginas ativas com cálculo de tempo sem acesso
    pages = ArticlePage.query.order_by(ArticlePage.last_accessed_at.desc()).all()

    return render_template(
        'admin.html',
        db_path=db_path,
        db_exists=db_exists,
        db_size_kb=db_size_kb,
        total_articles=total_articles,
        total_pages=total_pages,
        total_logs=total_logs,
        pages=pages,
        maintenance_history=maintenance_history,
        expiration_days=current_app.config.get('PAGE_EXPIRATION_DAYS', 5)
    )

@admin_bp.route('/limpeza/executar', methods=['POST'])
def trigger_cleanup():
    """Executa manualmente a rotina de exclusão das páginas com >= 5 dias sem acesso."""
    checked, deleted, msg = clean_expired_pages(current_app, execution_type='manual')
    flash(msg, 'success' if deleted > 0 else 'info')
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/pagina/<int:page_id>/envelhecer', methods=['POST'])
def age_page(page_id):
    """
    Simula 5+ dias sem acesso em uma página específica.
    Facilita testar a exclusão e a posterior recriação dinâmica.
    """
    days = int(request.form.get('dias', 6))
    success, msg = simulate_age_page(page_id, days_to_age=days)
    flash(msg, 'warning' if success else 'error')
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/backups')
def backups():
    """Gerenciamento de backups locais do arquivo SQLite."""
    backup_list = BackupService.list_local_backups()
    db_path = BackupService.get_db_path()
    return render_template(
        'backup.html',
        backups=backup_list,
        db_path=db_path,
        backup_dir=BackupService.get_backup_dir()
    )

@admin_bp.route('/backups/criar', methods=['POST'])
def create_backup():
    """Gera um novo backup local no servidor."""
    note = request.form.get('note', '')
    success, filename, msg = BackupService.create_local_backup(note=note)
    flash(msg, 'success' if success else 'error')
    return redirect(url_for('admin.backups'))

@admin_bp.route('/backups/restaurar/<filename>', methods=['POST'])
def restore_backup(filename):
    """Restaura o banco SQLite a partir de um backup local."""
    success, msg = BackupService.restore_local_backup(filename)
    flash(msg, 'success' if success else 'error')
    return redirect(url_for('admin.backups'))

@admin_bp.route('/backups/download/<filename>')
def download_backup(filename):
    """Permite baixar uma cópia do arquivo SQLite para segurança offline."""
    backup_dir = BackupService.get_backup_dir()
    file_path = os.path.join(backup_dir, filename)
    if not os.path.exists(file_path):
        flash(f"Arquivo {filename} não encontrado.", "error")
        return redirect(url_for('admin.backups'))
    return send_file(file_path, as_attachment=True, download_name=filename)
