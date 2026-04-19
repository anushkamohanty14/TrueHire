// TrueHire Assessments JS — state machine: idle → loading → testing → complete

let tasks = [];
let taskIndex = 0;
let responses = [];
let taskStartTime = null;

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

const ABILITY_ICONS = {
  deductive_reasoning:    'account_tree',
  mathematical_reasoning: 'calculate',
  memorization:           'memory',
  perceptual_speed:       'speed',
  problem_sensitivity:    'troubleshoot',
  selective_attention:    'center_focus_strong',
  speed_of_closure:       'pattern',
  time_sharing:           'swap_horiz',
  written_comprehension:  'menu_book',
};

function checkAnswer(task, answer) {
  // Handle time_sharing dict answers
  if (typeof task.correct_answer === 'object' && task.correct_answer !== null) {
    if (typeof answer === 'object' && answer !== null) {
      const ca = task.correct_answer;
      try {
        const aOk = parseInt(String(answer.a || '').trim()) === parseInt(String(ca.a));
        const bOk = String(answer.b || '').trim().toLowerCase() === String(ca.b).trim().toLowerCase();
        return aOk && bOk;
      } catch { return false; }
    }
    return false;
  }

  // Digit span: compare digits only — ignore spaces/separators
  if (task.task_type === 'digit_span') {
    const digits = s => String(s).replace(/\D/g, '');
    return digits(task.correct_answer) === digits(answer);
  }

  const correct = String(task.correct_answer).trim().toLowerCase();
  const given = String(answer).trim().toLowerCase();
  return correct === given;
}

function closeModal() {
  const modal = document.getElementById('task-modal');
  if (modal) modal.style.display = 'none';
}

function submitAnswer(answer) {
  const rt = Date.now() - taskStartTime;
  const task = tasks[taskIndex];
  if (!task) return;
  const is_correct = checkAnswer(task, answer);
  responses.push({ability: task.ability, is_correct, reaction_time_ms: rt});
  taskIndex++;

  // Update progress
  const progressEl = document.getElementById('assessment-progress');
  if (progressEl) progressEl.textContent = `${taskIndex} / ${tasks.length}`;

  if (taskIndex < tasks.length) {
    startTask(taskIndex);
  } else {
    closeModal();
    submitAllResponses();
  }
}

function startTask(index) {
  const task = tasks[index];
  if (!task) return;
  taskStartTime = Date.now();

  const modal = document.getElementById('task-modal');
  if (!modal) return;
  modal.style.display = 'flex';

  const abilityEl = document.getElementById('modal-ability');
  if (abilityEl) abilityEl.textContent = ABILITY_LABELS[task.ability] || task.ability;

  const progressEl = document.getElementById('modal-progress');
  if (progressEl) progressEl.textContent = `${index + 1} / ${tasks.length}`;

  const questionEl = document.getElementById('modal-question');
  const optionsEl = document.getElementById('modal-options');
  const inputEl = document.getElementById('modal-input');
  const timerEl = document.getElementById('modal-timer');

  if (timerEl) timerEl.textContent = '';
  if (optionsEl) optionsEl.innerHTML = '';
  if (inputEl) inputEl.style.display = 'none';
  // Reset input to numeric for non-digit-span tasks
  const ansInputReset = document.getElementById('modal-answer-input');
  if (ansInputReset) { ansInputReset.type = 'number'; ansInputReset.placeholder = 'Enter your answer'; }

  const q = task.question;

  // Special handling for different task types
  if (task.task_type === 'stroop') {
    // Show coloured word
    const inkColors = {red:'#dc2626',blue:'#2563eb',green:'#16a34a',yellow:'#ca8a04',orange:'#ea580c',purple:'#9333ea'};
    const color = inkColors[q.ink_color] || '#191c1e';
    if (questionEl) questionEl.innerHTML = `<span style="font-size:2.5rem;font-weight:900;color:${color};">${q.word}</span><br><span style="font-size:1rem;color:#40484e;">${q.prompt}</span>`;
  } else if (task.task_type === 'digit_span') {
    // Phase 1: show sequence with countdown, then hide and ask for recall
    const displaySecs = (task.metadata && task.metadata.display_seconds) || 3;
    const seqStr = (q.sequence || []).join('  ');
    if (inputEl) inputEl.style.display = 'none';
    if (optionsEl) optionsEl.innerHTML = '';
    if (questionEl) questionEl.innerHTML = `
      <span style="font-size:11px;color:#40484e;text-transform:uppercase;letter-spacing:0.15em;">Memorise this sequence</span><br>
      <span id="digit-seq-display" style="font-size:2.5rem;font-weight:800;color:#00425e;letter-spacing:0.4em;">${seqStr}</span><br>
      <span id="digit-countdown" style="font-size:0.875rem;color:#40484e;margin-top:0.5rem;display:inline-block;">Hiding in <strong id="digit-count-num">${displaySecs}</strong>s…</span>
    `;
    taskStartTime = Date.now(); // reset — start timing from when sequence disappears
    let remaining = displaySecs;
    const countEl = () => document.getElementById('digit-count-num');
    const countInterval = setInterval(() => {
      remaining -= 1;
      if (countEl()) countEl().textContent = remaining;
      if (remaining <= 0) {
        clearInterval(countInterval);
        // Hide sequence, show recall input
        const seqEl = document.getElementById('digit-seq-display');
        const cdEl  = document.getElementById('digit-countdown');
        if (seqEl) seqEl.style.visibility = 'hidden';
        if (cdEl)  cdEl.textContent = 'Type the sequence from memory:';
        taskStartTime = Date.now(); // start reaction timer from here
        if (inputEl) {
          inputEl.style.display = 'block';
          const ans = document.getElementById('modal-answer-input');
          if (ans) {
            ans.type = 'text';           // allow spaces between digits
            ans.value = '';
            ans.placeholder = 'Type the digits in order (e.g. 4 7 1 2 9)';
            ans.focus();
          }
        }
      }
    }, 1000);
    return; // skip the generic options/input rendering below
  } else if (task.task_type === 'symbol_search') {
    const gridStr = (q.grid || []).join('  ');
    if (questionEl) questionEl.innerHTML = `<span style="font-size:11px;color:#40484e;">Target: <strong style="color:#00425e;font-size:1.5rem;">${q.target}</strong></span><br><span style="font-size:1.25rem;letter-spacing:0.2em;">${gridStr}</span><br><span style="font-size:0.875rem;color:#40484e;">${q.prompt}</span>`;
  } else if (task.task_type === 'sequence_completion') {
    if (questionEl) questionEl.textContent = (q.text || (q.sequence || []).join(', '));
  } else if (task.task_type === 'rule_violation') {
    if (questionEl) questionEl.innerHTML = `<strong>Rule:</strong> ${q.rule}<br><br>${q.scenario}<br><br><em>${q.prompt}</em>`;
  } else if (task.task_type === 'passage_mcq') {
    if (questionEl) questionEl.innerHTML = `<span style="font-size:0.875rem;color:#40484e;line-height:1.7;">${q.passage}</span><br><br><strong>${q.question}</strong>`;
  } else if (task.task_type === 'dual_task') {
    const ta = q.task_a || {};
    const tb = q.task_b || {};
    if (questionEl) questionEl.innerHTML = `<div style="background:#f2f4f7;border-radius:8px;padding:0.75rem;margin-bottom:0.5rem;"><strong style="font-size:11px;color:#40484e;">${ta.label}</strong><br>${ta.text}</div><div style="background:#f2f4f7;border-radius:8px;padding:0.75rem;"><strong style="font-size:11px;color:#40484e;">${tb.label}</strong><br>${tb.text}</div>`;
  } else {
    if (questionEl) questionEl.textContent = q.text || JSON.stringify(q);
  }

  // Render options or input
  if (task.task_type === 'dual_task') {
    // Dual task: numeric input for task A + MCQ for task B
    const ta = q.task_a || {};
    const tb = q.task_b || {};
    if (optionsEl) {
      optionsEl.innerHTML = `
        <div style="margin-bottom:1rem;">
          <label style="font-size:11px;font-weight:700;text-transform:uppercase;color:#40484e;letter-spacing:0.1em;">Task A answer (number):</label>
          <input id="dual-a-input" type="number" placeholder="Enter number"
                 style="width:100%;margin-top:0.4rem;background:#f2f4f7;border:1px solid #c0c7ce;border-radius:8px;padding:0.625rem 0.875rem;font-size:1rem;font-weight:700;color:#191c1e;outline:none;box-sizing:border-box;"/>
        </div>
        <div>
          <label style="font-size:11px;font-weight:700;text-transform:uppercase;color:#40484e;letter-spacing:0.1em;">Task B answer:</label>
          <div id="dual-b-options" style="margin-top:0.4rem;"></div>
        </div>
        <button onclick="submitDualAnswer()" style="width:100%;margin-top:1rem;background:#00425e;color:#fff;border:none;border-radius:10px;padding:0.75rem;font-weight:700;font-size:0.9375rem;cursor:pointer;">Submit Both Answers</button>
      `;
      const bOpts = document.getElementById('dual-b-options');
      if (bOpts && tb.options) {
        bOpts.innerHTML = tb.options.map(opt => `
          <button onclick="selectDualB(this, '${opt.replace(/'/g,"\\'")}');"
                  style="display:block;width:100%;text-align:left;background:#f2f4f7;border:1px solid #eceef1;border-radius:8px;padding:0.75rem 1rem;margin-bottom:0.5rem;font-size:0.9375rem;color:#191c1e;cursor:pointer;transition:background 0.15s;">
            ${opt}
          </button>
        `).join('');
      }
    }
  } else if (q.options && Array.isArray(q.options)) {
    if (optionsEl) {
      optionsEl.innerHTML = q.options.map(opt => `
        <button onclick="submitAnswer('${String(opt).replace(/'/g,"\\'")}');"
                style="display:block;width:100%;text-align:left;background:#f2f4f7;border:1px solid #eceef1;border-radius:8px;padding:0.75rem 1rem;margin-bottom:0.5rem;font-size:0.9375rem;color:#191c1e;cursor:pointer;transition:background 0.15s;"
                onmouseover="this.style.background='#e6e8eb'" onmouseout="this.style.background='#f2f4f7'">
          ${opt}
        </button>
      `).join('');
    }
  } else {
    // Free input
    if (inputEl) inputEl.style.display = 'block';
    const ansInput = document.getElementById('modal-answer-input');
    if (ansInput) { ansInput.value = ''; ansInput.focus(); }
  }
}

let selectedDualB = null;

function selectDualB(btn, val) {
  selectedDualB = val;
  const parent = document.getElementById('dual-b-options');
  if (parent) {
    parent.querySelectorAll('button').forEach(b => { b.style.background='#f2f4f7'; b.style.borderColor='#eceef1'; });
  }
  btn.style.background = '#c6e7ff';
  btn.style.borderColor = '#00425e';
}

function submitDualAnswer() {
  const aInput = document.getElementById('dual-a-input');
  const aVal = aInput ? aInput.value.trim() : '';
  const bVal = selectedDualB || '';
  selectedDualB = null;
  submitAnswer({a: aVal, b: bVal});
}

async function submitAllResponses() {
  const userId = getUserId();
  if (!userId) {
    showCompletionState(null, 'No user ID found. Please log in again.');
    return;
  }

  const grid = document.getElementById('tasks-grid');
  if (grid) grid.innerHTML = '<div style="text-align:center;padding:2rem;color:#40484e;">Scoring your responses...</div>';

  try {
    const result = await apiPost('/cognitive/assess', {user_id: userId, responses});
    renderResults(result);
  } catch (err) {
    showCompletionState(null, 'Error saving results: ' + err.message);
  }
}

function renderResults(result) {
  const grid = document.getElementById('tasks-grid');
  if (!grid) return;

  const percs = result.ability_percentiles || {};
  const readiness = result.readiness_score || 0;

  const barsHtml = Object.entries(percs).map(([ab, pct]) => {
    const label = ABILITY_LABELS[ab] || ab;
    const p = parseFloat(pct).toFixed(0);
    return `
      <div style="margin-bottom:0.75rem;">
        <div style="display:flex;justify-content:space-between;margin-bottom:4px;">
          <span style="font-size:13px;font-weight:600;color:#191c1e;">${label}</span>
          <span style="font-size:13px;font-weight:700;color:#00425e;">${p}th percentile</span>
        </div>
        <div style="height:8px;background:#eceef1;border-radius:4px;overflow:hidden;">
          <div style="height:100%;width:${Math.min(pct,100).toFixed(1)}%;background:#00425e;border-radius:4px;transition:width 0.6s;"></div>
        </div>
      </div>
    `;
  }).join('');

  grid.innerHTML = `
    <div style="background:#ffffff;border-radius:16px;padding:2rem;border:1px solid #eceef1;text-align:center;margin-bottom:1.5rem;">
      <span class="material-symbols-outlined" style="font-size:3rem;color:#006a6a;">check_circle</span>
      <h2 style="font-family:Manrope,sans-serif;font-size:1.75rem;font-weight:800;color:#191c1e;margin:0.5rem 0;">Assessment Complete!</h2>
      <div style="font-family:Manrope,sans-serif;font-size:3rem;font-weight:800;color:#00425e;">${readiness.toFixed(0)}</div>
      <div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.15em;color:#40484e;">Overall Readiness Score</div>
    </div>
    <div style="background:#ffffff;border-radius:16px;padding:1.5rem;border:1px solid #eceef1;">
      <div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.15em;color:#40484e;margin-bottom:1rem;">Ability Breakdown</div>
      ${barsHtml}
      <div style="margin-top:1rem;display:flex;gap:0.75rem;justify-content:center;flex-wrap:wrap;">
        <a href="/" style="background:#00425e;color:#fff;padding:0.625rem 1.25rem;border-radius:8px;font-weight:600;font-size:13px;text-decoration:none;">View Dashboard</a>
        <a href="/jobs.html" style="background:#eceef1;color:#191c1e;padding:0.625rem 1.25rem;border-radius:8px;font-weight:600;font-size:13px;text-decoration:none;">See Job Matches</a>
      </div>
    </div>
  `;
}

function showCompletionState(result, message) {
  const grid = document.getElementById('tasks-grid');
  if (grid) grid.innerHTML = `<div style="text-align:center;padding:2rem;color:#40484e;">${message || 'Done!'}</div>`;
}

async function loadAndStartAssessment() {
  const userId = getUserId();
  if (!userId) {
    alert('No user ID found. Please log in again.');
    return;
  }

  const grid = document.getElementById('tasks-grid');
  if (grid) grid.innerHTML = '<div style="text-align:center;padding:2rem;color:#40484e;">Loading tasks...</div>';

  try {
    tasks = await apiGet('/cognitive/tasks');
    taskIndex = 0;
    responses = [];
    renderTaskCards();
  } catch (err) {
    if (grid) grid.innerHTML = `<div style="color:#ba1a1a;padding:1rem;">Error loading tasks: ${err.message}</div>`;
  }
}

function renderTaskCards() {
  const grid = document.getElementById('tasks-grid');
  if (!grid) return;

  // Group tasks by ability (first task per ability)
  const byAbility = {};
  tasks.forEach(t => {
    if (!byAbility[t.ability]) byAbility[t.ability] = t;
  });

  const cards = Object.values(byAbility).map((task, i) => {
    const label = ABILITY_LABELS[task.ability] || task.ability;
    const icon = ABILITY_ICONS[task.ability] || 'psychology';
    const isFirst = i === 0;
    return `
      <div style="background:#ffffff;border-radius:12px;padding:1.25rem;border:1px solid #eceef1;display:flex;flex-direction:column;gap:0.75rem;">
        <div style="display:flex;align-items:center;gap:0.75rem;">
          <div style="width:40px;height:40px;border-radius:10px;background:${isFirst ? '#00425e' : '#eceef1'};display:flex;align-items:center;justify-content:center;flex-shrink:0;">
            <span class="material-symbols-outlined" style="font-size:1.25rem;color:${isFirst ? '#c6e7ff' : '#40484e'};">${icon}</span>
          </div>
          <div>
            <div style="font-family:Manrope,sans-serif;font-size:0.9375rem;font-weight:700;color:#191c1e;">${label}</div>
            ${isFirst ? '<div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.1em;color:#006a6a;">Current Task</div>' : ''}
          </div>
        </div>
        <div style="font-size:11px;color:#40484e;">2 tasks · Difficulty 2</div>
      </div>
    `;
  }).join('');

  grid.innerHTML = `
    <div style="grid-column:1/-1;background:#ffffff;border-radius:16px;padding:1.5rem;border:1px solid #eceef1;margin-bottom:1rem;display:flex;justify-content:space-between;align-items:center;">
      <div>
        <div style="font-family:Manrope,sans-serif;font-size:1.125rem;font-weight:800;color:#191c1e;">${tasks.length} Tasks Loaded</div>
        <div style="font-size:0.875rem;color:#40484e;">9 cognitive abilities · 2 tasks each</div>
      </div>
      <div style="display:flex;align-items:center;gap:0.75rem;">
        <span style="font-size:12px;color:#40484e;" id="assessment-progress">0 / ${tasks.length}</span>
        <button onclick="startTask(0)"
                style="background:#00425e;color:#fff;border:none;border-radius:8px;padding:0.625rem 1.25rem;font-weight:700;font-size:13px;cursor:pointer;">
          Begin Assessment
        </button>
      </div>
    </div>
    ${cards}
  `;
}
