import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../api/client";
import type { CommitInfo, HldDocument, Integration } from "../types";
import AppHeader from "../components/AppHeader";
import DocumentHeader from "../components/DocumentHeader";
import StructurePanel from "../components/StructurePanel";
import HldEditor from "../components/HldEditor";
import IntegrationPanel from "../components/IntegrationPanel";
import EditorFooter from "../components/EditorFooter";

export default function IntegrationDocPage() {
  const { documentId } = useParams();
  const navigate = useNavigate();
  const docId = Number(documentId);

  const [doc, setDoc] = useState<HldDocument | null>(null);
  const [integration, setIntegration] = useState<Integration | null>(null);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [commit, setCommit] = useState<CommitInfo | null>(null);
  const [status, setStatus] = useState<string>("");
  const [error, setError] = useState<string | null>(null);

  const reloadDocument = useCallback(async () => {
    const data = await api.getDocument(docId);
    setDoc(data);
    setSelectedId((prev) => prev ?? data.sections[0]?.id ?? null);
    return data;
  }, [docId]);

  const reloadIntegration = useCallback(async (): Promise<Integration> => {
    const data = await api.getDocument(docId);
    setDoc(data);
    if (!data.integration_ref) {
      throw new Error("Document is not an integration document");
    }
    const fresh = await api.getIntegration(data.integration_ref.id);
    setIntegration(fresh);
    return fresh;
  }, [docId]);

  useEffect(() => {
    (async () => {
      try {
        const data = await reloadDocument();
        if (data.integration_ref) {
          setIntegration(await api.getIntegration(data.integration_ref.id));
        } else {
          setError("This document is not an integration document.");
        }
      } catch (e) {
        setError((e as Error).message);
      }
    })();
  }, [reloadDocument]);

  async function handleSave() {
    setStatus("Saving to Git…");
    setError(null);
    try {
      const info = await api.saveDocument(docId);
      setCommit(info);
      await reloadDocument();
      setStatus(`Saved · commit ${info.short_hash}`);
    } catch (e) {
      setError((e as Error).message);
      setStatus("");
    }
  }

  async function handleExport(format: "docx" | "pdf") {
    setStatus(`Exporting ${format.toUpperCase()}…`);
    setError(null);
    try {
      const job = await api.exportDocument(docId, format);
      if (job.status === "completed") {
        window.open(api.exportDownloadUrl(job.id), "_blank");
        setStatus(`${format.toUpperCase()} export ready`);
      } else {
        setError(job.error || "Export failed");
        setStatus("");
      }
    } catch (e) {
      setError((e as Error).message);
      setStatus("");
    }
  }

  if (error && !doc) {
    return <div className="p-6 text-sm text-rose-700">{error}</div>;
  }
  if (!doc || !integration) {
    return (
      <div className="p-6 text-sm text-slate-500">
        Loading integration document…
      </div>
    );
  }

  const selected =
    doc.sections.find((s) => s.id === selectedId) ?? doc.sections[0] ?? null;

  return (
    <div className="flex h-screen flex-col bg-slate-100">
      <AppHeader
        breadcrumb={doc.breadcrumb}
        onSave={handleSave}
        onExport={handleExport}
        onOpenIntegrations={() =>
          navigate(`/increment/${doc.increment_id}/integrations`)
        }
      />
      <DocumentHeader document={doc} />
      <div className="flex min-h-0 flex-1">
        <StructurePanel
          document={doc}
          selectedId={selected?.id ?? null}
          validation={[]}
          onSelect={setSelectedId}
          onReload={reloadDocument}
        />
        <main className="scroll-thin min-w-0 flex-1 overflow-y-auto">
          {selected ? (
            <HldEditor
              key={selected.id}
              document={doc}
              section={selected}
              onReload={reloadDocument}
            />
          ) : (
            <div className="p-8 text-sm text-slate-500">
              No section selected.
            </div>
          )}
        </main>
        <aside className="flex w-96 flex-col border-l border-slate-200 bg-panel">
          <IntegrationPanel
            integration={integration}
            onReload={reloadIntegration}
          />
        </aside>
      </div>
      <EditorFooter
        status={status}
        error={error}
        commit={commit}
        headCommit={doc.head_commit}
      />
    </div>
  );
}
