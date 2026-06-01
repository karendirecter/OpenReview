import { Route, Routes } from "react-router-dom";

import { ReviewRunDetailPage } from "./pages/ReviewRunDetailPage";
import { ReviewRunListPage } from "./pages/ReviewRunListPage";

export function App() {
  return (
    <div className="shell">
      <header className="shell__header">
        <div>
          <p className="eyebrow">Local Review Console</p>
          <h1>GitHub PR Auto Review</h1>
        </div>
      </header>
      <main className="shell__content">
        <Routes>
          <Route path="/" element={<ReviewRunListPage />} />
          <Route path="/runs/:reviewRunId" element={<ReviewRunDetailPage />} />
        </Routes>
      </main>
    </div>
  );
}
