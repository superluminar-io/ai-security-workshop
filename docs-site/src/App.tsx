import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { Nav } from './components/Nav'
import { HomePage } from './pages/HomePage'
import { ModulePage } from './pages/ModulePage'

export function App() {
  return (
    <BrowserRouter>
      <div className="app-shell">
        <Nav />
        <div className="app-content">
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/module/:moduleId/:pageSlug" element={<ModulePage />} />
            <Route path="/module/:moduleId" element={<ModulePage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </div>
      </div>
    </BrowserRouter>
  )
}
