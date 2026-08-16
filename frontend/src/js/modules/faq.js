// faq.js
// Single-open accordion behavior for the FAQ section.

export function initFaq() {
  const faq = document.getElementById('fcrd2Faq');
  if (!faq) return;

  const items = Array.from(faq.querySelectorAll('.fcrd2-faq-item'));
  if (!items.length) return;

  items.forEach((item) => {
    const question = item.querySelector('.fcrd2-faq-q');
    if (!question) return;

    question.addEventListener('click', () => {
      const isOpen = item.classList.contains('open');

      items.forEach((sibling) => {
        if (sibling !== item) sibling.classList.remove('open');
      });

      item.classList.toggle('open', !isOpen);
    });
  });
}
