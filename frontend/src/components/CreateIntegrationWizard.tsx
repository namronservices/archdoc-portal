import { useState } from "react";
import { X } from "lucide-react";
import { api } from "../api/client";
import type { IntegrationType } from "../types";
import { Button } from "./ui";

const TYPES: { value: IntegrationType; label: string; priority: string }[] = [
  { value: "GRPC", label: "gRPC", priority: "highest" },
  { value: "KAFKA", label: "Kafka", priority: "highest" },
  { value: "MQ", label: "MQ", priority: "high" },
  { value: "SOAP", label: "Legacy SOAP", priority: "high" },
  { value: "REST", label: "REST", priority: "medium" },
  { value: "FILE", label: "File transfer", priority: "medium" },
  { value: "BATCH", label: "Batch", priority: "medium" },
];

interface Props {
  incrementId: number;
  onCreated: () => void;
  onCancel: () => void;
}

/** Inline wizard: pick type → fill details → declare (optionally with document). */
export default function CreateIntegrationWizard({
  incrementId,
  onCreated,
  onCancel,
}: Props) {
  const [type, setType] = useState<IntegrationType>("GRPC");
  const [name, setName] = useState("");
  const [source, setSource] = useState("");
  const [target, setTarget] = useState("");
  const [required, setRequired] = useState(true);
  const [createDoc, setCreateDoc] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    if (!name.trim()) return;
    setBusy(true);
    setError(null);
    try {
      await api.createIntegration(incrementId, {
        type,
        name: name.trim(),
        source_application: source.trim(),
        target_application: target.trim(),
        required,
        create_document: createDoc,
      });
      onCreated();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="rounded-lg border border-brand bg-white p-4 shadow-card">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-slate-800">
          Create Integration Doc
        </h2>
        <button
          className="text-slate-400 hover:text-slate-700"
          onClick={onCancel}
          title="Cancel"
        >
          <X size={16} />
        </button>
      </div>

      {error && (
        <div className="mb-3 rounded border border-rose-300 bg-rose-50 px-2 py-1 text-xs text-rose-700">
          {error}
        </div>
      )}

      <div className="mb-3">
        <label className="mb-1 block text-[11px] font-semibold uppercase tracking-wide text-slate-500">
          Integration type
        </label>
        <div className="grid grid-cols-4 gap-2">
          {TYPES.map((t) => (
            <button
              key={t.value}
              className={`rounded-md border px-2 py-1.5 text-xs ${
                type === t.value
                  ? "border-brand bg-brand-soft text-brand-fg"
                  : "border-slate-200 bg-white hover:bg-slate-50"
              }`}
              onClick={() => setType(t.value)}
            >
              <div className="font-semibold">{t.label}</div>
              <div className="text-[10px] text-slate-400">{t.priority}</div>
            </button>
          ))}
        </div>
      </div>

      <div className="mb-3 grid grid-cols-1 gap-2">
        <label className="text-xs text-slate-600">
          <span className="mb-0.5 block font-medium">Name</span>
          <input
            className="w-full rounded border border-slate-300 px-2 py-1.5 text-sm"
            placeholder="e.g. Fraud Check gRPC Service"
            value={name}
            onChange={(e) => setName(e.target.value)}
            autoFocus
          />
        </label>
        <div className="grid grid-cols-2 gap-2">
          <label className="text-xs text-slate-600">
            <span className="mb-0.5 block font-medium">Source application</span>
            <input
              className="w-full rounded border border-slate-300 px-2 py-1.5 text-sm"
              placeholder="payment-platform"
              value={source}
              onChange={(e) => setSource(e.target.value)}
            />
          </label>
          <label className="text-xs text-slate-600">
            <span className="mb-0.5 block font-medium">Target application</span>
            <input
              className="w-full rounded border border-slate-300 px-2 py-1.5 text-sm"
              placeholder="fraud-engine"
              value={target}
              onChange={(e) => setTarget(e.target.value)}
            />
          </label>
        </div>
      </div>

      <div className="mb-3 flex items-center gap-4 text-xs text-slate-600">
        <label className="inline-flex items-center gap-1.5">
          <input
            type="checkbox"
            checked={required}
            onChange={(e) => setRequired(e.target.checked)}
          />
          Required for this increment
        </label>
        <label className="inline-flex items-center gap-1.5">
          <input
            type="checkbox"
            checked={createDoc}
            onChange={(e) => setCreateDoc(e.target.checked)}
          />
          Create document now from template
        </label>
      </div>

      <div className="flex justify-end gap-2">
        <Button variant="ghost" onClick={onCancel}>
          Cancel
        </Button>
        <Button
          variant="primary"
          disabled={busy || !name.trim()}
          onClick={submit}
        >
          {busy ? "Creating…" : createDoc ? "Create with Document" : "Declare"}
        </Button>
      </div>
    </div>
  );
}
