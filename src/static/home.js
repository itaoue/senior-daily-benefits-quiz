if (!window.__sdbHome) { window.__sdbHome = true;
/* Senior Daily Benefits — homepage: newsletter signup + attribution capture */
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

function subscribe(event, source) {
  event.preventDefault();
  const form = event.target;
  const email = form.querySelector('input[type="email"]').value;
  const button = form.querySelector('button');
  const original = button.textContent;
  button.textContent = 'Sending…'; button.disabled = true;
  fetch('/api/submit-email', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, answers: { source }, track: Object.assign({ source: 'newsletter-' + source }, TRACK) }),
  })
    .then(r => r.json())
    .then(data => {
      if (data.success) {
        if (typeof nbpix !== 'undefined') nbpix('event', 'subscribe');
        const box = form.parentElement;
        const ok = box.querySelector('.success');
        if (ok) { form.hidden = true; const fp = box.querySelector('.fineprint'); if (fp) fp.hidden = true; ok.hidden = false; }
        else { button.textContent = '✓ Subscribed'; form.querySelector('input').value = ''; }
      } else { alert('Error: ' + (data.error || 'Please try again.')); button.textContent = original; button.disabled = false; }
    })
    .catch(() => { alert('Network error. Please try again.'); button.textContent = original; button.disabled = false; });
}

window.subscribe = subscribe;
}
