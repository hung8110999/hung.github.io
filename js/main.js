// ===================================
// Main JavaScript - hung.github.io
// Minimalist Light Blue Theme
// ===================================

// ---------- Navbar ----------
function initNavbar() {
  const toggle = document.querySelector('.nav-toggle');
  const navLinks = document.querySelector('.nav-links');

  const closeMobileDropdowns = () => {
    document.querySelectorAll('.nav-dropdown.dropdown-open').forEach((dd) =>
      dd.classList.remove('dropdown-open')
    );
  };

  const isMobileNav = () => window.matchMedia('(max-width: 768px)').matches;

  // Mobile toggle
  if (toggle && navLinks) {
    toggle.addEventListener('click', () => {
      toggle.classList.toggle('open');
      navLinks.classList.toggle('open');
      if (!navLinks.classList.contains('open')) closeMobileDropdowns();
    });

    // Close menu on link click (excluding dropdown trigger; submenu links close below)
    navLinks.querySelectorAll('a').forEach((link) => {
      const parent = link.parentElement;
      if (parent && parent.classList.contains('nav-dropdown') && link.nextElementSibling?.classList?.contains('dropdown-menu')) {
        link.addEventListener('click', (e) => {
          if (!isMobileNav()) return;
          e.preventDefault();
          const dd = parent;
          const willOpen = !dd.classList.contains('dropdown-open');
          closeMobileDropdowns();
          if (willOpen) dd.classList.add('dropdown-open');
        });
        return;
      }
      link.addEventListener('click', () => {
        toggle.classList.remove('open');
        navLinks.classList.remove('open');
        closeMobileDropdowns();
      });
    });

    document.addEventListener('click', (e) => {
      if (!isMobileNav()) return;
      if (e.target.closest('.nav-dropdown')) return;
      closeMobileDropdowns();
    });
  }
}

function initTopicTagTooltips() {
  const mq = window.matchMedia('(hover: none), (pointer: coarse)');

  const bind = () => {
    if (!mq.matches) return;
    document.querySelectorAll('.topic-tag-wrapper .topic-tag').forEach((tag) => {
      if (tag.dataset.touchTipBound === '1') return;
      tag.dataset.touchTipBound = '1';
      tag.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        const wrap = tag.closest('.topic-tag-wrapper');
        const open = wrap.classList.contains('is-expanded');
        document.querySelectorAll('.topic-tag-wrapper.is-expanded').forEach((w) =>
          w.classList.remove('is-expanded')
        );
        if (!open) wrap.classList.add('is-expanded');
      });
    });
  };

  bind();
  mq.addEventListener('change', bind);

  document.addEventListener('click', (e) => {
    if (!mq.matches) return;
    if (e.target.closest('.topic-tag-wrapper')) return;
    document.querySelectorAll('.topic-tag-wrapper.is-expanded').forEach((w) =>
      w.classList.remove('is-expanded')
    );
  });
}

// ---------- Topic Toggles (Study Pages) ----------
function initTopicToggles() {
  document.querySelectorAll('.topic-header').forEach(header => {
    header.addEventListener('click', () => {
      const card = header.closest('.topic-card');
      // Optional: Close others
      document.querySelectorAll('.topic-card.open').forEach(openCard => {
        if (openCard !== card) openCard.classList.remove('open');
      });
      card.classList.toggle('open');
    });
  });
}

// Timeline dots are centred purely in CSS (.timeline-dot / .timeline-content-wrapper::before);
// the old JS that wrote an inline `top` fought those rules and left the connector detached.

/** Wide-screen margin notes: per side (left / right), nudge top so same-side notes do not overlap. */
function initMarginNotesStacking() {
  const body = document.querySelector('.blog-post-body');
  if (!body) return;

  const listNotes = () => Array.from(body.querySelectorAll('.blog-post-notes'));
  if (!listNotes().length) return;

  const mq = window.matchMedia('(min-width: 1280px)');
  let raf = null;
  let debounceId = null;
  /** Debounce resize/observation/MathJax: avoids dozens of layout passes while the article body is still settling. */
  const DEBOUNCE_MS = 120;

  let resizeObserver = null;

  const stackGapPx = () => {
    const raw = getComputedStyle(body).getPropertyValue('--blog-post-notes-stack-gap').trim();
    const n = parseFloat(raw);
    return Number.isFinite(n) ? n : 20;
  };

  const noteSide = (el) => (el.classList.contains('blog-post-notes--left') ? 'left' : 'right');

  const stackOneSide = (group, gap) => {
    if (group.length < 2) return;

    const heights = group.map((el) => el.getBoundingClientRect().height);
    const naturalTops = group.map((el) => el.offsetTop);
    let prevBottom = 0;

    for (let i = 0; i < group.length; i++) {
      const floor = i === 0 ? naturalTops[i] : prevBottom + gap;
      const t = Math.max(naturalTops[i], floor);
      prevBottom = t + heights[i];
      if (Math.abs(t - naturalTops[i]) > 0.5) {
        group[i].style.top = `${Math.round(t * 100) / 100}px`;
      } else {
        group[i].style.top = '';
      }
    }
  };

  const run = () => {
    const notes = listNotes();
    if (!notes.length) return;

    if (!mq.matches) {
      notes.forEach((el) => {
        el.style.top = '';
      });
      return;
    }

    const gap = stackGapPx();

    notes.forEach((el) => {
      el.style.top = '';
    });
    void body.offsetHeight;

    const left = [];
    const right = [];
    notes.forEach((el) => {
      if (noteSide(el) === 'left') left.push(el);
      else right.push(el);
    });

    stackOneSide(left, gap);
    stackOneSide(right, gap);
  };

  const schedule = () => {
    if (raf != null) cancelAnimationFrame(raf);
    raf = requestAnimationFrame(() => {
      raf = null;
      run();
    });
  };

  const debouncedSchedule = () => {
    if (debounceId != null) clearTimeout(debounceId);
    debounceId = setTimeout(() => {
      debounceId = null;
      schedule();
    }, DEBOUNCE_MS);
  };

  const syncResizeObserver = () => {
    if (typeof ResizeObserver === 'undefined') return;
    if (!resizeObserver) {
      resizeObserver = new ResizeObserver(() => {
        if (!mq.matches) return;
        debouncedSchedule();
      });
    }
    resizeObserver.disconnect();
    if (mq.matches) {
      resizeObserver.observe(body);
    }
  };

  schedule();
  syncResizeObserver();

  mq.addEventListener('change', () => {
    syncResizeObserver();
    schedule();
  });

  window.addEventListener('resize', debouncedSchedule);

  listNotes().forEach((aside) => {
    aside.querySelectorAll('img').forEach((img) => {
      if (!img.complete) img.addEventListener('load', schedule, { once: true });
    });
  });

  if (window.MathJax && window.MathJax.startup && window.MathJax.startup.promise) {
    window.MathJax.startup.promise.then(debouncedSchedule).catch(() => {});
  }
}

// ---------- Dynamic Posts Loading ----------
async function loadPosts() {
  const targets = Array.from(document.querySelectorAll('[data-json], [data-json-sources]'));
  if (!targets.length) return;

  try {
    const isPostPage = window.location.pathname.includes('/posts/') ||
      window.location.pathname.includes('/math-posts/') ||
      window.location.pathname.includes('/english_posts/') ||
      window.location.pathname.includes('/coding_posts/');

    // Tag-to-CSS-class mapping for math posts (English display names)
    const tagToClass = {
      'Calculus': 'bg-calculus',
      'Algebra': 'bg-algebra',
      'Linear Algebra': 'bg-linear',
      'Statistics': 'bg-stats',
      'Discrete Math': 'bg-discrete',
      'Reading': 'bg-reading',
      'Writing': 'bg-writing',
      'Speaking': 'bg-speaking',
      'Listening': 'bg-listening',
      'Grammar': 'bg-grammar',
      'Vocabulary': 'bg-vocab',
      'Algorithms': 'bg-algo',
      'Web': 'bg-web',
      'Web Dev': 'bg-web',
      'AI': 'bg-ai',
      'AI & ML': 'bg-ai',
      'Systems': 'bg-sys'
    };

    const postTagsList = (post) => {
      if (Array.isArray(post.tags) && post.tags.length) {
        return post.tags.map((t) => String(t).trim()).filter(Boolean);
      }
      if (post.tag) return [String(post.tag).trim()].filter(Boolean);
      return [];
    };

    const buildTagHtml = (post) => {
      const tags = postTagsList(post);
      if (!tags.length) return '';
      const inner = tags
        .map((t) => {
          const cls = tagToClass[t] || 'bg-algebra';
          return `<span class="post-tag ${cls}">${t}</span>`;
        })
        .join('');
      return `<div class="post-tags">${inner}</div>`;
    };

    const loadForTarget = async (target) => {
      const isHomeTarget = target.classList.contains('news-list') && !!target.dataset.jsonSources;
      const jsonFiles = isHomeTarget && target.dataset.jsonSources
        ? target.dataset.jsonSources.split(',').map(file => file.trim()).filter(Boolean)
        : [target.dataset.json || 'posts.json'];

      const postsFromSources = await Promise.all(
        jsonFiles.map(async (jsonFile) => {
          const jsonPath = isPostPage ? `../${jsonFile}` : jsonFile;
          const response = await fetch(jsonPath, { cache: 'no-store' });
          if (!response.ok) return [];

          const posts = await response.json();
          return posts.map(post => ({ ...post, _jsonFile: jsonFile }));
        })
      );

      const posts = postsFromSources
        .flat()
        .sort((a, b) => new Date(b.date) - new Date(a.date));

      const layout = target.dataset.layout || (isHomeTarget ? 'home' : 'news');
      let postsToDisplay = isHomeTarget ? posts.slice(0, 3) : posts;
      if (layout === 'repo') {
        postsToDisplay = posts.filter((post) => post.repo);
      }

      target.innerHTML = '';
      if (!postsToDisplay.length) {
        // Every post here may be unlisted (`hide: true`); say so rather than
        // leaving a section heading floating above empty space.
        target.innerHTML = '<p class="posts-empty">No posts published yet.</p>';
        return;
      }

      postsToDisplay.forEach((post) => {
        const dateObj = new Date(post.date);
        const options = { year: 'numeric', month: 'long', day: 'numeric' };
        const formattedDate = dateObj.toLocaleDateString('en-US', options) !== 'Invalid Date'
          ? dateObj.toLocaleDateString('en-US', options)
          : post.date;

        const tagHtml = buildTagHtml(post);

        if (layout === 'repo') {
          const tags = postTagsList(post);
          const repoMetaLeft = tags.length
            ? tags.map((t) => `<span>${t}</span>`).join('')
            : '<span>Repository</span>';
          const repoCard = document.createElement('a');
          repoCard.className = 'repo-card';
          repoCard.href = post.repo;
          repoCard.target = '_blank';
          repoCard.rel = 'noopener';
          repoCard.innerHTML = `
            <div class="repo-name">🔗 ${post.title}</div>
            <p class="repo-desc">${post.description || ''}</p>
            <div class="repo-meta">
              ${repoMetaLeft}
              <span>${formattedDate}</span>
            </div>
          `;
          target.appendChild(repoCard);
          return;
        }

        const article = document.createElement(layout === 'learning-log' ? 'a' : isHomeTarget ? 'div' : 'article');
        article.className = layout === 'learning-log' ? 'log-entry' : isHomeTarget ? 'home-news-item' : 'news-item';
        if (layout === 'learning-log') {
          article.href = post.url;
        }

        if (layout === 'learning-log') {
          article.innerHTML = `
            <div class="log-date">${formattedDate}</div>
            ${tagHtml}
            <h3>${post.title}</h3>
            <p>${post.description}</p>
          `;
        } else if (!isHomeTarget) {
          article.style.transition = 'transform 0.2s, box-shadow 0.2s';
          article.innerHTML = `
            <div class="news-date">${formattedDate}</div>
            ${tagHtml}
            <h3 style="font-size: 1.5rem; margin-top: 0.5rem; margin-bottom: 0.5rem;">
                <a href="${post.url}" style="color: var(--text-heading);">${post.title}</a>
            </h3>
            <p style="margin-bottom: 1rem;">${post.description}</p>
            <a href="${post.url}" class="card-link">Read more →</a>
          `;
        } else {
          article.innerHTML = `
            <div class="news-date">${formattedDate}</div>
            <h3><a href="${post.url}" style="color: inherit; text-decoration: none;">${post.title}</a></h3>
            <p>${post.description}</p>
          `;
        }

        target.appendChild(article);
      });
    };

    await Promise.all(targets.map((target) => loadForTarget(target)));
  } catch (err) {
    console.error("Failed to load posts:", err);
  }
}


document.addEventListener('DOMContentLoaded', () => {
  initNavbar();
  initTopicToggles();
  initTopicTagTooltips();
  initMarginNotesStacking();
  loadPosts();
});
