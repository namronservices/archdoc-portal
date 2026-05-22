import { useEffect, useMemo, useState } from "react";
import {
  AlertCircle,
  Boxes,
  Camera,
  GitFork,
  Layers3,
  Link2,
  Search,
} from "lucide-react";
import { api } from "../api/client";
import type { HldDocument, ReusableBlock, ValidationItem } from "../types";
import { Badge } from "./ui";

type Tab = "blocks" | "context" | "references" | "validation";

const TABS: { id: Tab; short: string; full: string }[] = [
  { id: "blocks", short: "Blocks", full: "Reusable Blocks" },
  { id: "context", short: "Context", full: "Architecture Context" },
  { id: "references", short: "References", full: "Linked References" },
  { id: "validation", short: "Validation", full: "Validation" },
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

  const b = document.breadcrumb;
  const contextLayers: { layer: string; rows: { label: string; value: string | null }[] }[] =
    [
      {
        layer: "Business Layer",
        rows: [
          { label: "Domain", value: b.repository ?? null },
          { label: "Capabilities", value: null },
          { label: "Business Process (BPMN)", value: null },
        ],
      },
      {
        layer: "Solution Layer",
        rows: [
          { label: "Application Group", value: b.application_group ?? null },
          { label: "Architecture Increment", value: b.increment ?? null },
          { label: "Architecture State", value: null },
        ],
      },
      {
        layer: "Scope",
        rows: [
          { label: "Applications", value: null },
          { label: "Integrations", value: null },
          { label: "Data Objects", value: null },
        ],
      },
      {
        layer: "Technology Layer",
        rows: [
          { label: "Technology Platforms", value: null },
          { label: "Deployment Environments", value: null },
        ],
      },
      {
        layer: "Standards & Principles",
        rows: [
          { label: "Linked Standards", value: null },
          { label: "Linked Principles", value: null },
        ],
      },
    ];

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

      {tab === "context" && (
        <div className="scroll-thin min-h-0 flex-1 overflow-y-auto p-3">
          <p className="mb-3 flex items-center gap-1.5 text-[11px] text-slate-400">
            <Layers3 size={13} />
            How this HLD connects to the enterprise architecture model.
          </p>
          {contextLayers.map((group) => (
            <div key={group.layer} className="mb-3">
              <div className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-slate-400">
                {group.layer}
              </div>
              <div className="space-y-0.5">
                {group.rows.map((r) => (
                  <div
                    key={r.label}
                    className="flex items-center gap-2 rounded px-1.5 py-1 text-xs hover:bg-white"
                  >
                    <span className="text-slate-500">{r.label}</span>
                    {r.value ? (
                      <span className="ml-auto font-medium text-slate-800">
                        {r.value}
                      </span>
                    ) : (
                      <span className="ml-auto text-[11px] italic text-slate-300">
                        Not linked yet
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          ))}
          <p className="mt-2 border-t border-slate-200 pt-2 text-[11px] text-slate-400">
            Deeper enterprise-model linking (capabilities, BPMN, data objects)
            arrives in a later phase.
          </p>
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
