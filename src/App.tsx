import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Toaster } from "sonner";
import Header from "@/components/layout/Header";
import UploadPage from "@/pages/UploadPage";
import FactsPage from "@/pages/FactsPage";
import RelationshipsPage from "@/pages/RelationshipsPage";

function NotFound() {
  return (
    <div className="page-container py-20 text-center">
      <p className="text-4xl font-bold text-foreground">404</p>
      <p className="text-muted-foreground mt-2">Page not found.</p>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-background flex flex-col">
        <Header />
        <main className="flex-1 py-2">
          <Routes>
            <Route path="/" element={<UploadPage />} />
            <Route path="/facts" element={<FactsPage />} />
            <Route path="/relationships" element={<RelationshipsPage />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </main>
        <Toaster richColors position="bottom-right" />
      </div>
    </BrowserRouter>
  );
}
