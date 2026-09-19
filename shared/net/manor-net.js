// ManorNet - the one peer-to-peer bridge every Wave 4 game uses.
//
//   import { joinManor } from '../../shared/net/manor-net.js';
//   const net = await joinManor({ game: 'bowling', alias: 'Luno' });
//   net.onAction((action, peer) => { ... });      // gameAction
//   net.sendAction({ type: 'throw', x, spin, power });
//   net.onChat((msg) => { ... });                 // chatMessage
//   net.sendChat('good shot');
//
// Signalling goes over public Nostr relays (default) or BitTorrent trackers;
// once two browsers find each other everything is a direct, encrypted WebRTC
// data channel. No server of ours is involved, so there is nothing to pay for -
// and nothing to moderate with. See docs/PRD.md section 4 for the caveats.

import {
  PROTOCOL, makeRoomCode, normaliseRoomCode, parseInvite, inviteLink, makeKey,
  readChat, readAction, cleanAlias, cleanText, rateLimiter, pickHost, LIMITS,
} from './manor-util.js';

const APP_ID = 'plumbmonkey-spectral-manor-w4';
const TRYSTERO_VERSION = '0.25.4';
const STRATEGIES = {
  nostr: `https://esm.run/trystero@${TRYSTERO_VERSION}`,
  torrent: `https://esm.run/@trystero-p2p/torrent@${TRYSTERO_VERSION}`,
};

function emitter() {
  const subs = new Set();
  return {
    on(fn) {
      subs.add(fn);
      return () => subs.delete(fn);
    },
    emit(...args) {
      for (const fn of subs) {
        try {
          fn(...args);
        } catch (err) {
          console.error('[ManorNet] listener failed', err);
        }
      }
    },
  };
}

/**
 * Join (or create) a room.
 *
 * @param {object}  opts
 * @param {string}  opts.game        'bowling' | 'pool' | 'putt' | 'links' | 'holdem'
 * @param {string}  [opts.alias]     display name for chat
 * @param {string}  [opts.room]      room code; defaults to ?room= in the URL, else a new one
 * @param {string}  [opts.key]       private-room key; defaults to #key= in the URL
 * @param {boolean} [opts.private]   make a key if there isn't one (invite-only room)
 * @param {'nostr'|'torrent'} [opts.strategy]
 * @param {object[]} [opts.turn]     TURN servers - needed for strict NATs
 * @param {Function} [opts.importer] (url) => module, to load a vendored Trystero instead of the CDN
 * @param {string}  [opts.baseUrl]   where invite links point (defaults to this page)
 */
export async function joinManor(opts = {}) {
  const here = typeof location !== 'undefined' ? location.href : 'https://plumbmonkey.online/manor';
  const fromUrl = parseInvite(here);
  const game = opts.game || fromUrl.game || 'bowling';
  const room = normaliseRoomCode(opts.room || '') || fromUrl.room || makeRoomCode();
  let key = opts.key || fromUrl.key || null;
  if (!key && opts.private) key = makeKey();
  let alias = cleanAlias(opts.alias || 'Luno');

  const strategy = opts.strategy === 'torrent' ? 'torrent' : 'nostr';
  const load = opts.importer || ((url) => import(/* @vite-ignore */ url));
  const trystero = await load(STRATEGIES[strategy]);

  const events = {
    join: emitter(), leave: emitter(), action: emitter(), chat: emitter(),
    peers: emitter(), error: emitter(),
  };

  const config = { appId: APP_ID };
  if (key) config.password = key;
  if (opts.turn?.length) config.turnConfig = opts.turn;

  // One Trystero room per game+code, so a bowling room and a pool room with
  // the same code never see each other.
  const trRoom = trystero.joinRoom(config, `${game}:${room}`, {
    onJoinError: (details) => events.error.emit(details),
  });

  const hello = trRoom.makeAction('hello');
  const gameAct = trRoom.makeAction('game');
  const chat = trRoom.makeAction('chat');

  const peers = new Map();            // id -> { id, alias, protocol, muted }
  const chatLimit = rateLimiter();
  const actionLimit = rateLimiter(60, 1000);

  const sayHello = (target) =>
    hello.send({ alias, protocol: PROTOCOL, game }, target ? { target } : undefined);

  trRoom.onPeerJoin = (id) => {
    peers.set(id, { id, alias: 'Stranger', protocol: null, muted: false });
    sayHello(id);
    events.join.emit(peers.get(id));
    events.peers.emit(list());
  };

  trRoom.onPeerLeave = (id) => {
    const p = peers.get(id);
    peers.delete(id);
    chatLimit.forget(id);
    actionLimit.forget(id);
    if (p) events.leave.emit(p);
    events.peers.emit(list());
  };

  hello.onMessage = (data, { peerId }) => {
    const p = peers.get(peerId) || { id: peerId, muted: false };
    p.alias = cleanAlias(data?.alias);
    p.protocol = Number.isInteger(data?.protocol) ? data.protocol : null;
    peers.set(peerId, p);
    if (p.protocol !== PROTOCOL) {
      events.error.emit({ peerId, error: `peer speaks protocol ${p.protocol}, we speak ${PROTOCOL}` });
    }
    events.peers.emit(list());
  };

  gameAct.onMessage = (data, { peerId }) => {
    if (!peers.has(peerId) || !actionLimit.allow(peerId)) return;
    const action = readAction(data);
    if (action) events.action.emit(action, peers.get(peerId));
  };

  chat.onMessage = (data, { peerId }) => {
    const p = peers.get(peerId);
    if (!p || p.muted || !chatLimit.allow(peerId)) return;
    const msg = readChat(data);
    if (msg) events.chat.emit({ ...msg, alias: p.alias, peerId, self: false });
  };

  function list() {
    return [...peers.values()].map((p) => ({ ...p }));
  }

  const selfId = trystero.selfId;
  const ownLimit = rateLimiter();

  return {
    game, room, key, selfId, strategy,

    get alias() {
      return alias;
    },
    setAlias(name) {
      alias = cleanAlias(name);
      sayHello();
      return alias;
    },

    inviteLink: (base = opts.baseUrl || here) => inviteLink(base, { game, room, key }),
    peers: list,
    /** The lowest id in the room acts as host (deals cards, owns the rack...). */
    isHost: () => pickHost([selfId, ...peers.keys()]) === selfId,
    host: () => pickHost([selfId, ...peers.keys()]),

    /** gameAction: `{ type: 'throw', ... }` - under 4 KB. `to` = one peer id. */
    sendAction(action, to) {
      if (!readAction(action)) throw new Error('ManorNet: action needs a string `type` and must be < 4 KB');
      return gameAct.send(action, to ? { target: to } : undefined);
    },

    /** chatMessage. Returns the sent message, or null if empty / rate-limited. */
    sendChat(text) {
      const clean = cleanText(text, LIMITS.chatChars);
      if (!clean || !ownLimit.allow('self')) return null;
      const msg = { text: clean, alias, ts: Date.now() };
      chat.send(msg);
      const mine = { ...msg, peerId: selfId, self: true };
      events.chat.emit(mine);
      return mine;
    },

    mute(peerId, muted = true) {
      const p = peers.get(peerId);
      if (p) p.muted = muted;
      events.peers.emit(list());
    },

    onPeerJoin: events.join.on,
    onPeerLeave: events.leave.on,
    onPeers: events.peers.on,
    onAction: events.action.on,
    onChat: events.chat.on,
    onError: events.error.on,

    leave() {
      trRoom.leave();
      peers.clear();
      events.peers.emit([]);
    },
  };
}
