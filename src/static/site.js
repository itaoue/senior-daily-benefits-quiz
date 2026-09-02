/* Senior Daily Benefits — homepage behaviour */

// ─── Quiz (same questions, endpoint and redirect as before) ──────────────────
const QUIZ_REDIRECT = 'https://www.yrxtrk.com/aff_c?offer_id=21738&aff_id=2259&aff_sub=quiz';
const questions = [
  { q: 'Are you currently paying more than $25/month for your cell phone bill?', a: ['Yes', 'No'] },
  { q: 'Do you own a home that was built before 1995?', a: ['Yes', 'No'] },
  { q: 'Do you have less than $10,000 in credit card debt?', a: ['Yes', 'No'] },
  { q: 'When was the last time you compared auto insurance rates?', a: ['In the last 6 months', 'Over a year ago', "I've never done it"] },
];
let current = 0;
const answers = {};

function startQuiz() {
  document.getElementById('quiz-start').hidden = true;
  document.getElementById('quiz-body').hidden = false;
  showQuestion();
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
  button.textContent = 'Processing…'; button.disabled = true;
  fetch('/api/submit-email', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, answers }),
  })
    .then(r => r.json())
    .then(data => {
      if (data.success) {
        button.textContent = 'Success! Redirecting…';
        if (typeof nbpix !== 'undefined') nbpix('event', 'subscribe');
        setTimeout(() => { window.location.href = QUIZ_REDIRECT; }, 1200);
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

// ─── Newsletter forms (no redirect) ──────────────────────────────────────────
function subscribe(event, source) {
  event.preventDefault();
  const form = event.target;
  const email = form.querySelector('input[type="email"]').value;
  const button = form.querySelector('button');
  const original = button.textContent;
  button.textContent = 'Sending…'; button.disabled = true;
  fetch('/api/submit-email', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, answers: { source } }),
  })
    .then(r => r.json())
    .then(data => {
      if (data.success) {
        if (typeof nbpix !== 'undefined') nbpix('event', 'subscribe');
        const card = form.closest('.newsletter-card');
        if (card) { form.hidden = true; card.querySelector('.fineprint').hidden = true; card.querySelector('h3').hidden = true; card.querySelector('.muted').hidden = true; card.querySelector('.success').hidden = false; }
        else { button.textContent = '✓ Subscribed'; form.querySelector('input').value = ''; }
      } else { alert('Error: ' + (data.error || 'Please try again.')); button.textContent = original; button.disabled = false; }
    })
    .catch(() => { alert('Network error. Please try again.'); button.textContent = original; button.disabled = false; });
}

// ─── Topics ──────────────────────────────────────────────────────────────────
const topics = [
  { n: '01', icon: '🏥', color: '#1B2E5A', title: 'Medicare & Health Savings', tag: 'Health coverage', desc: 'What Medicare actually covers, what it doesn\'t, and the programs that pay your premiums and prescriptions.', items: ['Medicare Savings Programs', 'Extra Help for Part D', 'Advantage vs. Medigap', 'Open Enrollment dates'] },
  { n: '02', icon: '💰', color: '#D4521A', title: 'Social Security', tag: 'Retirement income', desc: 'When to claim, how overpayments and clawbacks work, and what recent rule changes mean for your check.', items: ['Claiming age decisions', 'Spousal & survivor benefits', 'Overpayment appeals', 'COLA updates'] },
  { n: '03', icon: '📋', color: '#2A5C3A', title: 'Taxes & Retirement Accounts', tag: 'Keep more of your money', desc: 'Senior deductions, required minimum distributions, and Roth conversion windows explained without jargon.', items: ['$6,000 senior deduction', 'RMD age 73 → 75', 'Roth conversions', 'Property tax relief'] },
  { n: '04', icon: '🏠', color: '#5C3A1B', title: 'Home, Utilities & Phone', tag: 'Monthly bills', desc: 'Discount programs on phone, internet, electricity, and heating that most eligible seniors never apply for.', items: ['Lifeline phone discount', 'LIHEAP energy aid', 'Weatherization help', 'Home repair grants'] },
  { n: '05', icon: '🛒', color: '#1B4A5C', title: 'Senior Discounts', tag: 'Everyday savings', desc: 'Store days, travel deals, memberships, and the discounts you only get if you ask for them.', items: ['Grocery & pharmacy days', 'Travel and hotels', 'AARP and memberships', 'Restaurants & entertainment'] },
  { n: '06', icon: '🛡️', color: '#3A1B5C', title: 'Scam Alerts', tag: 'Protect yourself', desc: 'The latest scams targeting people over 60, how to spot them, and what to do if you\'ve been contacted.', items: ['Medicare & SSA impostors', 'AI voice and obituary scams', 'Tap-to-pay theft', 'What to do next'] },
];
document.getElementById('topic-grid').innerHTML = topics.map(t => `
  <div class="topic reveal">
    <div class="topic-top"><div class="topic-num" style="background:${t.color}">${t.n}</div><span>${t.icon}</span></div>
    <h3 style="color:${t.color}">${t.title}</h3>
    <div class="tag">${t.tag}</div>
    <p>${t.desc}</p>
    <ul>${t.items.map(i => `<li>${i}</li>`).join('')}</ul>
    <a href="/articles/" style="color:${t.color}">Read articles →</a>
  </div>`).join('');

// ─── Latest articles (written by tools/build_articles.py) ────────────────────
fetch('/articles/latest.json').then(r => r.json()).then(list => {
  const grid = document.getElementById('latest-grid');
  if (!list.length) { grid.innerHTML = '<p class="muted">New articles coming soon.</p>'; return; }
  grid.innerHTML = list.slice(0, 3).map(a => `
    <a class="post reveal" href="/articles/${a.slug}.html">
      <span class="tag">${a.topic}</span>
      <h3>${a.title}</h3>
      <p>${a.summary}</p>
      <time>${a.date_nice}</time>
    </a>`).join('');
  observeReveals();
}).catch(() => { document.getElementById('latest-grid').innerHTML = '<p class="muted">New articles coming soon.</p>'; });

// ─── Testimonials ────────────────────────────────────────────────────────────
const stories = [
  { name: 'Margaret Johnson', who: 'Age 67, retired teacher', text: 'I had no idea I was eligible for a phone discount. The quiz helped me save $35 a month on my cell phone bill. That\'s over $400 a year.' },
  { name: 'Robert Williams', who: 'Age 72, veteran', text: 'The quiz revealed I was missing out on property tax exemptions. I saved $1,200 this year alone. I wish I had known about this sooner.' },
  { name: 'Dorothy Brown', who: 'Age 69, retired nurse', text: 'I discovered prescription assistance programs that cut my medication costs by 60%. It\'s been life-changing for my budget.' },
  { name: 'James Davis', who: 'Age 74, retired mechanic', text: 'I found utility assistance programs I never knew existed. My electric bill is now 40% lower every month.' },
  { name: 'Charles Wilson', who: 'Age 68, retired engineer', text: 'I discovered I was eligible for Medicare Savings Programs that I had never heard of. This quiz opened my eyes to so many opportunities.' },
];
let storyIdx = 0;
function showStory(i) {
  storyIdx = i;
  const s = stories[i], card = document.getElementById('story');
  card.querySelector('.story-text').textContent = '"' + s.text + '"';
  card.querySelector('.avatar').textContent = s.name.split(' ').map(w => w[0]).join('');
  card.querySelector('strong').textContent = s.name;
  card.querySelector('span').textContent = s.who;
  document.querySelectorAll('#story-dots button').forEach((b, j) => b.classList.toggle('on', j === i));
}
document.getElementById('story-dots').innerHTML = stories.map((_, i) => `<button aria-label="Story ${i + 1}" onclick="showStory(${i})"></button>`).join('');
showStory(0);
setInterval(() => showStory((storyIdx + 1) % stories.length), 6000);

// ─── FAQ ─────────────────────────────────────────────────────────────────────
const faqs = [
  ['Is the quiz really free?', 'Yes. There is no cost, no credit card, and no obligation. We earn a commission when readers sign up for some partner offers, which is how we keep everything free. That never changes which programs we tell you about.'],
  ['Do I have to be low-income to qualify for anything?', 'No. Some programs like Medicare Savings Programs and LIHEAP have income limits, but property tax exemptions, senior discounts, the $6,000 senior tax deduction, and most phone and insurance savings apply regardless of income.'],
  ['I already have Medicare. What else could I be missing?', 'Quite a lot. Extra Help for prescriptions, Medicare Savings Programs that pay your Part B premium, and state pharmacy assistance programs are all separate from basic Medicare and require their own application.'],
  ['What happens after I enter my email?', 'You see your quiz results immediately and get our daily benefits email. You can unsubscribe with one click at the bottom of any message.'],
  ['Are you affiliated with the government?', 'No. Senior Daily Benefits is an independent publisher. We link to official sources like SSA.gov and Medicare.gov so you can verify everything and apply directly.'],
  ['How often will you email me?', 'One short email each weekday morning. Occasionally an extra alert for a deadline like Medicare Open Enrollment.'],
];
document.getElementById('faq-list').innerHTML = faqs.map((f, i) => `
  <div class="faq-item">
    <button class="faq-q" onclick="this.parentElement.classList.toggle('open')"><span><b>${String(i + 1).padStart(2, '0')}</b>${f[0]}</span><i>+</i></button>
    <div class="faq-a">${f[1]}</div>
  </div>`).join('');

// ─── Counters + scroll reveal ────────────────────────────────────────────────
function animateCounters() {
  document.querySelectorAll('.stat-num').forEach(el => {
    const target = +el.dataset.count, pre = el.dataset.prefix || '', suf = el.dataset.suffix || '';
    let start = null;
    const step = ts => {
      if (!start) start = ts;
      const p = Math.min((ts - start) / 1800, 1), eased = 1 - Math.pow(1 - p, 3);
      el.textContent = pre + Math.floor(eased * target).toLocaleString() + suf;
      if (p < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  });
}
const statsObs = new IntersectionObserver(([e]) => { if (e.isIntersecting) { animateCounters(); statsObs.disconnect(); } }, { threshold: .3 });
statsObs.observe(document.querySelector('.stats'));

const revealObs = new IntersectionObserver(entries => entries.forEach(e => { if (e.isIntersecting) e.target.classList.add('visible'); }), { threshold: .1 });
function observeReveals() { document.querySelectorAll('.reveal:not(.visible)').forEach(el => revealObs.observe(el)); }
observeReveals();

document.getElementById('year').textContent = new Date().getFullYear();
document.querySelectorAll('.mobile-menu a').forEach(a => a.addEventListener('click', () => document.body.classList.remove('menu-open')));
