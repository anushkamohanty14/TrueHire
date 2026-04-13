import { apiGet, getUserId, requireAuth, populateNavUser } from './api.js';

requireAuth();

const ABILITY_LABELS = {
  deductive_reasoning:    'Deductive Reasoning',
  mathematical_reasoning: 'Mathematical Reasoning',
  memorization:           'Memorization',
  perceptual_speed:       'Perceptual Speed',
  problem_sensitivity:    'Problem Sensitivity',
  selective_attention:    'Selective Attention',
  speed_of_closure:       'Speed of Closure',
  time_sharing:           'Time Sharing',
  written_comprehension:  'Written Comprehension',
};

const ABILITY_KEYS = Object.keys(ABILITY_LABELS);
let radarChart = null;

// ── Main loader ───────────────────────────────────────────────────────────────

async function loadHistory() {
  const userId = getUserId();
  const loadingEl = document.getElementById('loading-state');
  const contentEl = document.getElementById('content');

  try {
    const data = await apiGet(`/api/users/history/${userId}`);
    loadingEl.style.display = 'none';
    contentEl.style.display = 'block';
    renderInsights(data);
    renderAssessment(data.assessment);
    renderResume(data.resume);
    renderReadinessBanner(data.assessment, data.resume);
  } catch (err) {
    loadingEl.textContent = `Error loading history: ${err.message}`;
  }
}

// ── Insight summary cards ─────────────────────────────────────────────────────

function renderInsights(data) {
  const assessment = data.assessment;
  const resume = data.resume;

  // Readiness score
  const readinessEl = document.getElementById('ins-readiness');
  const readinessDateEl = document.getElementById('ins-readiness-date');
  if (assessment) {
    readinessEl.textContent = `${Math.round(assessment.readiness_score)}%`;
    readinessDateEl.textContent = `Assessed ${_fmtDate(assessment.taken_at)}`;
  } else {
    readinessEl.textContent = '—';
    readinessDateEl.textContent = 'No assessment yet';
  }

  // Skills count
  const skillsEl = document.getElementById('ins-skills');
  const skillsDateEl = document.getElementById('ins-skills-date');
  if (resume) {
    skillsEl.textContent = (resume.skills || []).length;
    skillsDateEl.textContent = `Uploaded ${_fmtDate(resume.uploaded_at)}`;
  } else {
    skillsEl.textContent = '—';
    skillsDateEl.textContent = 'No resume uploaded yet';
  }

  // Experience
  const expEl = document.getElementById('ins-exp');
  if (resume && resume.experience_years != null) {
    expEl.textContent = `${resume.experience_years}yr`;
  } else {
    expEl.textContent = '—';
  }
}

// ── Cognitive assessment section ──────────────────────────────────────────────

function renderAssessment(assessment) {
  const dateEl = document.getElementById('assessment-date');
  const emptyEl = document.getElementById('assessment-empty');
  const dataEl = document.getElementById('assessment-data');

  if (!assessment) {
    dateEl.textContent = 'Not taken yet';
    emptyEl.style.display = 'block';
    dataEl.style.display = 'none';
    return;
  }

  dateEl.textContent = `Last taken: ${_fmtDate(assessment.taken_at)}`;
  emptyEl.style.display = 'none';
  dataEl.style.display = 'block';

  // Readiness ring
  const score = Math.round(assessment.readiness_score);
  document.getElementById('ring-score-val').textContent = `${score}%`;
  const arc = document.getElementById('ring-arc');
  const circumference = 251.3;
  arc.style.strokeDashoffset = circumference - (score / 100) * circumference;

  // Strengths / improvement tags
  const percentiles = assessment.ability_percentiles || {};
  const strengthsEl = document.getElementById('strength-tags');
  const improveEl = document.getElementById('improve-tags');
  strengthsEl.innerHTML = '';
  improveEl.innerHTML = '';

  ABILITY_KEYS.forEach(key => {
    const pct = percentiles[key] ?? 0;
    if (pct >= 70) {
      strengthsEl.innerHTML += `<span class="tag tag-strength">${ABILITY_LABELS[key]}</span>`;
    } else if (pct < 40) {
      improveEl.innerHTML += `<span class="tag tag-improve">${ABILITY_LABELS[key]}</span>`;
    }
  });
  if (!strengthsEl.innerHTML) strengthsEl.innerHTML = '<span style="font-size:0.78rem;color:#94a3b8;">None above 70th percentile yet</span>';
  if (!improveEl.innerHTML) improveEl.innerHTML = '<span style="font-size:0.78rem;color:#94a3b8;">All abilities at 40th percentile or above</span>';

  // Radar chart
  renderRadar(percentiles);

  // Ability bars
  const barsEl = document.getElementById('ability-bars');
  barsEl.innerHTML = ABILITY_KEYS.map(key => {
    const val = Math.round(percentiles[key] ?? 0);
    const color = val >= 70 ? '#1a7f5a' : val >= 50 ? '#b45309' : '#b91c1c';
    return `
      <div class="ability-row">
        <div class="ability-name-row">
          <span class="ability-name">${ABILITY_LABELS[key]}</span>
          <span class="ability-pct" style="color:${color};">${val}th</span>
        </div>
        <div class="bar-track">
          <div class="bar-fill" style="width:${val}%;background:${color};"></div>
        </div>
      </div>`;
  }).join('');
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
        label: 'Percentile',
        data: values,
        fill: true,
        backgroundColor: 'rgba(0,66,94,0.12)',
        borderColor: '#00425e',
        pointBackgroundColor: '#00425e',
        pointRadius: 3,
      }],
    },
    options: {
      responsive: true,
      scales: {
        r: {
          min: 0, max: 100,
          ticks: { stepSize: 25, font: { size: 10 } },
          pointLabels: { font: { size: 10, family: 'Inter' } },
        },
      },
      plugins: { legend: { display: false } },
    },
  });
}

// ── Resume section ────────────────────────────────────────────────────────────

function renderResume(resume) {
  const dateEl = document.getElementById('resume-date');
  const emptyEl = document.getElementById('resume-empty');
  const dataEl = document.getElementById('resume-data');

  if (!resume) {
    dateEl.textContent = 'Not uploaded yet';
    emptyEl.style.display = 'block';
    dataEl.style.display = 'none';
    return;
  }

  dateEl.textContent = `Last uploaded: ${_fmtDate(resume.uploaded_at)}` +
    (resume.file_name ? ` · ${resume.file_name}` : '');
  emptyEl.style.display = 'none';
  dataEl.style.display = 'block';

  // Skills chips
  const chipsEl = document.getElementById('skills-chips');
  const skills = resume.skills || [];
  if (skills.length === 0) {
    chipsEl.innerHTML = '<span style="color:#94a3b8;font-size:0.8rem;">No skills extracted</span>';
  } else {
    chipsEl.innerHTML = skills.map(s => `<span class="chip">${s}</span>`).join('');
  }

  // Education
  const eduEl = document.getElementById('edu-list');
  const education = resume.education || [];
  eduEl.innerHTML = education.length
    ? education.map(e => `<div class="info-item">${_esc(e)}</div>`).join('')
    : '<div class="info-item" style="color:#94a3b8;">Not detected</div>';

  // Certifications
  const certEl = document.getElementById('cert-list');
  const certs = resume.certifications || [];
  certEl.innerHTML = certs.length
    ? certs.map(c => `<div class="info-item">${_esc(c)}</div>`).join('')
    : '<div class="info-item" style="color:#94a3b8;">Not detected</div>';

  // Experience years
  const expEl = document.getElementById('exp-val');
  expEl.textContent = resume.experience_years != null
    ? `${resume.experience_years} year${resume.experience_years !== 1 ? 's' : ''} estimated`
    : 'Not detected';
}

// ── Interview readiness banner ────────────────────────────────────────────────

function renderReadinessBanner(assessment, resume) {
  if (assessment && resume) {
    document.getElementById('readiness-section-label').style.display = 'block';
    document.getElementById('readiness-banner').style.display = 'block';
  }
}

// ── Utilities ─────────────────────────────────────────────────────────────────

function _fmtDate(iso) {
  if (!iso) return 'unknown date';
  const d = new Date(iso);
  return d.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
}

function _esc(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

// ── Boot ──────────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  populateNavUser();
  loadHistory();
});
