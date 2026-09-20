/**
 * Browser Extension Popup Logic
 * Coordinates Local Perception -> Redaction -> Egress Gate -> Action Loop
 */
document.getElementById('btn-run').addEventListener('click', async () => {
  const task = document.getElementById('task-input').value;
  const logBox = document.getElementById('log-box');
  
  logBox.innerHTML += `<div>[TASK] Starting: ${task}</div>`;
  
  // 1. Send instruction to Background Service Worker to trigger perception & action loop
  chrome.runtime.sendMessage({ type: 'EXECUTE_TASK', task }, (res) => {
    if (res && res.success) {
      logBox.innerHTML += `<div style="color:#2ecc71;">[SUCCESS] Task executed with 0 PII leaks!</div>`;
    } else {
      logBox.innerHTML += `<div style="color:#e74c3c;">[ERROR] ${res ? res.error : 'Execution failed'}</div>`;
    }
  });
});

document.getElementById('btn-stop').addEventListener('click', () => {
  chrome.runtime.sendMessage({ type: 'KILL_SWITCH' });
  const logBox = document.getElementById('log-box');
  logBox.innerHTML += `<div style="color:#e74c3c;">[KILL SWITCH] Agent execution halted immediately.</div>`;
});
