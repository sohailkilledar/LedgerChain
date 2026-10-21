import { Card } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'

export default function ActivityLoading() {
  return (
    <div className="flex flex-col gap-6 lg:gap-8" aria-busy="true">
      <div className="flex flex-col gap-3">
        <Skeleton className="h-4 w-32" />
        <Skeleton className="h-8 w-40" />
        <Skeleton className="h-4 w-full max-w-lg" />
      </div>
      <div className="flex flex-col gap-3 md:flex-row md:justify-between">
        <Skeleton className="h-9 w-full max-w-md" />
        <Skeleton className="h-9 w-full md:w-48" />
      </div>
      <Card className="gap-0 divide-y py-0">
        {[0, 1, 2, 3, 4].map((i) => (
          <div key={i} className="flex items-center gap-4 px-5 py-4">
            <Skeleton className="size-9 rounded-lg" />
            <div className="flex flex-1 flex-col gap-2">
              <Skeleton className="h-4 w-1/2" />
              <Skeleton className="h-3 w-1/3" />
            </div>
            <Skeleton className="hidden h-5 w-24 rounded-full sm:block" />
          </div>
        ))}
      </Card>
      <span className="sr-only" role="status">
        Loading activity
      </span>
    </div>
  )
}
