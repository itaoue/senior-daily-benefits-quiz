/* Senior Daily Benefits — paid-traffic quiz landing page */
const QUIZ_REDIRECT = 'https://www.yrxtrk.com/aff_c?offer_id=21738&aff_id=2259&aff_sub=quiz';
const questions = [
  { q: 'Are you currently paying more than $25/month for your cell phone bill?', a: ['Yes', 'No'] },
  { q: 'Do you own a home that was built before 1995?', a: ['Yes', 'No'] },
  { q: 'Do you have less than $10,000 in credit card debt?', a: ['Yes', 'No'] },
  { q: 'When was the last time you compared auto insurance rates?', a: ['In the last 6 months', 'Over a year ago', "I've never done it"] },
];
let current = 0;
const answers = {};

function captureTrack() {
  try {
    const key = 'sdb_track';
    let t = JSON.parse(sessionStorage.getItem(key) || 'null');
    if (!t) {
      const u = new URL(window.location.href);
      t = { referrer: document.referrer || '', landing_url: u.origin + u.pathname + u.search };
      ['utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term'].forEach(k => { t[k] = u.searchParams.get(k) || ''; });
      sessionStorage.setItem(key, JSON.stringify(t));
    }
    return t;
  } catch (e) { return {}; }
}
const TRACK = captureTrack();

function startQuiz() {
  document.getElementById('quiz-start').hidden = true;
  document.getElementById('quiz-body').hidden = false;
  showQuestion();
  const card = document.getElementById('quiz');
  if (card && window.innerWidth < 900) card.scrollIntoView({ behavior: 'smooth', block: 'start' });
}
function showQuestion() {
  const q = questions[current];
  document.getElementById('question').textContent = q.q;
  document.getElementById('question-counter').textContent = `Question ${current + 1} of ${questions.length}`;
  document.getElementById('dots').innerHTML = questions.map((_, i) => `<i class="${i <= current ? 'on' : ''}"></i>`).join('');
  const box = document.getElementById('options');
  box.innerHTML = '';
  q.a.forEach(opt => {
    const b = document.createElement('button');
    b.className = 'option'; b.type = 'button'; b.textContent = opt;
    b.onclick = () => { b.classList.add('picked'); selectAnswer(opt); };
    box.appendChild(b);
  });
}
function selectAnswer(answer) {
  answers[current] = answer;
  setTimeout(() => {
    current++;
    if (current < questions.length) showQuestion();
    else { document.getElementById('quiz-body').hidden = true; document.getElementById('quiz-email').hidden = false; }
  }, 350);
}
function submitEmail(event) {
  event.preventDefault();
  const form = event.target;
  const email = form.querySelector('input[type="email"]').value;
  const button = form.querySelector('button');
  const original = button.textContent;
  button.textContent = 'Checking…'; button.disabled = true;
  fetch('/api/submit-email', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, answers, track: Object.assign({ source: 'quiz' }, TRACK) }),
  })
    .then(r => r.json())
    .then(data => {
      if (data.success) {
        button.textContent = 'Success! Loading your results…';
        if (typeof nbpix !== 'undefined') nbpix('event', 'subscribe');
        setTimeout(() => { window.location.href = QUIZ_REDIRECT; }, 900);
      } else {
        alert('Error: ' + (data.error || 'Failed to submit email. Please try again.'));
        button.textContent = original; button.disabled = false;
      }
    })
    .catch(() => {
      alert('Network error. Please check your connection and try again.');
      button.textContent = original; button.disabled = false;
    });
}
// FAQ toggles
document.querySelectorAll('.faq-q').forEach(b => b.addEventListener('click', () => {
  const item = b.parentElement; const open = item.classList.toggle('open');
  b.setAttribute('aria-expanded', open ? 'true' : 'false');
}));
