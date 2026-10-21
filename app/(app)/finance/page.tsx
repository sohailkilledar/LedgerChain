import { FinanceWorkspace } from '@/components/finance/finance-workspace'
import { PageHeader } from '@/components/ledger/page-header'
import { getServerFinancePageData } from '@/lib/ledger/server-service'

export default async function FinancePage() {
  const { account, budgets, requests } = await getServerFinancePageData()
  return (
    <div className="flex flex-col gap-6 lg:gap-8">
      <PageHeader
        eyebrow="Finance operations"
        title="Requests, approvals, and budgets"
        description="Move approved spend through the existing payment engine and double-entry ledger. Budget utilization is derived from linked requests."
      />
      <FinanceWorkspace account={account} initialBudgets={budgets} initialRequests={requests} />
    </div>
  )
}
