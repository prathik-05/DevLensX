import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import './index.css'
import { AppRoutes } from './App'
import { WorkspaceProvider } from './workspaceContext'
import { WikiProvider } from './wikiContext'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <WorkspaceProvider>
        <WikiProvider>
          <AppRoutes />
        </WikiProvider>
      </WorkspaceProvider>
    </BrowserRouter>
  </StrictMode>,
)