// The live-chat slide-out drawer, shared by every Wave 4 game.
//
//   import { mountChatDrawer } from '../../shared/net/chat-drawer.js';
//   const drawer = mountChatDrawer(net);          // net = await joinManor(...)
//
// Every piece of peer text is written with textContent - never innerHTML.

const CSS_URL = new URL('./chat-drawer.css', import.meta.url);

function el(tag, attrs = {}, ...kids) {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === 'class') n.className = v;
    else if (k.startsWith('on')) n.addEventListener(k.slice(2), v);
    else n.setAttribute(k, v);
  }
  for (const k of kids) n.append(k);
  return n;
}

// stable colour per alias, inside the manor palette
function aliasHue(alias) {
  let h = 0;
  for (const ch of alias) h = (h * 31 + ch.codePointAt(0)) >>> 0;
  return [158, 270, 42, 200, 320][h % 5];
}

export function mountChatDrawer(net, { parent = document.body, open = false } = {}) {
  if (!document.querySelector('link[data-manor-chat]')) {
    document.head.append(el('link', { rel: 'stylesheet', href: CSS_URL.href, 'data-manor-chat': '' }));
  }

  let unread = 0;
  const badge = el('span', { class: 'mc-badge', hidden: '' });
  const tab = el('button', { class: 'mc-tab', type: 'button', 'aria-expanded': 'false',
                              'aria-controls': 'manor-chat' }, 'Chat', badge);
  const roomLabel = el('span', { class: 'mc-room' }, net.room);
  const copyBtn = el('button', { class: 'mc-btn', type: 'button' }, 'Copy invite');
  const closeBtn = el('button', { class: 'mc-close', type: 'button', 'aria-label': 'Close chat' }, '×');
  const status = el('p', { class: 'mc-status', role: 'status' });
  const peerList = el('ul', { class: 'mc-peers', 'aria-label': 'Players in this room' });
  const log = el('ol', { class: 'mc-log', 'aria-live': 'polite', 'aria-label': 'Messages' });
  const aliasInput = el('input', { class: 'mc-alias', maxlength: '20', 'aria-label': 'Your name',
                                   value: net.alias });
  const input = el('input', { class: 'mc-input', maxlength: '280', autocomplete: 'off',
                              placeholder: 'Say something…', 'aria-label': 'Message' });
  const send = el('button', { class: 'mc-btn mc-send', type: 'submit' }, 'Send');
  const form = el('form', { class: 'mc-form' }, input, send);

  const panel = el('aside', { id: 'manor-chat', class: 'mc-panel', 'aria-label': 'Room chat' },
    el('header', { class: 'mc-head' },
      el('div', {}, el('span', { class: 'mc-kicker' }, 'Room'), roomLabel),
      copyBtn, closeBtn),
    status,
    peerList,
    log,
    el('label', { class: 'mc-alias-row' }, 'Name', aliasInput),
    form);

  const root = el('div', { class: 'manor-chat' + (open ? ' is-open' : '') }, tab, panel);
  parent.append(root);

  function setOpen(v) {
    root.classList.toggle('is-open', v);
    tab.setAttribute('aria-expanded', String(v));
    if (v) {
      unread = 0;
      badge.hidden = true;
      input.focus();
    }
  }

  function renderPeers(list) {
    peerList.replaceChildren(
      el('li', { class: 'mc-peer is-self' }, el('span', {}, `${net.alias} (you)`)),
      ...list.map((p) => {
        const mute = el('button', { class: 'mc-mute', type: 'button' }, p.muted ? 'Unmute' : 'Mute');
        mute.addEventListener('click', () => net.mute(p.id, !p.muted));
        const name = el('span', {}, p.alias);
        name.style.setProperty('--hue', aliasHue(p.alias));
        return el('li', { class: 'mc-peer' + (p.muted ? ' is-muted' : '') }, name, mute);
      }));
    status.textContent = list.length
      ? `${list.length + 1} in the room`
      : 'Waiting for someone to join — send them the invite.';
  }

  function addLine(msg) {
    const who = el('span', { class: 'mc-who' }, msg.self ? 'You' : msg.alias);
    who.style.setProperty('--hue', msg.self ? 42 : aliasHue(msg.alias));
    const time = el('time', { datetime: new Date(msg.ts).toISOString() },
      new Date(msg.ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }));
    log.append(el('li', { class: 'mc-line' + (msg.self ? ' is-self' : '') }, who,
      el('span', { class: 'mc-text' }, msg.text), time));
    while (log.children.length > 200) log.firstChild.remove();
    log.scrollTop = log.scrollHeight;
    if (!root.classList.contains('is-open') && !msg.self) {
      unread += 1;
      badge.textContent = String(unread);
      badge.hidden = false;
    }
  }

  function note(text) {
    log.append(el('li', { class: 'mc-note' }, text));
    log.scrollTop = log.scrollHeight;
  }

  tab.addEventListener('click', () => setOpen(!root.classList.contains('is-open')));
  closeBtn.addEventListener('click', () => setOpen(false));
  root.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') setOpen(false);
  });
  form.addEventListener('submit', (e) => {
    e.preventDefault();
    if (net.sendChat(input.value)) input.value = '';
    else if (input.value.trim()) note('Slow down a moment…');
  });
  aliasInput.addEventListener('change', () => {
    aliasInput.value = net.setAlias(aliasInput.value);
    renderPeers(net.peers());
  });
  copyBtn.addEventListener('click', async () => {
    const link = net.inviteLink();
    try {
      await navigator.clipboard.writeText(link);
      copyBtn.textContent = 'Copied!';
    } catch {
      window.prompt('Copy this invite link:', link);
    }
    setTimeout(() => (copyBtn.textContent = 'Copy invite'), 1600);
  });

  const offs = [
    net.onChat(addLine),
    net.onPeers(renderPeers),
    net.onPeerJoin((p) => note(`A player joined.`)),
    net.onPeerLeave((p) => note(`${p.alias} left.`)),
    net.onError((e) => note(e?.error ? `Connection problem: ${e.error}` : 'Connection problem.')),
  ];
  renderPeers(net.peers());

  return {
    open: () => setOpen(true),
    close: () => setOpen(false),
    note,
    destroy() {
      offs.forEach((off) => off());
      root.remove();
    },
  };
}
