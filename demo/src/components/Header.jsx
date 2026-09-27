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
          <div className="w-6 h-6 flex items-center justify-center text-[#0084ff] drop-shadow-[0_0_8px_rgba(0,132,255,0.7)]">
            <svg viewBox="0 0 64 64" fill="none" className="w-full h-full">
              <path d="M 8 22 V 12 C 8 9.8 9.8 8 12 8 H 22" stroke="#0084FF" strokeWidth="5" strokeLinecap="round" strokeLinejoin="round"/>
              <path d="M 42 8 H 52 C 54.2 8 56 9.8 56 12 V 22" stroke="#0084FF" strokeWidth="5" strokeLinecap="round" strokeLinejoin="round"/>
              <path d="M 56 42 V 52 C 56 54.2 54.2 56 52 56 H 42" stroke="#0084FF" strokeWidth="5" strokeLinecap="round" strokeLinejoin="round"/>
              <path d="M 22 56 H 12 C 9.8 56 8 54.2 8 52 V 42" stroke="#0084FF" strokeWidth="5" strokeLinecap="round" strokeLinejoin="round"/>
              <path d="M 14 32 C 20 20 44 20 50 32 C 44 44 20 44 14 32 Z" fill="#0084FF"/>
              <circle cx="32" cy="32" r="7.5" fill="#FFFFFF"/>
              <circle cx="32" cy="32" r="3.8" fill="#0084FF"/>
            </svg>
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
