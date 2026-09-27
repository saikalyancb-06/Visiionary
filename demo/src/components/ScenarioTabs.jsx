export default function ScenarioTabs({ scenarios, active, onSelect }) {
  return (
    <div className="w-full flex items-center gap-2 overflow-x-auto py-1.5 px-0.5 no-scrollbar flex-nowrap">
      {scenarios.map(s => {
        const isActive = active.id === s.id
        const isRedacted = s.egress === 'EGRESS_REDACTED'
        return (
          <button
            key={s.id}
            onClick={() => onSelect(s)}
            className={`
              flex items-center gap-2.5 px-4 py-2 rounded-xl text-xs font-semibold transition-all duration-200 cursor-pointer flex-shrink-0 whitespace-nowrap
              ${isActive
                ? 'bg-gradient-to-r from-blue-600 via-indigo-600 to-violet-600 text-white shadow-[0_0_22px_rgba(99,102,241,0.5)] border border-cyan-400/50 scale-[1.02]'
                : 'bg-white/[0.035] hover:bg-white/[0.08] text-gray-300 hover:text-white border border-white/[0.08] hover:border-white/20'}
            `}
          >
            <span className="text-sm">{s.icon}</span>
            <span className="tracking-tight">{s.label}</span>
            
            {/* Status chip */}
            <span
              className={`text-[9px] px-1.5 py-0.5 rounded-full font-mono font-medium flex items-center gap-1 ${
                isRedacted
                  ? 'bg-red-500/20 text-red-300 border border-red-500/30'
                  : 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
              }`}
            >
              <span className={`w-1 h-1 rounded-full ${isRedacted ? 'bg-red-400' : 'bg-emerald-400'}`} />
              <span>{isRedacted ? 'Redacted' : 'Allowed'}</span>
            </span>
          </button>
        )
      })}
    </div>
  )
}
