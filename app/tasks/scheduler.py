import threading
import time
import logging
from flask import Flask
from app.tasks.cleanup import clean_expired_pages
from app.services.news_service import NewsService

logger = logging.getLogger(__name__)

class MaintenanceScheduler:
    """
    Agendador em segundo plano baseado em thread dedicada.
    Executa a rotina de limpeza periódica no SQLite sem requerer Redis, Celery ou serviços em nuvem.
    """
    def __init__(self, app: Flask = None):
        self.app = app
        self._thread = None
        self._stop_event = threading.Event()

    def start(self, app: Flask):
        self.app = app
        if self._thread and self._thread.is_alive():
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="SQLiteMaintenanceWorker")
        self._thread.start()
        logger.info("Agendador de manutenção periódica do SQLite iniciado.")

    def _run_loop(self):
        # Aguarda inicialização completa da aplicação
        time.sleep(10)
        
        while not self._stop_event.is_set():
            try:
                interval_minutes = 60
                sync_interval_minutes = 15
                if self.app:
                    interval_minutes = self.app.config.get('CLEANUP_INTERVAL_MINUTES', 60)
                    sync_interval_minutes = self.app.config.get('NEWS_SYNC_INTERVAL_MINUTES', 15)
                
                logger.info("Executando ciclo agendado de sincronização de notícias...")
                if self.app:
                    with self.app.app_context():
                        news_svc = NewsService(
                            self.app.config.get('NEWS_API_KEY', ''),
                            self.app.config.get('NEWS_API_BASE_URL', '')
                        )
                        count, message = news_svc.sync_all_categories()
                        logger.info("Sincronização concluída: %s (%s novas)", message, count)

                logger.info("Executando ciclo agendado de manutenção e expiração de páginas...")
                clean_expired_pages(self.app, execution_type='automatic')

            except Exception as e:
                logger.error(f"Erro no ciclo do agendador SQLite: {e}")

            # Dormir com checagem do evento de parada
            # Usa o menor intervalo configurado para que a sincronização não fique parada.
            interval_sec = max(60, min(interval_minutes, sync_interval_minutes) * 60)
            self._stop_event.wait(timeout=interval_sec)

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2)
        logger.info("Agendador de manutenção do SQLite finalizado.")

scheduler = MaintenanceScheduler()
