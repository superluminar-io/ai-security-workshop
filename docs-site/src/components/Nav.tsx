import { Link } from 'react-router-dom'

export function Nav() {
  return (
    <nav className="nav">
      <Link to="/" className="nav-logo">
        <span className="nav-logo-mark">S</span>
        AI Security Workshop
      </Link>
    </nav>
  )
}
