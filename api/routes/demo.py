"""
GET /demo — interactive demo page for the MomoParse report endpoint.

Single self-contained HTML page. No templates, no static files, no JS frameworks.
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
<title>MomoParse — Monthly Report Demo</title>
<style>
  :root {
    --bg: #0f1117;
    --surface: #1a1d27;
    --border: #2a2d3a;
    --text: #e4e4e7;
    --muted: #8b8d97;
    --accent: #f59e0b;
    --accent-dim: #b45309;
    --green: #22c55e;
    --red: #ef4444;
    --blue: #3b82f6;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.6;
    min-height: 100vh;
  }
  .container { max-width: 800px; margin: 0 auto; padding: 2rem 1.5rem; }
  h1 { font-size: 1.75rem; font-weight: 700; margin-bottom: 0.25rem; }
  h1 span { color: var(--accent); }
  .subtitle { color: var(--muted); margin-bottom: 2rem; font-size: 0.95rem; }
  h2 { font-size: 1.1rem; font-weight: 600; margin-bottom: 0.75rem; color: var(--accent); }
  h3 { font-size: 0.95rem; font-weight: 600; margin-bottom: 0.5rem; }

  /* Input area */
  .input-section { margin-bottom: 2rem; }
  label { display: block; font-weight: 500; margin-bottom: 0.5rem; font-size: 0.9rem; }
  textarea {
    width: 100%;
    height: 220px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    color: var(--text);
    padding: 1rem;
    font-family: 'SF Mono', 'Fira Code', monospace;
    font-size: 0.8rem;
    resize: vertical;
    line-height: 1.5;
  }
  textarea:focus { outline: none; border-color: var(--accent); }
  .hint { color: var(--muted); font-size: 0.8rem; margin-top: 0.5rem; }

  .actions { display: flex; gap: 0.75rem; margin-top: 1rem; align-items: center; }
  button {
    padding: 0.6rem 1.5rem;
    border-radius: 6px;
    font-size: 0.9rem;
    font-weight: 600;
    cursor: pointer;
    border: none;
    transition: opacity 0.15s;
  }
  button:hover { opacity: 0.85; }
  button:disabled { opacity: 0.5; cursor: not-allowed; }
  .btn-primary { background: var(--accent); color: #000; }
  .btn-secondary { background: var(--surface); color: var(--muted); border: 1px solid var(--border); }

  /* Status */
  .status { color: var(--muted); font-size: 0.85rem; }
  .status.error { color: var(--red); }

  /* Report output */
  .report { display: none; margin-top: 2rem; }
  .report.visible { display: block; }

  .card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1.25rem;
    margin-bottom: 1rem;
  }

  /* Health score */
  .score-ring {
    display: flex;
    align-items: center;
    gap: 1.5rem;
    margin-bottom: 0.5rem;
  }
  .score-circle {
    width: 80px; height: 80px;
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 1.75rem; font-weight: 700;
    flex-shrink: 0;
  }
  .score-label { font-size: 0.85rem; color: var(--muted); }

  /* Stats grid */
  .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 0.75rem; }
  .stat { text-align: center; padding: 0.75rem; }
  .stat-value { font-size: 1.3rem; font-weight: 700; }
  .stat-label { font-size: 0.75rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.05em; }
  .positive { color: var(--green); }
  .negative { color: var(--red); }

  /* Month table */
  table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
  th { text-align: left; color: var(--muted); font-weight: 500; padding: 0.5rem 0.75rem;
       border-bottom: 1px solid var(--border); font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; }
  td { padding: 0.6rem 0.75rem; border-bottom: 1px solid var(--border); }

  /* Insight/recommendation cards */
  .item { padding: 0.75rem 0; border-bottom: 1px solid var(--border); }
  .item:last-child { border-bottom: none; }
  .item-title { font-weight: 600; font-size: 0.9rem; margin-bottom: 0.25rem; }
  .item-detail { color: var(--muted); font-size: 0.85rem; }
  .badge {
    display: inline-block; font-size: 0.7rem; font-weight: 600;
    padding: 0.15rem 0.5rem; border-radius: 4px; text-transform: uppercase;
    letter-spacing: 0.03em; margin-right: 0.5rem;
  }
  .badge-high { background: rgba(239,68,68,0.15); color: var(--red); }
  .badge-medium { background: rgba(245,158,11,0.15); color: var(--accent); }
  .badge-info { background: rgba(59,130,246,0.15); color: var(--blue); }

  /* Footer */
  .footer { margin-top: 3rem; padding-top: 1.5rem; border-top: 1px solid var(--border);
            text-align: center; color: var(--muted); font-size: 0.8rem; }
  .footer a { color: var(--accent); text-decoration: none; }
</style>
</head>
<body>
<div class="container">
  <h1>Momo<span>Parse</span></h1>
  <p class="subtitle">Paste your MoMo SMS messages below to generate a financial report.</p>

  <div class="input-section">
    <label for="sms-input">SMS Messages <span style="color:var(--muted); font-weight:400;">(one per line)</span></label>
    <textarea id="sms-input" placeholder="Paste your MoMo SMS messages here, one per line...">{{SAMPLE_SMS}}</textarea>
    <p class="hint">Each line is treated as a separate SMS. The sample data above shows 2 months of typical transactions.</p>
    <div class="actions">
      <select id="telco-select" title="Select your telco (affects how SMS is parsed)" style="padding:0.6rem 0.75rem; border-radius:6px; background:var(--surface); color:var(--text); border:1px solid var(--border); font-size:0.85rem;">
        <option value="auto">Auto-detect telco</option>
        <option value="MobileMoney">MTN MoMo</option>
        <option value="T-CASH" selected>Telecel Cash</option>
      </select>
      <button class="btn-primary" id="btn-generate" onclick="generateReport()">Generate Report</button>
      <button class="btn-secondary" onclick="resetSample()">Reset Sample</button>
      <span class="status" id="status"></span>
    </div>
  </div>

  <div class="report" id="report">
    <!-- Health Score -->
    <div class="card" id="health-card">
      <h2>Financial Health</h2>
      <div class="score-ring">
        <div class="score-circle" id="score-circle">—</div>
        <div>
          <div id="score-verdict" style="font-weight:600;"></div>
          <div class="score-label" id="score-detail"></div>
        </div>
      </div>
    </div>

    <!-- Savings overview -->
    <div class="card">
      <h2>Savings Overview</h2>
      <div class="stats" id="savings-stats"></div>
    </div>

    <!-- Monthly breakdown -->
    <div class="card">
      <h2>Monthly Breakdown</h2>
      <div style="overflow-x:auto;">
        <table id="month-table">
          <thead>
            <tr><th>Month</th><th>Income</th><th>Expenses</th><th>Saved</th><th>Rate</th></tr>
          </thead>
          <tbody></tbody>
        </table>
      </div>
    </div>

    <!-- Insights -->
    <div class="card" id="insights-card">
      <h2>Spending Insights</h2>
      <div id="insights-list"></div>
    </div>

    <!-- Recommendations -->
    <div class="card" id="recs-card">
      <h2>Recommendations</h2>
      <div id="recs-list"></div>
    </div>
  </div>

  <div class="footer">
    Powered by <a href="/docs">MomoParse API</a> &middot; Paste real MoMo SMS to try it with your own data
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
  const telco = document.getElementById('telco-select').value;
  return (telco === 'MobileMoney') ? SAMPLE_MTN : SAMPLE_TELECEL;
}

function resetSample() {
  document.getElementById('sms-input').value = getSample();
  document.getElementById('report').classList.remove('visible');
  document.getElementById('status').textContent = '';
}

document.getElementById('telco-select').addEventListener('change', function() {
  document.getElementById('sms-input').value = getSample();
  document.getElementById('report').classList.remove('visible');
  document.getElementById('status').textContent = '';
});

async function generateReport() {
  const btn = document.getElementById('btn-generate');
  const status = document.getElementById('status');
  const raw = document.getElementById('sms-input').value.trim();

  if (!raw) { status.textContent = 'Please paste at least one SMS.'; status.className = 'status error'; return; }

  const lines = raw.split('\\n').filter(l => l.trim());
  if (lines.length === 0) { status.textContent = 'No valid messages found.'; status.className = 'status error'; return; }

  btn.disabled = true;
  status.textContent = `Analyzing ${lines.length} message${lines.length > 1 ? 's' : ''}...`;
  status.className = 'status';

  try {
    const resp = await fetch('/v1/report', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-API-Key': 'sk-sandbox-momoparse' },
      body: JSON.stringify({ messages: lines.map(l => {
        const telco = document.getElementById('telco-select').value;
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
    status.textContent = `Report generated in ${data.processing_time_ms}ms`;
  } catch (e) {
    status.textContent = e.message;
    status.className = 'status error';
  } finally {
    btn.disabled = false;
  }
}

function ghs(n) { return 'GHS ' + Number(n).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2}); }

function renderReport(data) {
  const report = document.getElementById('report');
  report.classList.add('visible');

  // Health score
  const score = data.financial_health_score || 0;
  const circle = document.getElementById('score-circle');
  circle.textContent = score;
  let color, verdict;
  if (score >= 70) { color = 'var(--green)'; verdict = 'Healthy'; }
  else if (score >= 45) { color = 'var(--accent)'; verdict = 'Fair'; }
  else { color = 'var(--red)'; verdict = 'Needs Attention'; }
  circle.style.border = `4px solid ${color}`;
  circle.style.color = color;
  document.getElementById('score-verdict').textContent = verdict;
  document.getElementById('score-detail').textContent =
    `Based on your savings rate, spending patterns, and income consistency.`;

  // Savings overview
  const sa = data.savings_analysis || {};
  document.getElementById('savings-stats').innerHTML = [
    { label: 'Total Income', value: ghs(sa.total_income || 0), cls: 'positive' },
    { label: 'Total Expenses', value: ghs(sa.total_expenses || 0), cls: 'negative' },
    { label: 'Net Savings', value: ghs(sa.net_savings || 0), cls: (sa.net_savings || 0) >= 0 ? 'positive' : 'negative' },
    { label: 'Savings Rate', value: (sa.savings_rate || 0).toFixed(1) + '%', cls: (sa.savings_rate || 0) >= 10 ? 'positive' : 'negative' },
  ].map(s => `<div class="stat"><div class="stat-value ${s.cls}">${s.value}</div><div class="stat-label">${s.label}</div></div>`).join('');

  // Monthly breakdown
  const tbody = document.querySelector('#month-table tbody');
  tbody.innerHTML = (data.months || []).map(m => `<tr>
    <td>${m.month}</td>
    <td>${ghs(m.income)}</td>
    <td>${ghs(m.expenses)}</td>
    <td class="${m.net_savings >= 0 ? 'positive' : 'negative'}">${ghs(m.net_savings)}</td>
    <td>${m.savings_rate.toFixed(1)}%</td>
  </tr>`).join('');

  // Insights
  const insightsEl = document.getElementById('insights-list');
  const insights = data.insights || [];
  if (insights.length === 0) {
    document.getElementById('insights-card').style.display = 'none';
  } else {
    document.getElementById('insights-card').style.display = '';
    insightsEl.innerHTML = insights.map(i => `<div class="item">
      <div class="item-title">${i.title}</div>
      <div class="item-detail">${i.detail}</div>
    </div>`).join('');
  }

  // Recommendations
  const recsEl = document.getElementById('recs-list');
  const recs = data.recommendations || [];
  if (recs.length === 0) {
    document.getElementById('recs-card').style.display = 'none';
  } else {
    document.getElementById('recs-card').style.display = '';
    recsEl.innerHTML = recs.map(r => {
      const cls = r.priority === 'high' ? 'badge-high' : r.priority === 'medium' ? 'badge-medium' : 'badge-info';
      return `<div class="item">
        <div class="item-title"><span class="badge ${cls}">${r.priority}</span>${r.title}</div>
        <div class="item-detail">${r.detail}</div>
      </div>`;
    }).join('');
  }

  report.scrollIntoView({ behavior: 'smooth' });
}
</script>
</body>
</html>
"""
