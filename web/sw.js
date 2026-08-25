/* Service worker: offline shell + Web Push.
 *
 * Served from the origin root rather than /app/ so its scope covers the whole
 * site — a worker registered under /app/ can't receive push for the origin.
 */
'use strict';

const VERSION = 'flipscan-v1';
const SHELL = [
  '/app/',
  '/app/index.html',
  '/app/styles.css',
  '/app/app.js',
  '/app/icons/icon-192.png',
  '/app/icons/icon-512.png',
  '/manifest.webmanifest',
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(VERSION)
      // addAll is all-or-nothing; one missing file would fail the whole
      // install and leave the app with no worker at all.
      .then(cache => Promise.allSettled(SHELL.map(url => cache.add(url))))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== VERSION).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', event => {
  const request = event.request;
  if (request.method !== 'GET') return;

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  // Never cache the API. A stale deal list showing a listing that sold two
  // hours ago is worse than an honest offline message.
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(
      fetch(request).catch(() => new Response(
        JSON.stringify({ detail: 'Offline — reconnect to load deals.' }),
        { status: 503, headers: { 'Content-Type': 'application/json' } }
      ))
    );
    return;
  }

  // Shell and assets: cache first, refresh in the background.
  event.respondWith(
    caches.match(request).then(cached => {
      const network = fetch(request).then(response => {
        if (response && response.status === 200 && response.type === 'basic') {
          const copy = response.clone();
          caches.open(VERSION).then(cache => cache.put(request, copy));
        }
        return response;
      }).catch(() => cached);
      return cached || network;
    })
  );
});

// ------------------------------------------------------------------ push --
self.addEventListener('push', event => {
  let payload = {};
  try {
    payload = event.data ? event.data.json() : {};
  } catch {
    payload = { title: 'FlipScan', body: event.data ? event.data.text() : '' };
  }

  event.waitUntil(
    self.registration.showNotification(payload.title || 'FlipScan', {
      body: payload.body || '',
      icon: payload.icon || '/app/icons/icon-192.png',
      badge: payload.badge || '/app/icons/badge.png',
      image: payload.image || undefined,
      // Tagging by deal means a re-alert on the same listing replaces the
      // old notification instead of stacking a second one.
      tag: payload.tag || 'flipscan',
      data: payload.data || {},
      actions: payload.actions || [],
      requireInteraction: false,
      vibrate: [60, 40, 60],
    })
  );
});

self.addEventListener('notificationclick', event => {
  event.notification.close();
  const data = event.notification.data || {};

  if (event.action === 'open' && data.listing_url) {
    event.waitUntil(self.clients.openWindow(data.listing_url));
    return;
  }
  if (event.action === 'pass' && data.deal_id) {
    // Best-effort: the worker has no auth token, so this only succeeds if the
    // app has a session. The in-app Pass button is the reliable path.
    event.waitUntil(
      fetch(`/api/deals/${data.deal_id}/feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'passed' }),
      }).catch(() => {})
    );
    return;
  }

  const target = data.url || '/app/';
  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true })
      .then(windows => {
        for (const client of windows) {
          if (client.url.includes('/app/') && 'focus' in client) {
            client.navigate(target).catch(() => {});
            return client.focus();
          }
        }
        return self.clients.openWindow(target);
      })
  );
});
