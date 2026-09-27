import { METRICS } from '../data/scenarios'

export default function MetricsDashboard() {
  return (
    <section id="results" className="glass-card p-6">
      <div className="flex items-start justify-between mb-6">
        <div>
          <h3 className="text-white font-semibold text-base">Perception & Privacy Evaluation</h3>
          <p className="text-gray-500 text-xs mt-0.5">Empirical benchmarks on 1920×1080 real UI screens</p>
        </div>
        <div className="text-right">
          <p className="text-3xl font-bold text-gradient-cyan">94.8%</p>
          <p className="text-[10px] text-gray-500 mt-0.5">Mean Accuracy Rate</p>
        </div>
      </div>

      <div className="space-y-5">
        {METRICS.map((m, i) => (
          <div key={m.label}>
            <div className="flex items-center justify-between mb-1.5">
              <div className="flex items-center gap-2">
                <div
                  className="icon-badge text-xs"
                  style={{ width: 28, height: 28, borderRadius: 8, background: `linear-gradient(135deg, ${['#1e3a8a','#4c1d95','#065f46','#92400e','#7f1d1d'][i % 5]}, ${['#3b82f6','#a855f7','#10b981','#f97316','#ef4444'][i % 5]})` }}
                >
                  {['📸','🛡️','✂️','⚡','⏱️'][i]}
                </div>
                <span className="text-sm text-gray-300">{m.label}</span>
              </div>
              <span className="text-sm font-bold text-emerald-400">{m.score}%</span>
            </div>
            <div className="h-1.5 rounded-full" style={{ background: 'rgba(255,255,255,0.06)' }}>
              <div className="score-fill" style={{ width: `${m.score}%` }} />
            </div>
            <p className="text-[10px] text-gray-500 mt-1">{m.detail}</p>
          </div>
        ))}
      </div>

      {/* Stat tiles */}
      <div
        className="mt-6 pt-5 grid grid-cols-3 gap-3"
        style={{ borderTop: '1px solid rgba(255,255,255,0.05)' }}
      >
        {[
          { icon: '💾', label: 'Model Size',  value: '1.75 MB', sub: 'pii_detector.onnx',   color: '#3b82f6' },
          { icon: '⚡', label: 'Inference',   value: '11.2 ms', sub: 'WebGPU on-device',    color: '#a855f7' },
          { icon: '🔒', label: 'PII Leakage', value: '0.0%',    sub: 'All 10 workflows',    color: '#10b981' },
        ].map(s => (
          <div key={s.label} className="rounded-2xl p-4 text-center" style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)' }}>
            <div className="text-xl mb-1">{s.icon}</div>
            <p className="text-lg font-bold" style={{ color: s.color }}>{s.value}</p>
            <p className="text-[10px] text-gray-400 mt-0.5">{s.label}</p>
            <p className="text-[9px] text-gray-600 mt-0.5">{s.sub}</p>
          </div>
        ))}
      </div>
    </section>
  )
}
