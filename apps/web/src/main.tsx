import './index.css'
import { QueryClientProvider } from '@tanstack/react-query'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { RouterProvider } from 'react-router'
import { Toaster } from 'sonner'
import { router } from '@/app/router'
import { authService } from '@/features/auth/api/auth-service'
import { queryClient } from '@/shared/api/query-client'
import { useThemeStore } from '@/shared/theme/theme-store'
import { TooltipProvider } from '@/shared/ui/menus'

void authService.bootstrap()

function ThemedToaster() {
  const theme = useThemeStore((s) => s.theme)
  return (
    <Toaster
      theme={theme}
      position="top-right"
      richColors
      closeButton
      toastOptions={{ className: 'font-sans', duration: 3500 }}
    />
  )
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <TooltipProvider delayDuration={300}>
        <RouterProvider router={router} />
        <ThemedToaster />
      </TooltipProvider>
    </QueryClientProvider>
  </StrictMode>,
)
