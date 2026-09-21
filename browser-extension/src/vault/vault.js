/**
 * Local Credential & Secret Vault (Phase 9)
 * Stores user secrets locally in browser storage/memory.
 * INVARIANT: Secrets are keyed by secret_ref.
 * Only secret_ref is ever sent to or received from the planner/server.
 * The browser resolves secret_ref locally immediately before typing into the DOM.
 * Secrets are never logged, never transmitted over the network, and never included in telemetry.
 */

const LOCAL_VAULT = new Map();

// Default demo credentials pre-seeded into local storage
const DEFAULT_DEMO_SECRETS = {
  "bank.password": "SuperSecretBankPass2026!",
  "login.password": "SecureEnterprisePassword#99",
  "gov.otp": "849201",
  "gov.aadhaar": "5481 9201 3847",
  "shop.card_cvv": "782"
};

export async function initVault() {
  for (const [k, v] of Object.entries(DEFAULT_DEMO_SECRETS)) {
    if (!LOCAL_VAULT.has(k)) {
      LOCAL_VAULT.set(k, v);
    }
  }

  // Attempt to load any user-defined secrets from chrome.storage.local if available
  if (typeof chrome !== 'undefined' && chrome.storage && chrome.storage.local) {
    try {
      const stored = await chrome.storage.local.get('ps26171_vault');
      if (stored && stored.ps26171_vault) {
        for (const [k, v] of Object.entries(stored.ps26171_vault)) {
          LOCAL_VAULT.set(k, v);
        }
      }
    } catch (e) {
      console.warn('[VAULT] Local storage read error:', e);
    }
  }
}

/**
 * Registers or updates a secret reference locally in the browser.
 */
export async function setSecret(secretRef, secretValue) {
  if (!secretRef || typeof secretRef !== 'string') {
    throw new Error('Invalid secret_ref provided to vault');
  }
  LOCAL_VAULT.set(secretRef, secretValue);

  if (typeof chrome !== 'undefined' && chrome.storage && chrome.storage.local) {
    const obj = {};
    for (const [k, v] of LOCAL_VAULT.entries()) {
      obj[k] = v;
    }
    await chrome.storage.local.set({ ps26171_vault: obj });
  }
}

/**
 * Resolves a secret locally. Must ONLY be called during DOM action execution.
 */
export function resolveSecret(secretRef) {
  if (!secretRef) return null;
  if (!LOCAL_VAULT.has(secretRef)) {
    // Check fallback in defaults
    if (DEFAULT_DEMO_SECRETS[secretRef]) {
      return DEFAULT_DEMO_SECRETS[secretRef];
    }
    throw new Error(`Vault secret_ref not found: '${secretRef}'`);
  }
  return LOCAL_VAULT.get(secretRef);
}

/**
 * Checks if a given string contains any raw secret value from the vault.
 * Used by Egress Gate to guarantee zero leak of vault contents.
 */
export function containsVaultSecret(text) {
  if (!text || typeof text !== 'string') return false;
  for (const [ref, secret] of LOCAL_VAULT.entries()) {
    if (secret && secret.length >= 4 && text.includes(secret)) {
      return { leak: true, secretRef: ref };
    }
  }
  for (const [ref, secret] of Object.entries(DEFAULT_DEMO_SECRETS)) {
    if (secret && secret.length >= 4 && text.includes(secret)) {
      return { leak: true, secretRef: ref };
    }
  }
  return { leak: false };
}
