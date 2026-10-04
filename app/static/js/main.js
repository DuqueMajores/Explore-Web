// Interações limpas, fusos horários em tempo real e rolagem infinita sem interromper a leitura
document.addEventListener('DOMContentLoaded', () => {
    // 1. Data formatada em português no topo do Explore
    const dateEl = document.getElementById('currentDate');
    if (dateEl) {
        const now = new Date();
        const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
        try {
            const formatted = now.toLocaleDateString('pt-BR', options);
            dateEl.textContent = formatted.charAt(0).toUpperCase() + formatted.slice(1);
        } catch (e) {
            dateEl.textContent = 'Notícias em Tempo Real';
        }
    }

    // 2. Atualização dos relógios com fusos horários dos países na tira azul
    function updateWorldTimezones() {
        const clocks = document.querySelectorAll('.tz-clock');
        const now = new Date();
        clocks.forEach(clock => {
            const tz = clock.getAttribute('data-tz');
            if (tz) {
                try {
                    const timeFormatter = new Intl.DateTimeFormat('pt-BR', {
                        timeZone: tz,
                        hour: '2-digit',
                        minute: '2-digit',
                        hour12: false
                    });
                    clock.textContent = timeFormatter.format(now);
                } catch (err) {
                    console.warn('Erro ao formatar fuso:', tz, err);
                }
            }
        });
    }

    updateWorldTimezones();
    setInterval(updateWorldTimezones, 10000);

    // 3. Botão Voltar ao Topo (Seta Transparente com Efeito Blur)
    const backToTopBtn = document.getElementById('backToTopBtn');
    if (backToTopBtn) {
        const handleScroll = () => {
            if (window.scrollY > 280) {
                backToTopBtn.classList.remove('opacity-0', 'pointer-events-none', 'translate-y-3');
                backToTopBtn.classList.add('opacity-100', 'translate-y-0');
            } else {
                backToTopBtn.classList.add('opacity-0', 'pointer-events-none', 'translate-y-3');
                backToTopBtn.classList.remove('opacity-100', 'translate-y-0');
            }
        };

        window.addEventListener('scroll', handleScroll, { passive: true });
        handleScroll();
        deduplicateRenderedCards();

        backToTopBtn.addEventListener('click', () => {
            window.scrollTo({
                top: 0,
                behavior: 'smooth'
            });
            // A seta é um ponto explícito de atualização, sem refresh durante a rolagem.
            window.setTimeout(() => refreshPageFeed(false), 550);
        });
    }

    // 4. Mecanismo de Feed e Rolagem Infinita (com suporte híbrido Flask e GitHub Pages)
    const feedContainer = document.getElementById('newsFeedContainer');
    const newsGrid = document.getElementById('newsGrid');
    const trigger = document.getElementById('infiniteScrollTrigger');
    const loader = document.getElementById('infiniteScrollLoader');
    const endNotice = document.getElementById('infiniteScrollEnd');

    let currentPage = 1;
    let isLoading = false;
    let hasMore = feedContainer ? feedContainer.getAttribute('data-has-more') === 'true' : false;
    let currentCategory = feedContainer ? (feedContainer.getAttribute('data-category') || 'todas').toLowerCase() : 'todas';
    let currentQuery = feedContainer ? (feedContainer.getAttribute('data-query') || '').toLowerCase() : '';
    let staticArticlesCache = null;
    let lastRefreshTime = 0;

    function escapeHtml(text) {
        if (!text) return '';
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return text.replace(/[&<>"']/g, m => map[m]);
    }

    // Remove duplicatas por título ou foto antes de renderizar o feed.
    function deduplicateArticles(articles) {
        const seenTitles = new Set();
        const seenImages = new Set();
        return (Array.isArray(articles) ? articles : []).filter(article => {
            const title = String(article.title || '').trim().toLowerCase().replace(/\s+/g, ' ');
            const image = String(article.image_url || '').trim().toLowerCase();
            if (title && seenTitles.has(title)) return false;
            if (image && seenImages.has(image)) return false;
            if (title) seenTitles.add(title);
            if (image) seenImages.add(image);
            return true;
        });
    }

    function deduplicateRenderedCards() {
        const seenTitles = new Set();
        const seenImages = new Set();
        document.querySelectorAll('#newsGrid article').forEach(card => {
            const title = (card.querySelector('h3')?.textContent || '').trim().toLowerCase().replace(/\s+/g, ' ');
            const image = (card.querySelector('img')?.getAttribute('src') || '').trim().toLowerCase();
            if ((title && seenTitles.has(title)) || (image && seenImages.has(image))) {
                card.remove();
                return;
            }
            if (title) seenTitles.add(title);
            if (image) seenImages.add(image);
        });
    }

    // Carrega do arquivo estático (para compatibilidade total com GitHub Pages)
    async function loadFromStaticJson(page, perPage, categoryFilter = null) {
        const cat = (categoryFilter !== null ? categoryFilter : currentCategory).toLowerCase();

        // Sempre busca fresco se for página 1 ou forçado
        if (!staticArticlesCache) {
            const jsonUrls = [
                `./data/articles.json?t=${Date.now()}`,
                `../data/articles.json?t=${Date.now()}`,
                `/data/articles.json?t=${Date.now()}`,
                `data/articles.json?t=${Date.now()}`
            ];
            for (const url of jsonUrls) {
                try {
                    const r = await fetch(url, { cache: 'no-store' });
                    if (r.ok) {
                        staticArticlesCache = await r.json();
                        break;
                    }
                } catch (e) {
                    // continua tentando próximo caminho
                }
            }
        }

        if (!staticArticlesCache || !Array.isArray(staticArticlesCache)) {
            return { articles: [], has_more: false };
        }

        let filtered = deduplicateArticles(staticArticlesCache);
        if (cat && cat !== 'todas') {
            filtered = filtered.filter(a => (a.category || '').toLowerCase() === cat);
        }
        if (currentQuery) {
            filtered = filtered.filter(a => 
                (a.title || '').toLowerCase().includes(currentQuery) || 
                (a.description || '').toLowerCase().includes(currentQuery)
            );
        }

        const offset = (page - 1) * perPage;
        const slice = filtered.slice(offset, offset + perPage);
        const more = (offset + perPage) < filtered.length;

        return {
            articles: slice,
            has_more: more,
            total: filtered.length
        };
    }

    function updateHero(item) {
        if (!item) return;
        const heroSection = document.getElementById('heroSection');
        const heroLink = document.getElementById('heroLink');
        const heroImage = document.getElementById('heroImage');
        const heroCategory = document.getElementById('heroCategory');
        const heroTitle = document.getElementById('heroTitle');
        const heroDescription = document.getElementById('heroDescription');
        const heroAuthor = document.getElementById('heroAuthor');
        const heroTime = document.getElementById('heroTime');
        if (!heroSection) return;
        const fallback = 'https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=1200&q=80';
        heroSection.classList.remove('hidden');
        if (heroLink) heroLink.href = item.open_url || `noticia/${item.slug || item.id}/index.html`;
        if (heroImage) { heroImage.src = item.image_url || fallback; heroImage.alt = item.title || ''; }
        if (heroCategory) heroCategory.textContent = item.category || '';
        if (heroTitle) heroTitle.textContent = item.title || '';
        if (heroDescription) heroDescription.textContent = item.short_summary || item.description || '';
        if (heroAuthor) heroAuthor.textContent = item.author || 'Redação Explore';
        if (heroTime) heroTime.textContent = item.time_ago || 'recente';
    }

    function createCardElement(item) {
        const card = document.createElement('article');
        card.className = 'group flex flex-col justify-between opacity-0 translate-y-4 transition-all duration-500 ease-out';
        card.setAttribute('data-article-id', item.id);

        const defaultCover = 'https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=800&q=80';
        const coverImg = item.image_url || defaultCover;
        const targetUrl = item.open_url || `noticia/${item.slug || item.id}/index.html`;

        card.innerHTML = `
            <a href="${targetUrl}" class="block space-y-3">
                <div class="aspect-16/10 rounded-xl overflow-hidden bg-neutral-100">
                    <img src="${coverImg}"
                         alt="${escapeHtml(item.title)}"
                         onerror="this.src='${defaultCover}'"
                         class="w-full h-full object-cover group-hover:scale-105 transition duration-500">
                </div>
                <div class="text-[10px] font-bold uppercase tracking-widest text-neutral-400">
                    ${escapeHtml(item.category)}
                </div>
                <h3 class="font-serif text-lg font-semibold leading-snug text-neutral-900 group-hover:text-blue-700 transition line-clamp-2">
                    ${escapeHtml(item.title)}
                </h3>
                ${item.short_summary || item.description ? `
                    <p class="text-xs text-neutral-600 line-clamp-2 leading-relaxed">
                        ${escapeHtml(item.short_summary || item.description)}
                    </p>
                ` : ''}
            </a>
            <div class="pt-3 border-t border-neutral-100 mt-4 flex items-center justify-between text-[11px] text-neutral-400">
                <span class="truncate max-w-[150px]">${escapeHtml(item.author || 'Explore')}</span>
                <span>${escapeHtml(item.time_ago || 'recente')}</span>
            </div>
        `;
        return card;
    }

    async function loadMoreArticles() {
        if (isLoading || !hasMore || !newsGrid) return;
        isLoading = true;
        if (loader) loader.classList.remove('hidden');

        try {
            const nextPage = currentPage + 1;
            let articles = [];
            let more = false;

            try {
                const params = new URLSearchParams({
                    page: nextPage,
                    per_page: 12,
                    categoria: currentCategory,
                    q: currentQuery
                });

                const response = await fetch(`/api/noticias?${params.toString()}`);
                if (response.ok) {
                    const data = await response.json();
                    articles = deduplicateArticles(data.articles || []);
                    more = data.has_more;
                } else {
                    const staticData = await loadFromStaticJson(nextPage, 12);
                    articles = deduplicateArticles(staticData.articles);
                    more = staticData.has_more;
                }
            } catch (netErr) {
                const staticData = await loadFromStaticJson(nextPage, 12);
                articles = deduplicateArticles(staticData.articles);
                more = staticData.has_more;
            }

            if (articles.length > 0) {
                articles.forEach(item => {
                    if (document.querySelector(`[data-article-id="${item.id}"]`)) return;
                    const card = createCardElement(item);
                    newsGrid.appendChild(card);
                    requestAnimationFrame(() => {
                        card.classList.remove('opacity-0', 'translate-y-4');
                    });
                });
                currentPage = nextPage;
                hasMore = more;
            } else {
                hasMore = false;
            }

            if (!hasMore && endNotice) {
                endNotice.classList.remove('hidden');
            }
        } catch (err) {
            console.warn('Erro ao carregar mais notícias:', err);
        } finally {
            isLoading = false;
            if (loader) loader.classList.add('hidden');
        }
    }

    // Observador para carregar mais na rolagem
    if (trigger && feedContainer) {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting && hasMore && !isLoading) {
                    loadMoreArticles();
                }
            });
        }, { root: null, rootMargin: '250px', threshold: 0.1 });

        if (hasMore) observer.observe(trigger);
    }

    // 5. Função de Atualização Global da Página (Manual e Automática)
    async function refreshPageFeed(forceSync = false) {
        lastRefreshTime = Date.now();
        updateWorldTimezones();

        // 1. Tenta acionar a sincronização no backend Flask se disponível
        if (forceSync) {
            try {
                await fetch('/sincronizar?format=json', {
                    method: 'GET',
                    headers: { 'Accept': 'application/json' }
                });
            } catch (e) {
                // Se estiver no GitHub Pages ou sem backend, continua sem falhar
            }
        }

        // Se estivermos na página inicial (onde existe o newsGrid)
        if (newsGrid) {
            try {
                let firstBatch = [];
                let more = false;

                // Tenta API do backend
                try {
                    const params = new URLSearchParams({
                        page: 1,
                        per_page: 13,
                        categoria: currentCategory,
                        q: currentQuery,
                        t: Date.now()
                    });
                    const res = await fetch(`/api/noticias?${params.toString()}`);
                    if (res.ok) {
                        const data = await res.json();
                        firstBatch = deduplicateArticles(data.articles || []);
                        more = data.has_more;
                    } else {
                        const staticData = await loadFromStaticJson(1, 13);
                        firstBatch = deduplicateArticles(staticData.articles);
                        more = staticData.has_more;
                    }
                } catch (e) {
                    const staticData = await loadFromStaticJson(1, 13);
                    firstBatch = deduplicateArticles(staticData.articles);
                    more = staticData.has_more;
                }

                if (firstBatch.length > 0) {
                    // O destaque sempre pertence à categoria/filtro atualmente selecionado.
                    updateHero(firstBatch[0]);
                    newsGrid.innerHTML = '';
                    firstBatch.slice(1).forEach(item => {
                        const card = createCardElement(item);
                        newsGrid.appendChild(card);
                        requestAnimationFrame(() => {
                            card.classList.remove('opacity-0', 'translate-y-4');
                        });
                    });
                    currentPage = 1;
                    hasMore = more;
                    if (endNotice) {
                        if (hasMore) endNotice.classList.add('hidden');
                        else endNotice.classList.remove('hidden');
                    }
                }
            } catch (err) {
                console.warn('Erro ao atualizar feed:', err);
            }
        }
    }

    // 6. Botão de Atualizar Manual (Elimina erro 405 Not Allowed)
    window.handleManualRefresh = async function(event) {
        if (event) {
            event.preventDefault();
            event.stopPropagation();
        }

        const icon = document.getElementById('refreshNewsIcon');
        const text = document.getElementById('refreshNewsText');
        const btn = document.getElementById('refreshNewsBtn');

        if (icon) icon.classList.add('animate-spin');
        if (text) text.textContent = 'Atualizando...';
        if (btn) btn.disabled = true;

        try {
            await refreshPageFeed(true);
            if (text) text.textContent = 'Atualizado!';
        } catch (e) {
            if (text) text.textContent = 'Atualizado!';
        } finally {
            if (btn) btn.disabled = false;
            setTimeout(() => {
                if (icon) icon.classList.remove('animate-spin');
                if (text) text.textContent = 'Atualizar';
            }, 1800);
        }
    };

    // 7. ATUALIZAÇÃO AUTOMÁTICA TODA VEZ QUE MUDAR DE PÁGINA OU CATEGORIA
    // A) Toda vez que o leitor retornar a esta página (ex: clicou em voltar da matéria)
    window.addEventListener('pageshow', (event) => {
        // Atualiza somente ao retornar pelo histórico; a carga inicial não toca no DOM.
        if (event.persisted) refreshPageFeed(false);
    });

    // B) Toda vez que a navegação do histórico mudar (botões avançar/voltar)
    window.addEventListener('popstate', () => {
        const urlParams = new URLSearchParams(window.location.search);
        currentCategory = (urlParams.get('categoria') || 'todas').toLowerCase();
        currentQuery = (urlParams.get('q') || '').toLowerCase();
        refreshPageFeed(false);
    });

    // C) Transição suave e atualização automática instantânea ao clicar nas categorias
    const categoryLinks = document.querySelectorAll('nav a[href*="categoria="], nav a[href="{{ url_for(\'news.index\') }}"], nav a[href="/"], nav a[href="./index.html"]');
    categoryLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            const href = link.getAttribute('href') || '';
            const match = href.match(/categoria=([a-z0-9_-]+)/i);
            const targetCat = match ? match[1].toLowerCase() : 'todas';

            // Se for troca no front estático ou dinâmico
            if (newsGrid) {
                // Atualiza visualmente o estilo da aba ativa
                categoryLinks.forEach(l => {
                    l.className = 'px-2.5 py-1 rounded transition whitespace-nowrap text-neutral-500 hover:text-neutral-900';
                });
                link.className = 'px-2.5 py-1 rounded transition whitespace-nowrap text-neutral-950 border-b-2 border-neutral-900 font-bold';

                currentCategory = targetCat;
                if (feedContainer) feedContainer.setAttribute('data-category', targetCat);
                const feedTitle = document.getElementById('feedCategoryTitle');
                if (feedTitle) feedTitle.textContent = targetCat === 'todas' ? 'Edição de Hoje' : targetCat;

                // Atualiza a URL sem recarregar tela inteira
                const newUrl = targetCat === 'todas' ? (window.location.pathname || './index.html') : `?categoria=${targetCat}`;
                window.history.pushState({ category: targetCat }, '', newUrl);

                // Atualiza o feed de matérias automaticamente com dados novos
                refreshPageFeed(false);
                e.preventDefault();
            }
        });
    });

    // URLs abertas diretamente com categoria/filtro também carregam o lote correto.
    if (currentCategory !== 'todas' || currentQuery) {
        refreshPageFeed(false);
    }


});
