import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Building2,
  ChevronRight,
  Cog,
  Database,
  Network,
  Package,
  Plus,
  RefreshCcw,
  ScrollText,
  ShieldCheck,
} from "lucide-react";
import { api } from "../api/client";
import type {
  Capability,
  DataDomain,
  DataObject,
  Domain,
  EnterpriseApplication,
  Principle,
  Standard,
  TechnologyPlatform,
} from "../types";
import AppHeader from "../components/AppHeader";
import { Badge, Button, Panel } from "../components/ui";

type SectionKey =
  | "domains"
  | "capabilities"
  | "application-groups"
  | "applications"
  | "data-domains"
  | "data-objects"
  | "technology-platforms"
  | "standards"
  | "principles";

const SECTIONS: { key: SectionKey; label: string; layer: string; Icon: typeof Building2 }[] = [
  { key: "domains", label: "Domains", layer: "Business", Icon: Building2 },
  { key: "capabilities", label: "Capabilities", layer: "Business", Icon: Building2 },
  { key: "application-groups", label: "Application Groups", layer: "Application", Icon: Package },
  { key: "applications", label: "Applications", layer: "Application", Icon: Package },
  { key: "data-domains", label: "Data Domains", layer: "Data", Icon: Database },
  { key: "data-objects", label: "Data Objects", layer: "Data", Icon: Database },
  { key: "technology-platforms", label: "Technology Platforms", layer: "Technology", Icon: Cog },
  { key: "standards", label: "Standards", layer: "Motivation & Governance", Icon: ScrollText },
  { key: "principles", label: "Principles", layer: "Motivation & Governance", Icon: ShieldCheck },
];

const LAYERS = [
  "Business",
  "Application",
  "Data",
  "Technology",
  "Motivation & Governance",
];

/** Enterprise admin — list + lightweight create per TOGAF object type.
 *
 *  Edit-in-place is intentionally minimal for the MVP; richer editing lands
 *  in a later iteration. New objects commit YAML to the enterprise repo via
 *  the corresponding POST endpoint and immediately appear in the list.
 */
export default function EnterprisePage() {
  const [section, setSection] = useState<SectionKey>("domains");
  const [domains, setDomains] = useState<Domain[]>([]);
  const [capabilities, setCapabilities] = useState<Capability[]>([]);
  const [applications, setApplications] = useState<EnterpriseApplication[]>([]);
  const [applicationGroups, setApplicationGroups] = useState<
    { slug: string; name: string; domain_slug: string | null; description: string }[]
  >([]);
  const [dataDomains, setDataDomains] = useState<DataDomain[]>([]);
  const [dataObjects, setDataObjects] = useState<DataObject[]>([]);
  const [platforms, setPlatforms] = useState<TechnologyPlatform[]>([]);
  const [standards, setStandards] = useState<Standard[]>([]);
  const [principles, setPrinciples] = useState<Principle[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState<SectionKey | null>(null);

  const reload = useCallback(async () => {
    setError(null);
    const [
      d,
      c,
      a,
      ag,
      dd,
      doData,
      tp,
      st,
      pr,
    ] = await Promise.all([
      api.listDomains(),
      api.listCapabilities(),
      api.listEnterpriseApplications(),
      api.listEnterpriseApplicationGroups(),
      api.listDataDomains(),
      api.listDataObjects(),
      api.listTechnologyPlatforms(),
      api.listStandards(),
      api.listPrinciples(),
    ]);
    setDomains(d);
    setCapabilities(c);
    setApplications(a);
    setApplicationGroups(
      (ag as unknown as { slug: string; name: string; domain_slug: string | null; description: string }[]).map((g) => ({
        slug: g.slug,
        name: g.name,
        domain_slug: g.domain_slug,
        description: g.description,
      })),
    );
    setDataDomains(dd);
    setDataObjects(doData);
    setPlatforms(tp);
    setStandards(st);
    setPrinciples(pr);
  }, []);

  useEffect(() => {
    reload().catch((e) => setError((e as Error).message));
  }, [reload]);

  const sectionsByLayer = useMemo(() => {
    const m = new Map<string, typeof SECTIONS>();
    for (const s of SECTIONS) {
      m.set(s.layer, [...(m.get(s.layer) ?? []), s]);
    }
    return m;
  }, []);

  async function resync() {
    setBusy(true);
    try {
      await api.syncEnterprise();
      await reload();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-screen flex-col bg-slate-50">
      <AppHeader />
      <main className="mx-auto flex w-full max-w-6xl flex-1 gap-4 px-6 py-5">
        {/* Left tree */}
        <aside className="w-60 shrink-0">
          <div className="rounded-lg border border-slate-200 bg-white shadow-card">
            <header className="flex items-center justify-between border-b border-slate-100 px-3 py-2">
              <h2 className="flex items-center gap-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
                <Network size={12} /> Enterprise
              </h2>
              <button
                disabled={busy}
                onClick={resync}
                title="Resync from Git"
                className="text-slate-400 hover:text-slate-700"
              >
                <RefreshCcw size={13} />
              </button>
            </header>
            <div className="py-1">
              {LAYERS.map((layer) => (
                <div key={layer} className="px-1">
                  <div className="px-2 py-1 text-[10px] font-semibold uppercase tracking-wide text-slate-400">
                    {layer}
                  </div>
                  {(sectionsByLayer.get(layer) ?? []).map((s) => (
                    <button
                      key={s.key}
                      onClick={() => setSection(s.key)}
                      className={`flex w-full items-center gap-1.5 rounded px-2 py-1 text-left text-xs ${
                        section === s.key
                          ? "bg-brand-soft text-brand-fg"
                          : "text-slate-600 hover:bg-slate-50"
                      }`}
                    >
                      <s.Icon size={12} />
                      {s.label}
                      <ChevronRight
                        size={11}
                        className="ml-auto text-slate-300"
                      />
                    </button>
                  ))}
                </div>
              ))}
            </div>
          </div>
        </aside>

        {/* Right content */}
        <section className="min-w-0 flex-1">
          {error && (
            <div className="mb-3 rounded border border-rose-300 bg-rose-50 px-3 py-2 text-sm text-rose-700">
              {error}
            </div>
          )}

          {section === "domains" && (
            <ListPanel
              title="Domains"
              rows={domains.map((d) => ({
                slug: d.slug,
                primary: d.name,
                meta: d.owner || "",
                badges: d.archimate_type
                  ? [{ tone: "indigo" as const, text: d.archimate_type }]
                  : [],
              }))}
              onCreate={
                creating === "domains"
                  ? null
                  : () => setCreating("domains")
              }
            >
              {creating === "domains" && (
                <DomainForm
                  onSubmit={async (data) => {
                    await api.createDomain(data);
                    setCreating(null);
                    await reload();
                  }}
                  onCancel={() => setCreating(null)}
                />
              )}
            </ListPanel>
          )}

          {section === "capabilities" && (
            <ListPanel
              title="Capabilities"
              rows={capabilities.map((c) => ({
                slug: c.slug,
                primary: c.name,
                meta: c.domain_slug || "—",
                badges: [
                  c.criticality
                    ? {
                        tone:
                          c.criticality === "high"
                            ? ("rose" as const)
                            : ("slate" as const),
                        text: c.criticality,
                      }
                    : null,
                ].filter(Boolean) as { tone: "indigo" | "amber" | "slate" | "emerald" | "rose" | "sky"; text: string }[],
              }))}
              onCreate={
                creating === "capabilities"
                  ? null
                  : () => setCreating("capabilities")
              }
            >
              {creating === "capabilities" && (
                <CapabilityForm
                  domains={domains}
                  onSubmit={async (data) => {
                    await api.createCapability(data);
                    setCreating(null);
                    await reload();
                  }}
                  onCancel={() => setCreating(null)}
                />
              )}
            </ListPanel>
          )}

          {section === "application-groups" && (
            <ListPanel
              title="Application Groups"
              rows={applicationGroups.map((g) => ({
                slug: g.slug,
                primary: g.name,
                meta: g.domain_slug || "—",
                badges: [],
              }))}
              onCreate={
                creating === "application-groups"
                  ? null
                  : () => setCreating("application-groups")
              }
            >
              {creating === "application-groups" && (
                <ApplicationGroupForm
                  domains={domains}
                  onSubmit={async (data) => {
                    await api.createEnterpriseApplicationGroup(data);
                    setCreating(null);
                    await reload();
                  }}
                  onCancel={() => setCreating(null)}
                />
              )}
            </ListPanel>
          )}

          {section === "applications" && (
            <ListPanel
              title="Applications"
              rows={applications.map((a) => ({
                slug: a.slug,
                primary: a.name,
                meta: a.application_group_slug || "—",
                badges: [
                  a.architecture_state
                    ? {
                        tone:
                          a.architecture_state === "target"
                            ? ("emerald" as const)
                            : a.architecture_state === "transition"
                              ? ("amber" as const)
                              : ("slate" as const),
                        text: a.architecture_state,
                      }
                    : null,
                ].filter(Boolean) as { tone: "indigo" | "amber" | "slate" | "emerald" | "rose" | "sky"; text: string }[],
              }))}
              onCreate={
                creating === "applications"
                  ? null
                  : () => setCreating("applications")
              }
            >
              {creating === "applications" && (
                <ApplicationForm
                  domains={domains}
                  groups={applicationGroups.map((g) => ({
                    slug: g.slug,
                    name: g.name,
                  }))}
                  onSubmit={async (data) => {
                    await api.createEnterpriseApplication(data);
                    setCreating(null);
                    await reload();
                  }}
                  onCancel={() => setCreating(null)}
                />
              )}
            </ListPanel>
          )}

          {section === "data-domains" && (
            <ListPanel
              title="Data Domains"
              rows={dataDomains.map((d) => ({
                slug: d.slug,
                primary: d.name,
                meta: d.description,
                badges: [],
              }))}
              onCreate={
                creating === "data-domains"
                  ? null
                  : () => setCreating("data-domains")
              }
            >
              {creating === "data-domains" && (
                <NamedForm
                  placeholder="Data domain name"
                  onSubmit={async (name) => {
                    await api.createDataDomain({ name });
                    setCreating(null);
                    await reload();
                  }}
                  onCancel={() => setCreating(null)}
                />
              )}
            </ListPanel>
          )}

          {section === "data-objects" && (
            <ListPanel
              title="Data Objects"
              rows={dataObjects.map((d) => ({
                slug: d.slug,
                primary: d.name,
                meta: d.domain_slug || "—",
                badges: [],
              }))}
              onCreate={
                creating === "data-objects"
                  ? null
                  : () => setCreating("data-objects")
              }
            >
              {creating === "data-objects" && (
                <DataObjectForm
                  domains={domains}
                  onSubmit={async (data) => {
                    await api.createDataObject(data);
                    setCreating(null);
                    await reload();
                  }}
                  onCancel={() => setCreating(null)}
                />
              )}
            </ListPanel>
          )}

          {section === "technology-platforms" && (
            <ListPanel
              title="Technology Platforms"
              rows={platforms.map((p) => ({
                slug: p.slug,
                primary: p.name,
                meta: p.type || "—",
                badges: [],
              }))}
              onCreate={
                creating === "technology-platforms"
                  ? null
                  : () => setCreating("technology-platforms")
              }
            >
              {creating === "technology-platforms" && (
                <TechnologyPlatformForm
                  onSubmit={async (data) => {
                    await api.createTechnologyPlatform(data);
                    setCreating(null);
                    await reload();
                  }}
                  onCancel={() => setCreating(null)}
                />
              )}
            </ListPanel>
          )}

          {section === "standards" && (
            <ListPanel
              title="Standards"
              rows={standards.map((s) => ({
                slug: s.slug,
                primary: s.title,
                meta: "",
                badges: [],
              }))}
              onCreate={
                creating === "standards"
                  ? null
                  : () => setCreating("standards")
              }
            >
              {creating === "standards" && (
                <TitleBodyForm
                  titleLabel="Standard title"
                  onSubmit={async (data) => {
                    await api.createStandard(data);
                    setCreating(null);
                    await reload();
                  }}
                  onCancel={() => setCreating(null)}
                />
              )}
            </ListPanel>
          )}

          {section === "principles" && (
            <ListPanel
              title="Principles"
              rows={principles.map((p) => ({
                slug: p.slug,
                primary: p.title,
                meta: "",
                badges: [],
              }))}
              onCreate={
                creating === "principles"
                  ? null
                  : () => setCreating("principles")
              }
            >
              {creating === "principles" && (
                <TitleBodyForm
                  titleLabel="Principle title"
                  onSubmit={async (data) => {
                    await api.createPrinciple(data);
                    setCreating(null);
                    await reload();
                  }}
                  onCancel={() => setCreating(null)}
                />
              )}
            </ListPanel>
          )}
        </section>
      </main>
    </div>
  );
}

// --- Generic list panel ----------------------------------------------------
type Row = {
  slug: string;
  primary: string;
  meta: string;
  badges: { tone: "indigo" | "amber" | "slate" | "emerald" | "rose" | "sky"; text: string }[];
};

function ListPanel({
  title,
  rows,
  onCreate,
  children,
}: {
  title: string;
  rows: Row[];
  onCreate: (() => void) | null;
  children?: React.ReactNode;
}) {
  return (
    <Panel
      title={title}
      actions={
        onCreate ? (
          <button
            className="inline-flex items-center gap-1 rounded-md border border-slate-300 bg-white px-2 py-1 text-xs hover:bg-slate-50"
            onClick={onCreate}
          >
            <Plus size={12} /> New
          </button>
        ) : null
      }
    >
      {children && <div className="p-3">{children}</div>}
      {rows.length === 0 ? (
        <p className="px-4 py-6 text-xs text-slate-400">No entries yet.</p>
      ) : (
        <ul className="divide-y divide-slate-100">
          {rows.map((r) => (
            <li key={r.slug} className="flex items-center gap-2 px-3 py-2">
              <div className="min-w-0">
                <div className="truncate text-sm font-medium text-slate-800">
                  {r.primary}
                </div>
                <div className="truncate text-[10px] text-slate-400">
                  {r.slug}
                  {r.meta && ` · ${r.meta}`}
                </div>
              </div>
              <div className="ml-auto flex gap-1">
                {r.badges.map((b, i) => (
                  <Badge key={i} tone={b.tone}>
                    {b.text}
                  </Badge>
                ))}
              </div>
            </li>
          ))}
        </ul>
      )}
    </Panel>
  );
}

// --- Forms -----------------------------------------------------------------
function FormFooter({
  onCancel,
  onSubmit,
  disabled,
}: {
  onCancel: () => void;
  onSubmit: () => void;
  disabled: boolean;
}) {
  return (
    <div className="mt-2 flex justify-end gap-2">
      <button
        className="rounded px-2 py-1 text-xs text-slate-500 hover:bg-slate-100"
        onClick={onCancel}
      >
        Cancel
      </button>
      <Button variant="primary" disabled={disabled} onClick={onSubmit}>
        Create
      </Button>
    </div>
  );
}

function field(_label?: string) {
  return `mb-2 block text-[11px] text-slate-600`;
}

function DomainForm({
  onSubmit,
  onCancel,
}: {
  onSubmit: (data: { name: string; owner?: string; description?: string }) => Promise<void>;
  onCancel: () => void;
}) {
  const [name, setName] = useState("");
  const [owner, setOwner] = useState("");
  const [description, setDescription] = useState("");
  const [busy, setBusy] = useState(false);
  return (
    <div className="rounded-md border border-brand bg-brand-soft/30 p-3">
      <label className={field("Name")}>
        <span className="mb-0.5 block font-medium">Name</span>
        <input
          autoFocus
          className="w-full rounded border border-slate-300 px-2 py-1 text-xs"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
      </label>
      <label className={field("Owner")}>
        <span className="mb-0.5 block font-medium">Owner</span>
        <input
          className="w-full rounded border border-slate-300 px-2 py-1 text-xs"
          value={owner}
          onChange={(e) => setOwner(e.target.value)}
        />
      </label>
      <label className={field("Description")}>
        <span className="mb-0.5 block font-medium">Description</span>
        <textarea
          className="w-full rounded border border-slate-300 px-2 py-1 text-xs"
          rows={2}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
      </label>
      <FormFooter
        onCancel={onCancel}
        disabled={busy || !name.trim()}
        onSubmit={async () => {
          setBusy(true);
          await onSubmit({ name: name.trim(), owner, description });
          setBusy(false);
        }}
      />
    </div>
  );
}

function CapabilityForm({
  domains,
  onSubmit,
  onCancel,
}: {
  domains: Domain[];
  onSubmit: (data: {
    name: string;
    domain_slug: string | null;
    criticality: string | null;
  }) => Promise<void>;
  onCancel: () => void;
}) {
  const [name, setName] = useState("");
  const [domainSlug, setDomainSlug] = useState<string>("");
  const [criticality, setCriticality] = useState<string>("");
  const [busy, setBusy] = useState(false);
  return (
    <div className="rounded-md border border-brand bg-brand-soft/30 p-3">
      <label className={field("Name")}>
        <span className="mb-0.5 block font-medium">Name</span>
        <input
          autoFocus
          className="w-full rounded border border-slate-300 px-2 py-1 text-xs"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
      </label>
      <label className={field("Domain")}>
        <span className="mb-0.5 block font-medium">Domain</span>
        <select
          className="w-full rounded border border-slate-300 px-2 py-1 text-xs"
          value={domainSlug}
          onChange={(e) => setDomainSlug(e.target.value)}
        >
          <option value="">—</option>
          {domains.map((d) => (
            <option key={d.slug} value={d.slug}>
              {d.name}
            </option>
          ))}
        </select>
      </label>
      <label className={field("Criticality")}>
        <span className="mb-0.5 block font-medium">Criticality</span>
        <select
          className="w-full rounded border border-slate-300 px-2 py-1 text-xs"
          value={criticality}
          onChange={(e) => setCriticality(e.target.value)}
        >
          <option value="">—</option>
          <option value="low">low</option>
          <option value="medium">medium</option>
          <option value="high">high</option>
        </select>
      </label>
      <FormFooter
        onCancel={onCancel}
        disabled={busy || !name.trim()}
        onSubmit={async () => {
          setBusy(true);
          await onSubmit({
            name: name.trim(),
            domain_slug: domainSlug || null,
            criticality: criticality || null,
          });
          setBusy(false);
        }}
      />
    </div>
  );
}

function ApplicationGroupForm({
  domains,
  onSubmit,
  onCancel,
}: {
  domains: Domain[];
  onSubmit: (data: {
    name: string;
    domain_slug: string | null;
    description: string;
  }) => Promise<void>;
  onCancel: () => void;
}) {
  const [name, setName] = useState("");
  const [domainSlug, setDomainSlug] = useState<string>("");
  const [description, setDescription] = useState("");
  const [busy, setBusy] = useState(false);
  return (
    <div className="rounded-md border border-brand bg-brand-soft/30 p-3">
      <label className={field("Name")}>
        <span className="mb-0.5 block font-medium">Name</span>
        <input
          autoFocus
          className="w-full rounded border border-slate-300 px-2 py-1 text-xs"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
      </label>
      <label className={field("Domain")}>
        <span className="mb-0.5 block font-medium">Domain</span>
        <select
          className="w-full rounded border border-slate-300 px-2 py-1 text-xs"
          value={domainSlug}
          onChange={(e) => setDomainSlug(e.target.value)}
        >
          <option value="">—</option>
          {domains.map((d) => (
            <option key={d.slug} value={d.slug}>
              {d.name}
            </option>
          ))}
        </select>
      </label>
      <label className={field("Description")}>
        <span className="mb-0.5 block font-medium">Description</span>
        <textarea
          className="w-full rounded border border-slate-300 px-2 py-1 text-xs"
          rows={2}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
      </label>
      <FormFooter
        onCancel={onCancel}
        disabled={busy || !name.trim()}
        onSubmit={async () => {
          setBusy(true);
          await onSubmit({
            name: name.trim(),
            domain_slug: domainSlug || null,
            description,
          });
          setBusy(false);
        }}
      />
    </div>
  );
}

function ApplicationForm({
  domains,
  groups,
  onSubmit,
  onCancel,
}: {
  domains: Domain[];
  groups: { slug: string; name: string }[];
  onSubmit: (data: {
    name: string;
    domain_slug: string | null;
    application_group_slug: string | null;
    architecture_state: string | null;
    criticality: string | null;
    owner: string;
  }) => Promise<void>;
  onCancel: () => void;
}) {
  const [name, setName] = useState("");
  const [groupSlug, setGroupSlug] = useState("");
  const [domainSlug, setDomainSlug] = useState("");
  const [state, setState] = useState("");
  const [criticality, setCriticality] = useState("");
  const [owner, setOwner] = useState("");
  const [busy, setBusy] = useState(false);
  return (
    <div className="rounded-md border border-brand bg-brand-soft/30 p-3">
      <label className={field("Name")}>
        <span className="mb-0.5 block font-medium">Name</span>
        <input
          autoFocus
          className="w-full rounded border border-slate-300 px-2 py-1 text-xs"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
      </label>
      <div className="grid grid-cols-2 gap-2">
        <label className={field("Application group")}>
          <span className="mb-0.5 block font-medium">Application group</span>
          <select
            className="w-full rounded border border-slate-300 px-2 py-1 text-xs"
            value={groupSlug}
            onChange={(e) => setGroupSlug(e.target.value)}
          >
            <option value="">—</option>
            {groups.map((g) => (
              <option key={g.slug} value={g.slug}>
                {g.name}
              </option>
            ))}
          </select>
        </label>
        <label className={field("Domain")}>
          <span className="mb-0.5 block font-medium">Domain</span>
          <select
            className="w-full rounded border border-slate-300 px-2 py-1 text-xs"
            value={domainSlug}
            onChange={(e) => setDomainSlug(e.target.value)}
          >
            <option value="">—</option>
            {domains.map((d) => (
              <option key={d.slug} value={d.slug}>
                {d.name}
              </option>
            ))}
          </select>
        </label>
        <label className={field("Architecture state")}>
          <span className="mb-0.5 block font-medium">Architecture state</span>
          <select
            className="w-full rounded border border-slate-300 px-2 py-1 text-xs"
            value={state}
            onChange={(e) => setState(e.target.value)}
          >
            <option value="">—</option>
            <option value="current">current</option>
            <option value="transition">transition</option>
            <option value="target">target</option>
          </select>
        </label>
        <label className={field("Criticality")}>
          <span className="mb-0.5 block font-medium">Criticality</span>
          <select
            className="w-full rounded border border-slate-300 px-2 py-1 text-xs"
            value={criticality}
            onChange={(e) => setCriticality(e.target.value)}
          >
            <option value="">—</option>
            <option value="low">low</option>
            <option value="medium">medium</option>
            <option value="high">high</option>
          </select>
        </label>
      </div>
      <label className={field("Owner")}>
        <span className="mb-0.5 block font-medium">Owner</span>
        <input
          className="w-full rounded border border-slate-300 px-2 py-1 text-xs"
          value={owner}
          onChange={(e) => setOwner(e.target.value)}
        />
      </label>
      <FormFooter
        onCancel={onCancel}
        disabled={busy || !name.trim()}
        onSubmit={async () => {
          setBusy(true);
          await onSubmit({
            name: name.trim(),
            application_group_slug: groupSlug || null,
            domain_slug: domainSlug || null,
            architecture_state: state || null,
            criticality: criticality || null,
            owner,
          });
          setBusy(false);
        }}
      />
    </div>
  );
}

function DataObjectForm({
  domains,
  onSubmit,
  onCancel,
}: {
  domains: Domain[];
  onSubmit: (data: { name: string; domain_slug: string | null; description: string }) => Promise<void>;
  onCancel: () => void;
}) {
  const [name, setName] = useState("");
  const [domainSlug, setDomainSlug] = useState("");
  const [description, setDescription] = useState("");
  const [busy, setBusy] = useState(false);
  return (
    <div className="rounded-md border border-brand bg-brand-soft/30 p-3">
      <label className={field("Name")}>
        <span className="mb-0.5 block font-medium">Name</span>
        <input
          autoFocus
          className="w-full rounded border border-slate-300 px-2 py-1 text-xs"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
      </label>
      <label className={field("Domain")}>
        <span className="mb-0.5 block font-medium">Domain</span>
        <select
          className="w-full rounded border border-slate-300 px-2 py-1 text-xs"
          value={domainSlug}
          onChange={(e) => setDomainSlug(e.target.value)}
        >
          <option value="">—</option>
          {domains.map((d) => (
            <option key={d.slug} value={d.slug}>
              {d.name}
            </option>
          ))}
        </select>
      </label>
      <label className={field("Description")}>
        <span className="mb-0.5 block font-medium">Description</span>
        <textarea
          className="w-full rounded border border-slate-300 px-2 py-1 text-xs"
          rows={2}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
      </label>
      <FormFooter
        onCancel={onCancel}
        disabled={busy || !name.trim()}
        onSubmit={async () => {
          setBusy(true);
          await onSubmit({
            name: name.trim(),
            domain_slug: domainSlug || null,
            description,
          });
          setBusy(false);
        }}
      />
    </div>
  );
}

function TechnologyPlatformForm({
  onSubmit,
  onCancel,
}: {
  onSubmit: (data: { name: string; type: string | null; owner: string; description: string }) => Promise<void>;
  onCancel: () => void;
}) {
  const [name, setName] = useState("");
  const [type, setType] = useState("");
  const [owner, setOwner] = useState("");
  const [description, setDescription] = useState("");
  const [busy, setBusy] = useState(false);
  return (
    <div className="rounded-md border border-brand bg-brand-soft/30 p-3">
      <label className={field("Name")}>
        <span className="mb-0.5 block font-medium">Name</span>
        <input
          autoFocus
          className="w-full rounded border border-slate-300 px-2 py-1 text-xs"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
      </label>
      <label className={field("Type")}>
        <span className="mb-0.5 block font-medium">Type</span>
        <select
          className="w-full rounded border border-slate-300 px-2 py-1 text-xs"
          value={type}
          onChange={(e) => setType(e.target.value)}
        >
          <option value="">—</option>
          <option value="messaging_platform">messaging_platform</option>
          <option value="runtime_platform">runtime_platform</option>
          <option value="database_platform">database_platform</option>
          <option value="infrastructure_service">infrastructure_service</option>
        </select>
      </label>
      <label className={field("Owner")}>
        <span className="mb-0.5 block font-medium">Owner</span>
        <input
          className="w-full rounded border border-slate-300 px-2 py-1 text-xs"
          value={owner}
          onChange={(e) => setOwner(e.target.value)}
        />
      </label>
      <label className={field("Description")}>
        <span className="mb-0.5 block font-medium">Description</span>
        <textarea
          className="w-full rounded border border-slate-300 px-2 py-1 text-xs"
          rows={2}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
      </label>
      <FormFooter
        onCancel={onCancel}
        disabled={busy || !name.trim()}
        onSubmit={async () => {
          setBusy(true);
          await onSubmit({
            name: name.trim(),
            type: type || null,
            owner,
            description,
          });
          setBusy(false);
        }}
      />
    </div>
  );
}

function NamedForm({
  placeholder,
  onSubmit,
  onCancel,
}: {
  placeholder: string;
  onSubmit: (name: string) => Promise<void>;
  onCancel: () => void;
}) {
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  return (
    <div className="rounded-md border border-brand bg-brand-soft/30 p-3">
      <label className={field("Name")}>
        <span className="mb-0.5 block font-medium">Name</span>
        <input
          autoFocus
          className="w-full rounded border border-slate-300 px-2 py-1 text-xs"
          placeholder={placeholder}
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
      </label>
      <FormFooter
        onCancel={onCancel}
        disabled={busy || !name.trim()}
        onSubmit={async () => {
          setBusy(true);
          await onSubmit(name.trim());
          setBusy(false);
        }}
      />
    </div>
  );
}

function TitleBodyForm({
  titleLabel,
  onSubmit,
  onCancel,
}: {
  titleLabel: string;
  onSubmit: (data: { title: string; body: string }) => Promise<void>;
  onCancel: () => void;
}) {
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [busy, setBusy] = useState(false);
  return (
    <div className="rounded-md border border-brand bg-brand-soft/30 p-3">
      <label className={field("Title")}>
        <span className="mb-0.5 block font-medium">{titleLabel}</span>
        <input
          autoFocus
          className="w-full rounded border border-slate-300 px-2 py-1 text-xs"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
        />
      </label>
      <label className={field("Body")}>
        <span className="mb-0.5 block font-medium">Body</span>
        <textarea
          className="w-full rounded border border-slate-300 px-2 py-1 text-xs"
          rows={4}
          value={body}
          onChange={(e) => setBody(e.target.value)}
        />
      </label>
      <FormFooter
        onCancel={onCancel}
        disabled={busy || !title.trim()}
        onSubmit={async () => {
          setBusy(true);
          await onSubmit({ title: title.trim(), body });
          setBusy(false);
        }}
      />
    </div>
  );
}
