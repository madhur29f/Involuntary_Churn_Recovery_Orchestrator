"""
Interactive Real-Time Dashboard for Involuntary Churn Recovery Orchestrator.
Self-contained single-page application served directly by FastAPI.
Zero Node.js dependency required to view and evaluate.
"""

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Razorpay Buildathon · Track 03: Involuntary Churn Recovery Orchestrator</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    body { background-color: #0b0f19; color: #f3f4f6; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    .card { background: #111827; border: 1px solid #1f2937; border-radius: 12px; }
    .glow-blue { box-shadow: 0 0 20px -5px rgba(59, 130, 246, 0.4); }
    .glow-green { box-shadow: 0 0 20px -5px rgba(16, 185, 129, 0.4); }
  </style>
</head>
<body class="min-h-screen p-4 md:p-8">
  <div class="max-w-7xl mx-auto space-y-6">
    <!-- Header -->
    <header class="flex flex-col md:flex-row md:items-center md:justify-between border-b border-gray-800 pb-6 gap-4">
      <div>
        <div class="flex items-center gap-3">
          <span class="px-2.5 py-1 text-xs font-semibold bg-blue-900/60 text-blue-300 rounded-full border border-blue-700">
            RAZORPAY BUILDATHON · TRACK 03
          </span>
          <span class="px-2.5 py-1 text-xs font-semibold bg-indigo-900/60 text-indigo-300 rounded-full border border-indigo-700">
            DURABLE TEMPORAL WORKFLOWS
          </span>
        </div>
        <h1 class="text-3xl font-extrabold tracking-tight mt-2 text-white">
          Involuntary Churn Recovery Orchestrator
        </h1>
        <p class="text-gray-400 text-sm mt-1">
          Decline-aware recovery layer with deterministic rules safety floor, pay-cycle ML timing, and append-only audit trail.
        </p>
      </div>
      <div class="flex items-center gap-3">
        <a href="/docs" target="_blank" class="px-3 py-2 text-xs font-medium text-gray-300 bg-gray-800 hover:bg-gray-700 rounded-lg border border-gray-700 transition">
          Swagger OpenAPI
        </a>
        <a href="http://localhost:8088" target="_blank" class="px-3 py-2 text-xs font-medium text-purple-300 bg-purple-950/60 hover:bg-purple-900/60 rounded-lg border border-purple-700 transition">
          Temporal UI (8088)
        </a>
      </div>
    </header>

    <!-- Controls -->
    <section class="card p-5">
      <div class="flex flex-wrap items-center justify-between gap-4">
        <div class="flex flex-wrap items-center gap-4">
          <div>
            <label class="block text-xs font-medium text-gray-400 mb-1">Deterministic Seed</label>
            <input id="seedInput" type="number" value="42" class="bg-gray-900 border border-gray-700 text-white rounded-lg px-3 py-2 text-sm w-28 focus:outline-none focus:border-blue-500" />
          </div>
          <div>
            <label class="block text-xs font-medium text-gray-400 mb-1">Cohort Size (Subscriptions)</label>
            <input id="sizeInput" type="number" value="60" min="10" max="500" class="bg-gray-900 border border-gray-700 text-white rounded-lg px-3 py-2 text-sm w-28 focus:outline-none focus:border-blue-500" />
          </div>
          <button id="runBtn" onclick="runBenchmark()" class="mt-5 px-5 py-2.5 bg-blue-600 hover:bg-blue-500 text-white text-sm font-semibold rounded-lg shadow transition flex items-center gap-2">
            <span id="btnSpinner" class="hidden animate-spin">⏳</span>
            <span>Run Benchmark Comparison</span>
          </button>
        </div>
        <div id="statusText" class="text-xs text-gray-400 italic">Ready to run benchmark</div>
      </div>
    </section>

    <!-- KPI Summary Grid -->
    <section id="kpiSection" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 hidden">
      <div class="card p-5 border-l-4 border-l-red-500">
        <div class="text-xs text-gray-400 uppercase font-semibold">At-Risk Involuntary Churn</div>
        <div id="atRiskRevenue" class="text-2xl font-black text-white mt-1">₹0</div>
        <div id="cohortLabel" class="text-xs text-gray-500 mt-1">60 failed subscriptions</div>
      </div>
      <div class="card p-5 border-l-4 border-l-gray-500">
        <div class="text-xs text-gray-400 uppercase font-semibold">Naive 2-Day Retry Baseline</div>
        <div id="naiveRate" class="text-2xl font-bold text-gray-300 mt-1">0.0%</div>
        <div id="naiveRevenue" class="text-xs text-gray-400 mt-1">₹0 recovered</div>
      </div>
      <div class="card p-5 border-l-4 border-l-blue-500 glow-blue">
        <div class="text-xs text-blue-400 uppercase font-semibold">Orchestrator Recovery</div>
        <div id="orchRate" class="text-2xl font-bold text-blue-400 mt-1">0.0%</div>
        <div id="orchRevenue" class="text-xs text-blue-300 mt-1">₹0 recovered</div>
      </div>
      <div class="card p-5 border-l-4 border-l-emerald-500 glow-green">
        <div class="text-xs text-emerald-400 uppercase font-semibold">Net Recovery Lift</div>
        <div id="liftRate" class="text-2xl font-black text-emerald-400 mt-1">+0.0%</div>
        <div id="liftRevenue" class="text-xs text-emerald-300 mt-1">+₹0 additional revenue</div>
      </div>
    </section>

    <!-- Detailed Analytics & Visualizations -->
    <section id="analyticsSection" class="grid grid-cols-1 lg:grid-cols-2 gap-6 hidden">
      <!-- Recovery Rate Chart -->
      <div class="card p-5 space-y-3">
        <div class="flex justify-between items-center">
          <h3 class="font-bold text-gray-200 text-sm">Recovery Rate Comparison</h3>
          <span class="text-xs text-gray-500">Target Band: 20-40% vs 55-75%</span>
        </div>
        <div class="h-64">
          <canvas id="rateChart"></canvas>
        </div>
      </div>

      <!-- Retries & Efficiency Metrics -->
      <div class="card p-5 space-y-4">
        <h3 class="font-bold text-gray-200 text-sm">Efficiency & Compliance Impact</h3>
        <div class="grid grid-cols-2 gap-4 mt-2">
          <div class="p-4 bg-gray-900/80 rounded-lg border border-gray-800">
            <span class="text-xs text-gray-400 block">Wasted Retries Prevented</span>
            <span id="wastedPrevented" class="text-2xl font-bold text-emerald-400 mt-1 block">0</span>
            <span class="text-[11px] text-gray-500">Saves merchant processing fees & avoids issuer fraud blocks</span>
          </div>
          <div class="p-4 bg-gray-900/80 rounded-lg border border-gray-800">
            <span class="text-xs text-gray-400 block">Immediate Stopping Rules</span>
            <span id="stoppedCount" class="text-2xl font-bold text-amber-400 mt-1 block">0</span>
            <span class="text-[11px] text-gray-500">Fraud, stolen cards, and opted-out users strictly never retried</span>
          </div>
        </div>
        <div class="p-4 bg-gray-900/50 rounded-lg border border-gray-800 text-xs text-gray-400 space-y-2">
          <div class="flex justify-between">
            <span>Model Scoping:</span>
            <span class="text-gray-200 font-medium">Interpretable pay-cycle & transient middle</span>
          </div>
          <div class="flex justify-between">
            <span>Safety Floor:</span>
            <span class="text-gray-200 font-medium">Deterministic rules override any inference</span>
          </div>
          <div class="flex justify-between">
            <span>Audit Trail:</span>
            <span class="text-gray-200 font-medium">Every action & stop queryable with reason</span>
          </div>
        </div>
      </div>
    </section>

    <!-- Subscriptions Table -->
    <section id="tableSection" class="card p-5 hidden">
      <div class="flex justify-between items-center mb-4">
        <div>
          <h3 class="font-bold text-gray-200 text-base">Subscription Recovery Cohort</h3>
          <p class="text-xs text-gray-400">Click any subscription row to inspect its full chronological audit trail and decision reasons.</p>
        </div>
      </div>
      <div class="overflow-x-auto">
        <table class="w-full text-left text-xs text-gray-300">
          <thead class="bg-gray-900 text-gray-400 uppercase font-semibold border-b border-gray-800">
            <tr>
              <th class="p-3">Subscription</th>
              <th class="p-3">Decline Reason</th>
              <th class="p-3">Category</th>
              <th class="p-3">Plan Amount</th>
              <th class="p-3">Naive State</th>
              <th class="p-3">Orchestrator State</th>
              <th class="p-3 text-right">Audit</th>
            </tr>
          </thead>
          <tbody id="subTableBody" class="divide-y divide-gray-800">
          </tbody>
        </table>
      </div>
    </section>

    <!-- Audit Drawer / Modal -->
    <div id="auditModal" class="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center hidden p-4">
      <div class="bg-gray-900 border border-gray-700 rounded-xl max-w-2xl w-full p-6 space-y-4 max-h-[85vh] flex flex-col">
        <div class="flex justify-between items-center border-b border-gray-800 pb-3">
          <div>
            <h4 class="text-lg font-bold text-white flex items-center gap-2">
              <span>Subscription Audit Trail</span>
              <span id="modalSubId" class="text-xs bg-gray-800 text-blue-400 px-2 py-0.5 rounded font-mono"></span>
            </h4>
            <span class="text-xs text-gray-400">Complete append-only lifecycle reconstruction</span>
          </div>
          <button onclick="closeModal()" class="text-gray-400 hover:text-white text-xl font-bold">&times;</button>
        </div>
        <div id="modalContent" class="overflow-y-auto space-y-3 flex-1 pr-2">
        </div>
        <div class="pt-3 border-t border-gray-800 flex justify-end">
          <button onclick="closeModal()" class="px-4 py-2 bg-gray-800 hover:bg-gray-700 text-white text-xs font-semibold rounded-lg transition">
            Close
          </button>
        </div>
      </div>
    </div>
  </div>

  <script>
    let rateChart = null;

    async function runBenchmark() {
      const seed = parseInt(document.getElementById('seedInput').value) || 42;
      const size = parseInt(document.getElementById('sizeInput').value) || 60;
      const btn = document.getElementById('runBtn');
      const spinner = document.getElementById('btnSpinner');
      const status = document.getElementById('statusText');

      btn.disabled = true;
      spinner.classList.remove('hidden');
      status.innerText = "Seeding deterministic cohort...";

      try {
        // 1. Seed
        const seedRes = await fetch('/simulation/seed', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({seed, population_size: size})
        }).then(r => r.json());

        const batchId = seedRes.batch_id;

        // 2. Run Naive
        status.innerText = "Running Naive policy (blind fixed 2-day retry)...";
        await fetch('/simulation/run', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({batch_id: batchId, policy: 'naive'})
        });

        // 3. Run Orchestrator
        status.innerText = "Running Orchestrator (decline-aware + rules floor + ML timing)...";
        await fetch('/simulation/run', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({batch_id: batchId, policy: 'orchestrator'})
        });

        // 4. Fetch Metrics
        status.innerText = "Computing comparative metrics...";
        const metrics = await fetch(`/batches/${batchId}/metrics`).then(r => r.json());
        
        // 5. Fetch Subscriptions List
        const subsRes = await fetch(`/batches/${batchId}/subscriptions`).then(r => r.json());

        displayResults(metrics, subsRes.subscriptions);
        status.innerText = `Completed benchmark for ${batchId}`;
      } catch (err) {
        console.error(err);
        status.innerText = "Error running benchmark: " + err.message;
      } finally {
        btn.disabled = false;
        spinner.classList.add('hidden');
      }
    }

    function displayResults(metrics, subs) {
      document.getElementById('kpiSection').classList.remove('hidden');
      document.getElementById('analyticsSection').classList.remove('hidden');
      document.getElementById('tableSection').classList.remove('hidden');

      const atRiskInr = metrics.at_risk_revenue_paise / 100;
      const naive = metrics.policies.naive;
      const orch = metrics.policies.orchestrator;
      const liftRate = (orch.recovery_rate - naive.recovery_rate).toFixed(1);
      const liftInr = ((orch.recovered_revenue_paise - naive.recovered_revenue_paise) / 100);
      const wastedPrevented = Math.max(0, naive.false_positive_retries - orch.false_positive_retries);

      document.getElementById('atRiskRevenue').innerText = `₹${atRiskInr.toLocaleString()}`;
      document.getElementById('cohortLabel').innerText = `${metrics.population_size} failed subscriptions`;
      document.getElementById('naiveRate').innerText = `${naive.recovery_rate}%`;
      document.getElementById('naiveRevenue').innerText = `₹${(naive.recovered_revenue_paise / 100).toLocaleString()} recovered (${naive.recovered_count} subs)`;
      document.getElementById('orchRate').innerText = `${orch.recovery_rate}%`;
      document.getElementById('orchRevenue').innerText = `₹${(orch.recovered_revenue_paise / 100).toLocaleString()} recovered (${orch.recovered_count} subs)`;
      document.getElementById('liftRate').innerText = `+${liftRate}%`;
      document.getElementById('liftRevenue').innerText = `+₹${liftInr.toLocaleString()} recovered revenue`;
      document.getElementById('wastedPrevented').innerText = wastedPrevented;

      // Count stops
      const stopped = subs.filter(s => s.orch_state === 'stopped').length;
      document.getElementById('stoppedCount').innerText = stopped;

      renderChart(naive.recovery_rate, orch.recovery_rate);
      renderTable(subs);
    }

    function renderChart(naiveRate, orchRate) {
      const ctx = document.getElementById('rateChart').getContext('2d');
      if (rateChart) rateChart.destroy();
      rateChart = new Chart(ctx, {
        type: 'bar',
        data: {
          labels: ['Naive Fixed Retry', 'Decline-Aware Orchestrator'],
          datasets: [{
            label: 'Recovery Rate (%)',
            data: [naiveRate, orchRate],
            backgroundColor: ['#4b5563', '#3b82f6'],
            borderRadius: 8,
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: {
            y: {
              beginAtZero: true,
              max: 100,
              ticks: { callback: v => v + '%' },
              grid: { color: '#1f2937' }
            },
            x: { grid: { display: false } }
          }
        }
      });
    }

    function renderTable(subs) {
      const tbody = document.getElementById('subTableBody');
      tbody.innerHTML = '';

      subs.forEach(s => {
        const tr = document.createElement('tr');
        tr.className = "hover:bg-gray-800/60 transition cursor-pointer";
        tr.onclick = () => openAudit(s.id);

        const categoryBadge = {
          'hard': 'bg-red-950 text-red-400 border border-red-800',
          'soft': 'bg-emerald-950 text-emerald-400 border border-emerald-800',
          'ambiguous': 'bg-blue-950 text-blue-400 border border-blue-800',
          'business_error': 'bg-amber-950 text-amber-400 border border-amber-800',
        }[s.category] || 'bg-gray-800 text-gray-300';

        const orchBadge = s.orch_state === 'recovered' 
          ? 'text-emerald-400 font-semibold' 
          : (s.orch_state === 'stopped' ? 'text-amber-400' : 'text-gray-400');

        tr.innerHTML = `
          <td class="p-3 font-mono text-gray-200">${s.id}</td>
          <td class="p-3 font-medium">${s.decline_code}</td>
          <td class="p-3"><span class="px-2 py-0.5 rounded text-[10px] ${categoryBadge}">${s.category}</span></td>
          <td class="p-3 text-gray-200 font-mono">₹${(s.plan_amount / 100).toLocaleString()}</td>
          <td class="p-3 text-gray-400">${s.naive_state || 'failed'}</td>
          <td class="p-3 ${orchBadge}">${s.orch_state || 'failed'}</td>
          <td class="p-3 text-right">
            <button class="px-2 py-1 bg-gray-800 hover:bg-gray-700 text-blue-400 rounded text-xs">View Audit</button>
          </td>
        `;
        tbody.appendChild(tr);
      });
    }

    async function openAudit(subId) {
      document.getElementById('modalSubId').innerText = subId;
      const modal = document.getElementById('auditModal');
      const content = document.getElementById('modalContent');
      content.innerHTML = '<div class="text-gray-400 italic">Loading audit trail...</div>';
      modal.classList.remove('hidden');

      try {
        const res = await fetch(`/subscriptions/${subId}/audit`).then(r => r.json());
        content.innerHTML = '';
        res.trail.forEach((item, idx) => {
          const div = document.createElement('div');
          div.className = "p-3 bg-gray-950/80 rounded-lg border border-gray-800 text-xs space-y-1";
          div.innerHTML = `
            <div class="flex justify-between items-center">
              <span class="font-bold text-blue-400 uppercase text-[11px]">${item.event}</span>
              <span class="text-gray-500 font-mono text-[10px]">${item.timestamp}</span>
            </div>
            <p class="text-gray-300">${item.reason}</p>
            <div class="text-[10px] text-gray-500 flex gap-2">
              <span>Actor: <strong class="text-gray-400">${item.actor}</strong></span>
              ${item.decision_id ? `<span>Decision ID: ${item.decision_id}</span>` : ''}
            </div>
          `;
          content.appendChild(div);
        });
      } catch (e) {
        content.innerHTML = '<div class="text-red-400">Failed to load audit trail: ' + e.message + '</div>';
      }
    }

    function closeModal() {
      document.getElementById('auditModal').classList.add('hidden');
    }
  </script>
</body>
</html>
"""
