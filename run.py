#!/usr/bin/env python3
"""
Ponto de entrada para execução da aplicação Flask com persistência local SQLite.
Execute:
    python run.py
ou configure variáveis de ambiente no arquivo .env
"""
import os
from app import create_app

env_name = os.getenv('FLASK_ENV', 'development')
app = create_app(env_name)

if __name__ == '__main__':
    # Porta padrão para o Flask interno: 5000 (ou configurável via FLASK_PORT / PORT)
    port = int(os.getenv('FLASK_PORT', os.getenv('PORT', '5000')))
    # Evitar colisão com portas reservadas pelo ambiente do container (8000, 8080, 3000)
    if port in (3000, 8000, 8080) and not os.getenv('FLASK_PORT'):
        port = 5000

    host = os.getenv('HOST', '127.0.0.1')
    print(f"[*] Iniciando Portal de Notícias SQLite em http://{host}:{port}")
    print(f"[*] Base de dados SQLite local: {app.config.get('SQLALCHEMY_DATABASE_URI')}")
    print(f"[*] Política de expiração: {app.config.get('PAGE_EXPIRATION_DAYS')} dias sem acesso.")
    app.run(host=host, port=port, debug=False, use_reloader=False)
