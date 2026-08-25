/* FlipScan PWA.
 *
 * No build step and no framework, on purpose: this has to be installable from
 * Safari on a phone and maintainable by whoever picks it up next, and a
 * toolchain is one more thing that can break between here and a working app.
 */
'use strict';

// --------------------------------------------------------------- storage --
const Store = {
  get token()   { try { return localStorage.getItem('fs.token') || ''; } catch { return ''; } },
  set token(v)  { try { localStorage.setItem('fs.token', v); } catch {} },
  get baseUrl() { try { return localStorage.getItem('fs.base') || ''; } catch { return ''; } },
  set baseUrl(v){ try { localStorage.setItem('fs.base', v); } catch {} },
  get filters() {
    try { return JSON.parse(localStorage.getItem('fs.filters') || '{}'); } catch { return {}; }
  },
  set filters(v){ try { localStorage.setItem('fs.filters', JSON.stringify(v)); } catch {} },
  clear() { try { localStorage.removeItem('fs.token'); localStorage.removeItem('fs.base'); } catch {} },
};

// ------------------------------------------------------------------- api --
const Api = {
  base() { return Store.baseUrl || ''; },

  async call(path, options = {}) {
    const response = await fetch(this.base() + path, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + Store.token,
        ...(options.headers || {}),
      },
    });
    if (response.status === 401) {
      Store.clear();
      showSetup('That token was rejected. Check FLIPSCAN_API_TOKEN on the server.');
      throw new Error('unauthorized');
    }
    if (!response.ok) {
      let detail = response.statusText;
      try { detail = (await response.json()).detail || detail; } catch {}
      throw new Error(detail);
    }
    return response.status === 204 ? null : response.json();
  },

  deals(params = {}) {
    const q = new URLSearchParams(
      Object.entries(params).filter(([, v]) => v !== '' && v != null)
    );
    return this.call('/api/deals?' + q);
  },
  deal(id)            { return this.call('/api/deals/' + id); },
  runs(p = {})        { return this.call('/api/deals/runs?' + new URLSearchParams(p)); },
  feedback(id, body)  { return this.call(`/api/deals/${id}/feedback`,
                          { method: 'POST', body: JSON.stringify(body) }); },
  manual(body)        { return this.call('/api/deals/manual',
                          { method: 'POST', body: JSON.stringify(body) }); },
  status()            { return this.call('/api/status'); },
  settings()          { return this.call('/api/settings'); },
  patchSettings(u)    { return this.call('/api/settings',
                          { method: 'PATCH', body: JSON.stringify({ updates: u }) }); },
  scan(demo = false)  { return this.call('/api/scans/run?demo=' + (demo ? 'true' : 'false'),
                          { method: 'POST' }); },
  watchlists()        { return this.call('/api/watchlists'); },
  patchWatchlist(id, b) { return this.call('/api/watchlists/' + id,
                          { method: 'PATCH', body: JSON.stringify(b) }); },
};

// ----------------------------------------------------------------- utils --
const money = n => '$' + Math.round(Number(n) || 0).toLocaleString('en-US');
const money2 = n => '$' + (Number(n) || 0).toLocaleString('en-US',
                    { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const pct = n => Math.round(Number(n) || 0) + '%';
const miles = n => (Number(n) || 0).toFixed(n < 10 ? 1 : 0) + ' mi';

/** Escape before any interpolation into innerHTML. Listing titles and seller
 *  names are attacker-controlled text from a public marketplace. */
function esc(value) {
  return String(value == null ? '' : value)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

function timeAgo(iso) {
  if (!iso) return '';
  const seconds = (Date.now() - new Date(iso).getTime()) / 1000;
  if (seconds < 90) return 'just now';
  if (seconds < 3600) return Math.round(seconds / 60) + 'm ago';
  if (seconds < 86400) return Math.round(seconds / 3600) + 'h ago';
  return Math.round(seconds / 86400) + 'd ago';
}

let toastTimer;
function toast(message) {
  const el = document.getElementById('toast');
  el.textContent = message;
  el.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove('show'), 2600);
}

function confidenceClass(c) { return c < 0.35 ? 'low' : c < 0.6 ? 'mid' : ''; }

/** Drop a photo that failed to load; show the empty state if none survive. */
window.heroFailed = function (img) {
  const strip = img.parentElement;
  img.remove();
  if (strip && !strip.querySelector('img')) {
    strip.outerHTML = '<div class="hero-empty">Photos unavailable — open the listing</div>';
  }
};

function confidenceWord(c) {
  if (c >= 0.75) return 'well supported';
  if (c >= 0.5)  return 'reasonable';
  if (c >= 0.3)  return 'thin';
  return 'a guess';
}

// ------------------------------------------------------------ components --
function dealCard(deal) {
  const thumb = deal.image_url
    ? `<img class="deal-thumb" src="${esc(deal.image_url)}" alt="" loading="lazy"
            onerror="this.replaceWith(Object.assign(document.createElement('div'),
                     {className:'deal-thumb deal-thumb-empty',textContent:'📦'}))">`
    : `<div class="deal-thumb deal-thumb-empty">📦</div>`;

  const pills = [
    `<span class="pill pill-score">${Math.round(deal.deal_score)}</span>`,
    `<span class="pill pill-grade-${esc(deal.condition_grade)}">${esc(deal.condition_grade)}</span>`,
    `<span class="pill">${miles(deal.distance_miles)}</span>`,
  ];
  if (deal.est_days_to_sell) pills.push(`<span class="pill">~${deal.est_days_to_sell}d to sell</span>`);
  if (deal.warning_count) {
    pills.push(`<span class="pill pill-warn">⚠ ${deal.warning_count}</span>`);
  }
  if (deal.confidence < 0.35) pills.push(`<span class="pill pill-danger">unverified</span>`);
  if (deal.status === 'saved') pills.push(`<span class="pill pill-score">saved</span>`);

  return `
    <a class="deal-card" href="#/deal/${deal.id}">
      ${thumb}
      <div class="deal-body">
        <p class="deal-title">${esc(deal.title)}</p>
        <div class="deal-money">
          <span class="deal-profit">${money(deal.net_profit)}</span>
          <span class="deal-roi">${pct(deal.roi_pct)} ROI</span>
        </div>
        <div class="deal-prices">
          buy <b>${money(deal.buy_price)}</b> → sells <b>${money(deal.resale_estimate)}</b>
        </div>
        <div class="deal-meta">${pills.join('')}</div>
        <div class="conf-bar">
          <div class="conf-fill ${confidenceClass(deal.confidence)}"
               style="width:${Math.round((deal.confidence || 0) * 100)}%"></div>
        </div>
      </div>
    </a>`;
}

function emptyState(icon, title, body) {
  return `<div class="empty"><div class="empty-icon">${icon}</div>
          <h3>${esc(title)}</h3><p>${body}</p></div>`;
}

const skeletons = n => Array.from({ length: n }, () => '<div class="skeleton"></div>').join('');

// ----------------------------------------------------------------- views --
const view = () => document.getElementById('view');
const setTitle = t => { document.getElementById('view-title').textContent = t; };
const setFilters = html => { document.getElementById('filter-bar').innerHTML = html || ''; };

const FILTERS = [
  { key: 'all',      label: 'All',        params: {} },
  { key: 'best',     label: 'Best',       params: { sort: 'score' } },
  { key: 'profit',   label: 'Biggest $',  params: { sort: 'profit' } },
  { key: 'close',    label: 'Closest',    params: { sort: 'distance' } },
  { key: 'new',      label: 'Newest',     params: { sort: 'newest' } },
  { key: 'saved',    label: 'Saved',      params: { status: 'saved' } },
];

async function viewDeals() {
  setTitle('Deals');
  const state = Store.filters;
  const active = state.key || 'best';

  setFilters(FILTERS.map(f =>
    `<button class="chip" data-filter="${f.key}" aria-pressed="${f.key === active}">${f.label}</button>`
  ).join(''));

  document.getElementById('filter-bar').onclick = event => {
    const button = event.target.closest('[data-filter]');
    if (!button) return;
    Store.filters = { key: button.dataset.filter };
    viewDeals();
  };

  view().innerHTML = skeletons(4);

  try {
    const filter = FILTERS.find(f => f.key === active) || FILTERS[1];
    const params = { limit: 60, ...filter.params };
    if (filter.key === 'saved') params.include_dismissed = true;

    const deals = await Api.deals(params);
    if (!deals.length) {
      view().innerHTML = emptyState('🔍', 'Nothing yet',
        `No deals matching this filter. Scans run every hour — tap the refresh
         icon to run one now, or lower the profit bar in Settings.`);
      return;
    }

    const total = deals.reduce((sum, d) => sum + d.net_profit, 0);
    view().innerHTML = `
      <div class="section">
        <div class="stat-grid">
          <div class="stat"><div class="k">Open deals</div><div class="v">${deals.length}</div></div>
          <div class="stat"><div class="k">If you got them all</div><div class="v">${money(total)}</div></div>
        </div>
      </div>
      ${deals.map(dealCard).join('')}`;
  } catch (error) {
    view().innerHTML = emptyState('⚠️', "Couldn't load deals", esc(error.message));
  }
}

async function viewDeal(id) {
  setTitle('Deal');
  setFilters('');
  view().innerHTML = skeletons(3);

  let deal;
  try {
    deal = await Api.deal(id);
  } catch (error) {
    view().innerHTML = emptyState('⚠️', 'Not found', esc(error.message));
    return;
  }

  const m = deal.money;
  const c = deal.condition;
  const comps = deal.comps;

  // Marketplace CDN links expire and get hotlink-blocked constantly, so a
  // failed photo has to collapse rather than leave a 250px empty frame. If
  // every photo fails, the strip replaces itself with the no-photos message.
  const hero = deal.image_urls.length
    ? `<div class="detail-hero"><div class="hero-scroll" id="hero-strip">
         ${deal.image_urls.map(u =>
           `<img src="${esc(u)}" alt="" loading="lazy" onerror="heroFailed(this)">`).join('')}
       </div></div>`
    : `<div class="detail-hero"><div class="hero-empty">No photos in this listing</div></div>`;

  // Warnings first. If something is wrong with a deal, it should be the first
  // thing she reads, not a footnote under the profit number.
  const warnings = (deal.warnings || []).map(w =>
    `<div class="alert alert-warn">${esc(w)}</div>`).join('');

  const safetyClass = deal.safety.level === 'high' ? 'alert-danger' : 'alert-info';
  const safety = `
    <div class="alert ${safetyClass}">
      <b>${esc(deal.safety.headline)}</b>
      <ul class="plain" style="margin-top:7px">
        ${deal.safety.rules.slice(0, 4).map(r => `<li>${esc(r)}</li>`).join('')}
      </ul>
      <div style="margin-top:8px;font-size:12.5px">${esc(deal.safety.payment_note)}</div>
    </div>`;

  const costRow = (label, value, cls = 'cost') => value
    ? `<div class="money-row"><span class="label">${label}</span>
         <span class="value ${cls}">−${money2(value)}</span></div>` : '';

  // 'prior' carries no evidence — it's a category average, and the method
  // line above already says so. Listing it as a source implies comps exist.
  const sources = (comps.sources || [])
    .filter(s => s.provider !== 'prior')
    .filter(s => (s.examples || []).length > 0);
  const compEvidence = sources.length ? sources.map(source => `
    <div class="source-head">
      <span>${esc(source.provider)}</span>
      <span>${source.n || 0} comp${source.n === 1 ? '' : 's'}</span>
    </div>
    ${source.note ? `<div style="font-size:12.5px;color:var(--text-dim);margin-bottom:6px">${esc(source.note)}</div>` : ''}
    ${(source.examples || []).slice(0, 4).map(ex => `
      <div class="comp-row">
        ${ex.url ? `<a href="${esc(ex.url)}" target="_blank" rel="noopener">${esc(ex.title)}</a>`
                 : `<span>${esc(ex.title)}</span>`}
        <span class="price">${money(ex.price)}</span>
      </div>`).join('')}
  `).join('') : `<p style="font-size:13px;color:var(--text-dim);margin:0">
      No comparable sales were found, so this estimate comes from a category
      average. Check the price yourself before buying.</p>`;

  const checklist = (deal.inspection_checklist || []).length ? `
    <div class="section">
      <h3>Check before you pay</h3>
      <div class="card"><ul class="plain">
        ${deal.inspection_checklist.map(i => `<li>${esc(i)}</li>`).join('')}
      </ul></div>
    </div>` : '';

  const condDetail = [
    ...(c.damage_flags || []).map(f => `<li>${esc(f)}</li>`),
    ...(c.missing_parts || []).map(f => `<li>Missing: ${esc(f)}</li>`),
    ...(c.photo_caveats || []).map(f => `<li>${esc(f)}</li>`),
  ].join('');

  const priceHistory = (deal.price_history || []).length > 1 ? `
    <div class="section"><h3>Price history</h3><div class="card">
      ${deal.price_history.map(p =>
        `<div class="money-row"><span class="label">${esc(new Date(p.at).toLocaleDateString())}</span>
         <span class="value">${money(p.price)}</span></div>`).join('')}
    </div></div>` : '';

  view().innerHTML = `
    <a class="back-link" href="#/deals">← Deals</a>
    ${hero}
    <div class="detail-head">
      <h2>${esc(deal.title)}</h2>
      <div class="detail-sub">
        ${esc(deal.location || 'Unknown location')} · ${miles(deal.distance_miles)} ·
        found ${esc(timeAgo(deal.created_at))}
        ${deal.seller_name ? ' · ' + esc(deal.seller_name) : ''}
      </div>
    </div>

    ${warnings}

    <div class="headline-profit">
      <span class="big">${money(m.net_profit)}</span>
      <span class="sub">${pct(m.roi_pct)} ROI<br>after everything</span>
    </div>

    <div class="actions">
      <a class="btn btn-primary full" href="${esc(deal.listing_url)}" target="_blank" rel="noopener">
        Open the listing
      </a>
      <button class="btn" data-act="saved">Save</button>
      <button class="btn btn-danger" data-act="passed">Pass</button>
      <button class="btn btn-ghost full" data-act="bought">I bought it</button>
    </div>

    <div class="section">
      <h3>The money</h3>
      <div class="card">
        <div class="money-row"><span class="label">Asking price</span>
          <span class="value">${money2(m.buy_price)}</span></div>
        <div class="money-row"><span class="label">Expected resale (${esc(m.venue.replace('_',' '))})</span>
          <span class="value">${money2(m.resale_estimate)}</span></div>
        <div class="money-row"><span class="label">Range</span>
          <span class="value cost">${money(m.resale_low)} – ${money(m.resale_high)}</span></div>
        ${costRow('Platform fees', m.platform_fees)}
        ${costRow('Shipping &amp; supplies', m.shipping_cost)}
        ${costRow('Clean-up / repair', m.refurb_cost)}
        ${costRow('Getting there', m.trip_cost)}
        <div class="money-row total"><span class="label">You keep</span>
          <span class="value ${m.net_profit < 0 ? 'neg' : ''}">${money2(m.net_profit)}</span></div>
      </div>
    </div>

    <div class="section">
      <h3>The drive</h3>
      <div class="card">
        <div class="money-row"><span class="label">Distance</span>
          <span class="value">${miles(deal.distance_miles)}</span></div>
        <div class="money-row"><span class="label">Worth driving up to</span>
          <span class="value">${miles(deal.max_worth_driving_miles)}</span></div>
        <div class="money-row"><span class="label">Round-trip cost</span>
          <span class="value cost">${money2(m.trip_cost)}</span></div>
        <div class="money-row"><span class="label">Size</span>
          <span class="value">${esc(deal.bulk_class.replace('_', ' '))}</span></div>
      </div>
    </div>

    <div class="section">
      <h3>Condition — grade ${esc(c.grade)}${c.analyzed_by_ai ? '' : ' (from the text only)'}</h3>
      <div class="card">
        ${c.summary ? `<p style="margin:0 0 9px;font-size:14px">${esc(c.summary)}</p>` : ''}
        ${(c.identified_brand || c.identified_model) ? `
          <div class="money-row"><span class="label">Identified as</span>
            <span class="value">${esc([c.identified_brand, c.identified_model].filter(Boolean).join(' '))}</span></div>` : ''}
        <div class="money-row"><span class="label">Works?</span>
          <span class="value">${esc(c.functional_status.replace('_', ' '))}</span></div>
        ${c.uses_stock_photos ? `<div class="alert alert-warn" style="margin-top:9px">
           Stock photos — you can't see the actual item.</div>` : ''}
        ${condDetail ? `<ul class="plain" style="margin-top:9px">${condDetail}</ul>` : ''}
        ${(c.positive_signals || []).length ? `<ul class="plain" style="margin-top:7px;color:var(--accent)">
           ${c.positive_signals.map(s => `<li>${esc(s)}</li>`).join('')}</ul>` : ''}
      </div>
    </div>

    ${checklist}

    <div class="section">
      <h3>Why this scored ${Math.round(deal.deal_score)}</h3>
      <div class="card"><ul class="reasons">
        ${(deal.reasons || []).map(r => `<li>${esc(r)}</li>`).join('')}
      </ul></div>
    </div>

    <div class="section">
      <h3>What it's worth — ${esc(confidenceWord(comps.confidence))}</h3>
      <div class="card">
        <div class="money-row"><span class="label">Estimate</span>
          <span class="value">${money(comps.estimate_low)} – ${money(comps.estimate_high)}</span></div>
        <div class="money-row"><span class="label">Based on</span>
          <span class="value">${comps.sample_size} comparable${comps.sample_size === 1 ? '' : 's'}</span></div>
        ${comps.est_days_to_sell ? `<div class="money-row"><span class="label">Typical time to sell</span>
          <span class="value">${comps.est_days_to_sell} days</span></div>` : ''}
        ${comps.method ? `<div style="font-size:12.5px;color:var(--text-dim);margin-top:8px">
           ${esc(comps.method)}${comps.query_used ? ` · searched “${esc(comps.query_used)}”` : ''}</div>` : ''}
        ${compEvidence}
      </div>
    </div>

    ${priceHistory}

    <div class="section">
      <h3>Meeting the seller</h3>
      ${safety}
    </div>

    ${deal.description ? `<div class="section"><h3>Seller's description</h3>
      <div class="card"><p style="margin:0;font-size:13.5px;white-space:pre-wrap">${esc(deal.description)}</p></div>
    </div>` : ''}

    ${deal.screenshot_url ? `<div class="section"><h3>Listing snapshot</h3>
      <div class="card" style="padding:0;overflow:hidden">
        <img src="${esc(deal.screenshot_url)}" alt="Screenshot of the listing as it appeared"
             style="width:100%;display:block">
      </div>
      <p style="font-size:12px;color:var(--text-faint);margin:6px 2px 0">
        Captured when we found it — sellers edit and delete listings.</p>
    </div>` : ''}
  `;

  view().querySelectorAll('[data-act]').forEach(button => {
    button.onclick = () => act(deal.id, button.dataset.act);
  });
}

async function act(dealId, action) {
  try {
    if (action === 'bought') {
      const paid = prompt('What did you actually pay?');
      if (paid === null) return;
      await Api.feedback(dealId, { action: 'bought', actual_buy_price: parseFloat(paid) || null });
      toast('Marked as bought — tell me what it sells for later');
    } else {
      await Api.feedback(dealId, { action });
      toast(action === 'saved' ? 'Saved' : 'Passed');
      if (action === 'passed') location.hash = '#/deals';
    }
  } catch (error) {
    toast('Failed: ' + error.message);
  }
}

async function viewRuns() {
  setTitle('Pickup runs');
  setFilters('');
  view().innerHTML = skeletons(2);

  try {
    const runs = await Api.runs({ cluster_miles: 8, min_run_size: 2 });
    if (!runs.length) {
      view().innerHTML = emptyState('🚗', 'No runs yet',
        `When two or more deals turn up close together, they show up here as a
         single trip. One drive, several pickups — that's where the margin on
         small items actually comes from.`);
      return;
    }
    view().innerHTML = runs.map(run => `
      <div class="run-card">
        <div class="run-head">
          <span class="run-label">${esc(run.label)}</span>
          <span class="run-profit">${money(run.profit_after_trip)}</span>
        </div>
        <div class="run-meta">
          ${run.deal_count} pickups · ${miles(run.distance_from_home)} each way ·
          about ${run.est_hours.toFixed(1)}h · trip costs
          ${money(run.total_net_profit - run.profit_after_trip)}
        </div>
        <div class="actions" style="margin:0">
          ${run.deal_ids.slice(0, 4).map(id =>
            `<a class="btn btn-ghost" href="#/deal/${id}">Deal ${id}</a>`).join('')}
        </div>
      </div>`).join('');
  } catch (error) {
    view().innerHTML = emptyState('⚠️', "Couldn't load runs", esc(error.message));
  }
}

function viewAdd() {
  setTitle('Check an item');
  setFilters('');
  view().innerHTML = `
    <p style="color:var(--text-dim);font-size:14px;margin-top:0">
      Standing in front of something? Paste the listing link, or just type what
      it is and what they want for it.
    </p>
    <div class="field">
      <label for="m-url">Listing link</label>
      <input id="m-url" type="url" inputmode="url" placeholder="https://facebook.com/marketplace/item/…"
             autocapitalize="off" spellcheck="false">
    </div>
    <div class="field">
      <label for="m-title">What is it?</label>
      <input id="m-title" type="text" placeholder="Herman Miller Aeron size B">
    </div>
    <div class="field">
      <label for="m-price">Asking price</label>
      <input id="m-price" type="number" inputmode="decimal" placeholder="180">
    </div>
    <div class="field">
      <label for="m-loc">Where</label>
      <input id="m-loc" type="text" placeholder="Beaverton">
    </div>
    <div class="field">
      <label for="m-text">Anything else</label>
      <textarea id="m-text" rows="4" placeholder="Paste the seller's description here"></textarea>
    </div>
    <button class="btn btn-primary" id="m-go">Check it</button>
    <p class="hint" style="margin-top:10px;color:var(--text-dim);font-size:12.5px">
      It gets queued and priced on the next scan. Tap the refresh icon at the
      top to run one straight away.
    </p>`;

  document.getElementById('m-go').onclick = async () => {
    const payload = {
      url: document.getElementById('m-url').value.trim() || null,
      title: document.getElementById('m-title').value.trim() || null,
      price: parseFloat(document.getElementById('m-price').value) || null,
      location: document.getElementById('m-loc').value.trim() || null,
      text: document.getElementById('m-text').value.trim(),
    };
    if (!payload.url && !payload.title && !payload.text) {
      toast('Add a link, a title, or a description');
      return;
    }
    if (!payload.text) payload.text = payload.title || '';
    try {
      const result = await Api.manual(payload);
      toast(`Queued: ${result.queued.title}`);
      ['m-url', 'm-title', 'm-price', 'm-loc', 'm-text'].forEach(
        id => { document.getElementById(id).value = ''; });
    } catch (error) {
      toast('Failed: ' + error.message);
    }
  };
}

const SETTING_FIELDS = [
  { key: 'profit.min_net_profit',  label: 'Minimum profit', unit: '$', step: 10,
    hint: "Don't alert me unless I'd clear this much after every cost." },
  { key: 'profit.min_roi_pct',     label: 'Minimum return', unit: '%', step: 5,
    hint: 'Return on the cash you put in. Stops thin margins on pricey items.' },
  { key: 'profit.max_buy_price',   label: 'Most I’ll spend', unit: '$', step: 100,
    hint: "Never show me anything above this, however good it looks." },
  { key: 'trip.max_radius_miles',  label: 'Furthest I’ll drive', unit: 'mi', step: 5,
    hint: 'Hard ceiling. Big-profit items get the full distance; small ones stay close.' },
  { key: 'trip.max_trip_cost_fraction', label: 'Share of profit spent driving',
    unit: '', step: 0.05,
    hint: 'Raise this to travel further for the same money. 0.25 means a quarter.' },
  { key: 'trip.hourly_time_value', label: 'Your time per hour', unit: '$', step: 5,
    hint: 'Used to work out whether a trip pays for itself.' },
  { key: 'profit.min_deal_score',  label: 'Quality bar', unit: '/100', step: 5,
    hint: 'Catches deals that add up on paper but look risky in the photos.' },
];

async function viewSettings() {
  setTitle('Settings');
  setFilters('');
  view().innerHTML = skeletons(3);

  try {
    const [settings, status] = await Promise.all([Api.settings(), Api.status()]);
    const eff = settings.effective;

    const value = key => {
      const [section, field] = key.split('.');
      return (settings.overrides[key] !== undefined)
        ? settings.overrides[key] : eff[section][field];
    };

    const warnings = (status.warnings || []).map(w =>
      `<div class="alert alert-warn">${esc(w)}</div>`).join('');

    view().innerHTML = `
      ${warnings}
      <div class="section">
        <h3>Status</h3>
        <div class="stat-grid">
          <div class="stat"><div class="k">Listings tracked</div><div class="v">${status.active_listings}</div></div>
          <div class="stat"><div class="k">Open deals</div><div class="v">${status.open_deals}</div></div>
          <div class="stat"><div class="k">AI spend today</div>
            <div class="v">${money2(status.ai_spend_today.cost_usd)}</div></div>
          <div class="stat"><div class="k">Last scan</div>
            <div class="v" style="font-size:15px">${esc(
              status.last_scan ? timeAgo(status.last_scan.started_at) : 'never')}</div></div>
        </div>
      </div>

      <div class="section">
        <h3>What counts as a deal</h3>
        ${SETTING_FIELDS.map(f => `
          <div class="field">
            <label for="s-${f.key}">${esc(f.label)} ${f.unit ? `(${esc(f.unit)})` : ''}</label>
            <div class="hint">${esc(f.hint)}</div>
            <input id="s-${f.key}" data-key="${f.key}" type="number"
                   inputmode="decimal" step="${f.step}" value="${value(f.key)}">
          </div>`).join('')}
        <button class="btn btn-primary" id="s-save">Save</button>
      </div>

      <div class="section">
        <h3>Scanning</h3>
        <div class="card">
          <div class="money-row"><span class="label">Market</span>
            <span class="value">${esc(status.market)}</span></div>
          <div class="money-row"><span class="label">Sources</span>
            <span class="value">${esc((status.collectors || []).join(', ') || 'none')}</span></div>
          <div class="money-row"><span class="label">Alerts via</span>
            <span class="value">${esc((status.notify_channels || []).join(', ') || 'none')}</span></div>
          <div class="money-row"><span class="label">Next scan</span>
            <span class="value">${esc(status.scheduler.next_run
              ? new Date(status.scheduler.next_run).toLocaleTimeString([], {hour:'numeric',minute:'2-digit'})
              : 'not scheduled')}</span></div>
        </div>
      </div>

      <div class="section">
        <h3>Watchlists</h3>
        <div class="card" id="watchlists">Loading…</div>
      </div>

      <div class="section">
        <button class="btn btn-danger" id="s-logout">Disconnect this device</button>
      </div>`;

    document.getElementById('s-save').onclick = async () => {
      const updates = {};
      view().querySelectorAll('[data-key]').forEach(input => {
        const parsed = parseFloat(input.value);
        if (!Number.isNaN(parsed)) updates[input.dataset.key] = parsed;
      });
      try {
        await Api.patchSettings(updates);
        toast('Saved — takes effect on the next scan');
      } catch (error) {
        toast('Failed: ' + error.message);
      }
    };

    document.getElementById('s-logout').onclick = () => {
      if (confirm('Disconnect? You’ll need the token again to reconnect.')) {
        Store.clear();
        location.reload();
      }
    };

    Api.watchlists().then(lists => {
      document.getElementById('watchlists').innerHTML = lists.map(w => `
        <div class="money-row">
          <span class="label">${esc(w.name)}</span>
          <button class="chip" data-wl="${w.id}" aria-pressed="${w.enabled}">
            ${w.enabled ? 'on' : 'off'}</button>
        </div>`).join('');
      document.getElementById('watchlists').onclick = async event => {
        const button = event.target.closest('[data-wl]');
        if (!button) return;
        const enabled = button.getAttribute('aria-pressed') !== 'true';
        try {
          await Api.patchWatchlist(button.dataset.wl, { enabled });
          button.setAttribute('aria-pressed', String(enabled));
          button.textContent = enabled ? 'on' : 'off';
        } catch (error) { toast('Failed: ' + error.message); }
      };
    }).catch(() => {
      document.getElementById('watchlists').textContent = 'Could not load watchlists.';
    });

  } catch (error) {
    view().innerHTML = emptyState('⚠️', "Couldn't load settings", esc(error.message));
  }
}

// ---------------------------------------------------------------- router --
const ROUTES = [
  [/^#\/deals?$/,        viewDeals],
  [/^#\/deal\/(\d+)$/,   viewDeal],
  [/^#\/runs$/,          viewRuns],
  [/^#\/add$/,           viewAdd],
  [/^#\/settings$/,      viewSettings],
];

function route() {
  // Navigating while signed out must not fire an API call: it returns 401,
  // which clears the token and repaints the setup screen with a "rejected"
  // error the user never earned. Deep links are preserved — once connected,
  // showApp() calls route() again and lands on the requested view.
  if (!Store.token) { showSetup(); return; }

  const hash = location.hash || '#/deals';
  for (const [pattern, handler] of ROUTES) {
    const match = hash.match(pattern);
    if (match) {
      window.scrollTo(0, 0);
      handler(match[1]);
      break;
    }
  }
  const tab = hash.split('/')[1] || 'deals';
  document.querySelectorAll('.tab').forEach(el => {
    if (el.dataset.tab === tab || (tab === 'deal' && el.dataset.tab === 'deals')) {
      el.setAttribute('aria-current', 'page');
    } else {
      el.removeAttribute('aria-current');
    }
  });
}

// ------------------------------------------------------------------ boot --
function showSetup(message) {
  document.getElementById('app').classList.add('hidden');
  document.getElementById('setup').classList.remove('hidden');
  if (message) document.getElementById('setup-error').textContent = message;
}

function showApp() {
  document.getElementById('setup').classList.add('hidden');
  document.getElementById('app').classList.remove('hidden');
  route();
}

async function connect(token, baseUrl) {
  Store.token = token;
  Store.baseUrl = baseUrl || '';
  try {
    await Api.status();
    showApp();
    return true;
  } catch (error) {
    Store.clear();
    document.getElementById('setup-error').textContent =
      'Could not connect: ' + error.message;
    return false;
  }
}

document.getElementById('setup-go').onclick = () => {
  const token = document.getElementById('setup-token').value.trim();
  const base = document.getElementById('setup-url').value.trim().replace(/\/$/, '');
  if (!token) {
    document.getElementById('setup-error').textContent = 'Paste the token first.';
    return;
  }
  connect(token, base);
};
document.getElementById('setup-token').addEventListener('keydown', e => {
  if (e.key === 'Enter') document.getElementById('setup-go').click();
});

document.getElementById('btn-scan').onclick = async event => {
  const button = event.currentTarget;
  button.classList.add('spinning');
  try {
    await Api.scan();
    toast('Scanning… deals will appear shortly');
    // The scan runs in the background on the server; give it a moment before
    // refreshing rather than pretending it's instant.
    setTimeout(() => { route(); button.classList.remove('spinning'); }, 6000);
  } catch (error) {
    toast('Failed: ' + error.message);
    button.classList.remove('spinning');
  }
};

window.addEventListener('hashchange', route);

(function boot() {
  // A one-tap onboarding link can carry the token; strip it from the URL
  // immediately so it doesn't sit in history or get shared by accident.
  const params = new URLSearchParams(location.search);
  const urlToken = params.get('token');
  if (urlToken) {
    history.replaceState(null, '', location.pathname + location.hash);
    connect(urlToken, '');
    return;
  }
  if (Store.token) showApp(); else showSetup();
})();

if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch(() => {});
  });
}
