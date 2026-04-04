import { Link, useLocation } from 'react-router-dom'

const NAV_LINKS = [
  { to: '/', label: 'Search', exact: true },
  { to: '/upload', label: 'Upload', exact: false },
  { to: '/documents', label: 'Documents', exact: false },
  { to: '/graph', label: 'Graph', exact: false },
]

export default function Navbar() {
  const location = useLocation()

  function isActive(to: string, exact: boolean) {
    if (exact) return location.pathname === to
    return location.pathname.startsWith(to)
  }

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-black/80 backdrop-blur-md border-b border-white/[0.06]">
      <div className="flex items-center justify-between px-6 py-4 md:px-10 max-w-7xl mx-auto">
        {/* Logo */}
        <Link to="/" className="flex items-center gap-2.5 group flex-shrink-0">
          <div className="relative flex items-center justify-center w-8 h-8 rounded-lg border border-violet-500/40 bg-violet-600/20 transition-all duration-300 group-hover:border-violet-500/60 group-hover:bg-violet-600/30">
            {/* Graph-node SVG icon */}
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" className="text-violet-400">
              <circle cx="8" cy="8" r="2.5" fill="currentColor" />
              <circle cx="3" cy="4" r="1.5" fill="currentColor" opacity="0.6" />
              <circle cx="13" cy="4" r="1.5" fill="currentColor" opacity="0.6" />
              <circle cx="3" cy="12" r="1.5" fill="currentColor" opacity="0.6" />
              <circle cx="13" cy="12" r="1.5" fill="currentColor" opacity="0.6" />
              <line x1="8" y1="5.5" x2="3" y2="4" stroke="currentColor" strokeWidth="0.8" opacity="0.5" />
              <line x1="8" y1="5.5" x2="13" y2="4" stroke="currentColor" strokeWidth="0.8" opacity="0.5" />
              <line x1="8" y1="10.5" x2="3" y2="12" stroke="currentColor" strokeWidth="0.8" opacity="0.5" />
              <line x1="8" y1="10.5" x2="13" y2="12" stroke="currentColor" strokeWidth="0.8" opacity="0.5" />
            </svg>
          </div>
          <span className="text-lg font-semibold tracking-tight text-white transition-colors duration-200 group-hover:text-violet-200">
            Cortex
          </span>
        </Link>

        {/* Nav links */}
        <div className="flex items-center gap-0.5">
          {NAV_LINKS.map(({ to, label, exact }) => {
            const active = isActive(to, exact)
            return (
              <Link
                key={to}
                to={to}
                className={`relative px-4 py-2 text-sm font-medium transition-colors duration-200 ${
                  active
                    ? 'text-white'
                    : 'text-zinc-400 hover:text-white'
                }`}
              >
                {label}
                {active && (
                  <span className="absolute bottom-0 left-3 right-3 h-px bg-violet-500 rounded-full" />
                )}
              </Link>
            )
          })}
        </div>
      </div>
    </nav>
  )
}
