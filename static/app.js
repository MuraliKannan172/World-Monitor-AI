/* WorldMonitor AI — Alpine.js store + WS client */

const SEV_COLORS = {
  0: '#6b7280', 1: '#10b981', 2: '#10b981', 3: '#34d399',
  4: '#fbbf24', 5: '#f59e0b', 6: '#f59e0b', 7: '#ef4444',
  8: '#ef4444', 9: '#dc2626', 10: '#b91c1c',
};

const DEFAULT_CLOCK_ZONES = [
  { label: 'UTC',       tz: 'UTC',                time: '', date: '' },
  { label: 'New York',  tz: 'America/New_York',   time: '', date: '' },
  { label: 'London',    tz: 'Europe/London',      time: '', date: '' },
  { label: 'Moscow',    tz: 'Europe/Moscow',      time: '', date: '' },
  { label: 'Dubai',     tz: 'Asia/Dubai',         time: '', date: '' },
  { label: 'Singapore', tz: 'Asia/Singapore',     time: '', date: '' },
  { label: 'Tokyo',     tz: 'Asia/Tokyo',         time: '', date: '' },
  { label: 'Sydney',    tz: 'Australia/Sydney',   time: '', date: '' },
];

const EXTRA_TIMEZONES = [
  { label: 'Los Angeles',  tz: 'America/Los_Angeles' },
  { label: 'Chicago',      tz: 'America/Chicago' },
  { label: 'São Paulo',    tz: 'America/Sao_Paulo' },
  { label: 'Buenos Aires', tz: 'America/Argentina/Buenos_Aires' },
  { label: 'Paris',        tz: 'Europe/Paris' },
  { label: 'Berlin',       tz: 'Europe/Berlin' },
  { label: 'Istanbul',     tz: 'Europe/Istanbul' },
  { label: 'Riyadh',       tz: 'Asia/Riyadh' },
  { label: 'Karachi',      tz: 'Asia/Karachi' },
  { label: 'Mumbai',       tz: 'Asia/Kolkata' },
  { label: 'Bangkok',      tz: 'Asia/Bangkok' },
  { label: 'Beijing',      tz: 'Asia/Shanghai' },
  { label: 'Seoul',        tz: 'Asia/Seoul' },
  { label: 'Auckland',     tz: 'Pacific/Auckland' },
  { label: 'Honolulu',     tz: 'Pacific/Honolulu' },
  { label: 'Nairobi',      tz: 'Africa/Nairobi' },
  { label: 'Lagos',        tz: 'Africa/Lagos' },
  { label: 'Cairo',        tz: 'Africa/Cairo' },
];

function worldMonitor() {
  return {
    // Map
    mapMode: '2d',
    mapSrc: '/map/2d',

    // Events
    events: [],
    eventCount: 0,

    // Layer panel
    layerDefs: [],
    activeLayers: {},

    // Chat
    models: [],
    selectedModel: '',
    ollamaDown: false,
    chatInput: '',
    chatHistory: [],
    streaming: false,
    streamingText: '',
    chatWsReady: false,
    sessionId: '',
    _chatWs: null,

    // Quick questions
    quickQuestions: [
      { label: '🌐 Global briefing',  prompt: 'Give me a global intelligence briefing of the most significant events happening right now.' },
      { label: '⚔️ Conflicts',        prompt: 'What active conflict zones are showing activity? Summarize the situation in each.' },
      { label: '🔥 Critical events',  prompt: 'List all critical severity events (severity 8-10) from the current data.' },
      { label: '🌏 Asia update',      prompt: 'Summarize the latest events and developments in Asia.' },
      { label: '🇪🇺 Europe update',  prompt: 'Summarize the latest events and developments in Europe.' },
      { label: '🌍 Africa update',    prompt: 'What are the major events happening across Africa?' },
      { label: '🛡️ Cyber threats',   prompt: 'What are the latest cyber security incidents and digital threats in the current event feed?' },
      { label: '⚡ Energy sector',    prompt: 'What energy sector events are occurring and how might they impact global stability?' },
      { label: '💰 Markets impact',   prompt: 'Which geopolitical events are most likely to impact financial markets?' },
      { label: '🗺️ Hotspots',        prompt: 'Which countries or regions are experiencing the highest concentration of incidents right now?' },
      { label: '📊 24h summary',      prompt: 'Give me a concise summary of events from the last 24 hours.' },
      { label: '🔮 Risk forecast',    prompt: 'Based on current event patterns, which regions face escalating instability in the near term?' },
    ],

    // Countries (extracted from events)
    countries: [],

    // World clock
    clockOpen: false,
    clockZones: DEFAULT_CLOCK_ZONES.map(z => ({ ...z })),
    customTz: '',
    availableTimezones: EXTRA_TIMEZONES,

    _filterTimer: null,
    _clockTimer: null,

    // ── Init ─────────────────────────────────────────────────────────────

    async init() {
      this.sessionId = crypto.randomUUID();
      await Promise.all([this.loadModels(), this.loadLayerDefs(), this.loadEvents()]);
      this.connectEventWs();
      this.connectChatWs();
      this.tickClock();
      this._clockTimer = setInterval(() => this.tickClock(), 1000);
    },

    // ── Layer panel ───────────────────────────────────────────────────────

    async loadLayerDefs() {
      try {
        const res = await fetch('/api/layers');
        this.layerDefs = await res.json();
      } catch { this.layerDefs = []; }
    },

    get layerGroups() {
      return [...new Set(this.layerDefs.map(l => l.group))];
    },

    get activeLayerCount() {
      return Object.values(this.activeLayers).filter(Boolean).length;
    },

    layersByGroup(group) {
      return this.layerDefs.filter(l => l.group === group);
    },

    toggleLayer(id) {
      this.activeLayers = { ...this.activeLayers, [id]: !this.activeLayers[id] };
      const frame = document.getElementById('map-frame');
      if (frame?.contentWindow) {
        frame.contentWindow.postMessage(
          { action: 'toggle_layer', layer_id: id, active: !!this.activeLayers[id] }, '*'
        );
      }
    },

    // ── World Clock ───────────────────────────────────────────────────────

    tickClock() {
      const now = new Date();
      this.clockZones = this.clockZones.map(z => ({
        ...z,
        time: now.toLocaleTimeString('en-US', {
          timeZone: z.tz, hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false,
        }),
        date: now.toLocaleDateString('en-US', {
          timeZone: z.tz, weekday: 'short', month: 'short', day: 'numeric',
        }),
      }));
    },

    addClockZone() {
      if (!this.customTz) return;
      const found = EXTRA_TIMEZONES.find(z => z.tz === this.customTz);
      if (!found || this.clockZones.some(z => z.tz === this.customTz)) return;
      this.clockZones = [...this.clockZones, { label: found.label, tz: found.tz, time: '', date: '' }];
      this.tickClock();
      this.customTz = '';
    },

    // ── Map ───────────────────────────────────────────────────────────────

    setMapMode(mode) {
      this.mapMode = mode;
      this.mapSrc = `/map/${mode}`;
    },

    // ── Events ────────────────────────────────────────────────────────────

    async loadEvents() {
      const params = this.buildQueryParams();
      const res = await fetch(`/api/events?${params}`);
      const data = await res.json();
      this.events = data.events;
      this.eventCount = data.count;
      this.extractCountries(data.events);
    },

    buildQueryParams() {
      return new URLSearchParams({ limit: '100' }).toString();
    },

    extractCountries(events) {
      const seen = new Set(this.countries);
      for (const ev of events) {
        if (ev.country) seen.add(ev.country);
      }
      this.countries = [...seen].sort();
    },

    prependEvent(ev) {
      this.events.unshift(ev);
      if (this.events.length > 200) this.events.pop();
      this.eventCount++;
      if (ev.country && !this.countries.includes(ev.country)) {
        this.countries = [...this.countries, ev.country].sort();
      }
    },

    // ── Event WebSocket ───────────────────────────────────────────────────

    connectEventWs() {
      const proto = location.protocol === 'https:' ? 'wss' : 'ws';
      const ws = new WebSocket(`${proto}://${location.host}/ws`);

      ws.onmessage = (e) => {
        const msg = JSON.parse(e.data);
        if (msg.type === 'new_event') this.prependEvent(msg.event);
        if (msg.type === 'ingest_complete') this.loadEvents();
      };

      ws.onclose = () => setTimeout(() => this.connectEventWs(), 3000);
      setInterval(() => { if (ws.readyState === WebSocket.OPEN) ws.send('ping'); }, 25000);
    },

    // ── Models ────────────────────────────────────────────────────────────

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

    // ── Chat WebSocket (persistent) ───────────────────────────────────────

    connectChatWs() {
      const proto = location.protocol === 'https:' ? 'wss' : 'ws';
      this._chatWs = new WebSocket(`${proto}://${location.host}/ws/chat`);
      this.chatWsReady = false;

      this._chatWs.onopen = () => { this.chatWsReady = true; };

      this._chatWs.onmessage = (e) => {
        const msg = JSON.parse(e.data);
        if (msg.type === 'token') {
          this.streamingText += msg.content;
          this.$nextTick(() => this.scrollChat());
        }
        if (msg.type === 'done') {
          this.chatHistory.push({
            role: 'assistant',
            content: this.renderMarkdown(this.streamingText),
          });
          this.streamingText = '';
          this.streaming = false;
          this.$nextTick(() => this.scrollChat());
        }
      };

      this._chatWs.onerror = () => {
        this.streaming = false;
        this.chatWsReady = false;
      };

      this._chatWs.onclose = () => {
        this.chatWsReady = false;
        setTimeout(() => this.connectChatWs(), 3000);
      };

      setInterval(() => {
        if (this._chatWs?.readyState === WebSocket.OPEN) {
          this._chatWs.send(JSON.stringify({ type: 'ping' }));
        }
      }, 25000);
    },

    handleKeydown(e) {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        this.sendChat();
      }
    },

    autoGrowTextarea(e) {
      const el = e.target;
      el.style.height = 'auto';
      el.style.height = Math.min(el.scrollHeight, 120) + 'px';
    },

    sendChat() {
      const q = this.chatInput.trim();
      if (!q || this.streaming || !this.chatWsReady) return;

      this.chatHistory.push({ role: 'user', content: this.escapeHtml(q) });
      this.chatInput = '';
      this.streaming = true;
      this.streamingText = '';

      this._chatWs.send(JSON.stringify({
        question: q,
        model: this.selectedModel,
        session_id: this.sessionId,
      }));

      this.$nextTick(() => {
        const ta = document.getElementById('chat-input');
        if (ta) ta.style.height = '38px';
        this.scrollChat();
      });
    },

    askQuick(prompt) {
      if (this.streaming || !this.chatWsReady) return;
      this.chatInput = prompt;
      this.sendChat();
    },

    clearChat() {
      this.chatHistory = [];
      this.streamingText = '';
      this.streaming = false;
      this.sessionId = crypto.randomUUID();
    },

    scrollChat() {
      const el = this.$refs.chatMessages;
      if (el) el.scrollTop = el.scrollHeight;
    },

    // ── Formatting helpers ────────────────────────────────────────────────

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

    renderMarkdown(text) {
      return text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.+?)\*/g, '<em>$1</em>')
        .replace(/`([^`]+)`/g, '<code>$1</code>')
        .replace(/\[(\d+)\]/g, '<span class="citation">[$1]</span>')
        .replace(/\n/g, '<br>');
    },
  };
}
