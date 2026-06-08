/**
 * RAG Q&A — Embeddable Chat Widget (Shadow DOM isolated)
 *
 * Usage:
 *   <script src="https://your-domain.com/widget.js"></script>
 *   <script src="https://your-domain.com/widget.js" data-api="https://your-api.com"></script>
 *
 * Options (data attributes):
 *   data-api       — API base URL (defaults to current origin)
 *   data-title     — Chat title (default: "Ask anything")
 *   data-subtitle  — Subtitle (default: "AI-powered document Q&A")
 *   data-color     — Brand color hex (default: "#4f46e5")
 *   data-position  — "right" or "left" (default: "right")
 */
(function () {
  'use strict';

  const script = document.currentScript;
  const API = (script.getAttribute('data-api') || window.location.origin).replace(/\/$/, '');
  const TITLE = script.getAttribute('data-title') || 'Ask anything';
  const SUBTITLE = script.getAttribute('data-subtitle') || 'AI-powered document Q&A';
  const COLOR = script.getAttribute('data-color') || '#4f46e5';
  const POS = script.getAttribute('data-position') || 'right';

  // ===== HOST ELEMENT =====
  const host = document.createElement('div');
  host.id = 'ragqa-widget-host';
  host.style.cssText = 'position:fixed;z-index:99999;bottom:0;left:0;width:0;height:0;';
  document.body.appendChild(host);

  const shadow = host.attachShadow({ mode: 'open' });

  // ===== SHADOW STYLES =====
  const css = `
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    :host { font-family: 'Inter', system-ui, -apple-system, sans-serif; font-size: 14px; line-height: 1.5; color: #e2e8f0; }

    /* ----- BUBBLE ----- */
    .bubble {
      position: fixed; bottom: 24px; ${POS}: 24px;
      width: 60px; height: 60px; border-radius: 50%;
      background: ${COLOR}; color: #fff; border: none; cursor: pointer;
      box-shadow: 0 4px 24px rgba(0,0,0,0.3);
      display: flex; align-items: center; justify-content: center;
      transition: transform 0.2s, box-shadow 0.2s;
      animation: pulse 3s ease-in-out infinite;
    }
    .bubble:hover { transform: scale(1.08); box-shadow: 0 6px 32px rgba(0,0,0,0.4); }
    .bubble svg { width: 28px; height: 28px; fill: none; stroke: currentColor; stroke-width: 2; stroke-linecap: round; stroke-linejoin: round; }
    .bubble .icon-close { display: none; }
    .bubble.open .icon-chat { display: none; }
    .bubble.open .icon-close { display: block; }
    @keyframes pulse {
      0%, 100% { box-shadow: 0 4px 24px rgba(0,0,0,0.3), 0 0 0 0 ${COLOR}40; }
      50% { box-shadow: 0 4px 24px rgba(0,0,0,0.3), 0 0 0 8px ${COLOR}00; }
    }

    /* ----- PANEL ----- */
    .panel {
      position: fixed; bottom: 100px; ${POS}: 24px;
      width: 420px; max-width: calc(100vw - 48px);
      height: 580px; max-height: calc(100vh - 140px);
      background: #0c0d13; border: 1px solid rgba(255,255,255,0.08);
      border-radius: 24px; overflow: hidden;
      display: none; flex-direction: column;
      box-shadow: 0 25px 60px rgba(0,0,0,0.5);
      animation: slideup 0.25s ease-out;
    }
    .panel.open { display: flex; }
    @keyframes slideup { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: translateY(0); } }

    /* ----- HEADER ----- */
    .header {
      padding: 24px 28px 20px;
      border-bottom: 1px solid rgba(255,255,255,0.06);
      background: linear-gradient(180deg, #151720 0%, #0c0d13 100%);
    }
    .header h3 { font-size: 16px; font-weight: 700; color: #f1f5f9; }
    .header p { font-size: 12px; color: #64748b; margin-top: 4px; font-weight: 500; }

    /* ----- MESSAGES ----- */
    .messages {
      flex: 1; overflow-y: auto; padding: 24px 28px;
      display: flex; flex-direction: column; gap: 18px;
      scrollbar-width: thin; scrollbar-color: #2a2d3a transparent;
    }
    .messages::-webkit-scrollbar { width: 4px; }
    .messages::-webkit-scrollbar-thumb { background: #2a2d3a; border-radius: 99px; }

    /* ----- MESSAGE ROW ----- */
    .msg { display: flex; gap: 12px; animation: fadein 0.3s ease-out; }
    .msg.user { flex-direction: row-reverse; }
    @keyframes fadein { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: translateY(0); } }

    .avatar {
      width: 32px; height: 32px; border-radius: 10px; flex-shrink: 0;
      display: flex; align-items: center; justify-content: center; margin-top: 2px;
    }
    .avatar.bot { background: linear-gradient(135deg, ${COLOR}, ${COLOR}cc); }
    .avatar.user { background: #374151; }
    .avatar svg { width: 15px; height: 15px; fill: none; stroke: #fff; stroke-width: 2; stroke-linecap: round; stroke-linejoin: round; }

    .bubble-text {
      max-width: 80%; padding: 14px 18px; border-radius: 18px;
      font-size: 13px; line-height: 1.65; color: #e2e8f0; word-break: break-word;
    }
    .msg.user .bubble-text { background: ${COLOR}; border-bottom-right-radius: 6px; color: #fff; }
    .msg.bot .bubble-text { background: #1a1d27; border-bottom-left-radius: 6px; }
    .bubble-text strong { font-weight: 600; color: #f8fafc; }
    .bubble-text code { background: #13151d; padding: 2px 6px; border-radius: 5px; font-size: 11px; font-family: monospace; }
    .bubble-text pre { background: #13151d; padding: 10px 12px; border-radius: 10px; font-size: 11px; overflow-x: auto; margin: 8px 0; font-family: monospace; }
    .bubble-text .cite {
      display: inline-flex; align-items: center; justify-content: center;
      min-width: 20px; height: 20px; padding: 0 5px; font-size: 10px; font-weight: 700;
      background: ${COLOR}22; color: ${COLOR}; border-radius: 6px; border: 1px solid ${COLOR}20;
      vertical-align: text-top; margin: 0 2px;
    }

    /* ----- TYPING ----- */
    .typing { display: flex; gap: 4px; padding: 4px 0; }
    .typing span {
      display: inline-block; width: 7px; height: 7px; background: #475569;
      border-radius: 50%; animation: dot 1.4s infinite;
    }
    .typing span:nth-child(2) { animation-delay: 0.2s; }
    .typing span:nth-child(3) { animation-delay: 0.4s; }
    @keyframes dot { 0%,80%,100% { opacity: 0.25; } 40% { opacity: 1; } }

    /* ----- INPUT ----- */
    .input-area {
      padding: 22px 28px;
      border-top: 1px solid rgba(255,255,255,0.06);
      background: #0e1017;
    }
    .input-wrap { display: flex; gap: 12px; align-items: center; }
    .input-wrap input {
      flex: 1; background: #1a1d27; border: 1px solid rgba(255,255,255,0.1);
      border-radius: 16px; padding: 14px 20px; font-size: 13px; color: #e2e8f0;
      outline: none; font-family: inherit; transition: border-color 0.15s;
    }
    .input-wrap input::placeholder { color: #4b5563; }
    .input-wrap input:focus { border-color: ${COLOR}88; }
    .input-wrap button {
      width: 48px; height: 48px; border-radius: 16px; border: none;
      background: ${COLOR}; color: #fff; cursor: pointer; flex-shrink: 0;
      display: flex; align-items: center; justify-content: center;
      transition: background 0.15s;
    }
    .input-wrap button:hover { background: ${COLOR}dd; }
    .input-wrap button:disabled { opacity: 0.3; cursor: not-allowed; }
    .input-wrap button svg { width: 18px; height: 18px; fill: none; stroke: currentColor; stroke-width: 2; stroke-linecap: round; stroke-linejoin: round; }

    /* ----- FOOTER ----- */
    .footer {
      padding: 14px 28px; text-align: center; font-size: 11px; color: #334155;
      border-top: 1px solid rgba(255,255,255,0.03);
    }
    .footer a { color: #475569; text-decoration: none; }
    .footer a:hover { color: #64748b; }

    /* ----- WELCOME ----- */
    .welcome {
      flex: 1; display: flex; align-items: center; justify-content: center;
      text-align: center; padding: 44px 36px;
    }
    .welcome-icon {
      width: 52px; height: 52px; border-radius: 18px; margin: 0 auto 18px;
      background: ${COLOR}12; border: 1px solid ${COLOR}18;
      display: flex; align-items: center; justify-content: center;
    }
    .welcome-icon svg { width: 26px; height: 26px; fill: none; stroke: ${COLOR}; stroke-width: 1.5; stroke-linecap: round; stroke-linejoin: round; }
    .welcome h4 { font-size: 17px; font-weight: 700; color: #e2e8f0; margin-bottom: 8px; }
    .welcome p { font-size: 13px; color: #64748b; line-height: 1.6; max-width: 280px; margin: 0 auto; }

    @media (max-width: 480px) {
      .panel { width: calc(100vw - 16px); ${POS}: 8px; bottom: 88px; height: calc(100vh - 110px); border-radius: 18px; }
      .bubble { bottom: 16px; ${POS}: 16px; width: 54px; height: 54px; }
    }
  `;

  // ===== BUILD DOM =====
  shadow.innerHTML = `
    <style>${css}</style>

    <button class="bubble" id="bubble" aria-label="Open chat">
      <svg class="icon-chat" viewBox="0 0 24 24"><path d="M7.5 8.25h9m-9 3H12m-9.75 1.51c0 1.6 1.123 2.994 2.707 3.227 1.087.16 2.185.283 3.293.369V21l4.076-4.076a1.526 1.526 0 011.037-.443 48.282 48.282 0 005.68-.494c1.584-.233 2.707-1.626 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0012 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018z"/></svg>
      <svg class="icon-close" viewBox="0 0 24 24"><path d="M6 18L18 6M6 6l12 12"/></svg>
    </button>

    <div class="panel" id="panel">
      <div class="header">
        <h3>${TITLE}</h3>
        <p>${SUBTITLE}</p>
      </div>
      <div class="messages" id="messages">
        <div class="welcome">
          <div>
            <div class="welcome-icon">
              <svg viewBox="0 0 24 24"><path d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m5.231 13.481L15 17.25m-4.5-15H5.625c-.621 0-1.125.504-1.125 1.125v16.5c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9zm3.75 11.625a2.625 2.625 0 11-5.25 0 2.625 2.625 0 015.25 0z"/></svg>
            </div>
            <h4>${TITLE}</h4>
            <p>Ask me anything about the uploaded documents. I'll answer with source citations.</p>
          </div>
        </div>
      </div>
      <div class="input-area">
        <form class="input-wrap" id="form">
          <input type="text" placeholder="Type your question..." autocomplete="off" id="input" />
          <button type="submit" id="send"><svg viewBox="0 0 24 24"><path d="M4.5 10.5L12 3m0 0l7.5 7.5M12 3v18"/></svg></button>
        </form>
      </div>
      <div class="footer">Powered by <a href="#">RAG Q&A</a></div>
    </div>
  `;

  // ===== REFS =====
  const bubble = shadow.getElementById('bubble');
  const panel = shadow.getElementById('panel');
  const messages = shadow.getElementById('messages');
  const form = shadow.getElementById('form');
  const input = shadow.getElementById('input');
  const sendBtn = shadow.getElementById('send');

  // Expose bubble ID for auto-open script
  host.setAttribute('data-bubble-ready', 'true');

  let isOpen = false;
  let streaming = false;
  let history = [];

  // ===== TOGGLE =====
  bubble.addEventListener('click', () => {
    isOpen = !isOpen;
    panel.classList.toggle('open', isOpen);
    bubble.classList.toggle('open', isOpen);
    if (isOpen) input.focus();
  });

  // Global toggle for auto-open
  window.__ragqaToggle = () => { if (!isOpen) bubble.click(); };

  // ===== HELPERS =====
  function esc(s) { const d = document.createElement('span'); d.textContent = s; return d.innerHTML; }

  function miniMd(t) {
    return t
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>')
      .replace(/`([^`]+)`/g, '<code>$1</code>')
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.+?)\*/g, '<em>$1</em>')
      .replace(/^\- (.+)$/gm, '&bull; $1')
      .replace(/\[(\d+)\]/g, '<span class="cite">$1</span>')
      .replace(/\n/g, '<br>');
  }

  function addMsg(role, html) {
    const w = messages.querySelector('.welcome');
    if (w) w.remove();

    const row = document.createElement('div');
    row.className = `msg ${role}`;

    const av = document.createElement('div');
    av.className = `avatar ${role}`;
    av.innerHTML = role === 'user'
      ? '<svg viewBox="0 0 24 24"><path d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0"/></svg>'
      : '<svg viewBox="0 0 24 24"><path d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z"/></svg>';

    const bub = document.createElement('div');
    bub.className = 'bubble-text';
    bub.innerHTML = html;

    row.appendChild(av);
    row.appendChild(bub);
    messages.appendChild(row);
    messages.scrollTop = messages.scrollHeight;
    return bub;
  }

  // ===== SUBMIT =====
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const q = input.value.trim();
    if (!q || streaming) return;

    streaming = true;
    sendBtn.disabled = true;
    input.value = '';

    history.push({ role: 'user', content: q });
    addMsg('user', esc(q));

    const botBub = addMsg('bot', '<span class="typing"><span></span><span></span><span></span></span>');

    try {
      const res = await fetch(`${API}/api/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: q, history: history.slice(0, -1) }),
      });

      if (!res.ok) {
        let msg = `Error (${res.status})`;
        try { const err = await res.json(); msg = err.detail || msg; } catch {}
        throw new Error(msg);
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buf = '', full = '', first = true;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        const lines = buf.split('\n');
        buf = lines.pop() || '';
        for (const line of lines) {
          if (line.startsWith('event: ')) var ev = line.slice(7).trim();
          else if (line.startsWith('data: ')) {
            const d = JSON.parse(line.slice(6));
            if (ev === 'token') {
              if (first) { botBub.innerHTML = ''; first = false; }
              full += d.text;
              botBub.innerHTML = miniMd(full);
              messages.scrollTop = messages.scrollHeight;
            } else if (ev === 'done') {
              history.push({ role: 'assistant', content: full });
            }
          }
        }
      }
    } catch (err) {
      botBub.innerHTML = `<span style="color:#f87171">${esc(err.message)}</span>`;
    } finally {
      streaming = false;
      sendBtn.disabled = false;
      input.focus();
    }
  });
})();
