// ===================================
// Main JavaScript — hung.github.io
// Minimalist Light Blue Theme
// ===================================

document.addEventListener('DOMContentLoaded', () => {
  initNavbar();
  initTopicToggles();
});

// ---------- Navbar ----------
function initNavbar() {
  const toggle = document.querySelector('.nav-toggle');
  const navLinks = document.querySelector('.nav-links');

  // Mobile toggle
  if (toggle && navLinks) {
    toggle.addEventListener('click', () => {
      toggle.classList.toggle('open');
      navLinks.classList.toggle('open');
    });

    // Close menu on link click (excluding dropdown toggles)
    navLinks.querySelectorAll('a').forEach(link => {
      if (!link.parentElement.classList.contains('nav-dropdown')) {
        link.addEventListener('click', () => {
          toggle.classList.remove('open');
          navLinks.classList.remove('open');
        });
      }
    });
  }
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
    // Use data-json if set (e.g. math_posts.json on math.html), else posts.json
    const jsonFile = newsList.dataset.json || 'posts.json';
    const isPostPage = window.location.pathname.includes('/posts/') || window.location.pathname.includes('/math-posts/');
    const jsonPath = isPostPage ? `../${jsonFile}` : jsonFile;

    const response = await fetch(jsonPath);
    if (!response.ok) return;
    const posts = await response.json();

    const isHomePage = document.querySelector('.home-name-section') !== null;
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
      'Discrete Math': 'bg-discrete'
    };

    const isMathPosts = jsonFile.includes('math_posts');

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

      const tag = post.tag || '';
      const tagClass = tagToClass[tag] || 'bg-algebra';
      const tagHtml = (isMathPosts && tag) ? `<div class="post-tags"><span class="post-tag ${tagClass}">${tag}</span></div>` : '';

      if (layout === 'learning-log') {
        article.innerHTML = `
          <div class="log-date">${formattedDate}</div>
          ${tagHtml}
          <h3>${post.title}</h3>
          <p>${post.description}</p>
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
  alignTimelineDots();
  loadPosts();
});

window.addEventListener('resize', alignTimelineDots);
