import { PIPELINE_STEPS } from '../data/scenarios'

const STEP_META = [
  { icon: 'icon-badge-blue',   color: '#3b82f6' },
  { icon: 'icon-badge-purple', color: '#8b5cf6' },
  { icon: 'icon-badge-cyan',   color: '#06b6d4' },
  { icon: 'icon-badge-red',    color: '#ef4444' },
  { icon: 'icon-badge-orange', color: '#f97316' },
  { icon: 'icon-badge-green',  color: '#10b981' },
]

export default function PipelineFlow({ activeStep, isScanning }) {
  return (
    <section id="pipeline" className="glass-card p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-white font-semibold text-base">On-Device Pipeline</h3>
          <p className="text-gray-600 text-xs mt-0.5">End-to-end visual agent execution trace — zero cloud inference</p>
        </div>
        {isScanning && (
          <span className="flex items-center gap-2 text-xs text-blue-400">
            <span className="w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
            Running...
          </span>
        )}
      </div>

      <div className="flex items-stretch gap-0 overflow-x-auto pb-2 min-w-0">
        {PIPELINE_STEPS.map((step, i) => {
          const meta    = STEP_META[i]
          const isDone  = activeStep > i
          const isActive= activeStep === i
          const pending = activeStep < i

          return (
            <div key={step.id} className="flex items-center flex-shrink-0">
              {/* Step card */}
              <div
                className="flex flex-col items-center w-32 px-2 py-4 rounded-2xl transition-all duration-500"
                style={{
                  background: isDone || isActive ? `${meta.color}12` : 'rgba(255,255,255,0.03)',
                  border: `1px solid ${isDone || isActive ? `${meta.color}40` : 'rgba(255,255,255,0.06)'}`,
                  transform: isActive ? 'scale(1.05)' : 'scale(1)',
                  boxShadow: isActive ? `0 0 30px ${meta.color}25` : 'none',
                }}
              >
                {/* Icon badge */}
                <div
                  className={`icon-badge ${isDone || isActive ? meta.icon : ''} mb-2 text-base transition-all`}
                  style={pending ? { background: 'rgba(255,255,255,0.06)', opacity: 0.4 } : {}}
                >
                  {step.icon}
                </div>

                {/* Status dot + label */}
                <div className="flex items-center gap-1 mb-1">
                  <span
                    className="w-1.5 h-1.5 rounded-full flex-shrink-0"
                    style={{ background: isDone || isActive ? meta.color : 'rgba(255,255,255,0.2)' }}
                  />
                  <span className="text-[10px] font-semibold text-center leading-tight" style={{ color: isDone || isActive ? '#fff' : 'rgba(255,255,255,0.3)' }}>
                    {step.label}
                  </span>
                </div>

                <p className="text-[9px] text-center leading-tight" style={{ color: 'rgba(255,255,255,0.25)' }}>
                  {step.desc}
                </p>

                {/* Status badge */}
                {isDone && (
                  <span className="mt-2 text-[9px] px-2 py-0.5 rounded-full font-semibold" style={{ background: `${meta.color}20`, color: meta.color }}>
                    ✓ done
                  </span>
                )}
                {isActive && (
                  <span className="mt-2 text-[9px] px-2 py-0.5 rounded-full font-semibold animate-pulse" style={{ background: `${meta.color}20`, color: meta.color }}>
                    processing
                  </span>
                )}
              </div>

              {/* Connector */}
              {i < PIPELINE_STEPS.length - 1 && (
                <div className="w-6 flex flex-col items-center flex-shrink-0">
                  <div
                    className={`h-px w-full ${isDone ? 'pipe-line-active' : ''}`}
                    style={{ background: isDone ? undefined : 'rgba(255,255,255,0.07)' }}
                  />
                  <span className="text-[9px]" style={{ color: isDone ? meta.color : 'rgba(255,255,255,0.1)' }}>▶</span>
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* Bottom legend */}
      <div
        className="mt-5 pt-4 grid grid-cols-3 gap-3 text-[10px] text-gray-600"
        style={{ borderTop: '1px solid rgba(255,255,255,0.05)' }}
      >
        {[
          { dot: '#3b82f6', label: 'Capture → UI Perception (34 classes)' },
          { dot: '#ef4444', label: 'Privacy Gate — PII intercepted here' },
          { dot: '#10b981', label: 'Action executed locally on-device' },
        ].map(l => (
          <span key={l.label} className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: l.dot }} />
            {l.label}
          </span>
        ))}
      </div>
    </section>
  )
}
