# 📰 Portal de Notícias com Flask e SQLite Local Exclusivo

Sistema completo de publicação e catalogação de notícias desenvolvido em **Python / Flask**, com persistência de dados local baseada **exclusivamente em arquivo SQLite** gerenciado através de **SQLAlchemy**.

> **Aviso de Arquitetura:** Este projeto **NÃO** utiliza Firebase, Firestore, Supabase, MongoDB, PostgreSQL, MySQL, Redis ou qualquer banco de dados ou serviço de nuvem externa para persistência de dados. Toda a persistência é centralizada localmente no arquivo SQLite no próprio servidor.

---

## 📑 Sumário

- [Visão Geral e Arquitetura](#-visão-geral-e-arquitetura)
- [Localização e Gestão do Arquivo SQLite](#-localização-e-gestão-do-arquivo-sqlite)
- [Páginas HTML Estáticas Permanentes](#-páginas-html-estáticas-permanentes)
- [Multi-Usuário: Servidor vs. Navegador vs. GitHub Pages](#-multi-usuário-servidor-vs-navegador-vs-github-pages)
- [Sistema de Backup e Restauração Local](#-sistema-de-backup-e-restauração-local)
- [Estrutura do Projeto](#-estrutura-do-projeto)
- [Instalação e Execução Passo a Passo](#-instalação-e-execução-passo-a-passo)
- [Execução dos Testes Automatizados](#-execução-dos-testes-automatizados)
- [Configuração de Variáveis de Ambiente](#-configuração-de-variáveis-de-ambiente)

---

## 🏛 Visão Geral e Arquitetura

O sistema consome a API da **NewsAPI** (ou base demonstrativa local em caso de ausência de conexão), cataloga as matérias com identificadores únicos (*hashes* SHA-256) e as organiza em categorias (`tecnologia`, `negócios`, `ciência`, `saúde`, `entretenimento`, `esportes`, `geral`).

### Páginas HTML Estáticas Permanentes
- No primeiro clique em uma matéria no servidor Flask, a aplicação renderiza e grava `noticia/<slug>/index.html`.
- A resposta passa a ser servida desse arquivo estático; os metadados e acessos continuam registrados no SQLite.
- A rotina de manutenção não exclui páginas por falta de acesso. O arquivo HTML permanece acessível mesmo que os metadados do SQLite sejam removidos.
- Configure `STATIC_ARTICLES_DIR` para um volume persistente em produção. Em hospedagens com disco efêmero, arquivos podem ser perdidos quando o serviço reinicia ou é publicado novamente.
- O GitHub Pages não executa Flask nem escreve arquivos durante um clique. O exportador gera as páginas durante o build e preserva os snapshots já presentes no repositório entre exportações.

---

## 💾 Localização e Gestão do Arquivo SQLite

Por padrão, o banco de dados é mantido no diretório dedicado de instância:

```bash
instance/database.sqlite3
```

- **Criação Automática na Primeira Execução:** Quando a aplicação Flask sobe pela primeira vez, o método `create_app()` detecta a ausência do arquivo, cria automaticamente a pasta `instance/` e executa `db.create_all()`.
- **Customização por Variável de Ambiente:** O caminho do banco pode ser alterado via `.env` através da variável `SQLITE_PATH` ou `DATABASE_URL` (ex: `SQLITE_PATH=data/database.sqlite3`).
- **Segurança no Git (`.gitignore`):** O arquivo `.gitignore` vem pré-configurado para ignorar `instance/*.sqlite3`, `data/*.sqlite3` e backups locais, impedindo que dados reais de leitores ou acessos de produção sejam enviados acidentalmente ao repositório público do GitHub.
- **Script Manual de Migração e Criação:** Para inicializar ou verificar o banco manualmente pela linha de comando:
  ```bash
  python migrations/init_db.py
  ```

---

## ♾️ Páginas HTML Estáticas Permanentes

1. **Primeiro acesso:** O clique cria o metadado da página no SQLite e materializa seu HTML em `STATIC_ARTICLES_DIR/<slug>/index.html`.
2. **Acessos seguintes:** A aplicação serve o snapshot gravado, sem renderizar novamente o conteúdo da matéria. A URL permanece a mesma (`/noticia/<slug>`).
3. **Sem expiração:** As rotinas agendadas e manuais apenas registram uma verificação; não removem páginas ou logs por inatividade.
4. **Armazenamento durável:** O diretório `STATIC_ARTICLES_DIR` deve estar em um volume persistente. O padrão é `noticia/` na raiz do projeto; altere-o pela variável de ambiente para apontar ao volume do servidor.
5. **GitHub Pages:** Como esse serviço não pode gravar arquivos ao receber um clique, o exportador publica os HTMLs no build e mantém os snapshots já publicados. Novas matérias ficam disponíveis como arquivos estáticos após o próximo export/deploy.

---

## 👥 Multi-Usuário: Servidor vs. Navegador vs. GitHub Pages

### O problema de João em São Paulo e Maria no Rio de Janeiro
Para que diferentes pessoas em computadores e cidades distintas visualizem o mesmo portal e compartilhem o mesmo estado de páginas:
- **O SQLite DEVE residir no servidor central** que executa a aplicação Flask.
- **O navegador do usuário NÃO armazena o banco:** Armazenar dados em `localStorage`, `IndexedDB` ou SQLite no navegador faria com que cada usuário vivesse em uma ilha isolada. No navegador, o sistema armazena apenas um cookie HTTP anônimo (`noticias_reader_id`) para identificar acessos individuais sem exigir login.
- **Por que NÃO funciona no GitHub Pages:**
  - O **GitHub Pages é exclusivo para conteúdo estático** (HTML, CSS e JavaScript client-side).
  - Ele não executa interpretadores Python, não suporta o servidor WSGI do Flask e não possui sistema de arquivos com permissão de escrita persistente para manter um arquivo SQLite.
  - Para produção na internet, a aplicação deve ser executada em um servidor compatível com Python (como uma VPS, Docker, Render com Persistent Disk, Fly.io com volume montado ou Railway), garantindo que o diretório `instance/` permaneça persistente entre reinicializações do servidor.

---

## 📦 Sistema de Backup e Restauração Local

O sistema inclui ferramentas para salvaguardar a base SQLite sem qualquer dependência de nuvem:

- **Localização dos Backups:** Armazenados no diretório local `backups/` com formato de carimbo de data/hora:
  ```bash
  backups/backup_sqlite_YYYYMMDD_HHMMSS.sqlite3
  ```
- **Consistência Transacional:** Utiliza a API nativa `sqlite3.Connection.backup()`, garantindo que o backup seja capturado de forma atômica mesmo com requisições concorrentes.
- **Painel Administrativo Web (`/admin/backups`):**
  - **Criar Backup:** Gera um backup instantâneo com nota opcional.
  - **Restaurar Backup:** Substitui a base ativa por um backup escolhido (gerando automaticamente uma cópia de segurança preventiva antes).
  - **Download:** Permite baixar o arquivo `.sqlite3` para a máquina do administrador.

---

## 📁 Estrutura do Projeto

```text
├── app/
│   ├── __init__.py           # Fábrica da aplicação Flask e inicialização do SQLite
│   ├── extensions.py         # Instância do SQLAlchemy (db)
│   ├── models/               # Modelos de dados
│   │   ├── __init__.py
│   │   ├── news.py           # Tabela news_articles (notícias e hashes SHA-256)
│   │   ├── page.py           # Metadados article_pages e último acesso
│   │   └── log.py            # Tabelas access_logs e maintenance_logs
│   ├── services/             # Regras de negócio e integrações
│   │   ├── __init__.py
│   │   ├── classifier.py     # Classificador de matérias por palavras-chave
│   │   ├── news_service.py   # Integração NewsAPI e criação de metadados
│   │   ├── static_pages.py   # Persistência atômica dos snapshots HTML
│   │   └── backup_service.py # Rotinas de backup atômico e restauração local
│   ├── tasks/                # Tarefas agendadas e manutenção
│   │   ├── __init__.py
│   │   ├── cleanup.py        # Auditoria compatível sem exclusão de páginas
│   │   └── scheduler.py      # Agendador periódico em segundo plano
│   ├── routes/               # Rotas e controladores
│   │   ├── __init__.py
│   │   ├── news.py           # Rotas públicas (/ e /noticia/<slug>)
│   │   ├── admin.py          # Painel administrativo (/admin)
│   │   └── api.py            # Endpoints JSON para monitoramento (/api/stats)
│   ├── templates/            # Templates Jinja2
│   │   ├── base.html         # Layout base e navegação
│   │   ├── index.html        # Feed de notícias e filtros de categoria
│   │   ├── article.html      # Template usado na criação do snapshot estático
│   │   ├── admin.html        # Painel de páginas permanentes
│   │   └── backup.html       # Gerenciador de backups locais
│   └── static/               # Arquivos estáticos
│       ├── css/style.css
│       └── js/main.js
├── instance/                 # Diretório onde o arquivo SQLite é mantido
│   └── database.sqlite3      # Banco SQLite local
├── backups/                  # Cópias de segurança locais do SQLite
├── migrations/
│   └── init_db.py            # Script CLI de inicialização e migração
├── tests/                    # Testes automatizados (pytest)
│   ├── test_models.py        # Validação dos modelos e integridade
│   ├── test_cleanup.py       # Validação da retenção permanente
│   ├── test_recreation.py   # Validação dos snapshots HTML
│   └── test_backup.py        # Validação de backup e listagem
├── config.py                 # Classes de configuração (Dev, Test, Prod)
├── run.py                    # Ponto de entrada da aplicação
├── requirements.txt          # Dependências Python
├── .env.example              # Modelo de variáveis de ambiente
├── .env                      # Arquivo local com credenciais
└── .gitignore                # Regras de exclusão do Git
```

---

## 🚀 Instalação e Execução Passo a Passo

### 1. Clonar o repositório e criar o ambiente virtual
```bash
git clone <url-do-repositorio>
cd portal-noticias-sqlite

# Criar ambiente virtual Python
python3 -m venv venv

# Ativar ambiente virtual
source venv/bin/activate   # Linux / macOS
# ou: venv\Scripts\activate  # Windows
```

### 2. Instalar dependências
```bash
pip install -r requirements.txt
```

### 3. Configurar variáveis de ambiente
Copie o arquivo `.env.example` para `.env`:
```bash
cp .env.example .env
```
Edite `.env` e insira sua chave da NewsAPI caso queira notícias ao vivo (uma chave padrão funcional já acompanha o projeto).

### 4. Inicializar o banco de dados (Opcional, pois ocorre automaticamente)
```bash
python migrations/init_db.py
```

### 5. Executar a aplicação
```bash
python run.py
```
Acesse a aplicação no navegador em: **`http://localhost:5000`**

---

## 🧪 Execução dos Testes Automatizados

Os testes com `pytest` validam os modelos SQLAlchemy, a retenção dos snapshots HTML, as rotinas de manutenção e os backups:

```bash
pytest tests/ -v
```

---

## ⚙ Configuração de Variáveis de Ambiente

| Variável | Padrão | Descrição |
|---|---|---|
| `SECRET_KEY` | *(aleatória)* | Chave de segurança para sessões Flask e cookies |
| `SQLITE_PATH` | `instance/database.sqlite3` | Caminho do arquivo SQLite local no servidor |
| `STATIC_ARTICLES_DIR` | `noticia/` | Diretório de snapshots HTML; use um volume persistente em produção |
| `DATABASE_URL` | `sqlite:///instance/database.sqlite3` | URI de conexão SQLAlchemy |
| `NEWS_API_KEY` | *(chave fornecida)* | Chave da NewsAPI para coleta de notícias |
| `CLEANUP_INTERVAL_MINUTES` | `60` | Frequência em minutos da verificação compatível, sem apagar páginas |
| `PORT` | `5000` | Porta onde o Flask responderá |
| `FLASK_ENV` | `development` | Ambiente de execução (`development` ou `production`) |
