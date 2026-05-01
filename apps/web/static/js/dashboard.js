// TrueHire Dashboard JS

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

function renderJobCard(job) {
  const scorePct = Math.min(job.total_score * 100, 100).toFixed(0);
  const abilityPct = Math.min(job.ability_score * 100, 100).toFixed(0);
  const activityPct = Math.min(job.activity_score * 100, 100).toFixed(0);
  const skillPct = Math.min(job.skill_score * 100, 100).toFixed(0);
  const acts = (job.strength_activities || []).slice(0, 2).join(', ') || '—';

  return `
    <div style="background:#ffffff;border-radius:12px;padding:1.25rem 1.5rem;border:1px solid #eceef1;box-shadow:0 1px 3px rgba(0,0,0,0.04);display:flex;flex-direction:column;gap:0;">
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
      <a href="/interview.html?job=${encodeURIComponent(job.job_title)}"
         style="margin-top:0.875rem;display:block;text-align:center;background:#00425e;color:#fff;padding:0.5rem;border-radius:7px;font-weight:600;font-size:12px;">
        Practice Interview →
      </a>
    </div>
  `;
}

// ── Workflow progress stepper ─────────────────────────────────────────────────

function renderWorkflowProgress(hasResume, hasAssessment, hasJobs) {
  const el = document.getElementById('workflow-progress');
  if (!el) return;

  const steps = [
    { label: 'Upload Resume',  icon: 'description',       done: hasResume,     href: '/resume.html' },
    { label: 'Assessment',     icon: 'psychology',        done: hasAssessment, href: '/assessments.html' },
    { label: 'Job Matches',    icon: 'work_outline',      done: hasJobs,       href: '/jobs.html' },
    { label: 'Interview Prep', icon: 'record_voice_over', done: false,         href: '/interview.html' },
  ];

  // First incomplete step is the active "next" step
  const nextIdx = steps.findIndex(s => !s.done);

  const stepHtml = steps.map((s, i) => {
    const isDone   = s.done;
    const isNext   = i === nextIdx;
    const isLocked = !isDone && !isNext;

    const bg     = isDone ? '#006a6a' : isNext ? '#00425e' : '#eceef1';
    const fg     = isDone || isNext ? '#fff' : '#c0c7ce';
    const icon   = isDone ? 'check_circle' : s.icon;
    const labelC = isDone ? '#006a6a' : isNext ? '#00425e' : '#c0c7ce';
    const badge  = isDone ? '<span style="font-size:9px;font-weight:700;color:#006a6a;background:#ccfbf1;padding:1px 5px;border-radius:4px;margin-left:4px;">Done</span>'
                          : isNext ? '<span style="font-size:9px;font-weight:700;color:#fff;background:#00425e;padding:1px 5px;border-radius:4px;margin-left:4px;">Next</span>'
                          : '';

    const connector = i < steps.length - 1
      ? `<div style="flex:1;height:2px;background:${isDone ? '#006a6a' : '#eceef1'};margin:0 4px;min-width:16px;"></div>`
      : '';

    return `
      <div style="display:flex;align-items:center;flex:1;min-width:0;">
        <a href="${s.href}" style="display:flex;flex-direction:column;align-items:center;gap:0.35rem;text-decoration:none;min-width:64px;">
          <div style="width:40px;height:40px;border-radius:10px;background:${bg};display:flex;align-items:center;justify-content:center;">
            <span class="material-symbols-outlined" style="font-size:1.25rem;color:${fg};">${icon}</span>
          </div>
          <span style="font-size:11px;font-weight:600;color:${labelC};text-align:center;white-space:nowrap;">${s.label}${badge}</span>
        </a>
        ${connector}
      </div>`;
  }).join('');

  // Next-step CTA
  const next = nextIdx >= 0 ? steps[nextIdx] : null;
  const ctaHtml = next
    ? `<div style="margin-top:1rem;padding-top:1rem;border-top:1px solid #eceef1;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:0.75rem;">
        <div style="font-size:0.875rem;color:#40484e;">
          <strong style="color:#191c1e;">Next:</strong> ${next.label}
        </div>
        <a href="${next.href}" style="background:#00425e;color:#fff;padding:0.5rem 1.1rem;border-radius:8px;font-weight:700;font-size:13px;white-space:nowrap;">
          Continue →
        </a>
       </div>`
    : `<div style="margin-top:1rem;padding-top:1rem;border-top:1px solid #eceef1;font-size:0.875rem;color:#006a6a;font-weight:600;">
        ✓ All steps complete — start a new interview session any time.
       </div>`;

  el.innerHTML = `
    <div style="background:#fff;border-radius:12px;padding:1.25rem 1.5rem;margin-bottom:1.5rem;border:1px solid #eceef1;box-shadow:0 1px 3px rgba(0,0,0,0.04);">
      <div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.15em;color:#40484e;margin-bottom:1rem;">Your Progress</div>
      <div style="display:flex;align-items:flex-start;gap:0;">${stepHtml}</div>
      ${ctaHtml}
    </div>`;
}

// ── Quick-actions cards (state-aware) ─────────────────────────────────────────

function renderQuickActions(hasResume, hasAssessment) {
  const grid = document.getElementById('quick-actions-grid');
  if (!grid) return;

  function card(bg, border, iconColor, icon, title, subtitle, btnBg, btnColor, btnText, href, checkmark) {
    return `
      <div>
        <div style="background:${bg};border-radius:12px;padding:1.5rem;min-height:130px;display:flex;flex-direction:column;justify-content:space-between;border:${border};margin-bottom:0.5rem;position:relative;">
          ${checkmark ? '<span class="material-symbols-outlined" style="position:absolute;top:0.75rem;right:0.75rem;font-size:1.1rem;color:#006a6a;">check_circle</span>' : ''}
          <span class="material-symbols-outlined" style="font-size:1.75rem;color:${iconColor};">${icon}</span>
          <div>
            <div style="font-family:Manrope,sans-serif;font-size:1rem;font-weight:700;color:${bg === '#00425e' ? '#fff' : '#191c1e'};margin-bottom:0.25rem;">${title}</div>
            <div style="font-size:12px;color:${bg === '#00425e' ? 'rgba(255,255,255,0.7)' : '#40484e'};">${subtitle}</div>
          </div>
        </div>
        <a href="${href}" style="display:block;text-align:center;background:${btnBg};color:${btnColor};padding:0.625rem;border-radius:8px;font-weight:600;font-size:13px;">${btnText}</a>
      </div>`;
  }

  let assessmentCard, resumeCard, interviewCard;

  if (!hasResume && !hasAssessment) {
    // Nothing done — highlight Resume first
    resumeCard     = card('#00425e','none','#c6e7ff','description','Analyze Resume','Extract skills automatically','#fff','#00425e','Upload Resume →','/resume.html',false);
    assessmentCard = card('#fff','1px solid #eceef1','#c0c7ce','psychology','Cognitive Assessment','Complete resume first','#eceef1','#c0c7ce','Locked','/resume.html',false);
    interviewCard  = card('#fff','1px solid #eceef1','#c0c7ce','record_voice_over','Practice Interview','Complete steps above first','#eceef1','#c0c7ce','Locked','/interview.html',false);
  } else if (hasResume && !hasAssessment) {
    // Resume done — highlight Assessment
    resumeCard     = card('#f0fdf4','1px solid #bbf7d0','#006a6a','description','Resume Analysed','Skills extracted ✓','#ccfbf1','#006a6a','Update Resume','/resume.html',true);
    assessmentCard = card('#00425e','none','#c6e7ff','psychology','Cognitive Assessment','18 tasks · 10-15 min','#fff','#00425e','Start Assessment →','/assessments.html',false);
    interviewCard  = card('#fff','1px solid #eceef1','#c0c7ce','record_voice_over','Practice Interview','Complete assessment first','#eceef1','#c0c7ce','Locked','/interview.html',false);
  } else {
    // Both done — highlight Interview
    resumeCard     = card('#f0fdf4','1px solid #bbf7d0','#006a6a','description','Resume Analysed','Skills extracted ✓','#ccfbf1','#006a6a','Update Resume','/resume.html',true);
    assessmentCard = card('#f0fdf4','1px solid #bbf7d0','#006a6a','psychology','Assessment Complete','Profile active ✓','#ccfbf1','#006a6a','Retake Assessment','/assessments.html',true);
    interviewCard  = card('#00425e','none','#c6e7ff','record_voice_over','Practice Interview','AI-powered mock sessions','#fff','#00425e','Start Interview →','/interview.html',false);
  }

  grid.innerHTML = assessmentCard + resumeCard + interviewCard;
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
    const resumeSkills       = profile.resume_skills || [];
    const readiness          = profile.readiness_score;

    const hasResume     = resumeSkills.length > 0;
    const hasAssessment = Object.keys(abilityPercentiles).length > 0;

    if (readiness != null) updateReadinessRing(readiness);

    renderSkillBars(abilityPercentiles);
    renderQuickActions(hasResume, hasAssessment);

    // Load recommendations
    let hasJobs = false;
    try {
      const recs = await apiGet(`/recommendations/${userId}`);
      const grid = document.getElementById('job-matches-grid');
      if (grid && recs.length > 0) {
        hasJobs = true;
        grid.innerHTML = recs.slice(0, 3).map(job => renderJobCard(job)).join('');
      } else if (grid) {
        grid.innerHTML = `
          <div class="card" style="grid-column:1/-1;text-align:center;padding:2rem;">
            <span class="material-symbols-outlined" style="font-size:2.5rem;color:#c0c7ce;">work_outline</span>
            <p style="font-size:0.9375rem;color:#40484e;margin-top:0.5rem;">Complete the Cognitive Assessment to see job matches.</p>
            <a href="/assessments.html" style="display:inline-block;margin-top:1rem;background:#00425e;color:#fff;padding:0.5rem 1.1rem;border-radius:8px;font-weight:600;font-size:13px;">Start Assessment →</a>
          </div>`;
      }
    } catch (recErr) {
      console.warn('Recommendations not available:', recErr.message);
      const grid = document.getElementById('job-matches-grid');
      if (grid) grid.innerHTML = '<p style="color:#40484e;font-size:0.875rem;padding:1rem;">Complete the cognitive assessment to see job matches.</p>';
    }

    // Workflow stepper — rendered after jobs so hasJobs is known
    renderWorkflowProgress(hasResume, hasAssessment, hasJobs);

    // Activity timeline
    const timeline = document.getElementById('activity-timeline');
    if (timeline) {
      const items = [];
      if (hasAssessment) items.push({icon:'psychology', bg:'#c6e7ff', fg:'#00425e', title:'Cognitive Assessment', subtitle: profile.assessed_at ? profile.assessed_at.slice(0,10) : 'Completed', badge:'Done'});
      if (hasResume)     items.push({icon:'description', bg:'#ccfbf1', fg:'#006a6a', title:'Resume Uploaded', subtitle:`${resumeSkills.length} skills extracted`, badge:'Done'});
      if (!items.length) items.push({icon:'flag', bg:'#eceef1', fg:'#40484e', title:'No activity yet', subtitle:'Upload a resume or take the assessment to get started', badge:'—'});

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

    // Bottom "Continue" grid — contextual based on state
    const continueGrid = document.getElementById('continue-grid');
    if (continueGrid) {
      const links = hasAssessment
        ? [
            {href:'/jobs.html',      label:'View Job Matches'},
            {href:'/interview.html', label:'Start Interview Prep'},
            {href:'/skills.html',    label:'Skills & Gaps'},
          ]
        : hasResume
        ? [
            {href:'/assessments.html', label:'Take Assessment'},
            {href:'/resume.html',      label:'Update Resume'},
            {href:'/skills.html',      label:'Skills & Growth'},
          ]
        : [
            {href:'/resume.html',      label:'Upload Resume'},
            {href:'/assessments.html', label:'Take Assessment'},
            {href:'/skills.html',      label:'Skills & Growth'},
          ];
      continueGrid.innerHTML = links.map((l, i) =>
        `<a href="${l.href}" style="display:block;text-align:center;background:${i===0?'#00425e':'#eceef1'};color:${i===0?'#fff':'#191c1e'};padding:0.625rem;border-radius:8px;font-weight:600;font-size:13px;">${l.label}</a>`
      ).join('');
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
