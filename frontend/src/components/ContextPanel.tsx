import { useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import type { HldDocument, ReusableBlock, ValidationItem } from "../types";

type Tab = "blocks" | "context" | "references" | "validation";

const TABS: { id: Tab; label: string }[] = [
  { id: "blocks", label: "Reusable Blocks" },
  { id: "context", label: "Architecture Context" },
  { id: "references", label: "Linked References" },
  { id: "validation", label: "Validation" },
];

const SEVERITY_STYLE: Record<string, string> = {
  error: "border-rose-300 bg-rose-50 text-rose-700",
  warning: "border-amber-300 bg-amber-50 text-amber-700",
  info: "border-sky-300 bg-sky-50 text-sky-700",
};

const MODE_STYLE: Record<string, string> = {
  linked: "bg-blue-100 text-blue-700",
  snapshot: "bg-slate-200 text-slate-700",
  forked: "bg-orange-100 text-orange-700",
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

  return (
    <aside className="flex w-80 flex-col border-l border-slate-200 bg-panel">
      <div className="flex flex-wrap border-b border-slate-200">
        {TABS.map((t) => (
          <button
            key={t.id}
            className={`px-2.5 py-2 text-xs font-medium ${
              tab === t.id
                ? "border-b-2 border-slate-800 text-slate-800"
                : "text-slate-400 hover:text-slate-600"
            }`}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "blocks" && (
        <div className="flex min-h-0 flex-1 flex-col p-3">
          {!selectedSectionId && (
            <p className="mb-2 text-[11px] text-amber-600">
              Select a section to insert blocks into.
            </p>
          )}
          <input
            className="mb-2 w-full rounded border border-slate-300 px-2 py-1 text-xs"
            placeholder="Search reusable blocks…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <select
            className="mb-2 w-full rounded border border-slate-300 px-2 py-1 text-xs"
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

          <div className="min-h-0 flex-1 space-y-2 overflow-y-auto">
            {loadError && (
              <p className="text-xs text-rose-600">{loadError}</p>
            )}
            {!loadError && filtered.length === 0 && (
              <p className="text-xs text-slate-400">No matching blocks.</p>
            )}
            {filtered.map((b) => (
              <div
                key={b.block_id}
                className="rounded border border-slate-200 bg-white p-2"
              >
                <div className="flex items-start gap-1.5">
                  <span className="text-xs font-semibold text-slate-800">
                    {b.title}
                  </span>
                  <span className="ml-auto whitespace-nowrap rounded bg-slate-100 px-1 text-[10px] text-slate-500">
                    v{b.version}
                  </span>
                </div>
                <div className="mt-0.5 flex items-center gap-1.5 text-[10px] text-slate-400">
                  <span>{b.category}</span>
                  <span
                    className={`rounded px-1 ${
                      b.status === "approved"
                        ? "bg-emerald-100 text-emerald-700"
                        : "bg-amber-100 text-amber-700"
                    }`}
                  >
                    {b.status}
                  </span>
                  <button
                    className="ml-auto hover:underline"
                    onClick={() =>
                      setExpanded(expanded === b.block_id ? null : b.block_id)
                    }
                  >
                    {expanded === b.block_id ? "Hide" : "Preview"}
                  </button>
                </div>
                {expanded === b.block_id && (
                  <pre className="mt-1.5 max-h-40 overflow-y-auto whitespace-pre-wrap rounded bg-slate-50 px-2 py-1 text-[11px] text-slate-600">
                    {b.body}
                  </pre>
                )}
                <div className="mt-2 flex gap-1">
                  {(["linked", "snapshot", "fork"] as const).map((kind) => (
                    <button
                      key={kind}
                      className="flex-1 rounded border border-slate-300 px-1 py-1 text-[10px] hover:bg-slate-50 disabled:opacity-40"
                      disabled={!selectedSectionId || busy !== null}
                      onClick={() => act(kind, b)}
                    >
                      {busy === `${b.block_id}:${kind}`
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
        <section className="p-3">
          <p className="text-xs text-slate-400">
            Linking to Enterprise Repository objects arrives in a later phase.
          </p>
        </section>
      )}

      {tab === "references" && (
        <div className="min-h-0 flex-1 space-y-2 overflow-y-auto p-3">
          {document.reuse_instances.length === 0 ? (
            <p className="text-xs text-slate-400">
              No reused blocks in this document yet.
            </p>
          ) : (
            document.reuse_instances.map((r) => {
              const section = document.sections.find(
                (s) => s.id === r.section_id,
              );
              return (
                <div
                  key={r.id}
                  className="rounded border border-slate-200 bg-white p-2"
                >
                  <div className="flex items-center gap-1.5">
                    <span
                      className={`rounded px-1 text-[10px] font-semibold uppercase ${
                        MODE_STYLE[r.reuse_mode]
                      }`}
                    >
                      {r.reuse_mode}
                    </span>
                    <span className="text-xs font-semibold text-slate-700">
                      {r.title}
                    </span>
                  </div>
                  <p className="mt-0.5 text-[10px] text-slate-400">
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
            <h2 className="text-sm font-semibold">Validation</h2>
            <button
              className="rounded border border-slate-300 px-2 py-1 text-xs hover:bg-white"
              onClick={onValidate}
            >
              Run checks
            </button>
          </div>
          <div className="min-h-0 flex-1 space-y-2 overflow-y-auto">
            {validation.length === 0 ? (
              <p className="text-xs text-slate-400">
                No issues. Run checks after editing.
              </p>
            ) : (
              validation.map((item, i) => (
                <div
                  key={i}
                  className={`rounded border px-2 py-1.5 text-xs ${
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
