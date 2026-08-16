// scrollspy.js
// Highlights the nav link matching the section currently in view.

export function initScrollSpy() {
  const nav = document.getElementById('fcrd2Nav');
  if (!nav) return;

  const sections = getTopLevelSections();
  if (!sections.length) return;

  const links = Array.from(nav.querySelectorAll('a[href^="#"]'));
  if (!links.length) return;

  const linkForId = new Map();
  links.forEach((link) => {
    const href = link.getAttribute('href');
    if (!href || !href.startsWith('#')) return;
    const id = href.slice(1);
    if (id) linkForId.set(id, link);
  });

  const activateLink = (id) => {
    const activeLink = linkForId.get(id);
    if (!activeLink) return;
    links.forEach((link) => link.classList.remove('active'));
    activeLink.classList.add('active');
  };

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          activateLink(entry.target.id);
        }
      });
    },
    { rootMargin: '-45% 0px -45% 0px', threshold: 0 }
  );

  sections.forEach((section) => {
    if (section.id) observer.observe(section);
  });
}

function getTopLevelSections() {
  const container = document.querySelector('main') || document.body;
  return Array.from(container.children).filter(
    (el) => el.tagName === 'SECTION' && el.id
  );
}
