import os
import re
import tempfile


def static_article_path(slug: str, articles_dir: str) -> str:
    """Retorna o caminho seguro do HTML estático associado ao slug."""
    if not isinstance(slug, str) or not re.fullmatch(r'[a-zA-Z0-9_-]+', slug):
        raise ValueError('Slug inválido para página estática.')

    root = os.path.abspath(articles_dir)
    path = os.path.abspath(os.path.join(root, slug, 'index.html'))
    if os.path.commonpath((root, path)) != root:
        raise ValueError('O caminho da página estática está fora do diretório permitido.')
    return path


def persist_static_article(slug: str, html: str, articles_dir: str) -> str:
    """Grava uma cópia HTML uma única vez para que a página não dependa do SQLite."""
    path = static_article_path(slug, articles_dir)
    os.makedirs(os.path.dirname(path), exist_ok=True)

    if os.path.isfile(path):
        return path

    fd, temporary_path = tempfile.mkstemp(prefix='.index-', suffix='.tmp', dir=os.path.dirname(path))
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as snapshot:
            snapshot.write(html)
        # Link exclusivo e atômico evita arquivos parciais ou sobrescritas concorrentes.
        try:
            os.link(temporary_path, path)
        except FileExistsError:
            pass
    finally:
        if os.path.exists(temporary_path):
            os.unlink(temporary_path)
    return path
