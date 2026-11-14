import { useQuery } from '@tanstack/react-query'
import { Search, X } from 'lucide-react'
import { useState } from 'react'
import { useDebounce } from '@/shared/hooks/use-debounce'
import { Button } from '@/shared/ui/button'
import { Input } from '@/shared/ui/input'

import { prospectsKeys, prospectsService, type Prospect } from '../api/prospects-service'

export interface PickedProspect {
  id: string
  display_name: string
  document_number: string | null
}

/** Buscador de prospecto (por nombre o documento). Devuelve el prospecto elegido con `onChange`. */
export function ProspectPicker({
  value,
  onChange,
  id,
  invalid,
}: {
  value: PickedProspect | null
  onChange: (prospect: PickedProspect | null) => void
  id?: string
  invalid?: boolean
}) {
  const [search, setSearch] = useState('')
  const q = useDebounce(search.trim())

  const resultsQ = useQuery({
    queryKey: prospectsKeys.list({ q, page: 1 }),
    queryFn: () => prospectsService.list({ q, page: 1 }),
    enabled: !value && q.length >= 2,
  })

  if (value) {
    return (
      <div className="flex items-center justify-between gap-2 rounded-md border border-zinc-200 bg-zinc-50 px-3 py-2 text-sm">
        <div className="min-w-0">
          <p className="truncate font-medium text-zinc-900">{value.display_name}</p>
          {value.document_number && <p className="text-xs text-muted-foreground">{value.document_number}</p>}
        </div>
        <Button type="button" variant="ghost" size="icon-sm" aria-label="Cambiar prospecto" onClick={() => onChange(null)}>
          <X className="size-4" />
        </Button>
      </div>
    )
  }

  const items: Prospect[] = resultsQ.data?.items ?? []
  return (
    <div className="space-y-2">
      <div className="relative">
        <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-zinc-400" />
        <Input
          id={id}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Buscar por nombre o documento…"
          className="pl-9"
          aria-invalid={invalid}
          autoComplete="off"
        />
      </div>
      {q.length >= 2 && (
        <div className="max-h-56 overflow-y-auto rounded-md border border-zinc-200 bg-card">
          {resultsQ.isLoading ? (
            <p className="p-3 text-sm text-muted-foreground">Buscando…</p>
          ) : items.length === 0 ? (
            <p className="p-3 text-sm text-muted-foreground">Sin resultados.</p>
          ) : (
            items.map((p) => (
              <button
                key={p.id}
                type="button"
                className="block w-full px-3 py-2 text-left text-sm hover:bg-brand-50"
                onClick={() => onChange({ id: p.id, display_name: p.display_name, document_number: p.document_number })}
              >
                <span className="font-medium text-zinc-900">{p.display_name}</span>
                {p.document_number && <span className="ml-2 text-xs text-muted-foreground">{p.document_number}</span>}
              </button>
            ))
          )}
        </div>
      )}
    </div>
  )
}
