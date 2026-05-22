import { Navigate, Route, Routes } from "react-router-dom";
import HomePage from "./pages/HomePage";
import HldEditorPage from "./pages/HldEditorPage";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/hld/:documentId" element={<HldEditorPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
