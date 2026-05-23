import { Navigate, Route, Routes } from "react-router-dom";
import DashboardPage from "./pages/DashboardPage";
import EnterprisePage from "./pages/EnterprisePage";
import HldEditorPage from "./pages/HldEditorPage";
import IncrementIntegrationsPage from "./pages/IncrementIntegrationsPage";
import IntegrationDocPage from "./pages/IntegrationDocPage";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<DashboardPage />} />
      <Route path="/enterprise" element={<EnterprisePage />} />
      <Route path="/hld/:documentId" element={<HldEditorPage />} />
      <Route
        path="/increment/:incrementId/integrations"
        element={<IncrementIntegrationsPage />}
      />
      <Route
        path="/integration-doc/:documentId"
        element={<IntegrationDocPage />}
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
