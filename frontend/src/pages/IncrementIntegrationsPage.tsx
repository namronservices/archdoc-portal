import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  ArrowLeft,
  CheckCircle2,
  CircleDashed,
  FileWarning,
  Link2,
  Plus,
  RefreshCcw,
  ShieldCheck,
  Zap,
} from "lucide-react";
import { api } from "../api/client";
import type {
  HldDocument,
  Increment,
  IntegrationListItem,
  IntegrationType,
} from "../types";
import { Badge, Button, Panel } from "../components/ui";
import CreateIntegrationWizard from "../components/CreateIntegrationWizard";

const TYPE_TONE: Record<IntegrationType, "indigo" | "amber" | "slate" | "sky" | "emerald" | "rose"> = {
  GRPC: "indigo",
  KAFKA: "amber",
  MQ: "sky",
  SOAP: "rose",
  REST: "emerald",
  FILE: "slate",
  BATCH: "slate",
};

export default function IncrementIntegrationsPage() {
  const { incrementId } = useParams();
  const navigate = useNavigate();
  const incId = Number(incrementId);

  const [increment, setIncrement] = useState<Increment | null>(null);
  const [rows, setRows] = useState<IntegrationListItem[]>([]);
  const [hld, setHld] = useState<HldDocument | null>(null);
  const [showWizard, setShowWizard] = useState(false);
  const [status, setStatus] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const reload = useCallback(async () => {
    const [list, inc] = await Promise.all([
      api.listIntegrations(incId),
      api.getIncrement(incId),
    ]);
    setRows(list);
    setIncrement(inc);
    try {
      setHld(await api.getIncrementHld(incId));
    } catch {
      setHld(null);
    }
  }, [incId]);

  useEffect(() => {
    reload().catch((e) => setError((e as Error).message));
  }, [reload]);

  const linkedIds = useMemo(
    () => new Set((hld?.linked_integrations ?? []).map((i) => i.id)),
    [hld],
  );

  const missingCount = rows.filter(
    (r) => r.required && r.document_id === null,
  ).length;

  async function createMissing() {
    setBusy(true);
    setStatus("");
    setError(null);
    try {
      const res = await api.createMissingIntegrationDocs(incId);
      setStatus(
        res.created.length
          ? `Generated ${res.created.length} document${res.created.length === 1 ? "" : "s"} from template.`
          : "Nothing to generate — all required integrations already have docs.",
      );
      await reload();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function validateAll() {
    setBusy(true);
    setStatus("");
    setError(null);
    try {
      const documented = rows.filter((r) => r.document_id !== null);
      let total = 0;
      let issues = 0;
      for (const row of documented) {
        const res = await api.validateIntegration(row.id);
        total += 1;
        issues += res.results.filter((i) => i.severity !== "info").length;
      }
      setStatus(
        `Validated ${total} integration${total === 1 ? "" : "s"} — ${issues} issue${issues === 1 ? "" : "s"}.`,
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function toggleLink(row: IntegrationListItem) {
    if (!hld) {
      setError("This increment has no HLD yet — create one first.");
      return;
    }
    try {
      if (linkedIds.has(row.id)) {
        setHld(await api.unlinkIntegrationFromHld(hld.id, row.id));
      } else {
        setHld(await api.linkIntegrationToHld(hld.id, row.id));
      }
    } catch (e) {
      setError((e as Error).message);
    }
  }

  async function openOrGenerate(row: IntegrationListItem) {
    if (row.document_id !== null) {
      navigate(`/integration-doc/${row.document_id}`);
      return;
    }
    try {
      const updated = await api.createIntegrationDocument(row.id);
      if (updated.document_id !== null) {
        navigate(`/integration-doc/${updated.document_id}`);
      }
    } catch (e) {
      setError((e as Error).message);
    }
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white px-6 py-4">
        <div className="flex items-center gap-4">
          <Link
            to="/"
            className="inline-flex items-center gap-1 text-xs text-slate-500 hover:text-slate-800"
          >
            <ArrowLeft size={14} /> Home
          </Link>
          <div>
            <h1 className="text-lg font-bold text-slate-900">
              {increment?.name ?? "Increment"} — Integration Docs
            </h1>
            <p className="text-xs text-slate-500">
              Required integration documents for this architecture increment.
            </p>
          </div>
          <div className="ml-auto flex items-center gap-2">
            <Button
              variant="secondary"
              disabled={busy}
              onClick={validateAll}
            >
              <ShieldCheck size={14} /> Validate Integrations
            </Button>
            <Button
              variant="secondary"
              disabled={busy || missingCount === 0}
              onClick={createMissing}
              title={
                missingCount === 0
                  ? "All required integrations already have documents"
                  : `Generate documents for ${missingCount} required integration${missingCount === 1 ? "" : "s"}`
              }
            >
              <Zap size={14} /> Create Missing Docs
              {missingCount > 0 && (
                <span className="ml-1 rounded bg-amber-100 px-1 text-[10px] font-semibold text-amber-700">
                  {missingCount}
                </span>
              )}
            </Button>
            <Button variant="primary" onClick={() => setShowWizard((s) => !s)}>
              <Plus size={14} /> Create Integration Doc
            </Button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-6 py-5">
        {error && (
          <div className="mb-3 rounded border border-rose-300 bg-rose-50 px-3 py-2 text-sm text-rose-700">
            {error}
          </div>
        )}
        {status && (
          <div className="mb-3 rounded border border-emerald-300 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">
            {status}
          </div>
        )}

        {showWizard && (
          <div className="mb-4">
            <CreateIntegrationWizard
              incrementId={incId}
              onCancel={() => setShowWizard(false)}
              onCreated={async () => {
                setShowWizard(false);
                await reload();
              }}
            />
          </div>
        )}

        <Panel
          title={
            <span className="flex items-center gap-2">
              Integrations
              <span className="rounded bg-slate-100 px-1.5 text-[10px] text-slate-500">
                {rows.length}
              </span>
            </span>
          }
          actions={
            <button
              className="text-slate-400 hover:text-slate-700"
              onClick={() => reload()}
              title="Refresh"
            >
              <RefreshCcw size={14} />
            </button>
          }
        >
          {rows.length === 0 ? (
            <div className="px-6 py-12 text-center text-sm text-slate-400">
              No integrations declared yet. Use{" "}
              <strong>Create Integration Doc</strong> to add one.
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead className="border-b border-slate-100 text-left text-[11px] uppercase tracking-wide text-slate-400">
                <tr>
                  <th className="px-3 py-2">Integration</th>
                  <th className="px-3 py-2">Type</th>
                  <th className="px-3 py-2">Source</th>
                  <th className="px-3 py-2">Target</th>
                  <th className="px-3 py-2">Req.</th>
                  <th className="px-3 py-2">Document</th>
                  <th className="px-3 py-2">Status</th>
                  <th className="px-3 py-2 text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => {
                  const linked = linkedIds.has(r.id);
                  return (
                    <tr
                      key={r.id}
                      className="border-b border-slate-50 last:border-b-0"
                    >
                      <td className="px-3 py-2">
                        <button
                          className="text-left font-medium text-slate-800 hover:text-brand-fg"
                          onClick={() => openOrGenerate(r)}
                        >
                          {r.name}
                        </button>
                        <div className="text-[10px] text-slate-400">
                          {r.integration_id}
                        </div>
                      </td>
                      <td className="px-3 py-2">
                        <Badge tone={TYPE_TONE[r.type]}>{r.type_label}</Badge>
                      </td>
                      <td className="px-3 py-2 text-slate-600">
                        {r.source_application || (
                          <span className="text-slate-300">—</span>
                        )}
                      </td>
                      <td className="px-3 py-2 text-slate-600">
                        {r.target_application || (
                          <span className="text-slate-300">—</span>
                        )}
                      </td>
                      <td className="px-3 py-2">
                        {r.required ? (
                          <Badge tone="rose">yes</Badge>
                        ) : (
                          <span className="text-xs text-slate-400">no</span>
                        )}
                      </td>
                      <td className="px-3 py-2">
                        {r.document_filename ? (
                          <span className="inline-flex items-center gap-1 text-emerald-700">
                            <CheckCircle2 size={12} />
                            <span className="text-xs">
                              {r.document_filename}
                            </span>
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-amber-700">
                            <FileWarning size={12} />
                            <span className="text-xs">missing</span>
                          </span>
                        )}
                      </td>
                      <td className="px-3 py-2">
                        <Badge
                          tone={r.status === "approved" ? "emerald" : "slate"}
                        >
                          {r.status}
                        </Badge>
                      </td>
                      <td className="px-3 py-2 text-right">
                        <div className="inline-flex gap-1">
                          <button
                            className="rounded border border-slate-300 px-2 py-1 text-[11px] hover:bg-slate-50"
                            onClick={() => openOrGenerate(r)}
                            title={
                              r.document_id === null
                                ? "Generate document and open"
                                : "Open document"
                            }
                          >
                            {r.document_id === null ? "Create & Open" : "Open"}
                          </button>
                          <button
                            className={`inline-flex items-center gap-1 rounded border px-2 py-1 text-[11px] ${
                              linked
                                ? "border-indigo-300 bg-indigo-50 text-indigo-700"
                                : "border-slate-300 hover:bg-slate-50"
                            } ${hld ? "" : "opacity-40"}`}
                            onClick={() => toggleLink(r)}
                            disabled={!hld}
                            title={
                              hld
                                ? linked
                                  ? "Unlink from HLD"
                                  : "Link to HLD"
                                : "Create the HLD first to link integrations"
                            }
                          >
                            <Link2 size={11} />
                            {linked ? "Linked" : "Link"}
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </Panel>

        {!hld && rows.length > 0 && (
          <p className="mt-3 inline-flex items-center gap-1 text-xs text-slate-500">
            <CircleDashed size={12} /> This increment has no HLD yet — go Home
            and create one to link integrations into the HLD.
          </p>
        )}
      </main>
    </div>
  );
}
