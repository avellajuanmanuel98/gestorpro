import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import './index.css'
import App from './App.tsx'

// Initialize theme before first render to avoid flash
const storedTheme = (() => {
  try {
    const stored = localStorage.getItem('gestorpro-theme')
    if (stored) {
      const parsed = JSON.parse(stored)
      return parsed?.state?.theme as string | undefined
    }
  } catch { /* ignore */ }
  return undefined
})()

if (storedTheme === 'dark') {
  document.documentElement.classList.add('dark')
}

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 1000 * 60 * 5,
    },
  },
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <QueryClientProvider client={queryClient}>
        <App />
      </QueryClientProvider>
    </BrowserRouter>
  </StrictMode>,
)
