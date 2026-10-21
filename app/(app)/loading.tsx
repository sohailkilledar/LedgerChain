import { Skeleton } from '@/components/ui/skeleton'

export default function AppLoading() {
  return (
    <div className="flex flex-col gap-6 lg:gap-8" aria-busy="true">
      <div className="flex flex-col gap-3">
        <Skeleton className="h-4 w-32" />
        <Skeleton className="h-8 w-56" />
        <Skeleton className="h-4 w-full max-w-lg" />
      </div>
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_22rem]">
        <Skeleton className="h-48 rounded-xl" />
        <Skeleton className="h-48 rounded-xl" />
      </div>
      <Skeleton className="h-64 rounded-xl" />
      <span className="sr-only" role="status">
        Loading
      </span>
    </div>
  )
}
