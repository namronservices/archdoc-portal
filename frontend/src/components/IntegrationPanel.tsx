import { useEffect, useMemo, useState } from "react";
import { FileCode2, Save, ShieldCheck } from "lucide-react";
import { api } from "../api/client";
import type {
  Integration,
  MetadataFieldSpec,
  ValidationItem,
} from "../types";
import CodeEditor from "./CodeEditor";
import { Badge, Button } from "./ui";

interface Props {
  integration: Integration;
  onReload: () => Promise<Integration>;
}

const SEVERITY_STYLE: Record<string, string> = {
  error: "border-rose-300 bg-rose-50 text-rose-700",
  warning: "border-amber-300 bg-amber-50 text-amber-700",
  info: "border-sky-300 bg-sky-50 text-sky-700",
};

function formValue(spec: MetadataFieldSpec, raw: unknown): string | boolean {
  if (spec.kind === "bool") return Boolean(raw);
  if (spec.kind === "list") {
    return Array.isArray(raw) ? raw.join("\n") : String(raw ?? "");
  }
  if (raw === null || raw === undefined) return "";
  return String(raw);
}

function parseValue(spec: MetadataFieldSpec, input: string | boolean): unknown {
  if (spec.kind === "bool") return Boolean(input);
  if (spec.kind === "list") {
    return String(input)
      .split(/\r?\n/)
      .map((s) => s.trim())
      .filter(Boolean);
  }
  return String(input);
}

/** Sidebar panel for the integration document editor.
 *
 *  Type-aware metadata form, paste-as-text contract editor, status, validation,
 *  and the integration's linked HLDs.
 */
export default function IntegrationPanel({ integration, onReload }: Props) {
  const [form, setForm] = useState<Record<string, string | boolean>>({});
  const [contractName, setContractName] = useState(integration.contract_filename);
  const [contractContent, setContractContent] = useState("");
  const [contractLoaded, setContractLoaded] = useState(false);
  const [validation, setValidation] = useState<ValidationItem[]>([]);
  const [status, setStatus] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // Seed the form from metadata whenever the integration row reloads.
  useEffect(() => {
    const seeded: Record<string, string | boolean> = {};
    for (const spec of integration.metadata_schema) {
      seeded[spec.key] = formValue(spec, integration.metadata[spec.key]);
    }
    setForm(seeded);
    setContractName(integration.contract_filename);
  }, [integration]);

  // Lazy-load the contract body the first time the panel mounts.
  useEffect(() => {
    if (contractLoaded) return;
    api
      .getContract(integration.id)
      .then((c) => {
        setContractContent(c.content);
        setContractLoaded(true);
      })
      .catch((e) => setError((e as Error).message));
  }, [integration.id, contractLoaded]);

  // Initial validation snapshot from the persisted run.
  useEffect(() => {
    api
      .getIntegrationValidation(integration.id)
      .then((v) => setValidation(v.results))
      .catch(() => undefined);
  }, [integration.id]);

  const dirty = useMemo(() => {
    for (const spec of integration.metadata_schema) {
      if (
        parseValue(spec, form[spec.key] ?? "") !==
        (integration.metadata[spec.key] ?? (spec.kind === "list" ? [] : ""))
      ) {
        // Loose comparison — lists/strings rarely match exactly via ===; we
        // rely on the user-facing "Save metadata" button rather than auto-save.
        return true;
      }
    }
    return false;
  }, [form, integration]);

  async function saveMetadata() {
    setBusy(true);
    setStatus("");
    setError(null);
    try {
      const metadata: Record<string, unknown> = {};
      for (const spec of integration.metadata_schema) {
        const raw = form[spec.key];
        if (raw === "" || raw === undefined) continue;
        metadata[spec.key] = parseValue(spec, raw);
      }
      await api.updateIntegration(integration.id, { metadata });
      await onReload();
      setStatus("Metadata saved.");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function saveContract() {
    if (!contractName.trim()) {
      setError("Contract filename is required.");
      return;
    }
    setBusy(true);
    setStatus("");
    setError(null);
    try {
      await api.setContract(integration.id, {
        filename: contractName.trim(),
        content: contractContent,
      });
      await onReload();
      setStatus("Contract saved.");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function runValidation() {
    setBusy(true);
    setError(null);
    try {
      const v = await api.validateIntegration(integration.id);
      setValidation(v.results);
      setStatus(
        v.results.length === 0
          ? "Validation passed."
          : `${v.results.length} issue${v.results.length === 1 ? "" : "s"} found.`,
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function toggleApproved() {
    try {
      await api.updateIntegration(integration.id, {
        status: integration.status === "approved" ? "draft" : "approved",
      });
      await onReload();
    } catch (e) {
      setError((e as Error).message);
    }
  }

  return (
    <div className="scroll-thin flex h-full min-h-0 flex-col gap-3 overflow-y-auto p-3">
      {/* Identity */}
      <section className="rounded-lg border border-slate-200 bg-white p-3 shadow-card">
        <div className="mb-2 flex items-center gap-2">
          <Badge tone="indigo">{integration.type_label}</Badge>
          <Badge tone={integration.status === "approved" ? "emerald" : "amber"}>
            {integration.status}
          </Badge>
          {integration.required && <Badge tone="rose">required</Badge>}
        </div>
        <div className="text-xs text-slate-500">
          <span className="font-medium text-slate-700">
            {integration.source_application || "—"}
          </span>{" "}
          →{" "}
          <span className="font-medium text-slate-700">
            {integration.target_application || "—"}
          </span>
        </div>
        <p className="mt-1 text-[10px] text-slate-400">
          id: {integration.integration_id}
        </p>
        <div className="mt-2">
          <Button variant="secondary" onClick={toggleApproved}>
            {integration.status === "approved"
              ? "Mark as draft"
              : "Mark as approved"}
          </Button>
        </div>
      </section>

      {error && (
        <div className="rounded border border-rose-300 bg-rose-50 px-2 py-1 text-xs text-rose-700">
          {error}
        </div>
      )}
      {status && (
        <div className="rounded border border-emerald-300 bg-emerald-50 px-2 py-1 text-xs text-emerald-700">
          {status}
        </div>
      )}

      {/* Metadata form */}
      <section className="rounded-lg border border-slate-200 bg-white p-3 shadow-card">
        <div className="mb-2 flex items-center justify-between">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Metadata
          </h3>
          <Button
            variant="primary"
            disabled={busy || !dirty}
            onClick={saveMetadata}
          >
            <Save size={13} /> Save
          </Button>
        </div>
        <div className="space-y-2">
          {integration.metadata_schema.map((spec) => (
            <FieldEditor
              key={spec.key}
              spec={spec}
              value={form[spec.key] ?? (spec.kind === "bool" ? false : "")}
              onChange={(v) =>
                setForm((prev) => ({ ...prev, [spec.key]: v }))
              }
            />
          ))}
          {integration.metadata_schema.length === 0 && (
            <p className="text-xs text-slate-400">
              No metadata fields for this integration type.
            </p>
          )}
        </div>
      </section>

      {/* Contract */}
      <section className="rounded-lg border border-slate-200 bg-white p-3 shadow-card">
        <div className="mb-2 flex items-center justify-between">
          <h3 className="flex items-center gap-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
            <FileCode2 size={12} />
            Contract
            <span className="ml-1 normal-case text-slate-400">
              ({integration.contract_format || "text"})
            </span>
          </h3>
          <Button variant="primary" disabled={busy} onClick={saveContract}>
            <Save size={13} /> Save
          </Button>
        </div>
        <input
          className="mb-2 w-full rounded border border-slate-300 px-2 py-1 text-xs"
          placeholder="Filename (e.g. fraud_check.proto)"
          value={contractName}
          onChange={(e) => setContractName(e.target.value)}
        />
        {integration.contract_path && (
          <p className="mb-1 text-[10px] text-slate-400">
            Git path: {integration.contract_path}
          </p>
        )}
        {contractLoaded ? (
          <CodeEditor
            key={`contract-${integration.id}`}
            defaultValue={contractContent}
            onChange={setContractContent}
          />
        ) : (
          <p className="text-xs text-slate-400">Loading contract…</p>
        )}
      </section>

      {/* Validation */}
      <section className="rounded-lg border border-slate-200 bg-white p-3 shadow-card">
        <div className="mb-2 flex items-center justify-between">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Validation
          </h3>
          <Button variant="secondary" disabled={busy} onClick={runValidation}>
            <ShieldCheck size={13} /> Run
          </Button>
        </div>
        <div className="space-y-1.5">
          {validation.length === 0 ? (
            <p className="text-xs text-slate-400">
              No issues recorded. Run validation after edits.
            </p>
          ) : (
            validation.map((item, i) => (
              <div
                key={i}
                className={`rounded-md border px-2 py-1 text-[11px] ${
                  SEVERITY_STYLE[item.severity] ?? SEVERITY_STYLE.info
                }`}
              >
                <span className="font-semibold uppercase">{item.severity}</span>
                <span className="ml-1">{item.message}</span>
              </div>
            ))
          )}
        </div>
      </section>

      {/* Linked HLDs */}
      {integration.linked_hlds.length > 0 && (
        <section className="rounded-lg border border-slate-200 bg-white p-3 shadow-card">
          <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
            Linked HLDs
          </h3>
          <ul className="space-y-1 text-xs">
            {integration.linked_hlds.map((h) => (
              <li key={h.document_id}>
                <a
                  href={`/hld/${h.document_id}`}
                  className="text-brand-fg hover:underline"
                >
                  {h.title}
                </a>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}

function FieldEditor({
  spec,
  value,
  onChange,
}: {
  spec: MetadataFieldSpec;
  value: string | boolean;
  onChange: (v: string | boolean) => void;
}) {
  if (spec.kind === "bool") {
    return (
      <label className="flex items-center gap-2 text-xs text-slate-700">
        <input
          type="checkbox"
          checked={Boolean(value)}
          onChange={(e) => onChange(e.target.checked)}
        />
        {spec.label}
      </label>
    );
  }
  if (spec.kind === "select") {
    return (
      <label className="block text-[11px] text-slate-500">
        <span className="mb-0.5 block">{spec.label}</span>
        <select
          className="w-full rounded border border-slate-300 px-2 py-1 text-xs"
          value={String(value ?? "")}
          onChange={(e) => onChange(e.target.value)}
        >
          <option value="">—</option>
          {(spec.options ?? []).map((opt) => (
            <option key={opt} value={opt}>
              {opt}
            </option>
          ))}
        </select>
      </label>
    );
  }
  if (spec.kind === "list") {
    return (
      <label className="block text-[11px] text-slate-500">
        <span className="mb-0.5 block">{spec.label} (one per line)</span>
        <textarea
          className="scroll-thin block w-full rounded border border-slate-300 px-2 py-1 text-xs"
          rows={3}
          value={String(value ?? "")}
          onChange={(e) => onChange(e.target.value)}
        />
      </label>
    );
  }
  return (
    <label className="block text-[11px] text-slate-500">
      <span className="mb-0.5 block">{spec.label}</span>
      <input
        className="w-full rounded border border-slate-300 px-2 py-1 text-xs"
        value={String(value ?? "")}
        onChange={(e) => onChange(e.target.value)}
      />
    </label>
  );
}
