/* Senior Daily Benefits — article comments (loaded on article pages only) */
(function () {
  const root = document.getElementById('comments');
  if (!root) return;
  const slug = root.dataset.slug;
  const list = root.querySelector('.comment-list');
  const count = root.querySelector('.comment-count');
  const form = root.querySelector('form');
  const note = root.querySelector('.comment-note');

  function esc(s) { return String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c])); }
  function when(iso) {
    const d = new Date(iso);
    return isNaN(d) ? '' : d.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' });
  }
  function render(items) {
    count.textContent = items.length === 1 ? '1 comment' : items.length + ' comments';
    if (!items.length) { list.innerHTML = '<p class="muted">No comments yet. Be the first to share your experience.</p>'; return; }
    list.innerHTML = items.map(c => `
      <div class="comment">
        <div class="comment-head"><span class="comment-avatar">${esc(c.name.trim().charAt(0).toUpperCase())}</span><strong>${esc(c.name)}</strong><time>${when(c.created_at)}</time></div>
        <p>${esc(c.body).replace(/\n/g, '<br>')}</p>
      </div>`).join('');
  }

  fetch('/api/comments?slug=' + encodeURIComponent(slug))
    .then(r => r.json()).then(d => render(d.comments || []))
    .catch(() => { list.innerHTML = ''; });

  form.addEventListener('submit', e => {
    e.preventDefault();
    const btn = form.querySelector('button[type="submit"]');
    const payload = {
      slug,
      name: form.name.value, email: form.email.value, body: form.body.value,
      website: form.website.value, // honeypot: real people never see this field
    };
    btn.disabled = true; btn.textContent = 'Sending…';
    note.textContent = '';
    fetch('/api/comments', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })
      .then(r => r.json())
      .then(d => {
        if (d.success) {
          form.reset(); form.hidden = true;
          note.textContent = 'Thank you. Your comment has been received and will appear after a quick review.';
        } else {
          note.textContent = d.error || 'Something went wrong. Please try again.';
          btn.disabled = false; btn.textContent = 'Post comment';
        }
      })
      .catch(() => { note.textContent = 'Network error. Please try again.'; btn.disabled = false; btn.textContent = 'Post comment'; });
  });
})();
