/* WorldMonitor AI — Alpine.js store + WS client */

const SEV_COLORS = {
  0: '#6b7280', 1: '#10b981', 2: '#10b981', 3: '#34d399',
  4: '#fbbf24', 5: '#f59e0b', 6: '#f59e0b', 7: '#ef4444',
  8: '#ef4444', 9: '#dc2626', 10: '#b91c1c',
};

function worldMonitor() {
  return {
    // Map
    mapMode: '2d',
    mapSrc: '/map/2d',

    // Events
    events: [],
    eventCount: 0,

    // Filters
    categories: [
      { id: 'world',            label: 'World',       color: '#60a5fa' },
      { id: 'geopolitics',      label: 'Geopolitics', color: '#a78bfa' },
      { id: 'conflict',         label: 'Conflict',    color: '#ef4444' },
      { id: 'cyber',            label: 'Cyber',       color: '#00d4ff' },
      { id: 'energy',           label: 'Energy',      color: '#fbbf24' },
      { id: 'finance',          label: 'Finance',     color: '#34d399' },
      { id: 'regional_asia',    label: 'Asia',        color: '#f472b6' },
      { id: 'regional_europe',  label: 'Europe',      color: '#818cf8' },
      { id: 'regional_americas',label: 'Americas',    color: '#fb923c' },
      { id: 'tech',             label: 'Tech',        color: '#94a3b8' },
    ],
    selectedCategories: [],
    minSeverity: 0,
    dateFrom: '',
    dateTo: '',
    countries: [],
    selectedCountry: '',

    // Chat
    models: [],
    selectedModel: '',
    ollamaDown: false,
    chatInput: '',
    chatHistory: [],
    streaming: false,
    streamingText: '',

    _chatWs: null,
    _filterTimer: null,

    async init() {
      await this.loadModels();
      await this.loadEvents();
      this.connectEventWs();
    },

    // ── Map ──────────────────────────────────────────────────────────

    setMapMode(mode) {
      this.mapMode = mode;
      this.mapSrc = `/map/${mode}`;
    },

    // ── Events ───────────────────────────────────────────────────────

    async loadEvents() {
      const params = this.buildQueryParams();
      const res = await fetch(`/api/events?${params}`);
      const data = await res.json();
      this.events = data.events;
      this.eventCount = data.count;
      this.extractCountries(data.events);
    },

    buildQueryParams() {
      const p = new URLSearchParams();
      this.selectedCategories.forEach(c => p.append('categories', c));
      if (this.selectedCountry) p.append('countries', this.selectedCountry);
      if (this.minSeverity > 0) p.set('min_severity', this.minSeverity);
      if (this.dateFrom) p.set('date_from', this.dateFrom);
      if (this.dateTo) p.set('date_to', this.dateTo);
      p.set('limit', '100');
      return p.toString();
    },

    extractCountries(events) {
      const seen = new Set(this.countries);
      events.forEach(ev => { if (ev.country) seen.add(ev.country); });
      this.countries = Array.from(seen).sort();
    },

    applyFilters() {
      clearTimeout(this._filterTimer);
      this._filterTimer = setTimeout(() => this.loadEvents(), 300);
    },

    prependEvent(ev) {
      this.events.unshift(ev);
      if (this.events.length > 200) this.events.pop();
      this.eventCount++;
      if (ev.country && !this.countries.includes(ev.country)) {
        this.countries = [...this.countries, ev.country].sort();
      }
    },

    // ── WebSocket (event broadcast) ──────────────────────────────────

    connectEventWs() {
      const proto = location.protocol === 'https:' ? 'wss' : 'ws';
      const ws = new WebSocket(`${proto}://${location.host}/ws`);

      ws.onmessage = (e) => {
        const msg = JSON.parse(e.data);
        if (msg.type === 'new_event') this.prependEvent(msg.event);
        if (msg.type === 'ingest_complete') this.loadEvents();
      };

      ws.onclose = () => setTimeout(() => this.connectEventWs(), 3000);

      // Keepalive ping every 25s
      setInterval(() => { if (ws.readyState === WebSocket.OPEN) ws.send('ping'); }, 25000);
    },

    // ── Models ───────────────────────────────────────────────────────

    async loadModels() {
      try {
        const res = await fetch('/api/models');
        const data = await res.json();
        this.models = data.models;
        this.selectedModel = data.default || data.models[0] || '';
        this.ollamaDown = data.models.length === 0;
      } catch {
        this.ollamaDown = true;
      }
    },

    // ── Chat ─────────────────────────────────────────────────────────

    sendChat() {
      const q = this.chatInput.trim();
      if (!q || this.streaming) return;

      this.chatHistory.push({ role: 'user', content: this.escapeHtml(q) });
      this.chatInput = '';
      this.streaming = true;
      this.streamingText = '';

      const proto = location.protocol === 'https:' ? 'wss' : 'ws';
      const ws = new WebSocket(`${proto}://${location.host}/ws/chat`);
      this._chatWs = ws;

      ws.onopen = () => ws.send(JSON.stringify({ question: q, model: this.selectedModel }));

      ws.onmessage = (e) => {
        const msg = JSON.parse(e.data);
        if (msg.type === 'token') {
          this.streamingText += msg.content;
          this.$nextTick(() => this.scrollChat());
        }
        if (msg.type === 'done') {
          this.chatHistory.push({ role: 'assistant', content: this.escapeHtml(this.streamingText) });
          this.streamingText = '';
          this.streaming = false;
          ws.close();
          this.$nextTick(() => this.scrollChat());
        }
      };

      ws.onerror = () => {
        this.streaming = false;
        this.streamingText = '';
        this.chatHistory.push({ role: 'assistant', content: '[Connection error]' });
      };
    },

    scrollChat() {
      const el = this.$refs.chatMessages;
      if (el) el.scrollTop = el.scrollHeight;
    },

    // ── Formatting helpers ────────────────────────────────────────────

    formatDate(iso) {
      if (!iso) return '—';
      return iso.slice(0, 10);
    },

    severityBarStyle(sev) {
      const color = SEV_COLORS[sev] || SEV_COLORS[0];
      const width = sev ? `${sev * 10}%` : '5%';
      return `background:${color};width:${width}`;
    },

    escapeHtml(text) {
      return text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/\n/g, '<br>');
    },
  };
}
