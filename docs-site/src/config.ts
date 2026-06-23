export interface Page {
  slug: string
  title: string
  file: string
}

export interface Module {
  id: string
  number: string
  title: string
  description: string
  pages: Page[]
}

type ModuleDef = Omit<Module, 'number'>

const moduleDefinitions: ModuleDef[] = [
  {
    id: 'setup',
    title: 'Environment Setup',
    description: 'Install the required tools, configure your AWS credentials, and start the agent web interface.',
    pages: [
      { slug: 'prerequisites', title: 'Prerequisites', file: '/docs/setup/01-prerequisites.md' },
      { slug: 'credentials', title: 'AWS Credentials', file: '/docs/setup/02-credentials.md' },
      { slug: 'start', title: 'Start the Agent', file: '/docs/setup/03-start.md' },
    ],
  },
  {
    id: 'explore',
    title: 'Explore the Agent',
    description: 'Open the chat interface and see what the agent can do. Can you find any flaws? Are any of the things you find exploitable?',
    pages: [
      { slug: 'explore', title: 'Explore', file: '/docs/00-explore/README.md' },
    ],
  },
  {
    id: 'module-01',
    title: 'Excessive Refund Authority',
    description: 'The agent can issue refunds — but does it validate the amount? Try to obtain a refund for more than you paid.',
    pages: [
      { slug: 'task', title: 'Task', file: '/docs/01-module/README.md' },
      { slug: 'solution', title: 'Solution', file: '/docs/01-module/SOLUTION.md' },
    ],
  },
  {
    id: 'module-02',
    title: 'Cross-Customer Data Access & Social Engineering',
    description: 'Customers are receiving unsolicited promotional emails. Find out how — and whether the agent can be used to send them.',
    pages: [
      { slug: 'task', title: 'Task', file: '/docs/02-module/README.md' },
      { slug: 'solution', title: 'Solution', file: '/docs/02-module/SOLUTION.md' },
    ],
  },
  {
    id: 'module-03',
    title: 'Excessive Discount Authority',
    description: 'The agent can apply discounts to orders. Try to apply an unreasonably large one.',
    pages: [
      { slug: 'task', title: 'Task', file: '/docs/03-module/README.md' },
      { slug: 'solution', title: 'Solution', file: '/docs/03-module/SOLUTION.md' },
    ],
  },
  {
    id: 'module-04',
    title: 'Fixing Cross-Customer Data Access',
    description: "Throughout the previous modules, other customers' data was never truly restricted. Learn how to fix this at the right layer.",
    pages: [
      { slug: 'overview', title: 'Overview', file: '/docs/04-module/README.md' },
      { slug: 'solution', title: 'Solution', file: '/docs/04-module/SOLUTION.md' },
    ],
  },
]

export const modules: Module[] = moduleDefinitions.map((m, i) => ({
  ...m,
  number: String(i).padStart(2, '0'),
}))

export function getNextPage(
  moduleId: string,
  pageSlug: string
): { moduleId: string; pageSlug: string; title: string } | null {
  const modIndex = modules.findIndex((m) => m.id === moduleId)
  if (modIndex === -1) return null
  const mod = modules[modIndex]
  const pageIndex = mod.pages.findIndex((p) => p.slug === pageSlug)

  if (pageIndex < mod.pages.length - 1) {
    const next = mod.pages[pageIndex + 1]
    return { moduleId, pageSlug: next.slug, title: next.title }
  }

  if (modIndex < modules.length - 1) {
    const nextMod = modules[modIndex + 1]
    return { moduleId: nextMod.id, pageSlug: nextMod.pages[0].slug, title: nextMod.title }
  }

  return null
}
