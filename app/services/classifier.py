"""
Serviço de classificação de notícias por categorias.
Atribui categorias padronizadas às matérias obtidas da NewsAPI.
"""

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
    Se nenhuma palavra-chave for encontrada, retorna 'geral'.
    """
    combined = f"{title} {description} {source}".lower()
    
    scores = {}
    for category, keywords in KEYWORDS_MAP.items():
        score = sum(1 for kw in keywords if kw in combined)
        if score > 0:
            scores[category] = score
            
    if not scores:
        return 'geral'
        
    return max(scores, key=scores.get)
