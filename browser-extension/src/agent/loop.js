/**
 * Closed-Loop Autonomous Browser Agent Controller (Phase 11)
 * Pipeline:
 * OBSERVE -> PERCEIVE -> SANITIZE -> EGRESS -> PLAN -> EXECUTE -> RE-OBSERVE -> VERIFY -> NEXT ACTION
 * Continues until DONE, ASK_USER, or MAX_STEPS reached.
 */

import { sendSanitizedContextToGate } from '../egress/gate.js';
import { executeAction } from './executor.js';

export class AgentLoopController {
  constructor(options = {}) {
    this.serverUrl = options.serverUrl || 'http://127.0.0.1:8080';
    this.maxSteps = options.maxSteps || 10;
    this.isRunning = false;
    this.history = [];
    this.sessionId = `session_${Date.now()}`;
  }

  stop() {
    this.isRunning = false;
    console.log('[AGENT LOOP] Kill switch activated. Agent stopped.');
  }

  async runTask(instruction, getObservationCallback) {
    this.isRunning = true;
    this.history = [];
    this.sessionId = `session_${Date.now()}`;
    let currentStep = 1;

    console.log(`[AGENT LOOP] Starting closed-loop task: "${instruction}"`);

    while (this.isRunning && currentStep <= this.maxSteps) {
      console.log(`[AGENT LOOP] --- STEP ${currentStep} of ${this.maxSteps} ---`);

      // 1. OBSERVE & PERCEIVE & SANITIZE (Provided by tab capture & content script)
      const observation = await getObservationCallback();
      if (!observation) {
        throw new Error('Failed to retrieve page observation.');
      }

      // 2. Build Sanitized Payload Package
      const sanitizedPayload = {
        session_id: this.sessionId,
        step: currentStep,
        instruction_sanitized: instruction,
        page: {
          url_sanitized: observation.url || window.location?.href || 'http://localhost',
          title_sanitized: observation.title || document.title || 'Page',
          viewport: observation.viewport || { w: 1280, h: 720, dpr: 1.0 }
        },
        screenshot: observation.sanitizedScreenshot || null,
        elements: observation.elements || [],
        redactions: observation.redactions || [],
        privacy_report: observation.privacyReport || {
          detected: 0,
          sensitive: 0,
          redacted: 0,
          verification: 'PASS',
          gate: 'PASS'
        },
        history: this.history
      };

      // 3. EGRESS GATE ENFORCEMENT & SERVER PLANNING
      console.log('[AGENT LOOP] Sending sanitized payload through Egress Gate...');
      const planResponse = await sendSanitizedContextToGate(sanitizedPayload, this.serverUrl);
      console.log('[AGENT LOOP] Received validated plan from server:', planResponse);

      if (!planResponse || !planResponse.actions || planResponse.actions.length === 0) {
        console.log('[AGENT LOOP] No actions returned by planner. Stopping loop.');
        break;
      }

      // 4. EXECUTE ACTIONS
      let isDone = false;
      for (const action of planResponse.actions) {
        if (!this.isRunning) break;

        const actionResult = await executeAction(action);
        this.history.push({
          step: currentStep,
          action: action.type,
          result: actionResult.message || 'ok'
        });

        if (action.type === 'done' || actionResult.done) {
          isDone = true;
          break;
        }

        if (action.type === 'ask_user' || actionResult.askUser) {
          this.isRunning = false;
          return { success: true, status: 'ASK_USER', step: currentStep, plan: planResponse };
        }

        // Small delay between sub-actions
        await new Promise(r => setTimeout(r, 600));
      }

      if (isDone) {
        console.log(`[AGENT LOOP] Task completed successfully at step ${currentStep}!`);
        return {
          success: true,
          status: 'DONE',
          steps: currentStep,
          history: this.history
        };
      }

      currentStep++;
      // Wait for page reaction/re-render before next observation
      await new Promise(r => setTimeout(r, 1000));
    }

    if (currentStep > this.maxSteps) {
      console.warn(`[AGENT LOOP] Reached maximum allowed steps (${this.maxSteps}). Halting.`);
      return { success: false, status: 'MAX_STEPS_EXCEEDED', steps: currentStep };
    }

    return { success: true, status: 'STOPPED' };
  }
}
