// node --test shared/net/
import test from 'node:test';
import assert from 'node:assert/strict';
import {
  makeRoomCode, normaliseRoomCode, parseInvite, inviteLink, cleanText, cleanAlias,
  readChat, readAction, rateLimiter, pickHost, makeKey,
} from './manor-util.js';

test('room codes look like WORD-NNN and round-trip', () => {
  for (let i = 0; i < 200; i++) {
    const code = makeRoomCode();
    assert.match(code, /^[A-Z]{3,8}-\d{3}$/);
    assert.equal(normaliseRoomCode(code.toLowerCase()), code);
  }
  assert.equal(normaliseRoomCode('dark-404'), 'DARK-404');
  assert.equal(normaliseRoomCode('DARK404'), null);
  assert.equal(normaliseRoomCode('<script>-123'), null);
  assert.equal(normaliseRoomCode(42), null);
});

test('invite links carry game and room in the query, key only in the hash', () => {
  const link = inviteLink('https://plumbmonkey.online/manor?old=1#x',
    { game: 'pool', room: 'DARK-404', key: 'abcdef123456' });
  assert.equal(link, 'https://plumbmonkey.online/manor?game=pool&room=DARK-404#key=abcdef123456');
  assert.deepEqual(parseInvite(link), { game: 'pool', room: 'DARK-404', key: 'abcdef123456' });
  assert.deepEqual(parseInvite('https://x.test/manor?game=chess&room=bad'),
    { game: null, room: null, key: null });
});

test('private keys are url-safe', () => {
  const k = makeKey();
  assert.match(k, /^[a-z0-9]{8,64}$/);
});

test('chat text is stripped of control, zero-width and bidi characters', () => {
  assert.equal(cleanText('  hi‮there​ \n\n you ', 280), 'hithere you');
  assert.equal(cleanText('x'.repeat(500), 280).length, 280);
  assert.equal(cleanText(null, 10), '');
  assert.equal(cleanAlias('<b>Luno</b>!!'), 'bLunob');
  assert.equal(cleanAlias('   '), 'Stranger');
});

test('readChat rejects junk and clamps timestamps', () => {
  const now = 1_000_000;
  assert.equal(readChat(null, now), null);
  assert.equal(readChat({ text: '   ' }, now), null);
  const m = readChat({ text: 'gg', alias: 'Nyx', ts: now + 10 * 60000 }, now);
  assert.deepEqual(m, { text: 'gg', alias: 'Nyx', ts: now });
});

test('readAction needs a type and stays under 4 KB', () => {
  assert.equal(readAction({ x: 1 }), null);
  assert.deepEqual(readAction({ type: 'throw', x: 1 }), { type: 'throw', x: 1 });
  assert.equal(readAction({ type: 'x', blob: 'y'.repeat(5000) }), null);
  const loop = { type: 'loop' };
  loop.self = loop;
  assert.equal(readAction(loop), null);
});

test('rate limiter allows a burst then blocks until the window passes', () => {
  const rl = rateLimiter(3, 1000);
  assert.ok(rl.allow('p', 0));
  assert.ok(rl.allow('p', 10));
  assert.ok(rl.allow('p', 20));
  assert.ok(!rl.allow('p', 30));
  assert.ok(rl.allow('q', 30), 'limits are per peer');
  assert.ok(rl.allow('p', 1015));
});

test('every peer picks the same host', () => {
  assert.equal(pickHost(['zeta', 'alpha', 'mid']), 'alpha');
  assert.equal(pickHost([]), null);
});
