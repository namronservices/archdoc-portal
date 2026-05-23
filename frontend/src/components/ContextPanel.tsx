import { useCallback, useEffect, useMemo, useState } from "react";
import {
  AlertCircle,
  Boxes,
  Camera,
  ChevronRight,
  GitFork,
  Layers3,
  Link2,
  Plug,
  Plus,
  Search,
  X,
} from "lucide-react";
import { api } from "../api/client";
import type {
  ArchitectureContext,
  ContextObjectType,
  HldDocument,
  IntegrationType,
  LinkedIntegration,
  ReusableBlock,
  ValidationItem,
} from "../types";
import { Badge } from "./ui";

type Tab = "blocks" | "integrations" | "context" | "references" | "validation";

const TABS: { id: Tab; short: string; full: string }[] = [
  { id: "blocks", short: "Blocks", full: "Reusable Blocks" },
  { id: "integrations", short: "Integ.", full: "Integration Overview" },
  { id: "context", short: "Context", full: "Architecture Context" },
  { id: "references", short: "Refs", full: "Linked References" },
  { id: "validation", short: "Valid.", full: "Validation" },
];

const INTEGRATION_GROUP_ORDER: { type: IntegrationType; label: string }[] = [
  { type: "GRPC", label: "gRPC Services" },
  { type: "KAFKA", label: "Kafka Events" },
  { type: "MQ", label: "MQ Messages" },
  { type: "SOAP", label: "Legacy SOAP" },
  { type: "REST", label: "REST APIs" },
  { type: "FILE", label: "File Transfers" },
  { type: "BATCH", label: "Batch Jobs" },
];

const SEVERITY_STYLE: Record<string, string> = {
  error: "border-rose-300 bg-rose-50 text-rose-700",
  warning: "border-amber-300 bg-amber-50 text-amber-700",
  info: "border-sky-300 bg-sky-50 text-sky-700",
};

const MODE: Record<
  string,
  { tone: "indigo" | "slate" | "amber"; icon: typeof Link2 }
> = {
  linked: { tone: "indigo", icon: Link2 },
  snapshot: { tone: "slate", icon: Camera },
  forked: { tone: "amber", icon: GitFork },
};

interface Props {
  document: HldDocument;
  selectedSectionId: number | null;
  validation: ValidationItem[];
  onValidate: () => Promise<void>;
  onReload: () => Promise<HldDocument>;
}

export default function ContextPanel({
  document,
  selectedSectionId,
  validation,
  onValidate,
  onReload,
}: Props) {
  const [tab, setTab] = useState<Tab>("blocks");
  const [blocks, setBlocks] = useState<ReusableBlock[]>([]);
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("");
  const [expanded, setExpanded] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [archContext, setArchContext] = useState<ArchitectureContext | null>(
    null,
  );
  const [contextOptions, setContextOptions] = useState<
    Record<string, { slug: string; label: string }[]>
  >({});
  const [contextBusy, setContextBusy] = useState(false);

  const loadArchContext = useCallback(async () => {
    try {
      const ctx = await api.getArchitectureContext(document.id);
      setArchContext(ctx);
    } catch (e) {
      setLoadError((e as Error).message);
    }
  }, [document.id]);

  // Lazy-load architecture context + enterprise object lists when the Context
  // tab opens.
  useEffect(() => {
    if (tab !== "context" || archContext !== null) return;
    loadArchContext();
    Promise.all([
      api.listDomains(),
      api.listCapabilities(),
      api.listEnterpriseApplicationGroups(),
      api.listEnterpriseApplications(),
      api.listDataObjects(),
      api.listDataDomains(),
      api.listTechnologyPlatforms(),
      api.listStandards(),
      api.listPrinciples(),
    ])
      .then(
        ([
          domains,
          capabilities,
          appGroups,
          apps,
          dataObjects,
          dataDomains,
          platforms,
          standards,
          principles,
        ]) => {
          setContextOptions({
            domain: domains.map((d) => ({ slug: d.slug, label: d.name })),
            capability: capabilities.map((c) => ({
              slug: c.slug,
              label: c.name,
            })),
            application_group: appGroups.map((g) => ({
              slug: g.slug,
              label: g.name,
            })),
            application: apps.map((a) => ({ slug: a.slug, label: a.name })),
            data_object: dataObjects.map((d) => ({
              slug: d.slug,
              label: d.name,
            })),
            data_domain: dataDomains.map((d) => ({
              slug: d.slug,
              label: d.name,
            })),
            technology_platform: platforms.map((p) => ({
              slug: p.slug,
              label: p.name,
            })),
            standard: standards.map((s) => ({ slug: s.slug, label: s.title })),
            principle: principles.map((p) => ({
              slug: p.slug,
              label: p.title,
            })),
          });
        },
      )
      .catch((e) => setLoadError((e as Error).message));
  }, [tab, archContext, loadArchContext]);

  async function addContextLink(
    objectType: ContextObjectType,
    objectSlug: string,
  ) {
    if (!objectSlug) return;
    setContextBusy(true);
    try {
      const updated = await api.addContextLink(
        document.id,
        objectType,
        objectSlug,
      );
      setArchContext(updated);
    } catch (e) {
      setLoadError((e as Error).message);
    } finally {
      setContextBusy(false);
    }
  }

  async function removeContextLink(
    objectType: ContextObjectType,
    objectSlug: string,
  ) {
    setContextBusy(true);
    try {
      const updated = await api.removeContextLink(
        document.id,
        objectType,
        objectSlug,
      );
      setArchContext(updated);
    } catch (e) {
      setLoadError((e as Error).message);
    } finally {
      setContextBusy(false);
    }
  }

  useEffect(() => {
    if (tab !== "blocks" || blocks.length > 0) return;
    api
      .listReusableBlocks()
      .then(setBlocks)
      .catch((e) => setLoadError((e as Error).message));
  }, [tab, blocks.length]);

  const categories = useMemo(
    () => [...new Set(blocks.map((b) => b.category).filter(Boolean))].sort(),
    [blocks],
  );

  const filtered = useMemo(() => {
    const needle = search.trim().toLowerCase();
    return blocks.filter((b) => {
      if (category && b.category !== category) return false;
      if (!needle) return true;
      return (
        b.title.toLowerCase().includes(needle) ||
        b.block_id.toLowerCase().includes(needle) ||
        b.tags.some((t) => t.toLowerCase().includes(needle))
      );
    });
  }, [blocks, search, category]);

  async function act(kind: "linked" | "snapshot" | "fork", block: ReusableBlock) {
    if (!selectedSectionId) return;
    setBusy(`${block.block_id}:${kind}`);
    try {
      if (kind === "linked") {
        await api.insertLinked(document.id, block.block_id, selectedSectionId);
      } else if (kind === "snapshot") {
        await api.insertSnapshot(document.id, block.block_id, selectedSectionId);
      } else {
        await api.forkBlock(document.id, block.block_id, selectedSectionId);
      }
      await onReload();
    } finally {
      setBusy(null);
    }
  }

  return (
    <aside className="flex w-80 flex-col border-l border-slate-200 bg-panel">
      <div className="flex border-b border-slate-200 bg-white">
        {TABS.map((t) => (
          <button
            key={t.id}
            title={t.full}
            className={`flex-1 px-1 py-2 text-[11px] font-medium transition ${
              tab === t.id
                ? "border-b-2 border-brand text-brand-fg"
                : "border-b-2 border-transparent text-slate-400 hover:text-slate-600"
            }`}
            onClick={() => setTab(t.id)}
          >
            {t.short}
          </button>
        ))}
      </div>

      {tab === "blocks" && (
        <div className="flex min-h-0 flex-1 flex-col p-3">
          {!selectedSectionId && (
            <p className="mb-2 rounded bg-amber-50 px-2 py-1 text-[11px] text-amber-700">
              Select a section to insert blocks into.
            </p>
          )}
          <div className="relative mb-2">
            <Search
              size={13}
              className="absolute left-2 top-2 text-slate-400"
            />
            <input
              className="w-full rounded-md border border-slate-300 py-1.5 pl-7 pr-2 text-xs"
              placeholder="Search reusable blocks…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <select
            className="mb-2 w-full rounded-md border border-slate-300 px-2 py-1.5 text-xs"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
          >
            <option value="">All categories</option>
            {categories.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>

          <div className="scroll-thin min-h-0 flex-1 space-y-2 overflow-y-auto">
            {loadError && <p className="text-xs text-rose-600">{loadError}</p>}
            {!loadError && filtered.length === 0 && (
              <p className="text-xs text-slate-400">No matching blocks.</p>
            )}
            {filtered.map((blk) => (
              <div
                key={blk.block_id}
                className="rounded-lg border border-slate-200 bg-white p-2.5 shadow-card"
              >
                <div className="flex items-start gap-1.5">
                  <span className="text-xs font-semibold text-slate-800">
                    {blk.title}
                  </span>
                  <span className="ml-auto whitespace-nowrap rounded bg-slate-100 px-1 text-[10px] text-slate-500">
                    v{blk.version}
                  </span>
                </div>
                <div className="mt-1 flex items-center gap-1.5 text-[10px] text-slate-400">
                  <span>{blk.category}</span>
                  <Badge
                    tone={blk.status === "approved" ? "emerald" : "amber"}
                  >
                    {blk.status}
                  </Badge>
                  <button
                    className="ml-auto hover:underline"
                    onClick={() =>
                      setExpanded(
                        expanded === blk.block_id ? null : blk.block_id,
                      )
                    }
                  >
                    {expanded === blk.block_id ? "Hide" : "Preview"}
                  </button>
                </div>
                {expanded === blk.block_id && (
                  <pre className="scroll-thin mt-1.5 max-h-40 overflow-y-auto whitespace-pre-wrap rounded bg-slate-50 px-2 py-1 text-[11px] text-slate-600">
                    {blk.body}
                  </pre>
                )}
                <div className="mt-2 flex gap-1">
                  {(["linked", "snapshot", "fork"] as const).map((kind) => (
                    <button
                      key={kind}
                      className="flex-1 rounded-md border border-slate-300 px-1 py-1 text-[10px] font-medium hover:bg-slate-50 disabled:opacity-40"
                      disabled={!selectedSectionId || busy !== null}
                      onClick={() => act(kind, blk)}
                    >
                      {busy === `${blk.block_id}:${kind}`
                        ? "…"
                        : kind === "linked"
                          ? "Insert Linked"
                          : kind === "snapshot"
                            ? "Snapshot"
                            : "Fork & Edit"}
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {tab === "integrations" && (
        <div className="scroll-thin min-h-0 flex-1 overflow-y-auto p-3">
          <p className="mb-3 flex items-center gap-1.5 text-[11px] text-slate-400">
            <Plug size={13} />
            Integrations linked into this HLD, grouped by type.
          </p>
          {document.linked_integrations.length === 0 ? (
            <p className="text-xs text-slate-400">
              No integrations linked yet. Link them from the increment's
              Integration Docs screen.
            </p>
          ) : (
            <IntegrationGroups
              integrations={document.linked_integrations}
            />
          )}
        </div>
      )}

      {tab === "context" && (
        <div className="scroll-thin min-h-0 flex-1 overflow-y-auto p-3">
          <p className="mb-2 flex items-center gap-1.5 text-[11px] text-slate-400">
            <Layers3 size={13} />
            How this HLD connects to the enterprise TOGAF model.
          </p>

          {/* Top-level chain: Enterprise → Domain → Capability → AppGroup → Increment → HLD */}
          {archContext && archContext.chain.length > 0 && (
            <div className="mb-3 rounded-md border border-slate-200 bg-white p-2 text-[11px]">
              <div className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-slate-400">
                Top-level chain
              </div>
              <div className="flex flex-wrap items-center gap-1">
                <Badge tone="indigo">Enterprise</Badge>
                {archContext.chain.map((link, i) => (
                  <span key={i} className="flex items-center gap-1">
                    <ChevronRight size={11} className="text-slate-300" />
                    <span className="rounded bg-slate-100 px-1.5 py-0.5 text-slate-700">
                      {link.label ?? link.object_slug}
                    </span>
                  </span>
                ))}
              </div>
            </div>
          )}

          {!archContext && (
            <p className="text-[11px] text-slate-400">Loading…</p>
          )}

          {archContext?.layers.map((layer) => (
            <ContextLayerBlock
              key={layer.layer}
              layer={layer}
              options={contextOptions}
              busy={contextBusy}
              onAdd={addContextLink}
              onRemove={removeContextLink}
            />
          ))}
        </div>
      )}

      {tab === "references" && (
        <div className="scroll-thin min-h-0 flex-1 space-y-2 overflow-y-auto p-3">
          {document.reuse_instances.length === 0 ? (
            <p className="flex flex-col items-center gap-2 py-8 text-center text-xs text-slate-400">
              <Boxes size={28} className="text-slate-300" />
              No reused blocks in this document yet.
            </p>
          ) : (
            document.reuse_instances.map((r) => {
              const section = document.sections.find(
                (s) => s.id === r.section_id,
              );
              const m = MODE[r.reuse_mode];
              const Icon = m.icon;
              return (
                <div
                  key={r.id}
                  className="rounded-lg border border-slate-200 bg-white p-2.5 shadow-card"
                >
                  <div className="flex items-center gap-1.5">
                    <Badge tone={m.tone}>
                      <Icon size={10} />
                      {r.reuse_mode}
                    </Badge>
                    <span className="truncate text-xs font-semibold text-slate-700">
                      {r.title}
                    </span>
                  </div>
                  <p className="mt-1 text-[10px] text-slate-400">
                    {section
                      ? `§ ${section.number} ${section.title}`
                      : "Unassigned section"}
                  </p>
                </div>
              );
            })
          )}
        </div>
      )}

      {/* validation tab follows */}
      {tab === "validation" && (
        <section className="flex min-h-0 flex-1 flex-col p-3">
          <div className="mb-2 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-700">Validation</h2>
            <button
              className="rounded-md border border-slate-300 bg-white px-2 py-1 text-xs hover:bg-slate-50"
              onClick={onValidate}
            >
              Run checks
            </button>
          </div>
          <div className="scroll-thin min-h-0 flex-1 space-y-2 overflow-y-auto">
            {validation.length === 0 ? (
              <p className="flex flex-col items-center gap-2 py-8 text-center text-xs text-slate-400">
                <AlertCircle size={28} className="text-slate-300" />
                No issues. Run checks after editing.
              </p>
            ) : (
              validation.map((item, i) => (
                <div
                  key={i}
                  className={`rounded-md border px-2 py-1.5 text-xs ${
                    SEVERITY_STYLE[item.severity] ?? SEVERITY_STYLE.info
                  }`}
                >
                  <span className="font-semibold uppercase">
                    {item.severity}
                  </span>
                  <span className="ml-1">{item.message}</span>
                </div>
              ))
            )}
          </div>
        </section>
      )}
    </aside>
  );
}

// Per-layer types — drives the "+ Add" affordance for each layer.
const LAYER_TYPES: Record<string, ContextObjectType[]> = {
  "Business Layer": ["domain", "capability"],
  "Solution Layer": ["application_group", "architecture_increment"],
  Scope: ["application", "data_object", "data_domain"],
  "Technology Layer": ["technology_platform"],
  "Standards & Principles": ["standard", "principle"],
};

const TYPE_LABELS: Record<ContextObjectType, string> = {
  domain: "Domain",
  capability: "Capability",
  application_group: "Application Group",
  architecture_increment: "Architecture Increment",
  application: "Application",
  data_object: "Data Object",
  data_domain: "Data Domain",
  technology_platform: "Technology Platform",
  standard: "Standard",
  principle: "Principle",
  hld: "HLD",
};

function ContextLayerBlock({
  layer,
  options,
  busy,
  onAdd,
  onRemove,
}: {
  layer: { layer: string; rows: { object_type: ContextObjectType; object_slug: string; label: string | null }[] };
  options: Record<string, { slug: string; label: string }[]>;
  busy: boolean;
  onAdd: (objectType: ContextObjectType, objectSlug: string) => Promise<void>;
  onRemove: (
    objectType: ContextObjectType,
    objectSlug: string,
  ) => Promise<void>;
}) {
  const types = LAYER_TYPES[layer.layer] ?? [];
  const [pickerType, setPickerType] = useState<ContextObjectType | null>(null);
  const [pickerValue, setPickerValue] = useState<string>("");

  // architecture_increment is set at HLD creation and the operational tables —
  // we don't surface a picker for it, but we still show linked rows.
  const pickableTypes = types.filter((t) => t !== "architecture_increment");

  return (
    <div className="mb-3">
      <div className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-slate-400">
        {layer.layer}
      </div>
      <div className="space-y-1.5">
        {layer.rows.length === 0 && pickerType === null && (
          <p className="px-1 text-[11px] italic text-slate-300">
            Nothing linked yet.
          </p>
        )}
        {layer.rows.map((row) => (
          <div
            key={`${row.object_type}:${row.object_slug}`}
            className="flex items-center gap-2 rounded-md border border-slate-200 bg-white px-2 py-1 text-[11px]"
          >
            <Badge tone="slate" className="!px-1">
              {TYPE_LABELS[row.object_type]}
            </Badge>
            <span className="truncate text-slate-700">
              {row.label ?? row.object_slug}
            </span>
            <button
              className="ml-auto text-slate-400 hover:text-rose-600 disabled:opacity-40"
              disabled={busy || row.object_type === "architecture_increment"}
              title={
                row.object_type === "architecture_increment"
                  ? "Set at HLD creation"
                  : "Remove link"
              }
              onClick={() => onRemove(row.object_type, row.object_slug)}
            >
              <X size={12} />
            </button>
          </div>
        ))}

        {pickerType === null ? (
          pickableTypes.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {pickableTypes.map((t) => (
                <button
                  key={t}
                  className="inline-flex items-center gap-1 rounded-md border border-dashed border-slate-300 bg-white px-2 py-1 text-[11px] text-slate-600 hover:border-brand hover:text-brand-fg"
                  onClick={() => {
                    setPickerType(t);
                    setPickerValue("");
                  }}
                >
                  <Plus size={11} /> Add {TYPE_LABELS[t]}
                </button>
              ))}
            </div>
          )
        ) : (
          <div className="flex items-center gap-1 rounded-md border border-brand bg-brand-soft/30 px-2 py-1">
            <span className="text-[11px] text-slate-500">
              {TYPE_LABELS[pickerType]}:
            </span>
            <select
              className="min-w-0 flex-1 rounded border border-slate-300 px-1 py-0.5 text-[11px]"
              value={pickerValue}
              onChange={(e) => setPickerValue(e.target.value)}
            >
              <option value="">— pick —</option>
              {(options[pickerType] ?? []).map((opt) => (
                <option key={opt.slug} value={opt.slug}>
                  {opt.label}
                </option>
              ))}
            </select>
            <button
              className="rounded bg-brand px-2 py-0.5 text-[11px] text-white disabled:opacity-40"
              disabled={busy || !pickerValue}
              onClick={async () => {
                await onAdd(pickerType, pickerValue);
                setPickerType(null);
                setPickerValue("");
              }}
            >
              Add
            </button>
            <button
              className="text-slate-400 hover:text-slate-700"
              onClick={() => {
                setPickerType(null);
                setPickerValue("");
              }}
            >
              <X size={12} />
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

function IntegrationGroups({
  integrations,
}: {
  integrations: LinkedIntegration[];
}) {
  const byType = new Map<IntegrationType, LinkedIntegration[]>();
  for (const i of integrations) {
    const list = byType.get(i.type) ?? [];
    list.push(i);
    byType.set(i.type, list);
  }
  return (
    <>
      {INTEGRATION_GROUP_ORDER.map(({ type, label }) => {
        const list = byType.get(type);
        if (!list || list.length === 0) return null;
        return (
          <div key={type} className="mb-3">
            <div className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-slate-400">
              {label}
            </div>
            <div className="space-y-1">
              {list.map((i) => (
                <a
                  key={i.id}
                  href={
                    i.document_id !== null
                      ? `/integration-doc/${i.document_id}`
                      : "#"
                  }
                  className="block rounded-lg border border-slate-200 bg-white p-2.5 shadow-card hover:border-brand"
                >
                  <div className="text-xs font-semibold text-slate-800">
                    {i.name}
                  </div>
                  <div className="mt-0.5 text-[10px] text-slate-400">
                    {i.source_application || "—"} → {i.target_application || "—"}
                  </div>
                  <div className="mt-1 flex items-center gap-1.5">
                    <Badge tone="indigo">{i.type_label}</Badge>
                    <Badge tone={i.status === "approved" ? "emerald" : "slate"}>
                      {i.status}
                    </Badge>
                    {i.document_id === null && (
                      <Badge tone="amber">no doc</Badge>
                    )}
                  </div>
                </a>
              ))}
            </div>
          </div>
        );
      })}
    </>
  );
}
