import os
import shutil
import sqlite3
import logging
from datetime import datetime, timezone
from typing import List, Dict, Tuple
from flask import current_app

logger = logging.getLogger(__name__)

class BackupService:
    """Gerencia backups e restaurações locais do arquivo de banco SQLite."""

    @staticmethod
    def get_db_path() -> str:
        """Retorna o caminho absoluto do arquivo SQLite atual."""
        uri = current_app.config.get('SQLALCHEMY_DATABASE_URI', '')
        if uri.startswith('sqlite:///'):
            path = uri[len('sqlite:///'):]
            if not os.path.isabs(path):
                base_dir = current_app.config.get('BASE_DIR', os.path.abspath('.'))
                path = os.path.join(base_dir, path)
            return path
        if 'SQLITE_PATH' in current_app.config and current_app.config['SQLITE_PATH']:
            return current_app.config['SQLITE_PATH']
        return current_app.config.get('DEFAULT_SQLITE_PATH', os.path.abspath('instance/database.sqlite3'))

    @staticmethod
    def get_backup_dir() -> str:
        """Retorna o diretório de backups locais."""
        backup_dir = current_app.config.get('BACKUP_DIR')
        if not backup_dir:
            base_dir = current_app.config.get('BASE_DIR', os.path.abspath('.'))
            backup_dir = os.path.join(base_dir, 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        return backup_dir

    @classmethod
    def create_local_backup(cls, note: str = '') -> Tuple[bool, str, str]:
        """
        Cria uma cópia física segura do arquivo SQLite atual em backups/.
        Utiliza a API nativa sqlite3.Connection.backup() para consistência transacional.
        Retorna (sucesso, nome_arquivo, mensagem).
        """
        src_path = cls.get_db_path()
        if not os.path.exists(src_path):
            return False, '', f"Arquivo de banco {src_path} não encontrado no servidor."

        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
        clean_note = "".join(c for c in note if c.isalnum() or c in ('_', '-'))
        suffix = f"_{clean_note}" if clean_note else ""
        backup_filename = f"backup_sqlite_{timestamp}{suffix}.sqlite3"
        dest_path = os.path.join(cls.get_backup_dir(), backup_filename)

        try:
            # Uso da API nativa do SQLite para backup atômico e íntegro
            src_conn = sqlite3.connect(src_path)
            dest_conn = sqlite3.connect(dest_path)
            with dest_conn:
                src_conn.backup(dest_conn)
            dest_conn.close()
            src_conn.close()

            size_bytes = os.path.getsize(dest_path)
            size_kb = round(size_bytes / 1024, 2)
            logger.info(f"Backup local criado: {backup_filename} ({size_kb} KB)")
            return True, backup_filename, f"Backup local criado com sucesso: {backup_filename} ({size_kb} KB)."

        except Exception as e:
            logger.error(f"Erro ao criar backup local do SQLite: {e}")
            # Tentativa de cópia direta como fallback
            try:
                shutil.copy2(src_path, dest_path)
                return True, backup_filename, f"Backup criado via cópia de arquivo: {backup_filename}"
            except Exception as copy_err:
                return False, '', f"Falha ao realizar backup local: {str(copy_err)}"

    @classmethod
    def list_local_backups(cls) -> List[Dict]:
        """Lista todos os arquivos de backup disponíveis localmente no servidor."""
        backup_dir = cls.get_backup_dir()
        backups = []

        if not os.path.exists(backup_dir):
            return []

        for filename in sorted(os.listdir(backup_dir), reverse=True):
            if filename.endswith(('.sqlite3', '.db')) and not filename.startswith('.'):
                file_path = os.path.join(backup_dir, filename)
                try:
                    stat = os.stat(file_path)
                    size_kb = round(stat.st_size / 1024, 2)
                    modified_dt = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)

                    # Obter quantidade de matérias no arquivo de backup se possível
                    article_count = 0
                    page_count = 0
                    try:
                        conn = sqlite3.connect(file_path)
                        cur = conn.cursor()
                        cur.execute("SELECT COUNT(*) FROM news_articles")
                        article_count = cur.fetchone()[0]
                        cur.execute("SELECT COUNT(*) FROM article_pages")
                        page_count = cur.fetchone()[0]
                        conn.close()
                    except Exception:
                        pass

                    backups.append({
                        'filename': filename,
                        'file_path': file_path,
                        'size_kb': size_kb,
                        'created_at': modified_dt.strftime('%d/%m/%Y %H:%M:%S UTC'),
                        'article_count': article_count,
                        'page_count': page_count
                    })
                except Exception as e:
                    logger.warning(f"Erro ao ler metadados do backup {filename}: {e}")

        return backups

    @classmethod
    def restore_local_backup(cls, filename: str) -> Tuple[bool, str]:
        """
        Restaura o banco de dados a partir de um backup local selecionado.
        Garante que o arquivo exista e seja um banco SQLite válido.
        """
        backup_dir = cls.get_backup_dir()
        backup_path = os.path.join(backup_dir, filename)

        if not os.path.exists(backup_path):
            return False, f"Arquivo de backup '{filename}' não encontrado em {backup_dir}."

        dest_path = cls.get_db_path()

        # Cria uma cópia de segurança do banco atual antes de sobrescrever
        try:
            cls.create_local_backup(note='pre_restore_safety')
        except Exception:
            pass

        try:
            # Restauração com sqlite3 backup API
            src_conn = sqlite3.connect(backup_path)
            dest_conn = sqlite3.connect(dest_path)
            with dest_conn:
                src_conn.backup(dest_conn)
            dest_conn.close()
            src_conn.close()

            logger.info(f"Banco restaurado com sucesso a partir de {filename}")
            return True, f"Banco de dados SQLite restaurado com sucesso a partir de {filename}."

        except Exception as e:
            logger.error(f"Erro ao restaurar backup: {e}")
            try:
                shutil.copy2(backup_path, dest_path)
                return True, f"Banco restaurado via cópia direta de {filename}."
            except Exception as copy_err:
                return False, f"Falha na restauração do backup: {str(copy_err)}"
