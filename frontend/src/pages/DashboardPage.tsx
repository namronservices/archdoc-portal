import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  Building2,
  Cog,
  Database,
  FileText,
  Layers,
  Network,
  Package,
  Plus,
  RefreshCcw,
  ScrollText,
  ShieldCheck,
  Sparkles,
  Zap,
} from "lucide-react";
import { api } from "../api/client";
import type { Dashboard, DashboardApplicationGroup } from "../types";
import AppHeader from "../components/AppHeader";
import { Badge, Button, Panel } from "../components/ui";

/** TOGAF Dashboard — primary landing page; starts Increments + HLDs. */
export default function DashboardPage() {
  const navigate = useNavigate();
  const [data, setData] = useState<Dashboard | null>(null);
  const [domainFilter, setDomainFilter] = useState<string | null>(null);
  const [startTarget, setStartTarget] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const reload = useCallback(async () => {
    setData(await api.getDashboard());
  }, []);

  useEffect(() => {
    reload().catch((e) => setError((e as Error).message));
  }, [reload]);

  async function resync() {
    setBusy(true);
    setError(null);
    try {
      await api.syncEnterprise();
      await reload();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const filteredGroups = useMemo(() => {
    if (!data) return [];
    if (!domainFilter) return data.application.application_groups;
    return data.application.application_groups.filter(
      (g) => g.domain_slug === domainFilter,
    );
  }, [data, domainFilter]);

  const filteredCapabilities = useMemo(() => {
    if (!data) return [];
    if (!domainFilter) return data.business.capabilities;
    return data.business.capabilities.filter(
      (c) => c.domain_slug === domainFilter,
    );
  }, [data, domainFilter]);

  const filteredApplications = useMemo(() => {
    if (!data) return [];
    if (!domainFilter) return data.application.applications;
    return data.application.applications.filter(
      (a) => a.domain_slug === domainFilter,
    );
  }, [data, domainFilter]);

  if (error && !data) {
    return <div className="p-6 text-sm text-rose-700">{error}</div>;
  }
  if (!data) {
    return <div className="p-6 text-sm text-slate-500">Loading dashboard…</div>;
  }

  return (
    <div className="flex min-h-screen flex-col bg-slate-50">
      <AppHeader hideNav />

      <main className="mx-auto w-full max-w-6xl px-6 py-6">
        <div className="mb-5 flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-brand text-white">
            <Sparkles size={20} />
          </div>
          <div>
            <h1 className="text-xl font-bold text-slate-900">
              Architecture Dashboard
            </h1>
            <p className="text-xs text-slate-500">
              Company-level TOGAF context. Start a new increment + HLD from any
              Application Group.
            </p>
          </div>
          <div className="ml-auto flex items-center gap-2">
            <Link
              to="/enterprise"
              className="inline-flex items-center gap-1 rounded-md border border-slate-300 bg-white px-3 py-1.5 text-xs text-slate-700 hover:bg-slate-50"
            >
              <Network size={14} /> Manage Enterprise Objects
            </Link>
            <Button variant="secondary" disabled={busy} onClick={resync}>
              <RefreshCcw size={14} /> Resync
            </Button>
          </div>
        </div>

        {error && (
          <div className="mb-4 rounded border border-rose-300 bg-rose-50 px-3 py-2 text-sm text-rose-700">
            {error}
          </div>
        )}

        {/* Recent HLDs */}
        <Panel
          title={
            <span className="flex items-center gap-2">
              <FileText size={14} /> Recent HLDs
            </span>
          }
          className="mb-4"
        >
          {data.recent_hlds.length === 0 ? (
            <p className="px-4 py-6 text-xs text-slate-400">
              No HLDs yet. Start one below by clicking an Application Group.
            </p>
          ) : (
            <div className="grid grid-cols-1 gap-2 p-3 md:grid-cols-2 lg:grid-cols-3">
              {data.recent_hlds.map((h) => (
                <button
                  key={h.id}
                  className="text-left rounded-md border border-slate-200 bg-white p-3 hover:border-brand hover:bg-brand-soft/40"
                  onClick={() => navigate(`/hld/${h.id}`)}
                >
                  <div className="text-sm font-semibold text-slate-800">
                    {h.title}
                  </div>
                  <div className="mt-1 text-[10px] text-slate-400">
                    {h.application_group_slug ?? "—"} · {h.increment_slug}
                  </div>
                </button>
              ))}
            </div>
          )}
        </Panel>

        {/* Domain filter — also serves as a Business Architecture summary */}
        <Panel
          title={
            <span className="flex items-center gap-2">
              <Building2 size={14} /> Business Architecture
            </span>
          }
          className="mb-4"
        >
          <div className="flex flex-wrap items-center gap-2 p-3">
            <button
              onClick={() => setDomainFilter(null)}
              className={`rounded-md border px-3 py-1.5 text-xs ${
                domainFilter === null
                  ? "border-brand bg-brand-soft text-brand-fg"
                  : "border-slate-200 bg-white hover:bg-slate-50"
              }`}
            >
              All domains
            </button>
            {data.business.domains.map((d) => (
              <button
                key={d.slug}
                onClick={() => setDomainFilter(d.slug)}
                className={`rounded-md border px-3 py-1.5 text-xs ${
                  domainFilter === d.slug
                    ? "border-brand bg-brand-soft text-brand-fg"
                    : "border-slate-200 bg-white hover:bg-slate-50"
                }`}
                title={`${d.capability_count} caps · ${d.application_group_count} groups · ${d.application_count} apps`}
              >
                <div className="font-semibold">{d.name}</div>
                <div className="text-[10px] text-slate-400">
                  {d.capability_count} caps · {d.application_count} apps
                </div>
              </button>
            ))}
          </div>
          {filteredCapabilities.length > 0 && (
            <div className="border-t border-slate-100 px-3 py-2">
              <div className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-slate-400">
                Capabilities
                {domainFilter && (
                  <span className="ml-1 lowercase text-slate-300">
                    in {domainFilter}
                  </span>
                )}
              </div>
              <div className="flex flex-wrap gap-1.5">
                {filteredCapabilities.map((c) => (
                  <span
                    key={c.slug}
                    className="inline-flex items-center gap-1 rounded-md border border-slate-200 bg-white px-2 py-1 text-[11px]"
                    title={c.criticality ?? undefined}
                  >
                    {c.name}
                    {c.criticality && (
                      <Badge
                        tone={
                          c.criticality === "high" ? "rose" : "slate"
                        }
                        className="!px-1"
                      >
                        {c.criticality}
                      </Badge>
                    )}
                  </span>
                ))}
              </div>
            </div>
          )}
        </Panel>

        {/* Application Architecture — primary action source */}
        <Panel
          title={
            <span className="flex items-center gap-2">
              <Package size={14} /> Application Architecture
              <Badge tone="indigo">primary</Badge>
            </span>
          }
          className="mb-4"
          actions={
            <Link
              to="/enterprise"
              className="text-xs text-brand-fg hover:underline"
            >
              + New group
            </Link>
          }
        >
          {filteredGroups.length === 0 ? (
            <p className="px-4 py-6 text-xs text-slate-400">
              No application groups
              {domainFilter ? ` in ${domainFilter}` : ""} yet. Create one in
              the Enterprise admin to start an increment.
            </p>
          ) : (
            <div className="grid grid-cols-1 gap-3 p-3 md:grid-cols-2">
              {filteredGroups.map((g) => (
                <ApplicationGroupCard
                  key={g.id}
                  group={g}
                  isStarting={startTarget === g.slug}
                  onStart={() => setStartTarget(g.slug)}
                  onCancelStart={() => setStartTarget(null)}
                  onStarted={async (hldId) => {
                    setStartTarget(null);
                    await reload();
                    navigate(`/hld/${hldId}`);
                  }}
                  onOpenHld={(hldId) => navigate(`/hld/${hldId}`)}
                  onOpenIntegrations={(incId) =>
                    navigate(`/increment/${incId}/integrations`)
                  }
                />
              ))}
            </div>
          )}
          {filteredApplications.length > 0 && (
            <div className="border-t border-slate-100 px-3 py-2">
              <div className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-slate-400">
                Applications
                {domainFilter && (
                  <span className="ml-1 lowercase text-slate-300">
                    in {domainFilter}
                  </span>
                )}
              </div>
              <div className="flex flex-wrap gap-1.5">
                {filteredApplications.map((a) => (
                  <span
                    key={a.slug}
                    className="inline-flex items-center gap-1 rounded-md border border-slate-200 bg-white px-2 py-1 text-[11px]"
                  >
                    {a.name}
                    {a.architecture_state && (
                      <Badge
                        tone={
                          a.architecture_state === "target"
                            ? "emerald"
                            : a.architecture_state === "transition"
                              ? "amber"
                              : "slate"
                        }
                        className="!px-1"
                      >
                        {a.architecture_state}
                      </Badge>
                    )}
                  </span>
                ))}
              </div>
            </div>
          )}
        </Panel>

        {/* Data Architecture */}
        <Panel
          title={
            <span className="flex items-center gap-2">
              <Database size={14} /> Data Architecture
            </span>
          }
          className="mb-4"
        >
          <div className="p-3">
            <div className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-slate-400">
              Data domains
            </div>
            <div className="mb-3 flex flex-wrap gap-1.5">
              {data.data.data_domains.length === 0 ? (
                <span className="text-[11px] text-slate-300">none</span>
              ) : (
                data.data.data_domains.map((d) => (
                  <span
                    key={d.slug}
                    className="inline-flex rounded-md border border-slate-200 bg-white px-2 py-1 text-[11px]"
                  >
                    {d.name}
                  </span>
                ))
              )}
            </div>
            <div className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-slate-400">
              Data objects
            </div>
            <div className="flex flex-wrap gap-1.5">
              {data.data.data_objects.length === 0 ? (
                <span className="text-[11px] text-slate-300">none</span>
              ) : (
                data.data.data_objects.map((d) => (
                  <span
                    key={d.slug}
                    className="inline-flex rounded-md border border-slate-200 bg-white px-2 py-1 text-[11px]"
                    title={d.domain_slug ?? undefined}
                  >
                    {d.name}
                  </span>
                ))
              )}
            </div>
          </div>
        </Panel>

        {/* Technology Architecture */}
        <Panel
          title={
            <span className="flex items-center gap-2">
              <Cog size={14} /> Technology Architecture
            </span>
          }
          className="mb-4"
        >
          <div className="flex flex-wrap gap-1.5 p-3">
            {data.technology.platforms.length === 0 ? (
              <span className="text-[11px] text-slate-300">none</span>
            ) : (
              data.technology.platforms.map((p) => (
                <span
                  key={p.slug}
                  className="inline-flex items-center gap-1 rounded-md border border-slate-200 bg-white px-2 py-1 text-[11px]"
                >
                  {p.name}
                  {p.type && (
                    <Badge tone="sky" className="!px-1">
                      {p.type}
                    </Badge>
                  )}
                </span>
              ))
            )}
          </div>
        </Panel>

        {/* Motivation & Governance */}
        <Panel
          title={
            <span className="flex items-center gap-2">
              <ShieldCheck size={14} /> Motivation & Governance
            </span>
          }
          className="mb-4"
        >
          <div className="grid grid-cols-1 gap-3 p-3 md:grid-cols-2">
            <div>
              <div className="mb-1 flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wide text-slate-400">
                <ScrollText size={11} /> Standards
              </div>
              <div className="flex flex-wrap gap-1.5">
                {data.motivation.standards.length === 0 ? (
                  <span className="text-[11px] text-slate-300">none</span>
                ) : (
                  data.motivation.standards.map((s) => (
                    <span
                      key={s.slug}
                      className="inline-flex rounded-md border border-slate-200 bg-white px-2 py-1 text-[11px]"
                    >
                      {s.title}
                    </span>
                  ))
                )}
              </div>
            </div>
            <div>
              <div className="mb-1 flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wide text-slate-400">
                <Layers size={11} /> Principles
              </div>
              <div className="flex flex-wrap gap-1.5">
                {data.motivation.principles.length === 0 ? (
                  <span className="text-[11px] text-slate-300">none</span>
                ) : (
                  data.motivation.principles.map((p) => (
                    <span
                      key={p.slug}
                      className="inline-flex rounded-md border border-slate-200 bg-white px-2 py-1 text-[11px]"
                    >
                      {p.title}
                    </span>
                  ))
                )}
              </div>
            </div>
          </div>
        </Panel>
      </main>
    </div>
  );
}

function ApplicationGroupCard({
  group,
  isStarting,
  onStart,
  onCancelStart,
  onStarted,
  onOpenHld,
  onOpenIntegrations,
}: {
  group: DashboardApplicationGroup;
  isStarting: boolean;
  onStart: () => void;
  onCancelStart: () => void;
  onStarted: (hldId: number) => void;
  onOpenHld: (hldId: number) => void;
  onOpenIntegrations: (incrementId: number) => void;
}) {
  const [name, setName] = useState("");
  const [title, setTitle] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    if (!name.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const res = await api.startIncrement(group.slug, {
        increment_name: name.trim(),
        hld_title: title.trim() || undefined,
      });
      onStarted(res.hld_id);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col rounded-lg border border-slate-200 bg-white p-3 shadow-card">
      <div className="flex items-start gap-2">
        <div>
          <div className="text-sm font-semibold text-slate-800">
            {group.name}
          </div>
          <div className="mt-0.5 text-[10px] text-slate-400">
            {group.domain_slug ?? "—"}
          </div>
        </div>
        <div className="ml-auto flex flex-wrap gap-1">
          <Badge tone="slate">{group.application_count} apps</Badge>
          <Badge tone="indigo">{group.increment_count} inc</Badge>
          <Badge tone="emerald">{group.hld_count} HLD</Badge>
        </div>
      </div>

      {group.recent_increments.length > 0 && (
        <div className="mt-2 border-t border-slate-100 pt-2 text-[11px]">
          <div className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-slate-400">
            Recent increments
          </div>
          <ul className="space-y-1">
            {group.recent_increments.map((inc) => (
              <li
                key={inc.id}
                className="flex items-center gap-2 rounded px-1 py-0.5 hover:bg-slate-50"
              >
                <span className="text-slate-700">{inc.name}</span>
                <Badge tone="slate" className="!px-1">
                  {inc.status}
                </Badge>
                <div className="ml-auto flex gap-1">
                  {inc.hld_id !== null && (
                    <button
                      className="text-brand-fg hover:underline"
                      onClick={() => onOpenHld(inc.hld_id!)}
                    >
                      open HLD
                    </button>
                  )}
                  <button
                    className="text-slate-500 hover:underline"
                    onClick={() => onOpenIntegrations(inc.id)}
                  >
                    integrations
                  </button>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}

      {!isStarting ? (
        <Button
          variant="primary"
          className="mt-3 self-start"
          onClick={onStart}
        >
          <Zap size={14} /> Start Increment
        </Button>
      ) : (
        <div className="mt-3 rounded-md border border-brand bg-brand-soft/30 p-2">
          <label className="block text-[11px] text-slate-600">
            <span className="mb-0.5 block font-medium">Increment name</span>
            <input
              autoFocus
              className="w-full rounded border border-slate-300 px-2 py-1 text-xs"
              placeholder="MVP2 Transition"
              value={name}
              onChange={(e) => setName(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && submit()}
            />
          </label>
          <label className="mt-2 block text-[11px] text-slate-600">
            <span className="mb-0.5 block font-medium">
              HLD title (optional)
            </span>
            <input
              className="w-full rounded border border-slate-300 px-2 py-1 text-xs"
              placeholder="Payment Platform HLD"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && submit()}
            />
          </label>
          {error && (
            <div className="mt-2 text-[11px] text-rose-700">{error}</div>
          )}
          <div className="mt-2 flex justify-end gap-1">
            <button
              className="rounded px-2 py-1 text-[11px] text-slate-500 hover:bg-slate-100"
              onClick={onCancelStart}
            >
              Cancel
            </button>
            <Button
              variant="primary"
              disabled={busy || !name.trim()}
              onClick={submit}
            >
              <Plus size={12} /> {busy ? "Creating…" : "Create"}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
