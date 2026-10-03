// Interações limpas, fusos horários em tempo real, Rolagem Infinita e Botão Voltar ao Topo
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

        backToTopBtn.addEventListener('click', () => {
            window.scrollTo({
                top: 0,
                behavior: 'smooth'
            });
        });
    }

    // 4. Rolagem Infinita (Infinite Scroll) com Suporte Híbrido (API Backend e Estático GitHub Pages)
    const feedContainer = document.getElementById('newsFeedContainer');
    const newsGrid = document.getElementById('newsGrid');
    const trigger = document.getElementById('infiniteScrollTrigger');
    const loader = document.getElementById('infiniteScrollLoader');
    const endNotice = document.getElementById('infiniteScrollEnd');

    if (feedContainer && newsGrid && trigger) {
        let currentPage = 1;
        let isLoading = false;
        let hasMore = feedContainer.getAttribute('data-has-more') === 'true';
        const category = (feedContainer.getAttribute('data-category') || 'todas').toLowerCase();
        const query = (feedContainer.getAttribute('data-query') || '').toLowerCase();
        let staticArticlesCache = null;

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

        // Função para carregar do arquivo estático (para compatibilidade total com GitHub Pages)
        async function loadFromStaticJson(page, perPage) {
            if (!staticArticlesCache) {
                // Tenta carregar o JSON estático gerado para o GitHub Pages
                const jsonUrls = ['./data/articles.json', '../data/articles.json', '/data/articles.json'];
                for (const url of jsonUrls) {
                    try {
                        const r = await fetch(url);
                        if (r.ok) {
                            staticArticlesCache = await r.json();
                            break;
                        }
                    } catch (e) {
                        // continua tentando o próximo caminho
                    }
                }
            }

            if (!staticArticlesCache || !Array.isArray(staticArticlesCache)) {
                return { articles: [], has_more: false };
            }

            // Filtragem local
            let filtered = staticArticlesCache;
            if (category && category !== 'todas') {
                filtered = filtered.filter(a => (a.category || '').toLowerCase() === category);
            }
            if (query) {
                filtered = filtered.filter(a => 
                    (a.title || '').toLowerCase().includes(query) || 
                    (a.description || '').toLowerCase().includes(query)
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

        async function loadMoreArticles() {
            if (isLoading || !hasMore) return;
            isLoading = true;

            if (loader) loader.classList.remove('hidden');

            try {
                const nextPage = currentPage + 1;
                let articles = [];
                let more = false;

                // Tenta primeiro a API dinâmica do backend
                try {
                    const params = new URLSearchParams({
                        page: nextPage,
                        per_page: 6,
                        categoria: category,
                        q: query
                    });

                    const response = await fetch(`/api/noticias?${params.toString()}`);
                    if (response.ok) {
                        const data = await response.json();
                        articles = data.articles || [];
                        more = data.has_more;
                    } else {
                        // Se retornou 404 (ex: rodando estaticamente no GitHub Pages), usa fallback estático
                        const staticData = await loadFromStaticJson(nextPage, 6);
                        articles = staticData.articles;
                        more = staticData.has_more;
                    }
                } catch (netErr) {
                    // Fallback para GitHub Pages
                    const staticData = await loadFromStaticJson(nextPage, 6);
                    articles = staticData.articles;
                    more = staticData.has_more;
                }

                if (articles.length > 0) {
                    articles.forEach(item => {
                        // Evita duplicatas de cards já visíveis na tela
                        if (document.querySelector(`[data-article-id="${item.id}"]`)) {
                            return;
                        }

                        const card = document.createElement('article');
                        card.className = 'group flex flex-col justify-between opacity-0 translate-y-4 transition-all duration-500 ease-out';
                        card.setAttribute('data-article-id', item.id);

                        const defaultCover = 'https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=800&q=80';
                        const coverImg = item.image_url || defaultCover;
                        const targetUrl = item.open_url || `noticia/${item.id}/index.html`;

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
                                ${item.description ? `
                                    <p class="text-xs text-neutral-600 line-clamp-2 leading-relaxed">
                                        ${escapeHtml(item.description)}
                                    </p>
                                ` : ''}
                            </a>
                            <div class="pt-3 border-t border-neutral-100 mt-4 flex items-center justify-between text-[11px] text-neutral-400">
                                <span class="truncate max-w-[150px]">${escapeHtml(item.author)}</span>
                                <span>${escapeHtml(item.time_ago)}</span>
                            </div>
                        `;

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

                if (!hasMore) {
                    if (endNotice) endNotice.classList.remove('hidden');
                    if (observer) observer.disconnect();
                }

            } catch (err) {
                console.warn('Erro ao carregar mais notícias:', err);
            } finally {
                isLoading = false;
                if (loader) loader.classList.add('hidden');
            }
        }

        // Observador de interseção para rolagem contínua
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting && hasMore && !isLoading) {
                    loadMoreArticles();
                }
            });
        }, {
            root: null,
            rootMargin: '250px',
            threshold: 0.1
        });

        if (hasMore) {
            observer.observe(trigger);
        } else {
            if (endNotice) endNotice.classList.remove('hidden');
        }
    }
});
