import { modules } from '../config'
import { ModuleCard } from '../components/ModuleCard'

export function HomePage() {
  return (
    <div className="home">
      <div className="home__hero">
        <div className="hero__label">superluminar workshops</div>
        <h1 className="hero__title">AI Security Workshop</h1>
        <p className="hero__subtitle">
          Hands-on exercises for understanding and fixing vulnerabilities in AI agent systems.
        </p>
      </div>
      <div className="home__modules">
        {modules.map((m) => (
          <ModuleCard key={m.id} module={m} />
        ))}
      </div>
    </div>
  )
}
