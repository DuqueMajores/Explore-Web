import threading
import time
import logging
from flask import Flask
from app.tasks.cleanup import clean_expired_pages

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
                if self.app:
                    interval_minutes = self.app.config.get('CLEANUP_INTERVAL_MINUTES', 60)
                
                logger.info("Executando ciclo agendado de manutenção e expiração de páginas...")
                clean_expired_pages(self.app, execution_type='automatic')

            except Exception as e:
                logger.error(f"Erro no ciclo do agendador SQLite: {e}")

            # Dormir com checagem do evento de parada
            interval_sec = max(60, interval_minutes * 60)
            self._stop_event.wait(timeout=interval_sec)

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2)
        logger.info("Agendador de manutenção do SQLite finalizado.")

scheduler = MaintenanceScheduler()
