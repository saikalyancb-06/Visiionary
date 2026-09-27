export default function Header() {
  const scrollTo = (id) => {
    const el = document.getElementById(id)
    if (el) {
      el.scrollIntoView({ behavior: 'smooth' })
    }
  }

  return (
    <header className="fixed top-0 left-0 right-0 z-50 flex justify-center pt-3 px-4 pointer-events-none">
      <nav className="pointer-events-auto flex items-center gap-1.5 sm:gap-2 px-3.5 py-1.5 shadow-2xl backdrop-blur-xl bg-[#090b17]/90 border border-white/10 rounded-full">
        {/* Brand */}
        <div 
          onClick={() => scrollTo('hero')}
          className="flex items-center gap-2 cursor-pointer mr-1"
        >
          <div className="w-6 h-6 rounded-full bg-gradient-to-tr from-cyan-400 to-blue-600 flex items-center justify-center shadow-[0_0_10px_rgba(59,130,246,0.6)]">
            <span className="text-[11px] font-black text-white">V</span>
          </div>
          <span className="text-xs font-bold text-white tracking-tight hidden sm:inline">Visiionary</span>
        </div>

        {/* Clean, distinct navigation links */}
        <button
          onClick={() => scrollTo('demo')}
          className="px-2.5 py-1 text-[11px] font-medium text-gray-300 hover:text-white rounded-full transition-colors cursor-pointer"
        >
          Live Demo
        </button>

        <button
          onClick={() => scrollTo('datasets')}
          className="px-2.5 py-1 text-[11px] font-medium text-gray-300 hover:text-white rounded-full transition-colors cursor-pointer hidden md:inline-block"
        >
          169 GB Datasets
        </button>

        <button
          onClick={() => scrollTo('features')}
          className="px-2.5 py-1 text-[11px] font-medium text-gray-300 hover:text-white rounded-full transition-colors cursor-pointer"
        >
          Capabilities
        </button>

        <button
          onClick={() => scrollTo('benchmark')}
          className="px-2.5 py-1 text-[11px] font-medium text-gray-300 hover:text-white rounded-full transition-colors cursor-pointer"
        >
          10-Workflow Tests
        </button>

        {/* Primary Action Button */}
        <button
          onClick={() => scrollTo('demo')}
          className="ml-1 px-3.5 py-1 rounded-full text-xs font-semibold text-white bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 shadow-[0_0_12px_rgba(59,130,246,0.5)] transition-all cursor-pointer"
        >
          Test Scanner ↓
        </button>
      </nav>
    </header>
  )
}
