#!/usr/bin/env python3
"""
Script de Exportação Estática para GitHub Pages (Explore).
Gera uma pasta /docs e sincroniza a raiz (/) de modo totalmente estático, auto-suficiente
e à prova de falhas para o GitHub Pages.

Compatível com as três formas de publicação no GitHub:
1. Settings -> Pages -> Source: Deploy from a branch -> Branch: main / Folder: /docs
2. Settings -> Pages -> Source: Deploy from a branch -> Branch: main / Folder: / (root)
3. Settings -> Pages -> Source: GitHub Actions (.github/workflows/deploy-gh-pages.yml)
"""

import os
import sys
import shutil
import json
import re
from datetime import datetime, timezone

# Assegura que o diretório raiz está no path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.extensions import db
from app.models.news import NewsArticle
from app.models.page import ArticlePage, slugify
from app.services.news_service import NewsService

def format_time_ago(dt):
    if dt is None:
        return '—'
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    diff = now - dt
    seconds = diff.total_seconds()
    if seconds < 60:
        return 'agora mesmo'
    elif seconds < 3600:
        mins = int(seconds // 60)
        return f'há {mins} min' if mins > 1 else 'há 1 min'
    elif seconds < 86400:
        hours = int(seconds // 3600)
        return f'há {hours} h' if hours > 1 else 'há 1 h'
    elif seconds < 172800:
        return 'ontem'
    else:
        days = int(seconds // 86400)
        return f'há {days} dias'

def asset_version() -> str:
    """Usa a revisão do CI para impedir que o CDN mantenha JS/CSS antigos."""
    return os.environ.get('GITHUB_SHA', datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S'))[:12]

def add_asset_version(html: str) -> str:
    version = asset_version()
    return html.replace('./static/js/main.js', f'./static/js/main.js?v={version}')\
               .replace('./static/css/style.css', f'./static/css/style.css?v={version}')

def make_relative_home(html: str) -> str:
    """Ajusta links e caminhos para funcionamento perfeito em subpastas do GitHub Pages."""
    h = html
    h = h.replace('href="/static/', 'href="./static/')
    h = h.replace('src="/static/', 'src="./static/')
    h = re.sub(r'href="/\?categoria=([^"]+)"', r'href="./index.html?categoria=\1"', h)
    h = re.sub(r'href="/noticia/abrir/(\d+)"', r'href="./noticia/abrir/\1/index.html"', h)
    h = re.sub(r'href="/noticia/([^"/?#]+)"', r'href="./noticia/\1/index.html"', h)
    h = h.replace('href="/"', 'href="./index.html"')
    h = h.replace('action="/"', 'action="./index.html"')
    h = h.replace("fetch('/api/noticias", "fetch('./data/articles.json")
    return add_asset_version(h)

def make_relative_article(html: str, prefix: str = '../../') -> str:
    """Ajusta links conforme a profundidade da página estática de matéria."""
    h = html
    h = h.replace('href="/static/', f'href="{prefix}static/')
    h = h.replace('src="/static/', f'src="{prefix}static/')
    h = re.sub(r'href="/\?categoria=([^"]+)"', rf'href="{prefix}index.html?categoria=\1"', h)
    h = re.sub(r'href="/noticia/abrir/(\d+)"', rf'href="{prefix}noticia/abrir/\1/index.html"', h)
    h = re.sub(r'href="/noticia/([^"/?#]+)"', rf'href="{prefix}noticia/\1/index.html"', h)
    h = h.replace('href="/"', f'href="{prefix}index.html"')
    version = asset_version()
    return h.replace(f'{prefix}static/js/main.js', f'{prefix}static/js/main.js?v={version}')\
            .replace(f'{prefix}static/css/style.css', f'{prefix}static/css/style.css?v={version}')

def make_robust_404(html: str) -> str:
    """Corrige URLs profundas/duplicadas antes que assets relativos sejam lidos."""
    recovery_script = '''<script>
(function () {
    var path = window.location.pathname || '';
    var match = path.match(/^(.*\\/)noticia\\/(?:noticia\\/)?abrir\\/(\\d+)\\/index\\.html$/);
    if (match) {
        window.location.replace(match[1] + 'noticia/abrir/' + match[2] + '/index.html');
    }
})();
</script>'''
    return html.replace('<head>', '<head>' + recovery_script, 1)

def export_static_site(output_dir='docs'):
    print(f"[*] Iniciando exportação para GitHub Pages na pasta '{output_dir}/'...")
    
    app = create_app()
    with app.app_context():
        news_svc = NewsService(app.config.get('NEWS_API_KEY', ''), app.config.get('NEWS_API_BASE_URL', ''))
        # O GitHub Pages não executa Flask em tempo de acesso. Sincroniza antes
        # da exportação para que cada deploy agendado publique um catálogo novo.
        synced_count, sync_message = news_svc.sync_all_categories()
        print(f"[*] Sincronização antes da exportação: {sync_message} ({synced_count} novas)")
        news_svc.seed_initial_articles()

        articles = NewsArticle.query.order_by(NewsArticle.published_at.desc().nullslast(), NewsArticle.id.desc()).all()

        # Evita exibir a mesma matéria ou a mesma foto várias vezes no catálogo exportado.
        seen_titles, seen_images, unique_articles = set(), set(), []
        for article in articles:
            title_key = ' '.join((article.title or '').lower().split())
            image_key = (article.image_url or '').strip().lower()
            if title_key and title_key in seen_titles:
                continue
            if image_key and image_key in seen_images:
                continue
            seen_titles.add(title_key)
            if image_key:
                seen_images.add(image_key)
            unique_articles.append(article)
        articles = unique_articles
        print(f"[*] Total de matérias únicas no SQLite: {len(articles)}")

        # Limpa e recria diretório de saída docs/
        if os.path.exists(output_dir):
            shutil.rmtree(output_dir)
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(os.path.join(output_dir, 'data'), exist_ok=True)

        # 1. Copia static assets para docs/static
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        static_src = os.path.join(root_dir, 'app', 'static')
        static_dest = os.path.join(output_dir, 'static')
        if os.path.exists(static_src):
            shutil.copytree(static_src, static_dest)
            print("[✓] Arquivos estáticos copiados para docs/static/")

        # 2. Cria arquivo .nojekyll TANTO em docs/ QUANTO na raiz / (crucial para desativar Jekyll)
        with open(os.path.join(output_dir, '.nojekyll'), 'w') as f:
            f.write('')
        with open(os.path.join(root_dir, '.nojekyll'), 'w') as f:
            f.write('')
        print("[✓] Arquivo .nojekyll criado em docs/ e na raiz / (Jekyll desativado com sucesso).")

        client = app.test_client()

        # 3. Exporta docs/index.html e docs/404.html com caminhos relativos
        resp = client.get('/')
        if resp.status_code == 200:
            raw_html = resp.data.decode('utf-8')
            rel_html = make_relative_home(raw_html)

            # Salva na pasta docs/
            with open(os.path.join(output_dir, 'index.html'), 'w', encoding='utf-8') as f:
                f.write(rel_html)
            with open(os.path.join(output_dir, '404.html'), 'w', encoding='utf-8') as f:
                f.write(make_robust_404(rel_html))
            print("[✓] Página inicial exportada com sucesso para docs/index.html e docs/404.html")

            # Salva também na raiz /index.html (incluindo Vite script para compatibilidade de build)
            vite_html = rel_html
            if '<script type="module" src="/src/main.tsx"></script>' not in vite_html:
                vite_html = vite_html.replace('</body>', '<script type="module" src="/src/main.tsx"></script>\n</body>')
            with open(os.path.join(root_dir, 'index.html'), 'w', encoding='utf-8') as f:
                f.write(vite_html)

            with open(os.path.join(root_dir, '404.html'), 'w', encoding='utf-8') as f:
                f.write(rel_html)
            print("[✓] Raiz /index.html e /404.html sincronizados para compatibilidade de deploy no root.")

        # 4. Prepara o catálogo e gera páginas estáticas para todas as matérias.
        articles_data = []
        rendered_count = 0

        for a in articles:
            # O feed estático disponibiliza o catálogo completo; toda matéria
            # exibida precisa ter uma página física para o GitHub Pages servir.
            slug = a.page.slug if a.page else f"{slugify(a.title)}-{a.id}"

            art_dict = {
                'id': a.id,
                'slug': slug,
                'title': a.title,
                'category': a.category,
                'author': a.author or a.source_name or 'Explore',
                'description': a.description or '',
                'short_summary': a.short_summary,
                'image_url': a.image_url or 'https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=800&q=80',
                'time_ago': format_time_ago(a.published_at),
                'open_url': f"noticia/{slug}/index.html",
                'paragraphs': a.get_reading_paragraphs()
            }
            articles_data.append(art_dict)

            # Pré-renderiza todas as matérias: categorias também exibem notícias
            # mais antigas, que antes eram listadas sem um HTML publicado.
            slug_dir = os.path.join(output_dir, 'noticia', slug)
            os.makedirs(slug_dir, exist_ok=True)
            art_resp = client.get(f'/noticia/{slug}')
            if art_resp.status_code == 200:
                art_html = make_relative_article(art_resp.data.decode('utf-8'))
                with open(os.path.join(slug_dir, 'index.html'), 'w', encoding='utf-8') as f:
                    f.write(art_html)
                rendered_count += 1

                # Cria alias por ID: docs/noticia/abrir/<id>/index.html.
                id_dir = os.path.join(output_dir, 'noticia', 'abrir', str(a.id))
                os.makedirs(id_dir, exist_ok=True)
                # O alias /noticia/abrir/<id>/ tem um nível extra em relação
                # a /noticia/<slug>/ e precisa de ../../../.
                alias_html = make_relative_article(art_resp.data.decode('utf-8'), prefix='../../../')
                with open(os.path.join(id_dir, 'index.html'), 'w', encoding='utf-8') as f:
                    f.write(alias_html)

        # Salva docs/data/articles.json e copia para /data/articles.json
        data_json_path = os.path.join(output_dir, 'data', 'articles.json')
        with open(data_json_path, 'w', encoding='utf-8') as f:
            json.dump(articles_data, f, ensure_ascii=False, indent=2)

        root_data_dir = os.path.join(root_dir, 'data')
        os.makedirs(root_data_dir, exist_ok=True)
        shutil.copy(data_json_path, os.path.join(root_data_dir, 'articles.json'))

        # Copia docs/noticia para /noticia na raiz
        root_noticia_dir = os.path.join(root_dir, 'noticia')
        if os.path.exists(root_noticia_dir):
            shutil.rmtree(root_noticia_dir)
        shutil.copytree(os.path.join(output_dir, 'noticia'), root_noticia_dir)

        print(f"[✓] {rendered_count} páginas estáticas pré-renderizadas e {len(articles_data)} matérias exportadas em docs/data/articles.json!")

    print(f"\n[🚀 SUCESSO] O site Explore está 100% pronto para o GitHub Pages!")
    print(f"Funciona em qualquer configuração:")
    print(f"a) Branch: 'main' / Folder: '/docs'")
    print(f"b) Branch: 'main' / Folder: '/ (root)'")
    print(f"c) GitHub Actions (Automático)")
    os._exit(0)

if __name__ == '__main__':
    export_static_site()
