import { useCallback, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api/client";
import type {
  CommitInfo,
  HldDocument,
  ValidationItem,
} from "../types";
import TopBar from "../components/TopBar";
import StructurePanel from "../components/StructurePanel";
import HldEditor from "../components/HldEditor";
import ContextPanel from "../components/ContextPanel";

export default function HldEditorPage() {
  const { documentId } = useParams();
  const docId = Number(documentId);

  const [doc, setDoc] = useState<HldDocument | null>(null);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [commit, setCommit] = useState<CommitInfo | null>(null);
  const [validation, setValidation] = useState<ValidationItem[]>([]);
  const [status, setStatus] = useState<string>("");
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    const data = await api.getHld(docId);
    setDoc(data);
    setSelectedId((prev) => prev ?? data.sections[0]?.id ?? null);
    return data;
  }, [docId]);

  useEffect(() => {
    reload().catch((e) => setError((e as Error).message));
  }, [reload]);

  const runValidation = useCallback(async () => {
    const res = await api.validateDocument(docId);
    setValidation(res.results);
  }, [docId]);

  async function handleSave() {
    setStatus("Saving to Git…");
    setError(null);
    try {
      const info = await api.saveDocument(docId);
      setCommit(info);
      await reload();
      await runValidation();
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
    return <div className="p-6 text-sm text-red-700">{error}</div>;
  }
  if (!doc) {
    return <div className="p-6 text-sm text-slate-500">Loading HLD…</div>;
  }

  const selected =
    doc.sections.find((s) => s.id === selectedId) ?? doc.sections[0] ?? null;

  return (
    <div className="flex h-screen flex-col">
      <TopBar
        breadcrumb={doc.breadcrumb}
        headCommit={doc.head_commit}
        commit={commit}
        status={status}
        error={error}
        onSave={handleSave}
        onExport={handleExport}
      />
      <div className="flex min-h-0 flex-1">
        <StructurePanel
          document={doc}
          selectedId={selected?.id ?? null}
          validation={validation}
          onSelect={setSelectedId}
          onReload={reload}
        />
        <main className="min-w-0 flex-1 overflow-y-auto bg-white">
          {selected ? (
            <HldEditor
              key={selected.id}
              document={doc}
              section={selected}
              onReload={reload}
            />
          ) : (
            <div className="p-8 text-sm text-slate-500">
              No section selected.
            </div>
          )}
        </main>
        <ContextPanel
          validation={validation}
          onValidate={runValidation}
        />
      </div>
    </div>
  );
}
