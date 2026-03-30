// ===================================
// Main JavaScript — hung.github.io
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

// ---------- Timeline helper ----------
function alignTimelineDots() {
  document.querySelectorAll('.timeline-item').forEach(item => {
    const dot = item.querySelector('.timeline-dot');
    const wrapper = item.querySelector('.timeline-content-wrapper');
    if (dot && wrapper) {
      const offset = wrapper.offsetTop + wrapper.offsetHeight / 2 - dot.offsetHeight / 2;
      dot.style.top = offset + 'px';
    }
  });
}

// ---------- Dynamic Posts Loading ----------
async function loadPosts() {
  const newsList = document.querySelector('[data-json]') || document.querySelector('.news-list');
  if (!newsList) return;

  try {
    const isPostPage = window.location.pathname.includes('/posts/') ||
      window.location.pathname.includes('/math-posts/') ||
      window.location.pathname.includes('/english_posts/');
    const isHomePage = document.querySelector('.home-name-section') !== null;
    const jsonFiles = isHomePage && newsList.dataset.jsonSources
      ? newsList.dataset.jsonSources.split(',').map(file => file.trim()).filter(Boolean)
      : [newsList.dataset.json || 'posts.json'];

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

    const layout = newsList.dataset.layout || (isHomePage ? 'home' : 'news');
    let postsToDisplay = posts;

    // Filter to latest 3 for home page
    if (isHomePage) {
      postsToDisplay = posts.slice(0, 3);
    }

    // Clear static fallback items
    newsList.innerHTML = '';

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

    postsToDisplay.forEach(post => {
      // Date formatting logic
      const dateObj = new Date(post.date);
      const options = { year: 'numeric', month: 'long', day: 'numeric' };
      const formattedDate = dateObj.toLocaleDateString('en-US', options) !== 'Invalid Date' ?
                            dateObj.toLocaleDateString('en-US', options) :
                            post.date;

      const article = document.createElement(layout === 'learning-log' ? 'a' : isHomePage ? 'div' : 'article');
      article.className = layout === 'learning-log' ? 'log-entry' : isHomePage ? 'home-news-item' : 'news-item';
      if (layout === 'learning-log') {
        article.href = post.url;
      }

      const tagHtml = buildTagHtml(post);

      const repoHtml = post.repo
        ? `<p><a href="${post.repo}" class="card-link" target="_blank" rel="noopener">Repository</a></p>`
        : '';

      if (layout === 'learning-log') {
        article.innerHTML = `
          <div class="log-date">${formattedDate}</div>
          ${tagHtml}
          <h3>${post.title}</h3>
          <p>${post.description}</p>
          ${repoHtml}
        `;
      } else if (!isHomePage) {
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

      newsList.appendChild(article);
    });
  } catch (err) {
    console.error("Failed to load posts:", err);
  }
}


document.addEventListener('DOMContentLoaded', () => {
  initNavbar();
  initTopicToggles();
  initTopicTagTooltips();
  alignTimelineDots();
  loadPosts();
});

window.addEventListener('resize', alignTimelineDots);
