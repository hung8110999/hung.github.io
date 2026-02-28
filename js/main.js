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
