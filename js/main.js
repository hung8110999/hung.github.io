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
  const newsList = document.querySelector('.news-list');
  if (!newsList) return;

  try {
    // Determine the path to posts.json based on current page depth
    const isPostPage = window.location.pathname.includes('/posts/');
    const jsonPath = isPostPage ? '../posts.json' : 'posts.json';

    const response = await fetch(jsonPath);
    if (!response.ok) return;
    const posts = await response.json();

    const isHomePage = document.querySelector('.home-name-section') !== null;
    let postsToDisplay = posts;

    // Filter to latest 3 for home page
    if (isHomePage) {
      postsToDisplay = posts.slice(0, 3);
    }

    // Clear static fallback items
    newsList.innerHTML = '';

    postsToDisplay.forEach(post => {
      // Date formatting logic
      const dateObj = new Date(post.date);
      const options = { year: 'numeric', month: 'long', day: 'numeric' };
      const formattedDate = dateObj.toLocaleDateString('en-US', options) !== 'Invalid Date' ? 
                            dateObj.toLocaleDateString('en-US', { year: 'numeric', month: 'long' }) : 
                            post.date; 
      
      const article = document.createElement(isHomePage ? 'div' : 'article');
      article.className = isHomePage ? 'home-news-item' : 'news-item';
      
      if (!isHomePage) {
        article.style.transition = 'transform 0.2s, box-shadow 0.2s';
        article.innerHTML = `
          <div class="news-date">${formattedDate}</div>
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
