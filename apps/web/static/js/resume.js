// TrueHire Resume JS

async function uploadResume(file) {
  const userId = getUserId();
  if (!userId || !file) return;

  const statusEl = document.getElementById('upload-status');
  if (statusEl) statusEl.textContent = 'Uploading...';

  // user_id must be a query param — the endpoint declares it as str, not Form()
  const form = new FormData();
  form.append('file', file);

  try {
    const result = await apiPostForm(`/users/resume?user_id=${encodeURIComponent(userId)}`, form);
    renderExtractedSkills(result.extracted_skills || []);
    const analyzedEl = document.getElementById('analyzed-status');
    if (analyzedEl) {
      analyzedEl.textContent = 'ANALYZED';
      analyzedEl.style.color = '#006a6a';
    }
    const count = (result.extracted_skills || []).length;
    if (statusEl) statusEl.textContent = `Extracted ${count} skills via ${result.extraction_method}`;
    showNextStepBanner(count);
  } catch (err) {
    if (statusEl) statusEl.textContent = 'Upload failed: ' + err.message;
  }
}

function showNextStepBanner(skillCount) {
  const existing = document.getElementById('next-step-banner');
  if (existing) existing.remove();
  const main = document.querySelector('.main');
  if (!main) return;
  const banner = document.createElement('div');
  banner.id = 'next-step-banner';
  banner.style.cssText = 'margin-top:1.5rem;background:linear-gradient(135deg,#00425e,#006a6a);border-radius:12px;padding:1.25rem 1.5rem;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:1rem;';
  banner.innerHTML = `
    <div>
      <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.15em;color:#c6e7ff;margin-bottom:0.25rem;">Resume Analysed — ${skillCount} skill${skillCount !== 1 ? 's' : ''} extracted</div>
      <div style="font-family:Manrope,sans-serif;font-size:1rem;font-weight:700;color:#fff;">Next: Take the Cognitive Assessment</div>
      <div style="font-size:0.8125rem;color:rgba(255,255,255,0.75);margin-top:0.2rem;">Complete all 9 ability tests to unlock personalised job matches.</div>
    </div>
    <a href="/assessments.html" style="background:#fff;color:#00425e;padding:0.625rem 1.25rem;border-radius:8px;font-weight:700;font-size:13px;white-space:nowrap;">
      Start Assessment →
    </a>
  `;
  main.appendChild(banner);
}

function renderExtractedSkills(skills) {
  const chipsEl = document.getElementById('skill-chips');
  if (!chipsEl) return;
  if (!skills || skills.length === 0) {
    chipsEl.innerHTML = '<span style="color:#40484e;font-size:0.875rem;">No skills extracted.</span>';
    return;
  }
  chipsEl.innerHTML = skills.map(s => `
    <span style="display:inline-block;background:#eceef1;border-radius:6px;padding:0.25rem 0.65rem;font-size:11px;font-weight:600;color:#40484e;margin-right:0.4rem;margin-bottom:0.4rem;">${s}</span>
  `).join('');
}

function renderResumeExtras(profile) {
  const chipsEl = document.getElementById('skill-chips');
  if (!chipsEl) return;

  const softSkills = profile.resume_soft_skills || [];
  const jobTitles = profile.resume_past_job_titles || [];

  let html = chipsEl.innerHTML;

  if (softSkills.length) {
    html += `
      <div style="margin-top:1rem;">
        <div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.12em;color:#40484e;margin-bottom:0.5rem;">Soft Skills</div>
        <div>${softSkills.map(s => `
          <span style="display:inline-block;background:#eceef1;border-radius:6px;padding:0.25rem 0.65rem;font-size:11px;font-weight:600;color:#40484e;margin-right:0.4rem;margin-bottom:0.4rem;">${s}</span>
        `).join('')}</div>
      </div>
    `;
  }

  if (jobTitles.length) {
    html += `
      <div style="margin-top:1rem;">
        <div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.12em;color:#40484e;margin-bottom:0.4rem;">Past Job Titles</div>
        <ul style="margin:0;padding-left:1rem;color:#40484e;font-size:0.875rem;line-height:1.6;">
          ${jobTitles.map(t => `<li>${t}</li>`).join('')}
        </ul>
      </div>
    `;
  }

  chipsEl.innerHTML = html;
}

function renderSkillBars(abilityPercentiles) {
  const el = document.getElementById('skills-bars');
  if (!el) return;
  if (!abilityPercentiles || Object.keys(abilityPercentiles).length === 0) {
    el.innerHTML = '<p style="color:#40484e;font-size:0.875rem;">No ability scores yet.</p>';
    return;
  }
  el.innerHTML = Object.entries(abilityPercentiles).slice(0,6).map(([ab, pct]) => {
    const label = ab.split('_').map(w => w[0].toUpperCase() + w.slice(1)).join(' ');
    return `
      <div style="margin-bottom:0.6rem;">
        <div style="display:flex;justify-content:space-between;margin-bottom:3px;">
          <span style="font-size:12px;font-weight:500;color:#40484e;">${label}</span>
          <span style="font-size:12px;font-weight:700;color:#191c1e;">${parseFloat(pct).toFixed(0)}</span>
        </div>
        <div style="height:6px;background:#eceef1;border-radius:3px;overflow:hidden;">
          <div style="height:100%;width:${Math.min(pct,100).toFixed(1)}%;background:#00425e;border-radius:3px;"></div>
        </div>
      </div>
    `;
  }).join('');
}

async function loadResumeProfile() {
  const userId = getUserId();
  if (!userId) return;

  try {
    const profile = await apiGet(`/users/profile/${userId}`);
    renderExtractedSkills(profile.resume_skills || []);
    renderResumeExtras(profile);
    renderSkillBars(profile.ability_percentiles || {});
    const analyzedEl = document.getElementById('analyzed-status');
    if (analyzedEl && (profile.resume_skills || []).length > 0) {
      analyzedEl.textContent = 'ANALYZED';
      analyzedEl.style.color = '#006a6a';
    }
  } catch (err) {
    console.warn('Profile load error:', err.message);
  }
}

document.addEventListener('DOMContentLoaded', () => {
  requireAuth();
  populateNavUser();
  loadResumeProfile();

  // Wire up file input
  const zone = document.getElementById('upload-zone');
  const fileInput = document.getElementById('resume-file-input');

  if (zone && fileInput) {
    zone.addEventListener('click', () => fileInput.click());
    zone.addEventListener('dragover', e => { e.preventDefault(); zone.style.borderColor = '#00425e'; });
    zone.addEventListener('dragleave', () => { zone.style.borderColor = ''; });
    zone.addEventListener('drop', e => {
      e.preventDefault();
      zone.style.borderColor = '';
      const file = e.dataTransfer.files[0];
      if (file) uploadResume(file);
    });
    fileInput.addEventListener('change', () => {
      if (fileInput.files[0]) uploadResume(fileInput.files[0]);
    });
  }
});
