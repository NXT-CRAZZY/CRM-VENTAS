import { motion } from 'motion/react'
import type { ReactNode } from 'react'
import { fadeUp, stagger } from '@/shared/lib/motion'
import { cn } from '@/shared/lib/utils'
import { Skeleton } from './skeleton'

export interface Column<T> {
  key: string
  header: ReactNode
  cell: (item: T) => ReactNode
  className?: string
}

/**
 * Lista responsiva: tabla en escritorio y tarjetas en celular
 * (nunca tablas imposibles de usar con el dedo).
 */
export function DataList<T>({
  items,
  columns,
  getKey,
  renderCard,
  onItemClick,
  loading,
  empty,
  footer,
}: {
  items: T[] | undefined
  columns: Column<T>[]
  getKey: (item: T) => string
  renderCard: (item: T) => ReactNode
  onItemClick?: (item: T) => void
  loading?: boolean
  empty?: ReactNode
  footer?: ReactNode
}) {
  if (loading) return <DataListSkeleton />
  if (!items?.length) return <>{empty}</>

  return (
    <>
      <div className="hidden overflow-x-auto md:block">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-zinc-100 text-left">
              {columns.map((c) => (
                <th
                  key={c.key}
                  className={cn('h-10 whitespace-nowrap px-4 text-xs font-medium uppercase tracking-wide text-zinc-500', c.className)}
                >
                  {c.header}
                </th>
              ))}
            </tr>
          </thead>
          <motion.tbody variants={stagger} initial="hidden" animate="show">
            {items.map((item) => (
              <motion.tr
                key={getKey(item)}
                variants={fadeUp}
                onClick={onItemClick ? () => onItemClick(item) : undefined}
                className={cn(
                  'border-b border-zinc-100 transition-colors last:border-0',
                  onItemClick && 'cursor-pointer hover:bg-zinc-50/80',
                )}
              >
                {columns.map((c) => (
                  <td key={c.key} className={cn('px-4 py-3 align-middle', c.className)}>
                    {c.cell(item)}
                  </td>
                ))}
              </motion.tr>
            ))}
          </motion.tbody>
        </table>
      </div>

      <motion.ul variants={stagger} initial="hidden" animate="show" className="divide-y divide-zinc-100 md:hidden">
        {items.map((item) => (
          <motion.li key={getKey(item)} variants={fadeUp}>
            <button
              type="button"
              disabled={!onItemClick}
              onClick={onItemClick ? () => onItemClick(item) : undefined}
              className="block w-full px-4 py-3.5 text-left transition-colors active:bg-zinc-50 disabled:cursor-default"
            >
              {renderCard(item)}
            </button>
          </motion.li>
        ))}
      </motion.ul>
      {footer}
    </>
  )
}

export function DataListSkeleton({ rows = 6 }: { rows?: number }) {
  return (
    <div className="divide-y divide-zinc-100" aria-busy="true" aria-label="Cargando">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex items-center gap-4 px-4 py-3.5">
          <Skeleton className="size-8 rounded-full" />
          <div className="flex-1 space-y-2">
            <Skeleton className="h-3.5 w-1/3" />
            <Skeleton className="h-3 w-1/4" />
          </div>
          <Skeleton className="hidden h-5 w-16 rounded-full sm:block" />
        </div>
      ))}
    </div>
  )
}
