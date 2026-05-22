import { useState } from "react";
import { api } from "../api/client";
import type { BlockCompare, ReuseInstance, ReuseMode } from "../types";
import CodeEditor from "./CodeEditor";

const STYLE: Record<
  ReuseMode,
  { card: string; badge: string; label: string }
> = {
  linked: {
    card: "border-blue-300 bg-blue-50",
    badge: "bg-blue-600",
    label: "REUSED BLOCK (LINKED)",
  },
  snapshot: {
    card: "border-slate-400 bg-slate-100",
    badge: "bg-slate-600",
    label: "SNAPSHOT BLOCK",
  },
  forked: {
    card: "border-orange-300 bg-orange-50",
    badge: "bg-orange-600",
    label: "FORKED BLOCK",
  },
};

interface Props {
  documentId: number;
  instance: ReuseInstance;
  onReload: () => Promise<unknown>;
}

/** A section-attached card rendering one reused/snapshot/forked block. */
export default function ReuseBlockCard({
  documentId,
  instance,
  onReload,
}: Props) {
  const style = STYLE[instance.reuse_mode];
  const isFork = instance.reuse_mode === "forked";
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState(false);
  const [body, setBody] = useState(instance.body);
  const [rationale, setRationale] = useState(instance.rationale);
  const [compare, setCompare] = useState<BlockCompare | null>(null);
  const [busy, setBusy] = useState(false);

  const stale =
    instance.reuse_mode === "linked" &&
    !!instance.library_version &&
    instance.library_version !== instance.source_version;

  async function remove() {
    if (!window.confirm("Remove this reused block?")) return;
    await api.deleteReuseInstance(documentId, instance.id);
    await onReload();
  }

  async function saveFork() {
    setBusy(true);
    try {
      await api.updateReuseInstance(documentId, instance.id, { body });
      setEditing(false);
      await onReload();
    } finally {
      setBusy(false);
    }
  }

  async function saveRationale() {
    if (rationale === instance.rationale) return;
    await api.updateReuseInstance(documentId, instance.id, { rationale });
    await onReload();
  }

  async function runCompare() {
    if (!instance.derived_block_id) return;
    if (compare) {
      setCompare(null);
      return;
    }
    setCompare(
      await api.compareBlocks(instance.block_id, instance.derived_block_id),
    );
  }

  async function promote() {
    if (!instance.derived_block_id) return;
    setBusy(true);
    try {
      await api.promoteBlock(instance.derived_block_id);
      await onReload();
    } finally {
      setBusy(false);
    }
  }

  const subtitle =
    instance.reuse_mode === "linked"
      ? `Source: library · v${instance.source_version}`
      : instance.reuse_mode === "snapshot"
        ? `Snapshot of ${instance.block_id} · v${instance.source_version}`
        : `Forked from ${instance.block_id} v${instance.source_version}`;

  return (
    <div className={`rounded-lg border ${style.card}`}>
      <div className="flex items-center gap-2 px-3 py-2">
        <span
          className={`rounded px-1.5 py-0.5 text-[10px] font-semibold text-white ${style.badge}`}
        >
          {style.label}
        </span>
        <span className="text-sm font-semibold text-slate-800">
          {instance.title}
        </span>
        {instance.broken && (
          <span className="rounded bg-rose-100 px-1.5 py-0.5 text-[10px] font-semibold text-rose-700">
            REFERENCE BROKEN
          </span>
        )}
        {stale && (
          <span className="rounded bg-amber-100 px-1.5 py-0.5 text-[10px] font-semibold text-amber-700">
            UPDATE AVAILABLE · v{instance.library_version}
          </span>
        )}
        <button
          className="ml-auto text-xs text-slate-500 hover:underline"
          onClick={remove}
        >
          Remove
        </button>
      </div>

      <div className="flex items-center gap-3 border-t border-black/5 px-3 py-1.5 text-[11px] text-slate-500">
        <span>{subtitle}</span>
        {instance.library_status && (
          <span className="uppercase">status: {instance.library_status}</span>
        )}
        <button
          className="ml-auto hover:underline"
          onClick={() => setOpen((v) => !v)}
        >
          {open ? "Hide" : "Preview"}
        </button>
        {isFork && !editing && (
          <button className="hover:underline" onClick={() => setEditing(true)}>
            Open
          </button>
        )}
        {isFork && (
          <button className="hover:underline" onClick={runCompare}>
            {compare ? "Close compare" : "Compare"}
          </button>
        )}
        {isFork && (
          <button
            className="hover:underline disabled:opacity-50"
            disabled={busy}
            onClick={promote}
          >
            Promote
          </button>
        )}
      </div>

      {open && !editing && (
        <pre className="max-h-60 overflow-y-auto whitespace-pre-wrap border-t border-black/5 px-3 py-2 text-xs text-slate-700">
          {instance.body || "(empty)"}
        </pre>
      )}

      {isFork && editing && (
        <div className="border-t border-black/5 p-3">
          <CodeEditor defaultValue={body} onChange={setBody} />
          <div className="mt-2 flex gap-2">
            <button
              className="rounded bg-slate-800 px-2 py-1 text-xs text-white disabled:opacity-50"
              disabled={busy}
              onClick={saveFork}
            >
              {busy ? "Saving…" : "Save fork"}
            </button>
            <button
              className="rounded border border-slate-300 px-2 py-1 text-xs"
              onClick={() => {
                setBody(instance.body);
                setEditing(false);
              }}
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {isFork && (
        <div className="border-t border-black/5 px-3 py-2">
          <label className="mb-1 block text-[11px] uppercase text-slate-400">
            Fork rationale
          </label>
          <input
            className="w-full rounded border border-slate-300 px-2 py-1 text-xs"
            placeholder="Why was this block forked?"
            value={rationale}
            onChange={(e) => setRationale(e.target.value)}
            onBlur={saveRationale}
          />
        </div>
      )}

      {compare && (
        <div className="grid grid-cols-2 gap-3 border-t border-black/5 p-3">
          <div>
            <p className="mb-1 text-[11px] uppercase text-slate-400">
              Source {compare.source ? `v${compare.source.version}` : ""}
            </p>
            <pre className="max-h-48 overflow-y-auto whitespace-pre-wrap rounded border border-slate-200 bg-white px-2 py-1 text-xs">
              {compare.source?.body ?? "(missing)"}
            </pre>
          </div>
          <div>
            <p className="mb-1 text-[11px] uppercase text-slate-400">
              Fork {compare.derived ? `v${compare.derived.version}` : ""}
            </p>
            <pre className="max-h-48 overflow-y-auto whitespace-pre-wrap rounded border border-slate-200 bg-white px-2 py-1 text-xs">
              {compare.derived?.body ?? "(missing)"}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}
