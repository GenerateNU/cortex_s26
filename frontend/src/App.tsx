import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import SearchPage from './pages/SearchPage'
import UploadPage from './pages/UploadPage'
import DocumentsPage from './pages/DocumentsPage'
import DocumentDetailPage from './pages/DocumentDetailPage'
import GraphPage from './pages/GraphPage'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<SearchPage />} />
        <Route path="/upload" element={<UploadPage />} />
        <Route path="/documents" element={<DocumentsPage />} />
        <Route path="/documents/:id" element={<DocumentDetailPage />} />
        <Route path="/graph" element={<GraphPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
