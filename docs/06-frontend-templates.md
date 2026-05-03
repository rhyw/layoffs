# Phase 6: Frontend Templates & Styling

## Goal
Build the HTML templates, CSS, and JavaScript for the frontend using Django templates + HTMX.

## Template Structure

```
layoffs/templates/
├── base.html                 # Base layout with nav, footer, theme support
├── home.html                 # Main homepage
├── dashboard.html            # Dashboard with charts
├── components/
│   ├── recent_table.html     # Layoff events table partial
│   ├── news_cards.html       # Tech news cards partial
│   ├── community_sidebar.html # Community stats partial
│   └── stats_panel.html      # Summary stats partial
└── 404.html                  # Error page

layoffs/static/
├── css/
│   ├── style.css             # Main stylesheet
│   └── themes.css            # Dark/light theme variables
├── js/
│   ├── theme.js              # Theme toggle logic
│   └── charts.js             # Chart.js dashboard setup
└── images/
    └── logo.svg              # Site logo
```

## Key UI Components

### 6.1 Sticky Header
- Logo (heart icon + "layoffs ICU" text)
- Navigation: Overview, Dashboard
- Theme toggle (sun/moon icon)
- Notification bell
- User menu (login/signup)

### 6.2 Dark/Light Theme
- CSS custom properties for all colors
- Dark mode is default
- Theme persisted in `localStorage.getItem('layoffs-theme')`
- Toggle button in header

```css
:root {
  --bg-primary: #0f0f0f;
  --bg-secondary: #1a1a2e;
  --text-primary: #e0e0e0;
  --accent: #7c3aed;
  /* ... */
}

[data-theme="light"] {
  --bg-primary: #ffffff;
  --bg-secondary: #f5f5f5;
  --text-primary: #1a1a1a;
  /* ... */
}
```

### 6.3 Recent Disclosures Table
| Company | Job Loss | % of Workforce | Source | Date |
|---------|----------|---------------|--------|------|
| Meta | 8,000 | 10% | Reuters | Apr 17 |
| Snap Inc | 1,000 | 16% | CNBC | Apr 15 |

**Features:**
- Clickable rows linking to source URL
- AI badge for AI-related layoffs
- Auto-refresh via HTMX `hx-trigger="every 60s"`
- Responsive: horizontal scroll on mobile

### 6.4 Tech News Section
- 4-column card grid (2-column on tablet, 1 on mobile)
- Each card: thumbnail, source badge, headline, snippet
- "read article" link
- Auto-refresh via HTMX every 120s

### 6.5 Dashboard Charts (Chart.js)
1. **Layoffs Over Time** — Line chart (monthly)
2. **By Industry** — Doughnut/pie chart
3. **Top Companies** — Horizontal bar chart
4. **Total Impact** — Big number counters

### 6.6 Community Sidebar
- Member count + thread count
- Latest 3 discussion threads
- "Browse all" link

### 6.7 Responsive Design
- Mobile-first approach
- Breakpoints: 768px, 1024px
- Sidebar collapses below 1024px
- Table becomes horizontally scrollable on mobile
- Cards stack vertically on mobile

### 6.8 HTMX Integration
```html
<!-- Auto-refreshing table -->
<div hx-get="/htmx/recent-disclosures/"
     hx-trigger="every 60s"
     hx-swap="outerHTML"
     hx-indicator="#loading-spinner">
</div>

<!-- Auto-refreshing news -->
<div hx-get="/htmx/tech-news/"
     hx-trigger="every 120s"
     hx-swap="outerHTML">
</div>

<!-- Lazy load dashboard stats on page load -->
<div hx-get="/htmx/stats-summary/"
     hx-trigger="load"
     hx-swap="innerHTML">
  <div class="spinner">Loading...</div>
</div>
```
