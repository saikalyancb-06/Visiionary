/**
 * Visiionary Side Panel Controller & Long-Running Agent Monitor
 * Completely decoupled from popup lifecycle.
 * Reconnects seamlessly to active tasks in chrome.storage.session / background.
 */

const logBox = document.getElementById('log-box');
const stateBadge = document.getElementById('agent-state-badge');
const lblStatus = document.getElementById('lbl-status');
const lblStepCount = document.getElementById('lbl-step-count');
const valTargetTab = document.getElementById('val-target-tab');
const valCurrentAction = document.getElementById('val-current-action');
const valCurrentUrl = document.getElementById('val-current-url');
const valVerifierState = document.getElementById('val-verifier-state');
const valRemainingGoal = document.getElementById('val-remaining-goal');
const valSubgoalsSummary = document.getElementById('val-subgoals-summary');
const lblLoopProtect = document.getElementById('lbl-loop-protect');

const statHardware = document.getElementById('stat-hardware');
const statInfLatency = document.getElementById('stat-inf-latency');
const statE2eLatency = document.getElementById('stat-e2e-latency');
const statMemory = document.getElementById('stat-memory');
const statRedactedCount = document.getElementById('stat-redacted-count');
const taskInput = document.getElementById('task-input');

function appendLog(msg, type = 'normal') {
  if (!logBox) return;
  const div = document.createElement('div');
  div.className = 'step-log';
  if (type === 'success') div.className += ' text-success';
  if (type === 'alert') div.className += ' text-alert';
  if (type === 'info') div.className += ' text-info';
  if (type === 'warn') div.className += ' text-warn';
  div.innerText = msg;
  logBox.appendChild(div);
  logBox.scrollTop = logBox.scrollHeight;
}

function updateResourceMetrics() {
  if (performance && performance.memory) {
    const memMB = (performance.memory.usedJSHeapSize / (1024 * 1024)).toFixed(1);
    if (statMemory) statMemory.innerText = `${memMB} MB`;
  } else {
    if (statMemory) statMemory.innerText = `< 45 MB`;
  }
}
updateResourceMetrics();
setInterval(updateResourceMetrics, 3000);

function renderState(state) {
  if (!state) return;

  if (state.task && taskInput && document.activeElement !== taskInput) {
    taskInput.value = state.task;
  }

  if (lblStepCount) {
    lblStepCount.innerText = `Step ${state.step || 0} / ${state.maxSteps || 8}`;
  }

  if (valTargetTab) {
    valTargetTab.innerText = state.tabId ? `Tab #${state.tabId}` : '--';
  }

  if (valCurrentAction) {
    valCurrentAction.innerText = state.currentAction || '--';
  }

  if (valCurrentUrl) {
    valCurrentUrl.innerText = state.currentUrl ? (state.currentUrl.length > 50 ? state.currentUrl.substring(0, 48) + '...' : state.currentUrl) : '--';
  }

  if (valRemainingGoal) {
    valRemainingGoal.innerText = state.remainingGoal || (state.verificationState?.verified ? 'None (Complete)' : state.task || '--');
  }

  if (valSubgoalsSummary) {
    if (state.subgoals && state.subgoals.length > 0) {
      const completed = new Set(state.completedSubgoals || []);
      const summary = state.subgoals.map((sg, i) => `${completed.has(sg) ? '✅' : '⏳'} ${sg}`).join(' | ');
      valSubgoalsSummary.innerText = summary;
    } else {
      valSubgoalsSummary.innerText = '--';
    }
  }

  if (valVerifierState) {
    const vState = state.verificationState;
    if (vState && (vState.verified || state.status === 'GOAL_ACHIEVED')) {
      valVerifierState.innerText = 'GOAL_ACHIEVED ✅';
      valVerifierState.style.color = '#34d399';
    } else if (state.status === 'RECOVERY_REQUIRED' || vState?.goal_status === 'RECOVERY_REQUIRED') {
      valVerifierState.innerText = 'RECOVERY_REQUIRED ⚠️';
      valVerifierState.style.color = '#fbbf24';
    } else if (state.status === 'ACTION_FAILED' || vState?.goal_status === 'ACTION_FAILED') {
      valVerifierState.innerText = 'ACTION_FAILED ❌';
      valVerifierState.style.color = '#f87171';
    } else if (state.status === 'GOAL_NOT_YET_ACHIEVED' || state.status === 'EXECUTING' || state.status === 'PLANNING' || state.status === 'OBSERVING') {
      valVerifierState.innerText = 'GOAL_NOT_YET_ACHIEVED ⏳ (Action in progress)';
      valVerifierState.style.color = '#38bdf8';
    } else {
      valVerifierState.innerText = vState?.goal_status || 'GOAL_NOT_YET_ACHIEVED';
      valVerifierState.style.color = '#94a3b8';
    }
  }

  if (lblLoopProtect && state.loopProtection) {
    if (state.loopProtection.loopDetected) {
      lblLoopProtect.innerText = 'Loop Shield: RECOVERY ACTIVE ⚠️';
      lblLoopProtect.style.color = '#f87171';
    } else {
      lblLoopProtect.innerText = 'Loop Shield: OK';
      lblLoopProtect.style.color = '#34d399';
    }
  }

  if (lblStatus) {
    lblStatus.innerText = state.status || 'Ready';
  }

  if (stateBadge) {
    stateBadge.className = 'badge';
    stateBadge.innerText = state.status || 'IDLE';
    if (state.status === 'RUNNING' || state.status === 'OBSERVING' || state.status === 'PLANNING' || state.status === 'EXECUTING' || state.status === 'VERIFYING') {
      stateBadge.className += ' badge-running';
    } else if (state.status === 'GOAL_ACHIEVED' || state.status === 'VERIFIED_SUCCESS' || state.status === 'DONE') {
      stateBadge.className += ' badge-success';
    } else if (state.status === 'FAILED' || state.status === 'STOPPED' || state.status === 'ACTION_FAILED') {
      stateBadge.className += ' badge-alert';
    } else if (state.status === 'GOAL_NOT_YET_ACHIEVED' || state.status === 'RECOVERY_REQUIRED') {
      stateBadge.className += ' badge-running';
    } else {
      stateBadge.className += ' badge-idle';
    }
  }

  const metrics = state.metrics || {};
  if (statHardware && metrics.provider) statHardware.innerText = metrics.provider.toUpperCase();
  if (statInfLatency && metrics.inference_latency_ms) statInfLatency.innerText = `${metrics.inference_latency_ms} ms`;
  if (statE2eLatency && metrics.e2e_latency_ms) statE2eLatency.innerText = `${metrics.e2e_latency_ms} ms`;
  if (statRedactedCount && metrics.redacted_count !== undefined) statRedactedCount.innerText = `${metrics.redacted_count} Items`;
}

// Request initial state from background service worker
function syncWithBackground() {
  chrome.runtime.sendMessage({ type: 'GET_AGENT_STATE' }, (res) => {
    if (chrome.runtime.lastError) {
      appendLog(`[CONNECT] Background worker initializing...`, 'info');
      return;
    }
    if (res && res.state) {
      renderState(res.state);
      if (res.state.isRunning) {
        appendLog(`[RECONNECTED] Reconnected to background run on Tab #${res.state.tabId} (Step ${res.state.step}).`, 'info');
      }
    }
  });
}

syncWithBackground();

// Listen for broadcast updates from background service worker
chrome.runtime.onMessage.addListener((msg) => {
  if (msg.type === 'AGENT_STATE_UPDATE' && msg.state) {
    renderState(msg.state);
    if (msg.logMessage) {
      appendLog(msg.logMessage, msg.logType || 'normal');
    }
  }
});

// Run task handler
document.getElementById('btn-run').addEventListener('click', async () => {
  const task = taskInput.value.trim();
  if (!task) return;

  appendLog(`[TASK INITIATED] "${task}"`, 'info');
  chrome.runtime.sendMessage({ type: 'EXECUTE_TASK', task }, (res) => {
    if (chrome.runtime.lastError) {
      appendLog(`[ERROR] ${chrome.runtime.lastError.message}`, 'alert');
      return;
    }
    if (res && res.error) {
      appendLog(`[START ERROR] ${res.error}`, 'alert');
    }
  });
});

// Kill switch handler
document.getElementById('btn-stop').addEventListener('click', () => {
  chrome.runtime.sendMessage({ type: 'KILL_SWITCH' }, (res) => {
    appendLog(`[HALT] Agent halted immediately by user kill switch.`, 'alert');
  });
});
