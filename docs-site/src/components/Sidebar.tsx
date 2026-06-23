import { Link, NavLink, useParams } from 'react-router-dom'
import { modules } from '../config'

export function Sidebar() {
  const { moduleId } = useParams<{ moduleId: string }>()

  const pageLinkClass = ({ isActive }: { isActive: boolean }) =>
    `sidebar__item${isActive ? ' sidebar__item--active' : ''}`

  return (
    <aside className="sidebar">
      {modules.map((m) => {
        const isExpanded = m.id === moduleId
        return (
          <div key={m.id} className="sidebar__module">
            <Link
              to={`/module/${m.id}`}
              className={`sidebar__module-header${isExpanded ? ' sidebar__module-header--active' : ''}`}
            >
              <span className="sidebar__module-number">
                {m.id === 'setup' ? 'Setup' : `Module ${m.number}`}
              </span>
              <span className="sidebar__module-title">{m.title}</span>
            </Link>
            {isExpanded && (
              <div className="sidebar__pages">
                {m.pages.map((p) => (
                  <NavLink
                    key={p.slug}
                    to={`/module/${m.id}/${p.slug}`}
                    className={pageLinkClass}
                  >
                    {p.title}
                  </NavLink>
                ))}
              </div>
            )}
          </div>
        )
      })}
    </aside>
  )
}
