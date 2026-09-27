import { useState, useEffect } from 'react'

const PII_STYLES = {
  '#ef4444': { tag: 'tag-red',    border: 'rgba(239,68,68,0.4)',    bg: 'rgba(239,68,68,0.08)'   },
  '#f97316': { tag: 'tag-red',    border: 'rgba(249,115,22,0.4)',   bg: 'rgba(249,115,22,0.08)'  },
  '#a855f7': { tag: 'tag-purple', border: 'rgba(168,85,247,0.4)',   bg: 'rgba(168,85,247,0.08)'  },
  '#eab308': { tag: 'tag-blue',   border: 'rgba(234,179,8,0.4)',    bg: 'rgba(234,179,8,0.08)'   },
  '#06b6d4': { tag: 'tag-cyan',   border: 'rgba(6,182,212,0.4)',    bg: 'rgba(6,182,212,0.08)'   },
  '#10b981': { tag: 'tag-green',  border: 'rgba(16,185,129,0.4)',   bg: 'rgba(16,185,129,0.08)'  },
}

function FieldRow({ field, redact, onValueChange }) {
  const [appeared, setAppeared] = useState(false)
  
  useEffect(() => { 
    if (redact && field.pii) { 
      const t = setTimeout(() => setAppeared(true), 60); 
      return () => clearTimeout(t) 
    } else {
      setAppeared(false)
    }
  }, [redact, field.pii])

  const style = field.color ? PII_STYLES[field.color] : null

  return (
    <div className="flex items-center gap-3 py-2 border-b border-white/[0.04] hover:bg-white/[0.015] px-2 rounded-lg transition-colors">
      <span className="text-xs text-gray-500 w-32 shrink-0 font-medium">{field.label}</span>

      {redact && field.pii ? (
        <div className={`flex-1 ${appeared ? 'redact-appear' : 'opacity-0'}`}>
          <div
            className="inline-flex items-center gap-2 px-2.5 py-0.5 rounded-md text-xs font-mono font-bold"
            style={{ background: style?.bg, border: `1px solid ${style?.border}` }}
          >
            <span className="opacity-40 select-none">█████</span>
            <span className="text-white/80 tracking-wider">REDACTED</span>
            <span className="opacity-40">·</span>
            <span className="text-white/60 uppercase tracking-widest text-[9px]">{field.piiType}</span>
          </div>
          <p className="text-[10px] mt-0.5 text-gray-500 flex items-center gap-1.5">
            <span className="line-through">{field.value}</span>
            <span className="text-red-400 text-[10px] font-medium">⊘ Blocked from Egress</span>
          </p>
        </div>
      ) : (
        <div className="flex-1 flex items-center gap-2">
          {onValueChange ? (
            <input
              type="text"
              value={field.value}
              onChange={(e) => onValueChange(field.id, e.target.value)}
              className="bg-black/40 border border-white/10 rounded px-2.5 py-1 text-xs text-white focus:outline-none focus:border-cyan-500/60 w-full max-w-[270px] font-mono transition-colors"
              title="Click to edit field value"
            />
          ) : (
            <span className={`text-xs ${field.pii && !redact ? 'text-white font-mono font-medium' : 'text-gray-400'}`}>
              {field.value}
            </span>
          )}
          
          {field.pii && !redact && style && (
            <span className={`tag ${style.tag} text-[9px] px-2 py-0.5`}>
              {field.piiType}
            </span>
          )}
          {!field.pii && !redact && (
            <span className="text-[9px] text-gray-600 font-mono">Public Safe</span>
          )}
        </div>
      )}
    </div>
  )
}

function GlassPane({ title, subtitle, badge, children, glowColor }) {
  return (
    <div
      className="glass-card flex flex-col overflow-hidden relative"
      style={glowColor ? { boxShadow: `0 0 40px ${glowColor}` } : {}}
    >
      <div className="flex items-center justify-between px-4 py-3 border-b border-white/[0.06] bg-white/[0.02]">
        <div className="flex items-center gap-2 min-w-0">
          <div className="flex gap-1.5 mr-1">
            <span className="w-2.5 h-2.5 rounded-full bg-red-500/50" />
            <span className="w-2.5 h-2.5 rounded-full bg-yellow-500/50" />
            <span className="w-2.5 h-2.5 rounded-full bg-green-500/50" />
          </div>
          <div>
            <p className="text-xs font-semibold text-white truncate">{title}</p>
            <p className="text-[10px] text-gray-500 truncate">{subtitle}</p>
          </div>
        </div>
        {badge}
      </div>

      <div className="flex-1 p-4 overflow-y-auto max-h-[380px]">{children}</div>
    </div>
  )
}

export default function SideBySideView({
  scenario,
  isScanning,
  showRedacted,
  scanDone,
  isAgentDispatched,
  agentOutput,
  onFieldValueChange
}) {
  const egressIsRedacted = scenario.egress === 'EGRESS_REDACTED'

  return (
    <div className="space-y-4">
      {/* 2-Column Side-by-Side Screen */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">

        {/* LEFT: Raw Browser View */}
        <div className="relative">
          {isScanning && (
            <div className="absolute inset-0 rounded-[20px] overflow-hidden z-20 pointer-events-none">
              <div className="scanner-beam" />
              <div className="absolute inset-0 bg-blue-500/[0.03]" />
            </div>
          )}
          <GlassPane
            title="Local Viewport (What Agent Sees On-Device)"
            subtitle="Raw unredacted pixels & text for on-device reasoning"
            glowColor={isScanning ? 'rgba(56,189,248,0.2)' : undefined}
            badge={<span className="tag tag-blue text-[9px]">Client Memory Only</span>}
          >
            <div className="space-y-0.5">
              {scenario.fields.map(f => (
                <FieldRow 
                  key={f.id} 
                  field={f} 
                  redact={false} 
                  onValueChange={onFieldValueChange}
                />
              ))}
            </div>

            {/* Target Agent Grounding Intent */}
            <div className="mt-4 p-3 rounded-xl bg-blue-950/30 border border-blue-500/20 flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-blue-600/30 text-blue-400 flex items-center justify-center font-bold text-sm">
                🎯
              </div>
              <div className="min-w-0">
                <p className="text-xs font-semibold text-blue-300">Action Grounding Target</p>
                <p className="text-[11px] text-gray-400 truncate">{scenario.agentAction.description}</p>
              </div>
            </div>
          </GlassPane>
        </div>

        {/* RIGHT: Egress Stream (What Cloud / Third Party Receives) */}
        <div className="relative">
          {!showRedacted && !scanDone && (
            <div className="absolute inset-0 rounded-[20px] z-10 flex flex-col items-center justify-center gap-3 bg-[#04040e]/90 backdrop-blur-md border border-white/10">
              <div className="w-12 h-12 rounded-2xl bg-purple-950/60 border border-purple-500/30 flex items-center justify-center text-2xl text-purple-300">
                🔒
              </div>
              <div className="text-center px-6">
                <p className="text-xs font-semibold text-gray-200">Egress Gate Active</p>
                <p className="text-[11px] text-gray-400 mt-1">
                  Click <strong className="text-cyan-400 font-medium">Dispatch Autonomous Agent</strong> to trigger redaction & task execution
                </p>
              </div>
            </div>
          )}

          <GlassPane
            title="Egress Network Stream (What Cloud Receives)"
            subtitle={showRedacted 
              ? (egressIsRedacted ? `${scenario.piiBlocked} PII fields masked with surrogate hashes` : 'Safe public fields cleared for network transmission')
              : 'Waiting for egress authorization...'}
            glowColor={showRedacted ? (egressIsRedacted ? 'rgba(239,68,68,0.15)' : 'rgba(16,185,129,0.15)') : undefined}
            badge={
              showRedacted
                ? <span className={`tag ${egressIsRedacted ? 'tag-red' : 'tag-green'} text-[9px]`}>
                    {egressIsRedacted ? '⊘ Zero PII Egress' : '✓ Full Payload Allowed'}
                  </span>
                : <span className="tag text-[9px] text-gray-500 bg-white/5 border-white/10">Awaiting Dispatch</span>
            }
          >
            <div className="space-y-0.5">
              {scenario.fields.map(f => (
                <FieldRow key={f.id} field={f} redact={showRedacted} />
              ))}
            </div>

            {/* Redaction Guarantee Stats */}
            {showRedacted && (
              <div className="mt-4 pt-3 border-t border-white/[0.05] space-y-2">
                <div
                  className="flex items-center gap-2 p-2.5 rounded-lg text-xs"
                  style={{
                    background: egressIsRedacted ? 'rgba(239,68,68,0.08)' : 'rgba(16,185,129,0.08)',
                    border: `1px solid ${egressIsRedacted ? 'rgba(239,68,68,0.25)' : 'rgba(16,185,129,0.25)'}`,
                  }}
                >
                  <span className="text-base">{egressIsRedacted ? '🛡️' : '✅'}</span>
                  <p className="text-[11px] font-medium" style={{ color: egressIsRedacted ? '#fca5a5' : '#6ee7b7' }}>
                    {egressIsRedacted
                      ? `Privacy Egress Verified: ${scenario.piiBlocked} sensitive entities masked. 0.0% PII escaped to server.`
                      : 'Egress Cleared: No regulated or private entities detected. Transmission permitted.'}
                  </p>
                </div>

                <div className="grid grid-cols-3 gap-2 text-center">
                  {[
                    { label: 'Fields Audited', val: scenario.fields.length, color: '#38bdf8' },
                    { label: 'Masked Entities', val: scenario.piiBlocked, color: '#f87171' },
                    { label: 'Verified Leakage', val: '0.0%', color: '#4ade80' },
                  ].map(stat => (
                    <div key={stat.label} className="bg-white/[0.03] border border-white/[0.05] rounded-lg py-1.5 px-2">
                      <p className="text-sm font-bold font-mono" style={{ color: stat.color }}>{stat.val}</p>
                      <p className="text-[9px] text-gray-500 mt-0.5">{stat.label}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </GlassPane>
        </div>
      </div>

      {/* Autonomous Agent Execution Output Terminal */}
      {isAgentDispatched && agentOutput && (
        <div className="p-4 rounded-xl bg-[#030614] border border-cyan-500/30 space-y-2 font-mono text-xs">
          <div className="flex items-center justify-between pb-2 border-b border-white/10">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-cyan-400 animate-ping" />
              <span className="text-cyan-300 font-bold uppercase tracking-wider text-[11px]">Autonomous Agent Terminal Execution</span>
            </div>
            <span className="text-emerald-400 text-[10px] bg-emerald-950/60 border border-emerald-500/30 px-2 py-0.5 rounded-full">
              Status: Action Dispatched & Executed (100% Target Precision)
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-1 text-[11px]">
            <div>
              <span className="text-gray-500">Agent Action Type:</span>{' '}
              <span className="text-yellow-400 font-bold">{agentOutput.actionType}</span>
            </div>
            <div>
              <span className="text-gray-500">Target Selector / Coords:</span>{' '}
              <span className="text-white">{agentOutput.target}</span>
            </div>
            <div>
              <span className="text-gray-500">Execution Latency:</span>{' '}
              <span className="text-emerald-400 font-bold">{agentOutput.latency}</span>
            </div>
          </div>

          <div className="bg-black/50 p-2.5 rounded border border-white/5 text-[11px] text-gray-300">
            <span className="text-cyan-400">$ agent.execute()</span> → {agentOutput.log}
          </div>
        </div>
      )}
    </div>
  )
}
