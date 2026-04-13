// CogniHire Resume JS

async function uploadResume(file) {
  const userId = getUserId();
  if (!userId || !file) return;

  const statusEl = document.getElementById('upload-status');
  if (statusEl) statusEl.textContent = 'Uploading...';

  const form = new FormData();
  form.append('user_id', userId);
  form.append('file', file);

  try {
    const result = await apiPostForm('/users/resume', form);
    renderExtractedSkills(result.extracted_skills || []);
    const analyzedEl = document.getElementById('analyzed-status');
    if (analyzedEl) {
      analyzedEl.textContent = 'ANALYZED';
      analyzedEl.style.color = '#006a6a';
    }
    if (statusEl) statusEl.textContent = `Extracted ${(result.extracted_skills||[]).length} skills via ${result.extraction_method}`;
  } catch (err) {
    if (statusEl) statusEl.textContent = 'Upload failed: ' + err.message;
  }
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
