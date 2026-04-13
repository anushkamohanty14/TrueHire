// CogniHire Skills JS

async function loadSkillGaps() {
  const selector = document.getElementById('job-selector');
  const userId = getUserId();
  const targetJob = selector ? selector.value : '';

  if (!userId) return;
  if (!targetJob) { alert('Please select a target job.'); return; }

  try {
    const data = await apiGet(`/skills/gaps/${userId}?target_job=${encodeURIComponent(targetJob)}`);

    // Update readiness display
    const readinessEl = document.getElementById('readiness-score-display');
    if (readinessEl) readinessEl.textContent = `${data.match_percent || 0}%`;

    // Strengths
    const strengthsEl = document.getElementById('strengths-list');
    if (strengthsEl) {
      const items = (data.strength_activities || []);
      strengthsEl.innerHTML = items.length
        ? items.map(a => `<li style="margin-bottom:0.5rem;font-size:0.9375rem;color:#191c1e;">${a}</li>`).join('')
        : '<li style="color:#40484e;">No strength data available.</li>';
    }

    // Gaps
    const gapsEl = document.getElementById('gaps-list');
    if (gapsEl) {
      const items = (data.gap_activities || []);
      gapsEl.innerHTML = items.length
        ? items.map(a => `<li style="margin-bottom:0.5rem;font-size:0.9375rem;color:#191c1e;">${a}</li>`).join('')
        : '<li style="color:#40484e;">No gap data available.</li>';
    }

    // Learning path (tech skill gaps as learning suggestions)
    const pathEl = document.getElementById('learning-path');
    if (pathEl) {
      const gaps = (data.tech_skill_gaps || []);
      if (gaps.length > 0) {
        pathEl.innerHTML = gaps.map((skill, i) => `
          <div style="display:flex;align-items:center;gap:0.75rem;padding:0.75rem;background:#ffffff;border-radius:10px;border:1px solid #eceef1;margin-bottom:0.5rem;">
            <div style="width:28px;height:28px;border-radius:50%;background:#c6e7ff;display:flex;align-items:center;justify-content:center;flex-shrink:0;font-size:11px;font-weight:700;color:#00425e;">${i+1}</div>
            <span style="font-size:0.9375rem;color:#191c1e;">${skill}</span>
            <span style="margin-left:auto;font-size:11px;font-weight:600;color:#40484e;background:#eceef1;padding:0.2rem 0.5rem;border-radius:4px;">Missing</span>
          </div>
        `).join('');
      } else {
        pathEl.innerHTML = '<p style="color:#40484e;">Great job! No major skill gaps identified.</p>';
      }
    }

  } catch (err) {
    console.error('Skill gaps error:', err);
    alert('Error loading skill gaps: ' + err.message);
  }
}

async function populateJobSelector(userId) {
  const selector = document.getElementById('job-selector');
  if (!selector) return;

  try {
    const recs = await apiGet(`/recommendations/${userId}`);
    if (recs && recs.length > 0) {
      selector.innerHTML = recs.slice(0, 10).map(r =>
        `<option value="${r.job_title}">${r.job_title}</option>`
      ).join('');
    }
  } catch (err) {
    console.warn('Could not load job selector:', err.message);
    const selector = document.getElementById('job-selector');
    if (selector) selector.innerHTML = '<option value="">— Complete assessment first —</option>';
  }
}

document.addEventListener('DOMContentLoaded', async () => {
  requireAuth();
  populateNavUser();

  // Pre-fill from URL param ?job=...
  const params = new URLSearchParams(window.location.search);
  const jobParam = params.get('job');

  const userId = getUserId();
  if (userId) {
    await populateJobSelector(userId);
    if (jobParam) {
      const selector = document.getElementById('job-selector');
      if (selector) {
        // Try to select the param value, or prepend it
        let found = false;
        for (const opt of selector.options) {
          if (opt.value === jobParam) { opt.selected = true; found = true; break; }
        }
        if (!found) {
          const opt = document.createElement('option');
          opt.value = jobParam;
          opt.textContent = jobParam;
          opt.selected = true;
          selector.prepend(opt);
        }
        loadSkillGaps();
      }
    }
  }
});
