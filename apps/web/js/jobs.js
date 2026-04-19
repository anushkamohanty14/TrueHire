// TrueHire Jobs JS

function renderJobCards(recs) {
  const grid = document.getElementById('jobs-grid');
  if (!grid) return;
  if (!recs || recs.length === 0) {
    grid.innerHTML = '<p style="color:#40484e;">No job matches found. Complete the cognitive assessment first.</p>';
    return;
  }

  grid.innerHTML = recs.map(job => {
    const scorePct = Math.min(job.total_score * 100, 100).toFixed(0);
    const abilityPct = Math.min(job.ability_score * 100, 100).toFixed(0);
    const activityPct = Math.min(job.activity_score * 100, 100).toFixed(0);
    const skillPct = Math.min(job.skill_score * 100, 100).toFixed(0);
    const strengths = (job.strength_activities || []).slice(0, 2).join(', ') || '—';
    const gaps = (job.gap_activities || []).slice(0, 1).join(', ') || '—';

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
        <div style="margin-top:0.75rem;">
          <a href="/skills.html?job=${encodeURIComponent(job.job_title)}"
             style="font-size:12px;font-weight:600;color:#00425e;text-decoration:none;">
            View Skill Gap &rarr;
          </a>
        </div>
      </div>
    `;
  }).join('');
}

async function loadJobs() {
  const userId = getUserId();
  if (!userId) return;

  const grid = document.getElementById('jobs-grid');
  if (grid) grid.innerHTML = '<div style="padding:1rem;color:#40484e;">Loading job matches...</div>';

  try {
    const recs = await apiGet(`/recommendations/${userId}`);
    renderJobCards(recs);
  } catch (err) {
    if (grid) grid.innerHTML = `<div style="color:#ba1a1a;padding:1rem;">${err.message}</div>`;
  }
}

document.addEventListener('DOMContentLoaded', () => {
  requireAuth();
  populateNavUser();
  loadJobs();
});
