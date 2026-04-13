// CogniHire Dashboard JS

// Readiness ring: circumference ~552.9 for r=88
function updateReadinessRing(score) {
  const circumference = 552.9;
  const offset = circumference * (1 - score / 100);
  const circle = document.querySelector('#readiness-ring circle.progress-arc');
  if (circle) {
    circle.setAttribute('stroke-dashoffset', offset.toFixed(1));
  }
  const label = document.getElementById('readiness-score');
  if (label) label.textContent = Math.round(score);
}

function renderJobCard(job, index) {
  const scorePct = Math.min(job.total_score * 100, 100).toFixed(0);
  const abilityPct = Math.min(job.ability_score * 100, 100).toFixed(0);
  const activityPct = Math.min(job.activity_score * 100, 100).toFixed(0);
  const skillPct = Math.min(job.skill_score * 100, 100).toFixed(0);
  const acts = (job.strength_activities || []).slice(0, 2).join(', ') || '—';

  return `
    <div style="background:#ffffff;border-radius:12px;padding:1.25rem 1.5rem;border:1px solid #eceef1;box-shadow:0 1px 3px rgba(0,0,0,0.04);">
      <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.12em;color:#00425e;margin-bottom:0.25rem;">#${job.rank} Match</div>
      <div style="font-family:Manrope,sans-serif;font-size:1rem;font-weight:700;color:#191c1e;margin-bottom:0.5rem;line-height:1.2;">${job.job_title}</div>
      <div style="font-family:Manrope,sans-serif;font-size:1.5rem;font-weight:800;color:#00425e;margin-bottom:0.5rem;">${scorePct}%</div>
      <div style="height:6px;background:#eceef1;border-radius:3px;overflow:hidden;margin-bottom:0.75rem;">
        <div style="height:100%;width:${scorePct}%;background:#00425e;border-radius:3px;transition:width 0.4s;"></div>
      </div>
      <div style="display:flex;gap:0.75rem;flex-wrap:wrap;">
        <span style="font-size:11px;color:#40484e;"><strong style="color:#006a6a;">Cog</strong> ${abilityPct}%</span>
        <span style="font-size:11px;color:#40484e;"><strong style="color:#00425e;">Activity</strong> ${activityPct}%</span>
        <span style="font-size:11px;color:#40484e;"><strong style="color:#40484e;">Skills</strong> ${skillPct}%</span>
      </div>
      <p style="font-size:11px;color:#70787e;margin-top:0.5rem;line-height:1.4;">${acts}</p>
    </div>
  `;
}

function renderSkillBars(abilityPercentiles) {
  const container = document.getElementById('skill-bars');
  if (!container) return;
  if (!abilityPercentiles || Object.keys(abilityPercentiles).length === 0) {
    container.innerHTML = '<p style="font-size:0.875rem;color:#40484e;">Complete the cognitive assessment to see ability scores.</p>';
    return;
  }
  const entries = Object.entries(abilityPercentiles).slice(0, 6);
  container.innerHTML = entries.map(([label, pct]) => {
    const short = label.split('_').map(w => w[0].toUpperCase() + w.slice(1)).join(' ').split(' ')[0];
    const pctNum = parseFloat(pct).toFixed(0);
    return `
      <div style="margin-bottom:0.6rem;">
        <div style="display:flex;justify-content:space-between;margin-bottom:3px;">
          <span style="font-size:12px;font-weight:500;color:#40484e;">${short}</span>
          <span style="font-size:12px;font-weight:700;color:#191c1e;">${pctNum}</span>
        </div>
        <div style="height:6px;background:#eceef1;border-radius:3px;overflow:hidden;">
          <div style="height:100%;width:${Math.min(pct,100).toFixed(1)}%;background:#00425e;border-radius:3px;transition:width 0.4s;"></div>
        </div>
      </div>
    `;
  }).join('');
}

async function loadDashboard() {
  const userId = getUserId();
  if (!userId) return;

  // Update hero name and dash user name
  const heroName = document.getElementById('hero-name');
  const dashUserName = document.getElementById('dash-user-name');
  const fullName = getFullName() || userId;
  if (heroName) heroName.textContent = fullName;
  if (dashUserName) dashUserName.textContent = fullName;

  try {
    const profile = await apiGet(`/users/profile/${userId}`);

    const abilityPercentiles = profile.ability_percentiles || {};
    const readiness = profile.readiness_score;

    if (readiness != null) {
      updateReadinessRing(readiness);
    }

    renderSkillBars(abilityPercentiles);

    // Load recommendations
    try {
      const recs = await apiGet(`/recommendations/${userId}`);
      const grid = document.getElementById('job-matches-grid');
      if (grid && recs.length > 0) {
        grid.innerHTML = recs.slice(0, 3).map((job, i) => renderJobCard(job, i)).join('');
      }
    } catch (recErr) {
      console.warn('Recommendations not available:', recErr.message);
      const grid = document.getElementById('job-matches-grid');
      if (grid) grid.innerHTML = '<p style="color:#40484e;font-size:0.875rem;">Complete the cognitive assessment to see job matches.</p>';
    }

    // Activity timeline
    const timeline = document.getElementById('activity-timeline');
    if (timeline) {
      const items = [
        {icon: 'psychology', bg: '#c6e7ff', fg: '#00425e', title: 'Cognitive Assessment', subtitle: profile.assessed_at ? profile.assessed_at.slice(0,10) : '—', badge: 'Completed'},
        {icon: 'description', bg: '#ccfbf1', fg: '#006a6a', title: 'Resume Uploaded', subtitle: `${(profile.resume_skills||[]).length} skills extracted`, badge: 'Done'},
      ];
      timeline.innerHTML = items.map(it => `
        <div style="display:flex;align-items:center;gap:1rem;padding:0.875rem 1rem;background:#ffffff;border-radius:10px;border:1px solid #eceef1;margin-bottom:0.5rem;">
          <div style="width:40px;height:40px;border-radius:10px;background:${it.bg};display:flex;align-items:center;justify-content:center;flex-shrink:0;">
            <span class="material-symbols-outlined" style="font-size:1.25rem;color:${it.fg};">${it.icon}</span>
          </div>
          <div style="flex:1;">
            <div style="font-size:13px;font-weight:600;color:#191c1e;">${it.title}</div>
            <div style="font-size:11px;color:#70787e;">${it.subtitle}</div>
          </div>
          <span style="font-size:11px;font-weight:600;color:#40484e;background:#f2f4f7;padding:0.2rem 0.6rem;border-radius:4px;">${it.badge}</span>
        </div>
      `).join('');
    }

  } catch (err) {
    console.error('Dashboard load error:', err);
  }
}

// Auto-load on page start
document.addEventListener('DOMContentLoaded', () => {
  requireAuth();
  populateNavUser();
  loadDashboard();
});
