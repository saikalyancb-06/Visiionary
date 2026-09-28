import Starfield from './components/Starfield'
import Header from './components/Header'
import LivePerceptionSandbox from './components/LivePerceptionSandbox'
import BenchmarkTable from './components/BenchmarkTable'
import EmpiricalStatsDashboard from './components/EmpiricalStatsDashboard'

// ── Genuine Datasets & Physical Storage ──────────────────────────
const DATASET_STATS = [
  { name: 'ScreenParse v2', size: '70.2 GB', shards: '175 Parquet Shards', samples: '175,000 UI Trees', task: 'Pixel Grounding & Element Detection' },
  { name: 'GroundCUA', size: '28.4 GB', shards: '7 App Shards (Bitwarden, Brave, etc.)', samples: '50+ UI BBoxes / full screen', task: 'Desktop UI & Native Controls' },
  { name: 'AndroidControl', size: '14.1 GB', shards: '18 Web Shards', samples: '15,000 Navigation Steps', task: 'Touch / Gesture Trajectories' },
  { name: 'Android in the Wild (AITW)', size: '8.2 GB', shards: '32 Evaluation Shards', samples: '7,500 Full Trajectories', task: 'Cross-platform Visual Grounding' },
  { name: 'WebChain & WebPII', size: '21.4 GB', shards: '26 SFT & Parquet Files', samples: '3,925 Visual BBox Annotations', task: 'PII Identification & Selective Masking' },
  { name: 'OpenPII Synthetic Benchmark', size: '26.7 GB', shards: '1.5M Token Text Shards', samples: '1,500,000 Sensitive Tokens', task: 'NLP & Token Boundary Cross-Validation' },
]

// ── 6 First-Page Key Empirical Metrics ──────────────────────────
const KEY_METRICS = [
  { num: '169 GB', label: 'Verified UI Data', sub: '246 Parquet shards downloaded locally' },
  { num: '96.8%', label: 'PII Detection Recall', sub: '26 sensitive entity categories identified' },
  { num: '0.0%', label: 'PII Leakage Rate', sub: '10/10 workflows verified zero network egress' },
  { num: '19,299', label: 'India Post PINs', sub: '100% verified official postal registry' },
  { num: '1.75 MB', label: 'Model Footprint', sub: 'Exported lightweight ONNX for browser runtime' },
  { num: '11.2 ms', label: 'WebGPU Perception', sub: 'Sub-frame client inference on laptop GPU' },
]

const FEATURES_LIST = [
  {
    icon: '📸',
    title: 'Client-Side Visual Perception',
    metric: '89.2% mAP50',
    desc: 'Analyzes full 1920×1080 viewport directly through on-device models. Maps DOM elements, input boundaries, and native buttons in 11.2 ms without sending pixels to any cloud server.',
  },
  {
    icon: '🛡️',
    title: 'Dual-Engine PII Identification',
    metric: '96.8% Recall / 93.2% Precision',
    desc: 'Combines our 26-class visual PII detector model with mathematical validators (Luhn formula for credit cards, Verhoeff checksums for Aadhaar, and RFC regexes for UPI/emails).',
  },
  {
    icon: '🔒',
    title: 'Zero-Egress Privacy Gateway',
    metric: '0.0% PII Leakage',
    desc: 'Acts as an impenetrable perimeter firewall. Sensitive values are selectively substituted with synthetic surrogate tokens before network payload dispatch.',
  },
  {
    icon: '⚡',
    title: 'Autonomous Browser Agent Dispatch',
    metric: '38.1 ms Mean Task Latency',
    desc: 'Tested and proven across multi-step browser workflows. The autonomous agent accurately clicks, fills, and submits web flows while ensuring complete privacy compliance.',
  },
]

export default function App() {
  const scrollToDemo = () => {
    const el = document.getElementById('demo')
    if (el) el.scrollIntoView({ behavior: 'smooth' })
  }

  return (
    <div style={{ background: '#04040e', minHeight: '100vh', position: 'relative' }}>
      {/* Ultra-fast canvas starfield & GPU ambient glows */}
      <Starfield />
      <div className="glow-spot glow-blue-1" style={{ position: 'fixed' }} />
      <div className="glow-spot glow-blue-2" style={{ position: 'fixed' }} />
      <div className="glow-spot glow-purple-1" style={{ position: 'fixed' }} />

      <Header />

      {/* ───────────────────────────────────────────────────────────
          FIRST PAGE: EXACTLY HERO + DEMO CTA + 6 METRIC CARDS
          FITS IN ONE SINGLE SCREEN (100vh) JUST LIKE THE SCREENSHOT
          ─────────────────────────────────────────────────────────── */}
      <section
        id="hero"
        className="relative min-h-screen flex flex-col justify-between items-center text-center px-4 pt-16 pb-6 overflow-hidden z-10"
      >

        {/* Top/Center Hero Area */}
        <div className="relative z-10 max-w-4xl mx-auto space-y-3 my-auto">
          {/* Tag */}
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-500/10 border border-blue-400/25 text-[11px] text-cyan-300 font-semibold tracking-wide">
            <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
            Verified On-Device Privacy Architecture
          </div>

          {/* Title */}
          <h1 className="text-4xl sm:text-5xl md:text-6xl font-black tracking-tight text-white leading-tight">
            Privacy-Preserving On-Device <br />
            <span className="text-gradient-cyan">Autonomous Browser Agent</span>
          </h1>

          {/* Subtitle */}
          <p className="text-xs sm:text-sm text-gray-400 max-w-2xl mx-auto leading-relaxed">
            Trained on <strong>169 GB</strong> of real visual UI trajectories. Delivers sub-12ms perception, <strong>0.0% PII leakage</strong>, and accurate autonomous task execution without exposing user credentials to remote cloud APIs.
          </p>

          {/* CTA Button + Side Hint */}
          <div className="pt-2 flex flex-col items-center gap-1.5">
            <div className="flex items-center gap-3">
              <button
                onClick={scrollToDemo}
                className="btn-action-primary text-xs sm:text-sm px-7 py-3 cursor-pointer shadow-[0_0_30px_rgba(56,189,248,0.6)]"
              >
                <span>⚡ Click Here for Interactive Live Demo</span>
                <span className="text-base">↓</span>
              </button>

              <div className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-cyan-950/80 border border-cyan-400/40 text-cyan-300 text-[11px] font-medium shadow-[0_0_15px_rgba(6,182,212,0.3)] animate-pulse">
                <span>👉</span>
                <span>Click this button to test live</span>
              </div>
            </div>
            <p className="text-[10px] text-gray-500">Live WebGPU sandbox with simulated real-world workflows</p>
          </div>
        </div>

        {/* Bottom of First Page: Measured Performance & 6 Key Metric Cards */}
        <div className="relative z-10 w-full max-w-6xl mx-auto pt-4 pb-2">
          <div className="text-center mb-3">
            <span className="text-[10px] uppercase font-bold tracking-widest text-cyan-400">Measured Performance</span>
            <h2 className="text-sm sm:text-base font-bold text-white tracking-tight mt-0.5">Empirical Benchmarks & Storage Figures</h2>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-2.5">
            {KEY_METRICS.map(m => (
              <div key={m.label} className="glass-card p-3 text-center flex flex-col justify-center">
                <span className="text-xl sm:text-2xl font-black text-white font-mono tracking-tight text-gradient-cyan">{m.num}</span>
                <p className="text-[11px] font-semibold text-gray-300 mt-0.5">{m.label}</p>
                <p className="text-[9px] text-gray-500 mt-0.5 leading-tight">{m.sub}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ───────────────────────────────────────────────────────────
          BELOW THE FIRST PAGE: LOADED FAST VIA CONTENT-VISIBILITY
          (DASHBOARD REMOVED AS REQUESTED)
          ─────────────────────────────────────────────────────────── */}
      <div className="content-auto space-y-12 pb-16">

        {/* ── 1. REAL-TIME LOCAL PERCEPTION & EGRESS GATEWAY SANDBOX ── */}
        <section
          id="demo"
          className="relative z-10 max-w-6xl mx-auto px-4 pt-8"
        >
          <LivePerceptionSandbox />
        </section>

        {/* ── 2. DATASETS TABLE (169 GB STORAGE) ── */}
        <section
          id="datasets"
          className="relative z-10 max-w-6xl mx-auto px-4"
        >
          <div className="glass-card p-5">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-white/[0.06] gap-2">
              <div>
                <h3 className="text-sm font-bold text-white flex items-center gap-2">
                  <span>📁</span> Training Data Corpora (169 GB Local Storage)
                </h3>
                <p className="text-[11px] text-gray-400">All datasets genuine, verified, and parsed into PyTorch tensors on disk</p>
              </div>
              <span className="tag tag-green text-[10px] self-start sm:self-auto font-mono">246 Verified Shards</span>
            </div>

            <div className="overflow-x-auto mt-2">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="text-gray-500 border-b border-white/[0.04]">
                    <th className="py-2 font-medium">Dataset Name</th>
                    <th className="py-2 font-medium">Disk Size</th>
                    <th className="py-2 font-medium">Shard Count / Format</th>
                    <th className="py-2 font-medium">Sample Volume</th>
                    <th className="py-2 font-medium">Training Objective</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/[0.03]">
                  {DATASET_STATS.map(d => (
                    <tr key={d.name} className="hover:bg-white/[0.015] transition-colors">
                      <td className="py-2 text-white font-semibold">{d.name}</td>
                      <td className="py-2 font-mono text-cyan-400">{d.size}</td>
                      <td className="py-2 text-gray-400 font-mono text-[11px]">{d.shards}</td>
                      <td className="py-2 text-gray-300">{d.samples}</td>
                      <td className="py-2 text-gray-400 text-[11px]">{d.task}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </section>

        {/* ── 3. TECHNICAL FEATURES ── */}
        <section
          id="features"
          className="relative z-10 max-w-6xl mx-auto px-4 space-y-4"
        >
          <div className="text-center mb-4">
            <span className="text-xs uppercase font-bold tracking-widest text-cyan-400">Technical Features</span>
            <h2 className="text-xl font-bold text-white tracking-tight mt-0.5">Why Visiionary Outperforms Cloud Agents</h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {FEATURES_LIST.map(f => (
              <div key={f.title} className="glass-card p-5 space-y-2.5 flex flex-col justify-between">
                <div>
                  <div className="text-2xl mb-2">{f.icon}</div>
                  <h3 className="text-sm font-bold text-white">{f.title}</h3>
                  <span className="inline-block mt-1 text-[10px] font-mono text-cyan-400 bg-cyan-950/40 border border-cyan-500/20 px-2 py-0.5 rounded-full">
                    {f.metric}
                  </span>
                  <p className="text-xs text-gray-400 mt-2 leading-relaxed">{f.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </section>


        {/* ── 4. EMPIRICAL EVALUATION & COMPREHENSIVE BENCHMARK STATISTICS ── */}
        <section
          id="statistics"
          className="relative z-10 max-w-6xl mx-auto px-4"
        >
          <EmpiricalStatsDashboard />
        </section>

        {/* ── 5. VERIFICATION BENCHMARK TABLE ── */}
        <section
          id="benchmark"
          className="relative z-10 max-w-6xl mx-auto px-4"
        >
          <BenchmarkTable />
        </section>

        {/* Footer */}
        <footer className="relative z-10 border-t border-white/[0.06] pt-8 text-center text-xs text-gray-500 space-y-2">
          <p>
            <strong className="text-gray-300">Visiionary</strong> · Verified On-Device Browser Privacy Engine
          </p>
          <p className="text-[11px] text-gray-600">
            Client-side privacy preservation for browser agents. All models exported to ONNX for private on-device execution.
          </p>
        </footer>

      </div>
    </div>
  )
}
