let sessionId = null;
let currentQuestionId = null;
let selectedMode = 'mixed';
let jobTitle = null;
let totalQuestions = 0;
let currentQuestionNumber = 1;

function show(screenId) {
  ['screen-setup', 'screen-qa', 'screen-summary', 'loading'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.style.display = id === screenId ? '' : 'none';
  });
}

function showLoading(msg) {
  const msgEl = document.getElementById('loading-msg');
  if (msgEl) msgEl.textContent = msg || 'Loading...';
  show('loading');
}

async function loadJobOptions() {
  try {
    const data = await apiGet(`/recommendations/${getUserId()}?limit=5`);
    const select = document.getElementById('job-select');
    if (!select) return;
    select.innerHTML = '<option value="">Select a role...</option>';

    const jobs = (data.recommendations || data).slice(0, 5);
    jobs.forEach(job => {
      const opt = document.createElement('option');
      opt.value = job.job_title;
      opt.textContent = job.job_title;
      select.appendChild(opt);
    });
  } catch {
    const select = document.getElementById('job-select');
    if (select) {
      select.innerHTML =
        '<option value="Software Developers">Software Developers</option><option value="Data Scientists">Data Scientists</option>';
    }
  }
}

function bindModeButtons() {
  document.querySelectorAll('.mode-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      selectedMode = btn.dataset.mode;
    });
  });
}

function showQuestion(q, num, total) {
  if (!q) return;
  show('screen-qa');
  currentQuestionId = q.id;
  currentQuestionNumber = Number(num);
  totalQuestions = Number(total);

  document.getElementById('qa-progress').textContent = `Question ${num} of ${total}`;
  document.getElementById('qa-type-badge').textContent = q.type || 'interview';
  document.getElementById('qa-question').textContent = q.question || '';
  document.getElementById('qa-focus').textContent = q.ability_focus || q.skill_focus || '';
  document.getElementById('qa-answer').value = '';
  document.getElementById('feedback-panel').style.display = 'none';
  document.getElementById('btn-next').style.display = 'none';
  document.getElementById('btn-submit').style.display = '';
}

async function startInterview() {
  const err = document.getElementById('setup-error');
  if (err) err.style.display = 'none';

  const select = document.getElementById('job-select');
  jobTitle = select ? select.value : null;
  if (!jobTitle) return;

  showLoading('Generating interview questions...');
  try {
    const data = await apiPost(`/interview/start?token=${getToken()}`, {
      job_title: jobTitle,
      mode: selectedMode,
    });
    sessionId = data.session_id;
    totalQuestions = data.total_questions || 0;
    showQuestion(data.first_question, 1, totalQuestions);
  } catch (e) {
    show('screen-setup');
    if (err) {
      err.textContent = e.message || 'Failed to start. Try again.';
      err.style.display = '';
    }
  }
}

async function submitAnswer() {
  const answer = document.getElementById('qa-answer').value.trim();
  if (!answer) return;

  const submitBtn = document.getElementById('btn-submit');
  submitBtn.disabled = true;
  submitBtn.textContent = 'Evaluating...';

  try {
    const data = await apiPost(`/interview/respond?token=${getToken()}`, {
      session_id: sessionId,
      question_id: currentQuestionId,
      answer,
    });

    document.getElementById('fb-score').textContent = data.score;
    document.getElementById('fb-feedback').textContent = data.feedback;
    document.getElementById('fb-strength').textContent = data.strength ? 'Strength: ' + data.strength : '';
    document.getElementById('fb-improvement').textContent = data.improvement ? 'Improve: ' + data.improvement : '';

    document.getElementById('feedback-panel').style.display = '';
    document.getElementById('btn-submit').style.display = 'none';

    const nextBtn = document.getElementById('btn-next');
    nextBtn.style.display = '';

    if (data.session_complete) {
      nextBtn.textContent = 'View Summary';
      nextBtn.onclick = loadSummary;
    } else {
      nextBtn.textContent = 'Next Question';
      nextBtn.onclick = () => showQuestion(data.next_question, currentQuestionNumber + 1, totalQuestions);
    }
  } catch (e) {
    alert(e.message || 'Error evaluating answer.');
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = 'Submit Answer';
  }
}

async function loadSummary() {
  showLoading('Generating session summary...');
  try {
    const data = await apiGet(`/interview/summary/${sessionId}`);
    document.getElementById('sum-score').textContent = (data.overall_score || 0).toFixed(1) + ' / 5';
    document.getElementById('sum-job').textContent = jobTitle || '';
    document.getElementById('sum-strengths').innerHTML =
      (data.strengths || []).map(s => `<li>${s}</li>`).join('');
    document.getElementById('sum-improve').innerHTML =
      (data.areas_to_improve || []).map(s => `<li>${s}</li>`).join('');
    document.getElementById('sum-focus').textContent = data.recommended_focus || '';
    show('screen-summary');
  } catch (e) {
    alert('Could not load summary. ' + e.message);
    show('screen-qa');
  }
}

function resetInterview() {
  sessionId = null;
  currentQuestionId = null;
  currentQuestionNumber = 1;
  totalQuestions = 0;
  show('screen-setup');
}

document.addEventListener('DOMContentLoaded', () => {
  requireAuth();
  populateNavUser();
  bindModeButtons();
  loadJobOptions();

  document.getElementById('btn-start').addEventListener('click', startInterview);
  document.getElementById('btn-submit').addEventListener('click', submitAnswer);
  document.getElementById('btn-practice-again').addEventListener('click', resetInterview);
  document.getElementById('btn-back-jobs').addEventListener('click', () => {
    window.location.href = '/jobs.html';
  });
});
