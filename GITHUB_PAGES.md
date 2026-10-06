# Como Publicar o Explore no GitHub Pages 🚀

O **Explore** está 100% pronto e compatível com o **GitHub Pages**, funcionando de forma totalmente estática e sem custos de servidor, preservando a **rolagem infinita**, a **tira azul com cotações de moedas, ações e fusos mundiais**, as **matérias completas com múltiplos parágrafos** e as **metatags com foto, título e resumo para o Facebook**.

---

## ⚠️ Por que antes apareceu "Explore-Web / GHBanner / Built with AI Studio"?

Quando você cria o repositório no GitHub através do Google AI Studio:
1. O exportador do AI Studio adiciona uma marcação de banner no `README.md`.
2. Por padrão, o GitHub Pages tenta rodar um mecanismo chamado **Jekyll**.
3. Como não havia um arquivo `/.nojekyll` na raiz para desativar o Jekyll, o GitHub ignorava o site e renderizava o texto do `README.md` com a mensagem do AI Studio.

**Essa questão foi totalmente resolvida:**
- Criamos o arquivo `/.nojekyll` na raiz e na pasta `/docs` (desativando o Jekyll definitivamente).
- O arquivo `index.html` da raiz e de `/docs` agora contém o portal **Explore** completo, com caminhos relativos adaptados para subpastas do GitHub Pages (`./static/`, `./data/articles.json`, `./noticia/`).

---

## Como Ativar no GitHub em 30 Segundos

No seu repositório no GitHub:

1. Acesse a aba **Settings** (Configurações) no topo do repositório.
2. No menu lateral esquerdo, clique em **Pages**.
3. Em **Build and deployment** ➔ **Source**, você pode escolher qualquer uma das opções abaixo:

### Opção A: Deploy direto da branch (Mais Rápido e Simples)
- **Source**: `Deploy from a branch`
- **Branch**: `main`
- **Folder**: Tanto `/ (root)` quanto `/docs` funcionarão imediatamente!
- Clique em **Save**.

### Opção B: GitHub Actions (Automático)
- **Source**: Selecione `GitHub Actions`.
- O GitHub usará automaticamente o arquivo `.github/workflows/deploy-gh-pages.yml` já configurado no projeto.

---

## O que está incluído na versão estática para GitHub Pages:

- **`index.html` e `docs/index.html`**: Página principal completa do Explore com notícias, destaques e tira azul com fusos e cotações.
- **`noticia/...` e `docs/noticia/...`**: Páginas de leitura estáticas de cada matéria com metatags Open Graph (título, foto 1200x630 e resumo) prontas para o Facebook.
- **`data/articles.json` e `docs/data/articles.json`**: Feed completo consumido dinamicamente pela **Rolagem Infinita** do navegador.
- **`static/` e `docs/static/`**: Estilos Tailwind, tipografia editorial, FontAwesome e relógios mundiais.
- **`.nojekyll`**: Desativa o processador Jekyll do GitHub, garantindo que o portal seja exibido com fidelidade.
- **`404.html`**: Redirecionamento amigável para rotas dinâmicas.

## Retenção das páginas de matérias

No servidor Flask, o primeiro clique grava a página como HTML em `STATIC_ARTICLES_DIR/<slug>/index.html`; as rotinas de manutenção não a excluem por inatividade. Em produção, esse diretório precisa apontar para armazenamento persistente.

O GitHub Pages não executa Flask e não consegue criar arquivos no momento do clique. Por isso, o exportador pré-renderiza os artigos durante o build e copia para `docs/noticia/` os snapshots já existentes em `noticia/`, preservando páginas antigas em publicações futuras.
