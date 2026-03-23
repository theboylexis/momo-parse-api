"""
GET /demo — interactive demo page for the MomoParse report endpoint.

Single self-contained HTML page. No templates, no static files, no JS frameworks.
CDN: Google Fonts (Inter).
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
<title>MomoParse</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    background: #fff;
    color: #111;
    line-height: 1.5;
    -webkit-font-smoothing: antialiased;
  }

  /* ── Header ──────────────────────────── */
  .topbar {
    border-bottom: 1px solid #e5e5e5;
    padding: 0 24px;
    height: 52px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    position: sticky;
    top: 0;
    background: #fff;
    z-index: 50;
  }
  .logo {
    display: flex;
    align-items: center;
    gap: 10px;
    text-decoration: none;
    color: #111;
  }
  .logo-mark {
    display: flex;
    align-items: center;
    gap: 2px;
  }
  .logo-mark span {
    display: block;
    width: 3px;
    border-radius: 1.5px;
    background: #111;
  }
  .logo-mark span:nth-child(1) { height: 8px; }
  .logo-mark span:nth-child(2) { height: 14px; }
  .logo-mark span:nth-child(3) { height: 11px; }
  .logo-mark span:nth-child(4) { height: 17px; }
  .logo-text {
    font-size: 15px;
    font-weight: 600;
    letter-spacing: -0.02em;
  }
  .topbar-nav { display: flex; gap: 20px; align-items: center; }
  .topbar-nav a {
    font-size: 13px;
    color: #666;
    text-decoration: none;
  }
  .topbar-nav a:hover { color: #111; }
  .env-tag {
    font-size: 11px;
    font-weight: 500;
    color: #0D9373;
    background: #E6F5F0;
    padding: 2px 8px;
    border-radius: 4px;
  }

  /* ── Main ─────────────────────────────── */
  .main { max-width: 880px; margin: 0 auto; padding: 48px 24px 80px; }

  .page-title {
    font-size: 28px;
    font-weight: 700;
    letter-spacing: -0.03em;
    margin-bottom: 4px;
  }
  .page-sub {
    color: #666;
    font-size: 15px;
    margin-bottom: 32px;
  }

  /* ── Input ─────────────────────────────── */
  .input-section { margin-bottom: 40px; }
  .input-section label {
    display: block;
    font-size: 13px;
    font-weight: 500;
    margin-bottom: 6px;
    color: #333;
  }
  textarea {
    width: 100%;
    height: 180px;
    border: 1px solid #d4d4d4;
    border-radius: 8px;
    padding: 12px 14px;
    font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
    font-size: 12px;
    line-height: 1.6;
    color: #333;
    background: #fafafa;
    resize: vertical;
  }
  textarea:focus {
    outline: none;
    border-color: #111;
    background: #fff;
  }
  .input-hint {
    font-size: 12px;
    color: #999;
    margin-top: 6px;
  }
  .controls {
    display: flex;
    gap: 8px;
    margin-top: 12px;
    align-items: center;
    flex-wrap: wrap;
  }
  select {
    padding: 7px 12px;
    border: 1px solid #d4d4d4;
    border-radius: 6px;
    font-size: 13px;
    font-family: inherit;
    color: #333;
    background: #fff;
    cursor: pointer;
  }
  select:focus { outline: none; border-color: #111; }

  .btn {
    padding: 7px 16px;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;
    border: none;
    font-family: inherit;
  }
  .btn:disabled { opacity: 0.4; cursor: not-allowed; }
  .btn-primary { background: #111; color: #fff; }
  .btn-primary:hover:not(:disabled) { background: #333; }
  .btn-secondary {
    background: #fff;
    color: #666;
    border: 1px solid #d4d4d4;
  }
  .btn-secondary:hover:not(:disabled) { background: #f5f5f5; color: #333; }

  .status { font-size: 13px; color: #999; margin-left: 4px; }
  .status.error { color: #dc2626; }
  .status.ok { color: #0D9373; }

  /* ── Report ────────────────────────────── */
  .report { display: none; }
  .report.visible { display: block; }

  .report-divider {
    border: none;
    border-top: 1px solid #e5e5e5;
    margin: 0 0 32px;
  }

  .confidence-bar {
    font-size: 13px;
    padding: 10px 14px;
    border-radius: 6px;
    margin-bottom: 24px;
    display: none;
    gap: 6px;
    align-items: flex-start;
    line-height: 1.5;
  }
  .confidence-bar.low { background: #FEF3C7; color: #92400E; display: flex; }
  .confidence-bar.medium { background: #F0F4FF; color: #3B4FAC; display: flex; }
  .confidence-bar.high { background: #E6F5F0; color: #065F46; display: flex; }

  .meta-line {
    font-size: 13px;
    color: #999;
    margin-bottom: 28px;
  }
  .meta-line strong { color: #666; font-weight: 500; }

  /* ── Score + KPIs ──────────────────────── */
  .overview-grid {
    display: grid;
    grid-template-columns: 200px 1fr;
    gap: 24px;
    margin-bottom: 32px;
  }
  @media (max-width: 640px) {
    .overview-grid { grid-template-columns: 1fr; }
  }

  .score-card {
    border: 1px solid #e5e5e5;
    border-radius: 10px;
    padding: 24px;
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
  }
  .score-ring { width: 100px; height: 100px; transform: rotate(-90deg); }
  .score-ring .track { fill: none; stroke: #f0f0f0; stroke-width: 7; }
  .score-ring .fill {
    fill: none;
    stroke-width: 7;
    stroke-linecap: round;
    transition: stroke-dashoffset 0.8s ease-out;
  }
  .score-num {
    font-size: 32px;
    font-weight: 700;
    letter-spacing: -0.03em;
    margin-top: 10px;
    line-height: 1;
  }
  .score-label {
    font-size: 13px;
    font-weight: 500;
    margin-top: 4px;
  }
  .score-sub {
    font-size: 11px;
    color: #999;
    margin-top: 2px;
  }

  .kpi-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
  }
  @media (max-width: 480px) { .kpi-grid { grid-template-columns: 1fr; } }

  .kpi {
    border: 1px solid #e5e5e5;
    border-radius: 10px;
    padding: 16px 18px;
  }
  .kpi-label {
    font-size: 11px;
    font-weight: 500;
    color: #999;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    margin-bottom: 4px;
  }
  .kpi-value {
    font-size: 22px;
    font-weight: 700;
    letter-spacing: -0.02em;
    line-height: 1.2;
  }
  .kpi-note {
    font-size: 11px;
    color: #999;
    margin-top: 2px;
  }
  .green { color: #0D9373; }
  .red { color: #dc2626; }

  /* ── Section titles ────────────────────── */
  .section { margin-bottom: 32px; }
  .section-title {
    font-size: 13px;
    font-weight: 600;
    color: #111;
    margin-bottom: 12px;
    padding-bottom: 8px;
    border-bottom: 1px solid #e5e5e5;
  }

  /* ── Table ──────────────────────────────── */
  table { width: 100%; border-collapse: collapse; }
  thead th {
    text-align: left;
    font-size: 11px;
    font-weight: 500;
    color: #999;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    padding: 0 0 8px;
    border-bottom: 1px solid #e5e5e5;
  }
  tbody td {
    padding: 10px 0;
    font-size: 13px;
    border-bottom: 1px solid #f0f0f0;
  }
  tbody tr:last-child td { border-bottom: none; }
  .savings-bar {
    display: inline-flex;
    align-items: center;
    gap: 6px;
  }
  .bar-track {
    width: 40px; height: 4px;
    background: #f0f0f0;
    border-radius: 2px;
    overflow: hidden;
  }
  .bar-fill { height: 100%; border-radius: 2px; }

  /* ── Category bars ─────────────────────── */
  .cat-row {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 6px 0;
  }
  .cat-name {
    width: 130px;
    font-size: 13px;
    color: #444;
    flex-shrink: 0;
    text-transform: capitalize;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .cat-track {
    flex: 1;
    height: 8px;
    background: #f0f0f0;
    border-radius: 4px;
    overflow: hidden;
  }
  .cat-fill {
    height: 100%;
    border-radius: 4px;
    transition: width 0.5s ease-out;
  }
  .cat-val {
    width: 90px;
    text-align: right;
    font-size: 13px;
    font-weight: 500;
    color: #333;
    flex-shrink: 0;
  }
  .cat-pct {
    width: 36px;
    text-align: right;
    font-size: 12px;
    color: #999;
    flex-shrink: 0;
  }

  /* ── Insight list ──────────────────────── */
  .insight-list { display: grid; gap: 8px; }
  .insight {
    padding: 12px 16px;
    border: 1px solid #e5e5e5;
    border-radius: 8px;
  }
  .insight-title {
    font-size: 13px;
    font-weight: 600;
    color: #111;
    margin-bottom: 2px;
  }
  .insight-detail {
    font-size: 13px;
    color: #666;
    line-height: 1.5;
  }
  .insight-tag {
    display: inline-block;
    font-size: 10px;
    font-weight: 600;
    padding: 1px 6px;
    border-radius: 3px;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    vertical-align: middle;
    margin-right: 6px;
  }
  .tag-high { background: #FEE2E2; color: #991B1B; }
  .tag-medium { background: #FEF3C7; color: #92400E; }
  .tag-info { background: #F0F4FF; color: #3B4FAC; }

  /* ── Footer ────────────────────────────── */
  .footer {
    margin-top: 48px;
    padding-top: 16px;
    border-top: 1px solid #e5e5e5;
    font-size: 12px;
    color: #999;
    text-align: center;
  }
  .footer a { color: #111; text-decoration: none; }
  .footer a:hover { text-decoration: underline; }
</style>
</head>
<body>

<header class="topbar">
  <a href="/" class="logo">
    <div class="logo-mark">
      <span></span><span></span><span></span><span></span>
    </div>
    <div class="logo-text">MomoParse</div>
  </a>
  <nav class="topbar-nav">
    <span class="env-tag">Sandbox</span>
    <a href="/docs">Docs</a>
    <a href="/redoc">Reference</a>
  </nav>
</header>

<div class="main">
  <h1 class="page-title">Financial Report</h1>
  <p class="page-sub">Paste MoMo SMS messages and get a structured financial breakdown.</p>

  <div class="input-section">
    <label for="sms-input">SMS Messages</label>
    <textarea id="sms-input" placeholder="Paste your MoMo SMS messages here, one per line...">{{SAMPLE_SMS}}</textarea>
    <p class="input-hint">Each line is one SMS. Sample above: 2 months of Telecel Cash transactions.</p>
    <div class="controls">
      <select id="telco-select" title="Select your telco">
        <option value="auto">Auto-detect</option>
        <option value="MobileMoney">MTN MoMo</option>
        <option value="T-CASH" selected>Telecel Cash</option>
      </select>
      <button class="btn btn-primary" id="btn-go" onclick="generateReport()">Generate report</button>
      <button class="btn btn-secondary" onclick="resetSample()">Reset</button>
      <span class="status" id="status"></span>
    </div>
  </div>

  <div class="report" id="report">
    <hr class="report-divider">

    <div id="confidence-bar" class="confidence-bar"></div>
    <div class="meta-line" id="meta-line"></div>

    <div class="overview-grid">
      <div class="score-card">
        <svg class="score-ring" viewBox="0 0 100 100">
          <circle class="track" cx="50" cy="50" r="42" />
          <circle class="fill" id="ring" cx="50" cy="50" r="42"
            stroke-dasharray="263.89" stroke-dashoffset="263.89" />
        </svg>
        <div class="score-num" id="score-num">--</div>
        <div class="score-label" id="score-label"></div>
        <div class="score-sub">Health Score</div>
      </div>
      <div class="kpi-grid" id="kpis"></div>
    </div>

    <div class="section" id="months-section">
      <div class="section-title">Monthly Breakdown</div>
      <table id="months-table">
        <thead>
          <tr><th>Month</th><th>Income</th><th>Expenses</th><th>Net</th><th>Rate</th></tr>
        </thead>
        <tbody></tbody>
      </table>
    </div>

    <div class="section" id="cats-section" style="display:none;">
      <div class="section-title">Spending by Category</div>
      <div id="cat-bars"></div>
    </div>

    <div class="section" id="insights-section" style="display:none;">
      <div class="section-title">Insights</div>
      <div class="insight-list" id="insights-list"></div>
    </div>

    <div class="section" id="recs-section" style="display:none;">
      <div class="section-title">Recommendations</div>
      <div class="insight-list" id="recs-list"></div>
    </div>
  </div>

  <div class="footer">
    Built with the <a href="/docs">MomoParse API</a>
  </div>
</div>

<script>
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
  document.getElementById('status').className = 'status';
}

document.getElementById('telco-select').addEventListener('change', () => {
  document.getElementById('sms-input').value = getSample();
  document.getElementById('report').classList.remove('visible');
  document.getElementById('status').textContent = '';
});

async function generateReport() {
  const btn = document.getElementById('btn-go');
  const status = document.getElementById('status');
  const raw = document.getElementById('sms-input').value.trim();

  if (!raw) { status.textContent = 'Paste at least one SMS.'; status.className = 'status error'; return; }

  const lines = raw.split('\\n').filter(l => l.trim());
  if (!lines.length) { status.textContent = 'No messages found.'; status.className = 'status error'; return; }

  btn.disabled = true;
  status.textContent = 'Analyzing ' + lines.length + ' message' + (lines.length > 1 ? 's' : '') + '...';
  status.className = 'status';

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
      throw new Error(err.detail || err.message || 'API returned ' + resp.status);
    }

    const data = await resp.json();
    renderReport(data);
    status.textContent = data.processing_time_ms + 'ms';
    status.className = 'status ok';
  } catch (e) {
    status.textContent = e.message;
    status.className = 'status error';
  } finally {
    btn.disabled = false;
  }
}

function ghs(n) {
  return 'GHS ' + Number(n).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

const COLORS = ['#3B82F6','#0D9373','#F59E0B','#dc2626','#8B5CF6','#0EA5E9','#EC4899','#14B8A6'];

function renderReport(data) {
  const report = document.getElementById('report');

  // ── Confidence ──
  const dc = data.data_confidence || 'medium';
  const bar = document.getElementById('confidence-bar');
  const msgs = {
    low: 'Low confidence \u2014 Limited data. Add more transactions for reliable scores.',
    medium: 'Medium confidence \u2014 Reasonable data. A third month would improve accuracy.',
    high: 'High confidence \u2014 Sufficient data for reliable analysis.',
  };
  bar.className = 'confidence-bar ' + dc;
  bar.textContent = msgs[dc] || msgs.medium;

  // ── Meta ──
  const summary = data.summary || {};
  const months = data.months || [];
  const range = months.map(m => m.month).filter(m => m !== 'undated').join(' \u2013 ');
  document.getElementById('meta-line').innerHTML =
    '<strong>' + (summary.transaction_count || 0) + '</strong> transactions' +
    (range ? ' across <strong>' + months.length + '</strong> months (' + range + ')' : '');

  // ── Health score ──
  const score = data.financial_health_score || 0;
  const ring = document.getElementById('ring');
  const circ = 263.89;
  const offset = circ - (score / 100) * circ;
  const color = score >= 70 ? '#0D9373' : score >= 45 ? '#F59E0B' : '#dc2626';

  ring.style.stroke = color;
  requestAnimationFrame(() => { ring.style.strokeDashoffset = offset; });

  const numEl = document.getElementById('score-num');
  numEl.textContent = score;
  numEl.style.color = color;
  const label = score >= 70 ? 'Healthy' : score >= 45 ? 'Fair' : 'Needs Attention';
  const labelEl = document.getElementById('score-label');
  labelEl.textContent = label;
  labelEl.style.color = color;

  // ── KPIs ──
  const sa = data.savings_analysis || {};
  document.getElementById('kpis').innerHTML = [
    { l: 'Total Income', v: ghs(sa.total_income || 0), c: 'green', n: months.length + ' month' + (months.length !== 1 ? 's' : '') },
    { l: 'Total Expenses', v: ghs(sa.total_expenses || 0), c: 'red', n: (summary.transaction_count || 0) + ' transactions' },
    { l: 'Net Savings', v: ghs(sa.net_savings || 0), c: (sa.net_savings || 0) >= 0 ? 'green' : 'red', n: 'Income minus expenses' },
    { l: 'Savings Rate', v: (sa.savings_rate || 0).toFixed(1) + '%', c: (sa.savings_rate || 0) >= 10 ? 'green' : 'red', n: sa.savings_rate >= 20 ? 'Excellent' : sa.savings_rate >= 10 ? 'Good' : 'Below target' },
  ].map(k => '<div class="kpi">' +
    '<div class="kpi-label">' + k.l + '</div>' +
    '<div class="kpi-value ' + k.c + '">' + k.v + '</div>' +
    '<div class="kpi-note">' + k.n + '</div>' +
  '</div>').join('');

  // ── Monthly table ──
  const tbody = document.querySelector('#months-table tbody');
  tbody.innerHTML = months.map(m => {
    const rate = m.savings_rate || 0;
    const bc = rate >= 20 ? '#0D9373' : rate >= 0 ? '#F59E0B' : '#dc2626';
    const bw = Math.min(Math.abs(rate), 100);
    return '<tr>' +
      '<td style="font-weight:500">' + m.month + '</td>' +
      '<td>' + ghs(m.income) + '</td>' +
      '<td>' + ghs(m.expenses) + '</td>' +
      '<td class="' + (m.net_savings >= 0 ? 'green' : 'red') + '" style="font-weight:500">' + ghs(m.net_savings) + '</td>' +
      '<td><div class="savings-bar"><span>' + rate.toFixed(1) + '%</span>' +
        '<div class="bar-track"><div class="bar-fill" style="width:' + bw + '%;background:' + bc + '"></div></div>' +
      '</div></td>' +
    '</tr>';
  }).join('');

  // ── Categories ──
  const cb = summary.category_breakdown || {};
  const expCats = Object.entries(cb)
    .filter(([c]) => ['supplier_payment','merchant_payment','personal_transfer_sent','airtime_data',
      'utilities','rent','transport','loan_repayment','cash_withdrawal','fee_charge'].includes(c))
    .sort((a, b) => b[1].amount - a[1].amount);

  const catSec = document.getElementById('cats-section');
  if (expCats.length) {
    catSec.style.display = '';
    const max = Math.max(...expCats.map(([, v]) => v.amount));
    document.getElementById('cat-bars').innerHTML = expCats.map(([cat, info], i) => {
      const pct = max > 0 ? (info.amount / max * 100) : 0;
      return '<div class="cat-row">' +
        '<div class="cat-name">' + cat.replace(/_/g, ' ') + '</div>' +
        '<div class="cat-track"><div class="cat-fill" style="width:' + pct + '%;background:' + COLORS[i % COLORS.length] + '"></div></div>' +
        '<div class="cat-val">' + ghs(info.amount) + '</div>' +
        '<div class="cat-pct">' + info.percentage + '%</div>' +
      '</div>';
    }).join('');
  } else {
    catSec.style.display = 'none';
  }

  // ── Insights ──
  const insights = data.insights || [];
  const insSec = document.getElementById('insights-section');
  if (insights.length) {
    insSec.style.display = '';
    document.getElementById('insights-list').innerHTML = insights.map(i =>
      '<div class="insight">' +
        '<div class="insight-title">' + i.title + '</div>' +
        '<div class="insight-detail">' + i.detail + '</div>' +
      '</div>'
    ).join('');
  } else { insSec.style.display = 'none'; }

  // ── Recommendations ──
  const recs = data.recommendations || [];
  const recSec = document.getElementById('recs-section');
  if (recs.length) {
    recSec.style.display = '';
    document.getElementById('recs-list').innerHTML = recs.map(r => {
      const t = r.priority === 'high' ? 'tag-high' : r.priority === 'medium' ? 'tag-medium' : 'tag-info';
      return '<div class="insight">' +
        '<div class="insight-title"><span class="insight-tag ' + t + '">' + r.priority + '</span>' + r.title + '</div>' +
        '<div class="insight-detail">' + r.detail + '</div>' +
      '</div>';
    }).join('');
  } else { recSec.style.display = 'none'; }

  report.classList.add('visible');
  report.scrollIntoView({ behavior: 'smooth', block: 'start' });
}
</script>
</body>
</html>
"""
