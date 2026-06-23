import { Navigate, useParams, Link } from 'react-router-dom'
import { modules, getNextPage } from '../config'
import { Sidebar } from '../components/Sidebar'
import { MarkdownView } from '../components/MarkdownView'

export function ModulePage() {
  const { moduleId, pageSlug } = useParams<{ moduleId: string; pageSlug?: string }>()
  const module = modules.find((m) => m.id === moduleId)

  if (!moduleId || !module) return <Navigate to="/" replace />

  if (!pageSlug) {
    return <Navigate to={`/module/${moduleId}/${module.pages[0].slug}`} replace />
  }

  const page = module.pages.find((p) => p.slug === pageSlug)
  if (!page) return <Navigate to={`/module/${moduleId}`} replace />

  const next = getNextPage(moduleId, pageSlug)

  return (
    <div className="module-page">
      <Sidebar />
      <main className="module-page__content">
        <MarkdownView file={page.file} />
        {next && (
          <div className="page-nav">
            <Link to={`/module/${next.moduleId}/${next.pageSlug}`} className="btn-next">
              {next.title}
            </Link>
          </div>
        )}
      </main>
    </div>
  )
}
