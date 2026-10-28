import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Link, Route, Routes } from "react-router";

import "./index.css";
import AnalysisPage from "./pages/AnalysisPage";
import LinkPage from "./pages/LinkPage";
import ShortPage from "./pages/ShortPage";
import TemplatePage from "./pages/TemplatePage";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <header className="border-b border-zinc-200 bg-white">
        <div className="mx-auto max-w-5xl px-4 py-3">
          <Link to="/" className="font-bold">
            쇼츠 편집 툴
          </Link>
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-4 py-8">
        <Routes>
          <Route path="/" element={<TemplatePage />} />
          <Route path="/new" element={<LinkPage />} />
          <Route path="/analyses/:id" element={<AnalysisPage />} />
          <Route path="/shorts/:id" element={<ShortPage />} />
        </Routes>
      </main>
    </BrowserRouter>
  </StrictMode>,
);
