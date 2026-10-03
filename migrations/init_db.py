#!/usr/bin/env python3
"""
Script de inicialização e migração do esquema SQLite local.
Garante a integridade das tabelas e índices sem depender de serviços externos.
"""
import os
import sys

# Adiciona diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.extensions import db
from app.models.news import NewsArticle
from app.models.page import ArticlePage
from app.models.log import AccessLog, MaintenanceLog

def init_database():
    app = create_app('production' if os.getenv('FLASK_ENV') == 'production' else 'development')
    with app.app_context():
        db_path = app.config.get('SQLITE_PATH')
        print(f"[*] Verificando diretório do banco de dados SQLite: {db_path}")
        
        dir_name = os.path.dirname(db_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
            
        print("[*] Criando tabelas e índices no SQLite local...")
        db.create_all()
        print("[+] Tabelas 'news_articles', 'article_pages', 'access_logs' e 'maintenance_logs' verificadas com sucesso.")
        print(f"[+] Arquivo SQLite pronto em: {db_path}")

if __name__ == '__main__':
    init_database()
