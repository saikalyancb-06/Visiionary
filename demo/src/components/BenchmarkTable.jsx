const WORKFLOWS = [
  { id: 'WF-01', desc: 'Contact feedback form',           pii: true,  status: 'EGRESS_REDACTED', latency: '36.9 ms' },
  { id: 'WF-02', desc: 'E-commerce search & filtering',  pii: false, status: 'EGRESS_ALLOWED',  latency: '45.0 ms' },
  { id: 'WF-03', desc: 'Multi-page doc navigation',      pii: false, status: 'EGRESS_ALLOWED',  latency: '37.0 ms' },
  { id: 'WF-04', desc: 'Non-sensitive institutional form',pii: false, status: 'EGRESS_ALLOWED',  latency: '36.5 ms' },
  { id: 'WF-05', desc: 'Scientific publication PDF',     pii: false, status: 'EGRESS_ALLOWED',  latency: '29.0 ms' },
  { id: 'WF-06', desc: 'Account security preferences',   pii: true,  status: 'EGRESS_REDACTED', latency: '37.1 ms' },
  { id: 'WF-07', desc: 'Refund with payment PII',        pii: true,  status: 'EGRESS_REDACTED', latency: '45.2 ms' },
  { id: 'WF-08', desc: 'Govt portal identity verify',    pii: true,  status: 'EGRESS_REDACTED', latency: '36.5 ms' },
  { id: 'WF-09', desc: 'UI table & modal examination',   pii: false, status: 'EGRESS_ALLOWED',  latency: '28.8 ms' },
  { id: 'WF-10', desc: 'Multi-step UPI checkout',        pii: true,  status: 'EGRESS_REDACTED', latency: '49.4 ms' },
]

export default function BenchmarkTable() {
  const redacted = WORKFLOWS.filter(w => w.status === 'EGRESS_REDACTED').length
  const allowed  = WORKFLOWS.filter(w => w.status === 'EGRESS_ALLOWED').length

  return (
    <section id="benchmark" className="glass-card p-6">
      <div className="flex items-start justify-between mb-6">
        <div>
          <h3 className="text-white font-semibold text-base">10-Workflow Benchmark</h3>
          <p className="text-gray-600 text-xs mt-0.5">100% pass rate · Zero PII leakage across all egress tests</p>
        </div>
        <div className="flex gap-2">
          <span className="tag tag-red">{redacted} Redacted</span>
          <span className="tag tag-green">{allowed} Allowed</span>
        </div>
      </div>

      <table className="w-full text-xs">
        <thead>
          <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
            {['ID', 'Workflow', 'PII', 'Egress Gate', 'Latency'].map(h => (
              <th key={h} className="text-left pb-3 pr-3 font-medium text-gray-600 last:text-right">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {WORKFLOWS.map((wf, i) => (
            <tr
              key={wf.id}
              style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}
              className="transition-colors hover:bg-white/[0.02]"
            >
              <td className="py-2.5 pr-3 font-mono text-gray-500">{wf.id}</td>
              <td className="py-2.5 pr-3 text-gray-300">{wf.desc}</td>
              <td className="py-2.5 pr-3">
                {wf.pii
                  ? <span className="text-red-400 font-semibold">Yes</span>
                  : <span className="text-gray-700">—</span>}
              </td>
              <td className="py-2.5 pr-3">
                <span className={`tag ${wf.status === 'EGRESS_REDACTED' ? 'tag-red' : 'tag-green'}`}>
                  {wf.status === 'EGRESS_REDACTED' ? '⊘ REDACTED' : '✓ ALLOWED'}
                </span>
              </td>
              <td className="py-2.5 text-right font-mono text-emerald-400">{wf.latency}</td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr style={{ borderTop: '1px solid rgba(255,255,255,0.06)' }}>
            <td colSpan={4} className="pt-3 text-gray-600 font-medium">Mean latency (10 workflows)</td>
            <td className="pt-3 text-right font-mono font-bold text-emerald-400">38.1 ms</td>
          </tr>
        </tfoot>
      </table>

      <div
        className="mt-5 flex items-center gap-2 p-3 rounded-xl text-xs"
        style={{ background: 'rgba(16,185,129,0.06)', border: '1px solid rgba(16,185,129,0.15)' }}
      >
        <span className="text-emerald-400 text-base">✓</span>
        <span className="text-emerald-400 font-medium">10 / 10 workflows — <strong>ZERO PII leakage</strong> across all egress gate tests</span>
      </div>
    </section>
  )
}
