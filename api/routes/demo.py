"""
GET /demo — interactive demo page for the MomoParse report endpoint.

Single self-contained HTML page. No templates, no static files, no JS frameworks.
CDN: Google Fonts (Inter) + Lucide Icons.
"""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

_SAMPLE_SMS = [
    # January income
    "0000014293069861 Confirmed. You have received GHS1200.00 from MTN MOBILE MONEY with transaction reference: Transfer From: 233245221771-KWAME ASANTE on 2026-01-05 at 09:00:00. Your Telecel Cash balance is GHS3450.00. Ref: January salary",
    "0000014293069865 Confirmed. You have received GHS500.00 from MTN MOBILE MONEY with transaction reference: Transfer From: 233554339337-AMA MENSAH on 2026-01-18 at 15:30:00. Your Telecel Cash balance is GHS3370.00. Ref: freelance work",
    # January expenses
    "0000014293069862 Confirmed. GHS350.00 paid to 400200 - SHOPRITE GHANA on 2026-01-10 at 14:30:00. Your new Telecel Cash balance is GHS3100.00. You were charged GHS0.00. Your E-levy charge is GHS0.00. Reference: groceries.\nSendi k3k3!",
    "0000014293069863 Confirmed. GHS150.00 sent to 0244123456 - GHANA WATER on MTN MOBILE MONEY on 2026-01-12 at 11:00:00. Your Telecel Cash balance is GHS2950.00. You were charged GHS0.50. Your E-levy charge is GHS0.00.\nReference: water bill.\nSendi k3k3!",
    "0000014293069864 Confirmed. You bought GHS80.00 of airtime for 0200123456 on 2026-01-15 at 10:30:00. Your Telecel Cash balance is GHS2870.00.",
    "0000014293069866 Confirmed. GHS200.00 paid to 400300 - BOLT RIDES on 2026-01-20 at 14:22:00. Your new Telecel Cash balance is GHS3170.00. You were charged GHS0.00. Your E-levy charge is GHS0.00. Reference: transport.\nSendi k3k3!",
    # February income
    "0000014293069870 Confirmed. You have received GHS1200.00 from MTN MOBILE MONEY with transaction reference: Transfer From: 233245221771-KWAME ASANTE on 2026-02-05 at 09:00:00. Your Telecel Cash balance is GHS4370.00. Ref: February salary",
    # February expenses
    "0000014293069871 Confirmed. GHS400.00 paid to 400200 - SHOPRITE GHANA on 2026-02-08 at 13:15:00. Your new Telecel Cash balance is GHS3970.00. You were charged GHS0.00. Your E-levy charge is GHS0.00. Reference: groceries.\nSendi k3k3!",
    "0000014293069872 Confirmed. GHS150.00 sent to 0244123456 - GHANA WATER on MTN MOBILE MONEY on 2026-02-12 at 11:00:00. Your Telecel Cash balance is GHS3820.00. You were charged GHS0.50. Your E-levy charge is GHS0.00.\nReference: water bill.\nSendi k3k3!",
    "0000014293069873 Confirmed. You bought GHS45.00 of airtime for 0200123456 on 2026-02-10 at 09:15:00. Your Telecel Cash balance is GHS3775.00.",
]


@router.get("/demo", response_class=HTMLResponse, include_in_schema=False)
async def demo_page():
    sample_text = "\n".join(_SAMPLE_SMS)
    return _HTML.replace("{{SAMPLE_SMS}}", sample_text)


_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MomoParse — Financial Report Demo</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<script src="https://unpkg.com/lucide@latest/dist/umd/lucide.js"></script>
<style>
  :root {
    --white: #ffffff;
    --gray-50: #f8fafc;
    --gray-100: #f1f5f9;
    --gray-200: #e2e8f0;
    --gray-300: #cbd5e1;
    --gray-400: #94a3b8;
    --gray-500: #64748b;
    --gray-600: #475569;
    --gray-700: #334155;
    --gray-800: #1e293b;
    --gray-900: #0f172a;
    --blue-50: #eff6ff;
    --blue-100: #dbeafe;
    --blue-500: #3b82f6;
    --blue-600: #2563eb;
    --blue-700: #1d4ed8;
    --emerald-50: #ecfdf5;
    --emerald-500: #10b981;
    --emerald-600: #059669;
    --emerald-700: #047857;
    --rose-50: #fff1f2;
    --rose-500: #f43f5e;
    --rose-600: #e11d48;
    --amber-50: #fffbeb;
    --amber-500: #f59e0b;
    --amber-600: #d97706;
    --amber-700: #b45309;
    --violet-50: #f5f3ff;
    --violet-500: #8b5cf6;
    --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
    --shadow: 0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1);
    --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
    --shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1);
    --radius: 12px;
    --radius-sm: 8px;
  }

  * { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: var(--gray-50);
    color: var(--gray-800);
    line-height: 1.6;
    min-height: 100vh;
    -webkit-font-smoothing: antialiased;
  }

  /* ── Header ──────────────────────────────────────── */
  .topbar {
    background: var(--white);
    border-bottom: 1px solid var(--gray-200);
    padding: 0 1.5rem;
    height: 56px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    position: sticky;
    top: 0;
    z-index: 50;
  }
  .logo {
    font-size: 1.125rem;
    font-weight: 700;
    color: var(--gray-900);
    text-decoration: none;
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }
  .logo-mark {
    width: 28px; height: 28px;
    background: var(--blue-600);
    border-radius: 7px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--white);
    font-weight: 700;
    font-size: 0.8rem;
  }
  .logo span { color: var(--blue-600); }
  .topbar-links { display: flex; gap: 1rem; align-items: center; }
  .topbar-links a {
    font-size: 0.8125rem;
    color: var(--gray-500);
    text-decoration: none;
    font-weight: 500;
    transition: color 0.15s;
  }
  .topbar-links a:hover { color: var(--gray-800); }
  .badge-live {
    font-size: 0.6875rem;
    font-weight: 600;
    background: var(--emerald-50);
    color: var(--emerald-700);
    padding: 0.2rem 0.5rem;
    border-radius: 999px;
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
  }
  .badge-live::before {
    content: '';
    width: 6px; height: 6px;
    background: var(--emerald-500);
    border-radius: 50%;
    display: inline-block;
  }

  /* ── Container ───────────────────────────────────── */
  .container { max-width: 960px; margin: 0 auto; padding: 2rem 1.5rem 4rem; }

  /* ── Page header ─────────────────────────────────── */
  .page-header { margin-bottom: 1.5rem; }
  .page-header h1 {
    font-size: 1.5rem;
    font-weight: 700;
    color: var(--gray-900);
    margin-bottom: 0.25rem;
  }
  .page-header p {
    color: var(--gray-500);
    font-size: 0.875rem;
  }

  /* ── Input section ───────────────────────────────── */
  .input-card {
    background: var(--white);
    border-radius: var(--radius);
    box-shadow: var(--shadow);
    padding: 1.5rem;
    margin-bottom: 2rem;
  }
  .input-label {
    display: block;
    font-weight: 600;
    font-size: 0.8125rem;
    color: var(--gray-700);
    margin-bottom: 0.5rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }
  textarea {
    width: 100%;
    height: 200px;
    background: var(--gray-50);
    border: 1px solid var(--gray-200);
    border-radius: var(--radius-sm);
    color: var(--gray-800);
    padding: 0.875rem 1rem;
    font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
    font-size: 0.75rem;
    resize: vertical;
    line-height: 1.6;
    transition: border-color 0.15s, box-shadow 0.15s;
  }
  textarea:focus {
    outline: none;
    border-color: var(--blue-500);
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
  }
  .input-hint {
    color: var(--gray-400);
    font-size: 0.75rem;
    margin-top: 0.5rem;
  }
  .actions-row {
    display: flex;
    gap: 0.75rem;
    margin-top: 1rem;
    align-items: center;
    flex-wrap: wrap;
  }

  select {
    padding: 0.5rem 0.75rem;
    border-radius: var(--radius-sm);
    background: var(--white);
    color: var(--gray-700);
    border: 1px solid var(--gray-200);
    font-size: 0.8125rem;
    font-family: inherit;
    cursor: pointer;
  }

  button {
    padding: 0.5rem 1.25rem;
    border-radius: var(--radius-sm);
    font-size: 0.8125rem;
    font-weight: 600;
    cursor: pointer;
    border: none;
    transition: all 0.15s;
    font-family: inherit;
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
  }
  button:hover { transform: translateY(-1px); box-shadow: var(--shadow-md); }
  button:active { transform: translateY(0); }
  button:disabled { opacity: 0.5; cursor: not-allowed; transform: none; box-shadow: none; }

  .btn-primary {
    background: var(--blue-600);
    color: var(--white);
  }
  .btn-primary:hover { background: var(--blue-700); }
  .btn-ghost {
    background: transparent;
    color: var(--gray-500);
    border: 1px solid var(--gray-200);
  }
  .btn-ghost:hover { background: var(--gray-50); color: var(--gray-700); box-shadow: none; transform: none; }

  .status-text { color: var(--gray-400); font-size: 0.8125rem; }
  .status-text.error { color: var(--rose-500); }
  .status-text.success { color: var(--emerald-600); }

  /* ── Report sections ─────────────────────────────── */
  .report { display: none; }
  .report.visible { display: block; }

  .section { margin-bottom: 1.5rem; }
  .section-header {
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--gray-400);
    margin-bottom: 0.75rem;
    display: flex;
    align-items: center;
    gap: 0.4rem;
  }

  /* ── Data confidence banner ──────────────────────── */
  .confidence-banner {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.75rem 1rem;
    border-radius: var(--radius-sm);
    font-size: 0.8125rem;
    margin-bottom: 1.5rem;
  }
  .confidence-banner.low {
    background: var(--amber-50);
    color: var(--amber-700);
    border: 1px solid #fde68a;
  }
  .confidence-banner.medium {
    background: var(--blue-50);
    color: var(--blue-700);
    border: 1px solid var(--blue-100);
  }
  .confidence-banner.high {
    background: var(--emerald-50);
    color: var(--emerald-700);
    border: 1px solid #a7f3d0;
  }
  .confidence-banner i { flex-shrink: 0; }

  /* ── Summary meta line ───────────────────────────── */
  .report-meta {
    font-size: 0.8125rem;
    color: var(--gray-500);
    margin-bottom: 1.5rem;
    display: flex;
    align-items: center;
    gap: 0.4rem;
  }

  /* ── Health + KPI row ────────────────────────────── */
  .top-grid {
    display: grid;
    grid-template-columns: 240px 1fr;
    gap: 1.5rem;
    margin-bottom: 1.5rem;
  }
  @media (max-width: 700px) {
    .top-grid { grid-template-columns: 1fr; }
  }

  .card {
    background: var(--white);
    border-radius: var(--radius);
    box-shadow: var(--shadow);
    padding: 1.5rem;
    transition: box-shadow 0.15s;
  }
  .card:hover { box-shadow: var(--shadow-md); }

  /* Health score ring */
  .health-card { display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; }
  .score-svg { width: 120px; height: 120px; transform: rotate(-90deg); }
  .score-track { fill: none; stroke: var(--gray-100); stroke-width: 8; }
  .score-fill {
    fill: none;
    stroke-width: 8;
    stroke-linecap: round;
    transition: stroke-dashoffset 1s ease-out, stroke 0.3s;
  }
  .score-text {
    font-size: 1.75rem;
    font-weight: 700;
    margin-top: 0.5rem;
  }
  .score-verdict {
    font-size: 0.8125rem;
    font-weight: 600;
    margin-top: 0.125rem;
  }
  .score-sublabel {
    font-size: 0.6875rem;
    color: var(--gray-400);
    margin-top: 0.25rem;
  }

  /* KPI cards */
  .kpi-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1rem;
  }
  @media (max-width: 480px) {
    .kpi-grid { grid-template-columns: 1fr; }
  }
  .kpi {
    background: var(--white);
    border-radius: var(--radius);
    box-shadow: var(--shadow);
    padding: 1.25rem;
  }
  .kpi-label {
    font-size: 0.6875rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--gray-400);
    margin-bottom: 0.375rem;
    display: flex;
    align-items: center;
    gap: 0.35rem;
  }
  .kpi-value {
    font-size: 1.375rem;
    font-weight: 700;
    line-height: 1.2;
  }
  .kpi-sub {
    font-size: 0.75rem;
    color: var(--gray-400);
    margin-top: 0.25rem;
  }
  .positive { color: var(--emerald-600); }
  .negative { color: var(--rose-500); }

  /* ── Monthly breakdown table ─────────────────────── */
  .table-card { overflow: hidden; padding: 0; }
  .table-card .section-header { padding: 1.25rem 1.5rem 0; margin-bottom: 0.5rem; }
  table { width: 100%; border-collapse: collapse; font-size: 0.8125rem; }
  thead th {
    text-align: left;
    font-size: 0.6875rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--gray-400);
    padding: 0.75rem 1.5rem;
    border-bottom: 1px solid var(--gray-100);
    background: var(--gray-50);
  }
  tbody td {
    padding: 0.75rem 1.5rem;
    border-bottom: 1px solid var(--gray-100);
    color: var(--gray-700);
  }
  tbody tr:last-child td { border-bottom: none; }
  tbody tr:hover { background: var(--gray-50); }
  .rate-bar-cell { display: flex; align-items: center; gap: 0.5rem; }
  .rate-bar-bg {
    width: 48px; height: 6px;
    background: var(--gray-100);
    border-radius: 3px;
    overflow: hidden;
    flex-shrink: 0;
  }
  .rate-bar-fill { height: 100%; border-radius: 3px; transition: width 0.5s ease-out; }

  /* ── Category breakdown ──────────────────────────── */
  .cat-bar-row {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.5rem 0;
  }
  .cat-label {
    width: 140px;
    font-size: 0.8125rem;
    color: var(--gray-600);
    flex-shrink: 0;
    text-transform: capitalize;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .cat-bar-track {
    flex: 1;
    height: 10px;
    background: var(--gray-100);
    border-radius: 5px;
    overflow: hidden;
  }
  .cat-bar-fill {
    height: 100%;
    border-radius: 5px;
    transition: width 0.6s ease-out;
  }
  .cat-amount {
    width: 100px;
    text-align: right;
    font-size: 0.8125rem;
    font-weight: 500;
    color: var(--gray-700);
    flex-shrink: 0;
  }
  .cat-pct {
    width: 40px;
    text-align: right;
    font-size: 0.75rem;
    color: var(--gray-400);
    flex-shrink: 0;
  }

  /* ── Insight / recommendation cards ──────────────── */
  .insight-cards { display: grid; gap: 0.75rem; }
  .insight-item {
    background: var(--white);
    border-radius: var(--radius-sm);
    box-shadow: var(--shadow-sm);
    padding: 1rem 1.25rem;
    border-left: 3px solid var(--gray-200);
    transition: box-shadow 0.15s;
  }
  .insight-item:hover { box-shadow: var(--shadow); }
  .insight-item.priority-high { border-left-color: var(--rose-500); }
  .insight-item.priority-medium { border-left-color: var(--amber-500); }
  .insight-item.priority-info { border-left-color: var(--blue-500); }
  .insight-item.type-top_spending { border-left-color: var(--violet-500); }
  .insight-item.type-spending_trend { border-left-color: var(--blue-500); }
  .insight-item.type-fee_alert { border-left-color: var(--amber-500); }
  .insight-item.type-airtime_alert { border-left-color: var(--rose-500); }
  .insight-title {
    font-size: 0.8125rem;
    font-weight: 600;
    color: var(--gray-800);
    margin-bottom: 0.25rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }
  .insight-detail {
    font-size: 0.8125rem;
    color: var(--gray-500);
    line-height: 1.5;
  }
  .priority-chip {
    font-size: 0.625rem;
    font-weight: 700;
    padding: 0.125rem 0.4rem;
    border-radius: 4px;
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }
  .priority-chip.high { background: var(--rose-50); color: var(--rose-600); }
  .priority-chip.medium { background: var(--amber-50); color: var(--amber-600); }
  .priority-chip.info { background: var(--blue-50); color: var(--blue-600); }

  /* ── Loading skeleton ────────────────────────────── */
  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
  }
  .skeleton {
    background: var(--gray-100);
    border-radius: var(--radius-sm);
    animation: pulse 1.5s infinite;
  }
  .skeleton-row { height: 1rem; margin-bottom: 0.5rem; border-radius: 4px; }
  .skeleton-block { height: 120px; }

  /* ── Fade-in animation ───────────────────────────── */
  @keyframes fadeUp {
    from { opacity: 0; transform: translateY(12px); }
    to { opacity: 1; transform: translateY(0); }
  }
  .fade-in {
    animation: fadeUp 0.4s ease-out forwards;
    opacity: 0;
  }
  .fade-in-delay-1 { animation-delay: 0.1s; }
  .fade-in-delay-2 { animation-delay: 0.2s; }
  .fade-in-delay-3 { animation-delay: 0.3s; }
  .fade-in-delay-4 { animation-delay: 0.4s; }
  .fade-in-delay-5 { animation-delay: 0.5s; }

  /* ── Footer ──────────────────────────────────────── */
  .footer {
    margin-top: 3rem;
    padding-top: 1.5rem;
    border-top: 1px solid var(--gray-200);
    text-align: center;
    color: var(--gray-400);
    font-size: 0.75rem;
  }
  .footer a { color: var(--blue-600); text-decoration: none; }
  .footer a:hover { text-decoration: underline; }
</style>
</head>
<body>

<!-- Top bar -->
<header class="topbar">
  <a href="/" class="logo">
    <div class="logo-mark">M</div>
    Momo<span>Parse</span>
  </a>
  <div class="topbar-links">
    <span class="badge-live">Sandbox</span>
    <a href="/docs">API Docs</a>
    <a href="/redoc">Reference</a>
  </div>
</header>

<div class="container">
  <!-- Page header -->
  <div class="page-header">
    <h1>Financial Report</h1>
    <p>Paste MoMo SMS messages to generate a detailed monthly breakdown, spending insights, and recommendations.</p>
  </div>

  <!-- Input card -->
  <div class="input-card">
    <label class="input-label" for="sms-input">SMS Messages</label>
    <textarea id="sms-input" placeholder="Paste your MoMo SMS messages here, one per line...">{{SAMPLE_SMS}}</textarea>
    <p class="input-hint">Each line is one SMS. The sample above shows 2 months of typical Telecel Cash transactions.</p>
    <div class="actions-row">
      <select id="telco-select" title="Select your telco">
        <option value="auto">Auto-detect telco</option>
        <option value="MobileMoney">MTN MoMo</option>
        <option value="T-CASH" selected>Telecel Cash</option>
      </select>
      <button class="btn-primary" id="btn-generate" onclick="generateReport()">
        <i data-lucide="bar-chart-3" style="width:15px;height:15px;"></i>
        Generate Report
      </button>
      <button class="btn-ghost" onclick="resetSample()">Reset Sample</button>
      <span class="status-text" id="status"></span>
    </div>
  </div>

  <!-- Report output -->
  <div class="report" id="report">

    <!-- Data confidence banner -->
    <div id="confidence-banner" class="confidence-banner" style="display:none;"></div>

    <!-- Report meta -->
    <div class="report-meta" id="report-meta"></div>

    <!-- Health score + KPI grid -->
    <div class="top-grid fade-in">
      <!-- Health score -->
      <div class="card health-card" id="health-card">
        <svg class="score-svg" viewBox="0 0 120 120">
          <circle class="score-track" cx="60" cy="60" r="52" />
          <circle class="score-fill" id="score-ring" cx="60" cy="60" r="52"
            stroke-dasharray="326.73" stroke-dashoffset="326.73" />
        </svg>
        <div class="score-text" id="score-text">--</div>
        <div class="score-verdict" id="score-verdict"></div>
        <div class="score-sublabel">Financial Health Score</div>
      </div>

      <!-- KPIs -->
      <div class="kpi-grid" id="kpi-grid"></div>
    </div>

    <!-- Monthly breakdown -->
    <div class="section fade-in fade-in-delay-1">
      <div class="card table-card">
        <div class="section-header">
          <i data-lucide="calendar" style="width:14px;height:14px;"></i>
          Monthly Breakdown
        </div>
        <div style="overflow-x:auto;">
          <table id="month-table">
            <thead>
              <tr><th>Month</th><th>Income</th><th>Expenses</th><th>Net Saved</th><th>Savings Rate</th></tr>
            </thead>
            <tbody></tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- Category breakdown -->
    <div class="section fade-in fade-in-delay-2" id="category-section" style="display:none;">
      <div class="card">
        <div class="section-header">
          <i data-lucide="pie-chart" style="width:14px;height:14px;"></i>
          Spending Breakdown
        </div>
        <div id="category-bars"></div>
      </div>
    </div>

    <!-- Insights -->
    <div class="section fade-in fade-in-delay-3" id="insights-section" style="display:none;">
      <div class="section-header">
        <i data-lucide="lightbulb" style="width:14px;height:14px;"></i>
        Spending Insights
      </div>
      <div class="insight-cards" id="insights-list"></div>
    </div>

    <!-- Recommendations -->
    <div class="section fade-in fade-in-delay-4" id="recs-section" style="display:none;">
      <div class="section-header">
        <i data-lucide="target" style="width:14px;height:14px;"></i>
        Recommendations
      </div>
      <div class="insight-cards" id="recs-list"></div>
    </div>
  </div>

  <div class="footer">
    Built with the <a href="/docs">MomoParse API</a> &middot; Paste real MoMo SMS to try your own data
  </div>
</div>

<script>
lucide.createIcons();

const SAMPLE_TELECEL = `{{SAMPLE_SMS}}`;
const SAMPLE_MTN = `Payment received for GHS 1,200.00 from KWAME ASANTE Current Balance: GHS 3,450.00 . Available Balance: GHS 3,450.00 . Reference: January salary. Transaction ID: 76712833868. TRANSACTION FEE: 0.00
Payment received for GHS 500.00 from AMA MENSAH Current Balance: GHS 3,370.00 . Available Balance: GHS 3,370.00 . Reference: freelance work. Transaction ID: 76712833869. TRANSACTION FEE: 0.00
Payment made for GHS 350.00 to SHOPRITE GHANA. Current Balance: GHS 3,100.00. Available Balance: GHS 3,100.00. Reference: groceries. Transaction ID: 76664093335. Fee charged: GHS 0.00 TAX charged: GHS 0.00.
Payment made for GHS 150.00 to GHANA WATER COMPANY. Current Balance: GHS 2,950.00. Available Balance: GHS 2,950.00. Reference: water bill. Transaction ID: 76664093336. Fee charged: GHS 0.50 TAX charged: GHS 0.00.
Your payment of GHS 80.00 to MTN AIRTIME has been completed at 2026-01-15 10:30:00. Your new balance: GHS 2,870.00. Fee was GHS 0.00 Tax was GHS -. Reference: -. Financial Transaction Id: 76664093337. External Transaction Id: 76664093337.
Your payment of GHS 200.00 to BOLT RIDES has been completed at 2026-01-20 14:22:00. Reference: transport. Your new balance: GHS 3,170.00. Fee was GHS 0.00 Tax charged: GHS0. Financial Transaction Id: 76664093338. External Transaction Id: -.
Payment received for GHS 1,200.00 from KWAME ASANTE Current Balance: GHS 4,370.00 . Available Balance: GHS 4,370.00 . Reference: February salary. Transaction ID: 76712833870. TRANSACTION FEE: 0.00
Payment made for GHS 400.00 to SHOPRITE GHANA. Current Balance: GHS 3,970.00. Available Balance: GHS 3,970.00. Reference: groceries. Transaction ID: 76664093340. Fee charged: GHS 0.00 TAX charged: GHS 0.00.
Payment made for GHS 150.00 to GHANA WATER COMPANY. Current Balance: GHS 3,820.00. Available Balance: GHS 3,820.00. Reference: water bill. Transaction ID: 76664093341. Fee charged: GHS 0.50 TAX charged: GHS 0.00.
Your payment of GHS 45.00 to MTN AIRTIME has been completed at 2026-02-10 09:15:00. Your new balance: GHS 3,775.00. Fee was GHS 0.00 Tax was GHS -. Reference: -. Financial Transaction Id: 76664093339. External Transaction Id: 76664093339.`;

function getSample() {
  return document.getElementById('telco-select').value === 'MobileMoney' ? SAMPLE_MTN : SAMPLE_TELECEL;
}

function resetSample() {
  document.getElementById('sms-input').value = getSample();
  document.getElementById('report').classList.remove('visible');
  document.getElementById('status').textContent = '';
  document.getElementById('status').className = 'status-text';
}

document.getElementById('telco-select').addEventListener('change', () => {
  document.getElementById('sms-input').value = getSample();
  document.getElementById('report').classList.remove('visible');
  document.getElementById('status').textContent = '';
});

async function generateReport() {
  const btn = document.getElementById('btn-generate');
  const status = document.getElementById('status');
  const raw = document.getElementById('sms-input').value.trim();

  if (!raw) { status.textContent = 'Please paste at least one SMS.'; status.className = 'status-text error'; return; }

  const lines = raw.split('\\n').filter(l => l.trim());
  if (!lines.length) { status.textContent = 'No valid messages found.'; status.className = 'status-text error'; return; }

  btn.disabled = true;
  status.textContent = `Analyzing ${lines.length} message${lines.length > 1 ? 's' : ''}...`;
  status.className = 'status-text';

  try {
    const telco = document.getElementById('telco-select').value;
    const resp = await fetch('/v1/report', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-API-Key': 'sk-sandbox-momoparse' },
      body: JSON.stringify({ messages: lines.map(l => {
        const msg = { sms_text: l };
        if (telco !== 'auto') msg.sender_id = telco;
        return msg;
      }) }),
    });

    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new Error(err.detail || err.message || `API returned ${resp.status}`);
    }

    const data = await resp.json();
    renderReport(data);
    status.textContent = `Generated in ${data.processing_time_ms}ms`;
    status.className = 'status-text success';
  } catch (e) {
    status.textContent = e.message;
    status.className = 'status-text error';
  } finally {
    btn.disabled = false;
  }
}

function ghs(n) {
  return 'GHS ' + Number(n).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

const CAT_COLORS = [
  'var(--blue-500)', 'var(--emerald-500)', 'var(--amber-500)', 'var(--rose-500)',
  'var(--violet-500)', '#0ea5e9', '#6366f1', '#ec4899', '#14b8a6', '#f97316'
];

function renderReport(data) {
  const report = document.getElementById('report');

  // ── Data confidence banner ──
  const dc = data.data_confidence || 'medium';
  const banner = document.getElementById('confidence-banner');
  const dcMessages = {
    low: '<i data-lucide="alert-triangle" style="width:16px;height:16px;"></i> <strong>Low confidence</strong> — Limited transaction data. Scores may not be reliable. Add more SMS for a better analysis.',
    medium: '<i data-lucide="info" style="width:16px;height:16px;"></i> <strong>Medium confidence</strong> — Reasonable data. Add a third month of transactions for higher accuracy.',
    high: '<i data-lucide="shield-check" style="width:16px;height:16px;"></i> <strong>High confidence</strong> — Sufficient data across multiple months for reliable analysis.',
  };
  banner.className = `confidence-banner ${dc}`;
  banner.innerHTML = dcMessages[dc] || dcMessages.medium;
  banner.style.display = 'flex';

  // ── Report meta ──
  const summary = data.summary || {};
  const months = data.months || [];
  const monthRange = months.length
    ? months.map(m => m.month).filter(m => m !== 'undated').join(' \u2013 ')
    : '';
  document.getElementById('report-meta').innerHTML =
    `<i data-lucide="file-text" style="width:14px;height:14px;"></i> ` +
    `Analyzed <strong>${summary.transaction_count || 0}</strong> transactions` +
    (monthRange ? ` across <strong>${months.length}</strong> months (${monthRange})` : '');

  // ── Health score ring ──
  const score = data.financial_health_score || 0;
  const ring = document.getElementById('score-ring');
  const circumference = 326.73;
  const offset = circumference - (score / 100) * circumference;
  let scoreColor;
  if (score >= 70) scoreColor = 'var(--emerald-500)';
  else if (score >= 45) scoreColor = 'var(--amber-500)';
  else scoreColor = 'var(--rose-500)';

  ring.style.stroke = scoreColor;
  // Trigger animation
  requestAnimationFrame(() => {
    ring.style.strokeDashoffset = offset;
  });

  document.getElementById('score-text').textContent = score;
  document.getElementById('score-text').style.color = scoreColor;
  const verdict = score >= 70 ? 'Healthy' : score >= 45 ? 'Fair' : 'Needs Attention';
  const verdictEl = document.getElementById('score-verdict');
  verdictEl.textContent = verdict;
  verdictEl.style.color = scoreColor;

  // ── KPI cards ──
  const sa = data.savings_analysis || {};
  document.getElementById('kpi-grid').innerHTML = [
    { icon: 'trending-up', label: 'Total Income', value: ghs(sa.total_income || 0), cls: 'positive', sub: `${months.length} month${months.length !== 1 ? 's' : ''}` },
    { icon: 'trending-down', label: 'Total Expenses', value: ghs(sa.total_expenses || 0), cls: 'negative', sub: `${summary.transaction_count || 0} transactions` },
    { icon: 'wallet', label: 'Net Savings', value: ghs(sa.net_savings || 0), cls: (sa.net_savings || 0) >= 0 ? 'positive' : 'negative', sub: 'Income minus expenses' },
    { icon: 'percent', label: 'Savings Rate', value: (sa.savings_rate || 0).toFixed(1) + '%', cls: (sa.savings_rate || 0) >= 10 ? 'positive' : 'negative', sub: sa.savings_rate >= 20 ? 'Excellent' : sa.savings_rate >= 10 ? 'Good' : 'Below target' },
  ].map(k => `
    <div class="kpi">
      <div class="kpi-label"><i data-lucide="${k.icon}" style="width:12px;height:12px;"></i> ${k.label}</div>
      <div class="kpi-value ${k.cls}">${k.value}</div>
      <div class="kpi-sub">${k.sub}</div>
    </div>
  `).join('');

  // ── Monthly breakdown table ──
  const tbody = document.querySelector('#month-table tbody');
  tbody.innerHTML = months.map(m => {
    const rate = m.savings_rate || 0;
    const barColor = rate >= 20 ? 'var(--emerald-500)' : rate >= 0 ? 'var(--amber-500)' : 'var(--rose-500)';
    const barWidth = Math.min(Math.abs(rate), 100);
    return `<tr>
      <td style="font-weight:500;">${m.month}</td>
      <td>${ghs(m.income)}</td>
      <td>${ghs(m.expenses)}</td>
      <td class="${m.net_savings >= 0 ? 'positive' : 'negative'}" style="font-weight:500;">${ghs(m.net_savings)}</td>
      <td>
        <div class="rate-bar-cell">
          <span>${rate.toFixed(1)}%</span>
          <div class="rate-bar-bg"><div class="rate-bar-fill" style="width:${barWidth}%;background:${barColor};"></div></div>
        </div>
      </td>
    </tr>`;
  }).join('');

  // ── Category breakdown ──
  const cb = summary.category_breakdown || {};
  const expenseCats = Object.entries(cb)
    .filter(([cat]) => ['supplier_payment','merchant_payment','personal_transfer_sent','airtime_data',
      'utilities','rent','transport','loan_repayment','cash_withdrawal','fee_charge'].includes(cat))
    .sort((a, b) => b[1].amount - a[1].amount);

  const catSection = document.getElementById('category-section');
  if (expenseCats.length > 0) {
    catSection.style.display = '';
    const maxAmt = Math.max(...expenseCats.map(([, v]) => v.amount));
    document.getElementById('category-bars').innerHTML = expenseCats.map(([cat, info], i) => {
      const pct = maxAmt > 0 ? (info.amount / maxAmt * 100) : 0;
      const color = CAT_COLORS[i % CAT_COLORS.length];
      const label = cat.replace(/_/g, ' ');
      return `<div class="cat-bar-row">
        <div class="cat-label">${label}</div>
        <div class="cat-bar-track"><div class="cat-bar-fill" style="width:${pct}%;background:${color};"></div></div>
        <div class="cat-amount">${ghs(info.amount)}</div>
        <div class="cat-pct">${info.percentage}%</div>
      </div>`;
    }).join('');
  } else {
    catSection.style.display = 'none';
  }

  // ── Insights ──
  const insights = data.insights || [];
  const insightsSection = document.getElementById('insights-section');
  if (insights.length) {
    insightsSection.style.display = '';
    document.getElementById('insights-list').innerHTML = insights.map(i =>
      `<div class="insight-item type-${i.type || ''}">
        <div class="insight-title">${i.title}</div>
        <div class="insight-detail">${i.detail}</div>
      </div>`
    ).join('');
  } else {
    insightsSection.style.display = 'none';
  }

  // ── Recommendations ──
  const recs = data.recommendations || [];
  const recsSection = document.getElementById('recs-section');
  if (recs.length) {
    recsSection.style.display = '';
    document.getElementById('recs-list').innerHTML = recs.map(r => {
      const cls = r.priority === 'high' ? 'high' : r.priority === 'medium' ? 'medium' : 'info';
      return `<div class="insight-item priority-${cls}">
        <div class="insight-title">
          <span class="priority-chip ${cls}">${r.priority}</span>
          ${r.title}
        </div>
        <div class="insight-detail">${r.detail}</div>
      </div>`;
    }).join('');
  } else {
    recsSection.style.display = 'none';
  }

  // Re-init Lucide icons for dynamically inserted elements
  lucide.createIcons();

  // Show report with animation
  report.classList.add('visible');
  report.scrollIntoView({ behavior: 'smooth', block: 'start' });
}
</script>
</body>
</html>
"""
