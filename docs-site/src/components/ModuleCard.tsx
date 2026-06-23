import { Link } from 'react-router-dom'
import type { Module } from '../config'

export function ModuleCard({ module }: { module: Module }) {
  return (
    <Link to={`/module/${module.id}`} className="module-card__link">
      <div className="module-card">
        <div className="module-card__number-col">
          <span className="module-card__number">{module.number}</span>
        </div>
        <div className="module-card__body">
          <div className="module-card__title">{module.title}</div>
          <p className="module-card__desc">{module.description}</p>
          <div className="module-card__pages">
            {module.pages.map((p) => (
              <span key={p.slug} className="page-chip">{p.title}</span>
            ))}
          </div>
        </div>
      </div>
    </Link>
  )
}
