const slides = [...document.querySelectorAll('.slide')];
const currentPage = document.getElementById('currentPage');
const pageTitle = document.getElementById('pageTitle');
const progressBar = document.getElementById('progressBar');
const prevBtn = document.getElementById('prevBtn');
const nextBtn = document.getElementById('nextBtn');
const hudRisk = document.getElementById('hudRisk');
const hudAnalysis = document.getElementById('hudAnalysis');

const initialIndex = Math.max(0, Math.min(slides.length - 1, Number(location.hash.slice(1)) - 1 || 0));
let activeIndex = -1;
let wheelLocked = false;
let touchStartX = 0;
let touchStartY = 0;

function render(index) {
  if (index === activeIndex && slides[index].classList.contains('active')) return;
  const previous = activeIndex >= 0 ? slides[activeIndex] : null;
  if (previous) {
    previous.classList.remove('active');
    previous.classList.add('leaving');
    window.setTimeout(() => previous.classList.remove('leaving'), 300);
  }

  activeIndex = Math.max(0, Math.min(slides.length - 1, index));
  const active = slides[activeIndex];
  active.classList.add('active');
  currentPage.textContent = String(activeIndex + 1).padStart(2, '0');
  pageTitle.textContent = active.dataset.title;
  progressBar.style.width = `${((activeIndex + 1) / slides.length) * 100}%`;
  hudRisk.textContent = active.dataset.risk;
  hudRisk.style.color = active.dataset.risk === 'LOW' ? 'var(--green)' : active.dataset.risk === 'HIGH' ? 'var(--red)' : 'var(--orange)';
  hudAnalysis.textContent = activeIndex >= 4 ? 'COMPLETE' : 'IDLE';
  prevBtn.disabled = activeIndex === 0;
  nextBtn.disabled = activeIndex === slides.length - 1;
  history.replaceState(null, '', `#${activeIndex + 1}`);
}

function move(delta) {
  const target = activeIndex + delta;
  if (target >= 0 && target < slides.length) render(target);
}

prevBtn.addEventListener('click', () => move(-1));
nextBtn.addEventListener('click', () => move(1));

document.addEventListener('keydown', event => {
  if (['ArrowRight', 'ArrowDown', 'PageDown', ' '].includes(event.key)) {
    event.preventDefault();
    move(1);
  }
  if (['ArrowLeft', 'ArrowUp', 'PageUp'].includes(event.key)) {
    event.preventDefault();
    move(-1);
  }
  if (event.key === 'Home') render(0);
  if (event.key === 'End') render(slides.length - 1);
});

document.addEventListener('wheel', event => {
  if (wheelLocked || Math.abs(event.deltaY) < 20) return;
  wheelLocked = true;
  move(event.deltaY > 0 ? 1 : -1);
  window.setTimeout(() => { wheelLocked = false; }, 650);
}, { passive: true });

document.addEventListener('touchstart', event => {
  touchStartX = event.changedTouches[0].clientX;
  touchStartY = event.changedTouches[0].clientY;
}, { passive: true });

document.addEventListener('touchend', event => {
  const deltaX = touchStartX - event.changedTouches[0].clientX;
  const deltaY = touchStartY - event.changedTouches[0].clientY;
  const delta = Math.abs(deltaX) > Math.abs(deltaY) ? deltaX : deltaY;
  if (Math.abs(delta) > 48) move(delta > 0 ? 1 : -1);
}, { passive: true });

slides.forEach(slide => slide.classList.remove('active'));
render(initialIndex);
