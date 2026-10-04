"""
Serviço de classificação de notícias por categorias.
Atribui categorias padronizadas às matérias obtidas da NewsAPI.
"""

import re
import unicodedata

KEYWORDS_MAP = {
    'tecnologia': [
        'tecnologia', 'tech', 'software', 'hardware', 'ia', 'inteligencia artificial',
        'apple', 'google', 'microsoft', 'smartphone', 'celular', 'aplicativo', 'app',
        'computador', 'cyber', 'segurança', 'hacker', 'chip', 'semicondutor', 'cloud',
        'openai', 'nvidia', 'gadget', 'robô', 'startup'
    ],
    'negocios': [
        'economia', 'mercado', 'ações', 'bolsa', 'dólar', 'euro', 'inflação', 'banco',
        'investimento', 'financeiro', 'lucro', 'receita', 'empresas', 'indústria',
        'comércio', 'taxa', 'selic', 'juros', 'pib', 'cripto', 'bitcoin'
    ],
    'ciencia': [
        'ciência', 'pesquisa', 'estudo', 'espaço', 'nasa', 'astronomia', 'planeta',
        'universo', 'física', 'química', 'biologia', 'fóssil', 'descoberta', 'clima',
        'cientistas', 'laboratório', 'telescópio'
    ],
    'saude': [
        'saúde', 'medicina', 'hospital', 'médico', 'doença', 'tratamento', 'vacina',
        'vírus', 'remédio', 'alimentação', 'nutrição', 'psicologia', 'bem-estar',
        'ansiedade', 'exercício', 'covid', 'dengue', 'câncer'
    ],
    'entretenimento': [
        'cinema', 'filme', 'série', 'netflix', 'música', 'show', 'ator', 'atriz',
        'cantor', 'cantora', 'cultura', 'teatro', 'livro', 'celebridade', 'famosos',
        'game', 'jogos', 'streaming', 'hollywood', 'oscar'
    ],
    'esportes': [
        'futebol', 'jogo', 'campeonato', 'gol', 'clube', 'flamengo', 'corinthians',
        'palmeiras', 'são paulo', 'seleção', 'copa', 'olimpíadas', 'basquete',
        'vôlei', 'tênis', 'fórmula 1', 'f1', 'atleta', 'torcida'
    ]
}

def classify_text(title: str = '', description: str = '', source: str = '') -> str:
    """
    Analisa o texto de uma notícia e retorna a categoria mais adequada.
    Usa palavras inteiras para evitar falsos positivos de siglas curtas.
    """
    combined = unicodedata.normalize('NFC', f"{title} {description} {source}".lower())
    scores = {}
    for category, keywords in KEYWORDS_MAP.items():
        score = 0
        for keyword in keywords:
            pattern = rf'(?<![\w]){re.escape(keyword.lower())}(?![\w])'
            if re.search(pattern, combined, flags=re.IGNORECASE):
                score += 1
        if score:
            scores[category] = score
    return max(scores, key=scores.get) if scores else 'geral'
