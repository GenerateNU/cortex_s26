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
          <img
            src="/logo.png"
            alt="Cortex"
            className="w-8 h-8 object-contain transition-opacity duration-200 group-hover:opacity-80"
          />
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
                  active ? 'text-white' : 'text-zinc-400 hover:text-white'
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
