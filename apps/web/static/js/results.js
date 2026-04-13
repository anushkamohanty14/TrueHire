import { apiGet, getUserId, requireAuth } from './api.js';

requireAuth();

const ABILITY_LABELS = {
  deductive_reasoning:   'Deductive Reasoning',
  mathematical_reasoning:'Mathematical Reasoning',
  memorization:          'Memorization',
  perceptual_speed:      'Perceptual Speed',
  problem_sensitivity:   'Problem Sensitivity',
  selective_attention:   'Selective Attention',
  speed_of_closure:      'Speed of Closure',
  time_sharing:          'Time Sharing',
  written_comprehension: 'Written Comprehension',
};

const ABILITY_KEYS = Object.keys(ABILITY_LABELS);

let radarChart = null;

async function loadHistory() {
  const userId = getUserId();
  const container = document.getElementById('history-container');
  const emptyState = document.getElementById('empty-state');
  const summarySection = document.getElementById('summary-section');

  try {
    const data = await apiGet(`/api/cognitive/history/${userId}`);
    const attempts = data.attempts || [];

    if (attempts.length === 0) {
      emptyState.style.display = 'block';
      summarySection.style.display = 'none';
      return;
    }

    emptyState.style.display = 'none';
    summarySection.style.display = 'block';

    // Summary cards
    const latest = attempts[0];
    document.getElementById('latest-score').textContent = `${Math.round(latest.readiness_score)}%`;
    document.getElementById('attempt-count').textContent = attempts.length;

    const improvement = attempts.length > 1
      ? (latest.readiness_score - attempts[attempts.length - 1].readiness_score).toFixed(1)
      : null;
    const improvEl = document.getElementById('improvement-val');
    if (improvement !== null) {
      improvEl.textContent = `${improvement > 0 ? '+' : ''}${improvement}%`;
      improvEl.style.color = improvement >= 0 ? '#1a7f5a' : '#b91c1c';
    } else {
      improvEl.textContent = '—';
    }

    // Radar chart for latest attempt
    renderRadar(latest.ability_percentiles);

    // History list
    container.innerHTML = '';
    attempts.forEach((attempt, idx) => {
      container.appendChild(buildAttemptCard(attempt, idx));
    });

  } catch (err) {
    container.innerHTML = `<p class="error-msg">Failed to load history: ${err.message}</p>`;
  }
}

function renderRadar(percentiles) {
  const labels = ABILITY_KEYS.map(k => ABILITY_LABELS[k]);
  const values = ABILITY_KEYS.map(k => percentiles[k] ?? 0);

  const ctx = document.getElementById('radar-chart').getContext('2d');
  if (radarChart) radarChart.destroy();

  radarChart = new Chart(ctx, {
    type: 'radar',
    data: {
      labels,
      datasets: [{
        label: 'Your Percentile',
        data: values,
        fill: true,
        backgroundColor: 'rgba(0, 66, 94, 0.15)',
        borderColor: '#00425e',
        pointBackgroundColor: '#00425e',
        pointRadius: 4,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      scales: {
        r: {
          min: 0,
          max: 100,
          ticks: { stepSize: 25, font: { size: 11 } },
          pointLabels: { font: { size: 12, family: 'Inter' } },
        },
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: ctx => `${ctx.raw}th percentile`,
          },
        },
      },
    },
  });
}

function buildAttemptCard(attempt, idx) {
  const card = document.createElement('div');
  card.className = 'attempt-card';

  const date = new Date(attempt.taken_at);
  const dateStr = date.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
  const timeStr = date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });

  const score = Math.round(attempt.readiness_score);
  const scoreClass = score >= 70 ? 'score-high' : score >= 50 ? 'score-mid' : 'score-low';

  card.innerHTML = `
    <div class="attempt-header" onclick="toggleAttempt(${idx})">
      <div class="attempt-meta">
        <span class="attempt-label">${idx === 0 ? '<span class="badge-latest">Latest</span> ' : ''}Attempt ${idx + 1}</span>
        <span class="attempt-date">${dateStr} at ${timeStr}</span>
      </div>
      <div class="attempt-right">
        <span class="readiness-score ${scoreClass}">${score}%</span>
        <span class="material-symbols-outlined expand-icon" id="icon-${idx}">expand_more</span>
      </div>
    </div>
    <div class="attempt-body" id="body-${idx}" style="display:none;">
      ${buildAbilityGrid(attempt.ability_percentiles)}
    </div>
  `;
  return card;
}

function buildAbilityGrid(percentiles) {
  return `
    <div class="ability-grid">
      ${ABILITY_KEYS.map(key => {
        const val = Math.round(percentiles[key] ?? 0);
        const pct = val;
        const color = val >= 70 ? '#1a7f5a' : val >= 50 ? '#b45309' : '#b91c1c';
        return `
          <div class="ability-item">
            <div class="ability-name">${ABILITY_LABELS[key]}</div>
            <div class="ability-bar-wrap">
              <div class="ability-bar" style="width:${pct}%;background:${color};"></div>
            </div>
            <div class="ability-pct" style="color:${color};">${val}<sup>th</sup></div>
          </div>`;
      }).join('')}
    </div>`;
}

window.toggleAttempt = function(idx) {
  const body = document.getElementById(`body-${idx}`);
  const icon = document.getElementById(`icon-${idx}`);
  if (body.style.display === 'none') {
    body.style.display = 'block';
    icon.textContent = 'expand_less';
  } else {
    body.style.display = 'none';
    icon.textContent = 'expand_more';
  }
};

loadHistory();
