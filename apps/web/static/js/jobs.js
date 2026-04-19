// TrueHire Jobs JS

// ── Industry picker ───────────────────────────────────────────────────────────

async function loadIndustries() {
  const grid = document.getElementById('industry-grid');
  try {
    const industries = await apiGet('/industries');
    if (!industries || industries.length === 0) {
      grid.innerHTML = '<p style="color:#40484e;">No industries found.</p>';
      return;
    }
    grid.innerHTML = industries.map(ind => `
      <div class="industry-card" onclick="selectIndustry('${ind.id}', '${escHtml(ind.name)}')">
        <span class="material-symbols-outlined" style="font-size:2rem;color:#00425e;">${ind.icon}</span>
        <div style="font-family:Manrope,sans-serif;font-size:0.9375rem;font-weight:700;color:#191c1e;">${ind.name}</div>
        <div style="font-size:11px;color:#40484e;">${ind.count} roles</div>
      </div>
    `).join('');
  } catch (err) {
    grid.innerHTML = `<div style="color:#ba1a1a;">${err.message}</div>`;
  }
}

function showIndustryPicker() {
  document.getElementById('industry-section').style.display = '';
  document.getElementById('jobs-section').style.display = 'none';
  document.getElementById('back-btn').style.display = 'none';
  document.getElementById('page-title').textContent = 'Choose an Industry';
  document.getElementById('page-subtitle').textContent = 'Select an industry to see your top matched roles within it.';
}

// ── Job results ───────────────────────────────────────────────────────────────

function selectIndustry(industryId, industryName) {
  document.getElementById('industry-section').style.display = 'none';
  document.getElementById('jobs-section').style.display = '';
  document.getElementById('back-btn').style.display = 'flex';
  document.getElementById('page-title').textContent = industryName;
  document.getElementById('page-subtitle').textContent = 'Your top matched roles based on your cognitive profile and skills.';
  document.getElementById('jobs-section-label').textContent = `Top Roles in ${industryName}`;
  loadJobs(industryId);
}

function renderAbilityBreakdown(breakdown) {
  if (!breakdown || breakdown.length === 0) return '';
  const rows = breakdown.map(ab => {
    const pct = ab.user_pct.toFixed(0);
    const color = pct >= 70 ? '#006a6a' : pct >= 40 ? '#00425e' : '#b45309';
    return `
      <div style="margin-bottom:0.5rem;">
        <div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:2px;">
          <span style="font-size:10px;color:#40484e;">${ab.ability}</span>
          <span style="font-size:10px;font-weight:700;color:${color};">${pct}%</span>
        </div>
        <div style="height:5px;background:#eceef1;border-radius:3px;overflow:hidden;">
          <div style="height:100%;width:${pct}%;background:${color};border-radius:3px;"></div>
        </div>
      </div>`;
  }).join('');
  return `
    <details style="margin-top:0.75rem;">
      <summary style="font-size:11px;font-weight:600;color:#00425e;cursor:pointer;list-style:none;display:flex;align-items:center;gap:4px;">
        <span style="font-size:10px;">&#9654;</span> Your ability scores
      </summary>
      <div style="margin-top:0.5rem;">${rows}</div>
    </details>`;
}

function renderJobCards(recs) {
  const grid = document.getElementById('jobs-grid');
  if (!grid) return;
  if (!recs || recs.length === 0) {
    grid.innerHTML = `
      <div style="grid-column:1/-1;background:#fff;border-radius:16px;padding:2.5rem;text-align:center;border:1px solid #eceef1;">
        <span class="material-symbols-outlined" style="font-size:3rem;color:#c0c7ce;">work_outline</span>
        <h2 style="font-family:Manrope,sans-serif;font-size:1.25rem;font-weight:700;color:#191c1e;margin:0.75rem 0 0.5rem;">No matches in this industry</h2>
        <p style="font-size:0.9375rem;color:#40484e;">Try another industry or complete your cognitive assessment first.</p>
      </div>`;
    return;
  }

  grid.innerHTML = recs.map(job => {
    const scorePct    = Math.min(job.total_score * 100, 100).toFixed(0);
    const abilityPct  = Math.min(job.ability_score * 100, 100).toFixed(0);
    const activityPct = Math.min(job.activity_score * 100, 100).toFixed(0);
    const skillPct    = Math.min(job.skill_score * 100, 100).toFixed(0);
    const strengths   = (job.strength_activities || []).slice(0, 2).join(', ') || '—';
    const gaps        = (job.gap_activities || []).slice(0, 1).join(', ') || '—';
    const breakdownHtml = renderAbilityBreakdown(job.ability_breakdown);

    return `
      <div style="background:#ffffff;border-radius:16px;padding:1.5rem;border:1px solid #eceef1;box-shadow:0 1px 3px rgba(0,0,0,0.04);">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:0.75rem;">
          <div>
            <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.12em;color:#00425e;margin-bottom:0.2rem;">#${job.rank} Match</div>
            <div style="font-family:Manrope,sans-serif;font-size:1.0625rem;font-weight:700;color:#191c1e;line-height:1.2;">${job.job_title}</div>
          </div>
          <div style="font-family:Manrope,sans-serif;font-size:1.5rem;font-weight:800;color:#00425e;white-space:nowrap;">${scorePct}%</div>
        </div>
        <div style="height:6px;background:#eceef1;border-radius:3px;overflow:hidden;margin-bottom:0.75rem;">
          <div style="height:100%;width:${scorePct}%;background:#00425e;border-radius:3px;transition:width 0.4s;"></div>
        </div>
        <div style="display:flex;gap:0.75rem;flex-wrap:wrap;margin-bottom:0.75rem;">
          <span style="font-size:11px;color:#40484e;"><strong style="color:#006a6a;">Cognitive</strong> ${abilityPct}%</span>
          <span style="font-size:11px;color:#40484e;"><strong style="color:#00425e;">Activity</strong> ${activityPct}%</span>
          <span style="font-size:11px;color:#40484e;"><strong style="color:#40484e;">Skills</strong> ${skillPct}%</span>
        </div>
        <div style="font-size:11px;color:#40484e;margin-bottom:0.25rem;"><span style="font-weight:600;color:#006a6a;">Strengths:</span> ${strengths}</div>
        <div style="font-size:11px;color:#40484e;"><span style="font-weight:600;color:#b45309;">Gaps:</span> ${gaps}</div>
        ${breakdownHtml}
        <div style="margin-top:0.75rem;">
          <a href="/skills.html?job=${encodeURIComponent(job.job_title)}"
             style="font-size:12px;font-weight:600;color:#00425e;text-decoration:none;">
            View Skill Gap &rarr;
          </a>
        </div>
      </div>`;
  }).join('');
}

async function loadJobs(industryId) {
  const userId = getUserId();
  if (!userId) return;

  const grid = document.getElementById('jobs-grid');
  if (grid) grid.innerHTML = '<div style="grid-column:1/-1;padding:2rem;text-align:center;color:#40484e;">Loading matches…</div>';

  try {
    const url = industryId
      ? `/recommendations/${userId}?industry=${encodeURIComponent(industryId)}`
      : `/recommendations/${userId}`;
    const recs = await apiGet(url);
    renderJobCards(recs);
  } catch (err) {
    if (grid) grid.innerHTML = `<div style="grid-column:1/-1;color:#ba1a1a;padding:1rem;">${err.message}</div>`;
  }
}

// ── Utilities ─────────────────────────────────────────────────────────────────

function escHtml(str) {
  return str.replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

// ── Init ──────────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  requireAuth();
  populateNavUser();
  loadIndustries();
});
