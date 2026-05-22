import { useState } from "react";
import {
  Camera,
  Check,
  Eye,
  GitCompare,
  GitFork,
  Link2,
  MoreVertical,
  Rocket,
  SquarePen,
  Trash2,
  TriangleAlert,
} from "lucide-react";
import { api } from "../api/client";
import type { BlockCompare, ReuseInstance, ReuseMode } from "../types";
import CodeEditor from "./CodeEditor";

const STYLE: Record<
  ReuseMode,
  { card: string; badge: string; label: string; icon: typeof Link2 }
> = {
  linked: {
    card: "border-indigo-300 bg-indigo-50/70",
    badge: "bg-indigo-600",
    label: "REUSED BLOCK (LINKED)",
    icon: Link2,
  },
  snapshot: {
    card: "border-slate-300 bg-slate-50",
    badge: "bg-slate-500",
    label: "SNAPSHOT BLOCK",
    icon: Camera,
  },
  forked: {
    card: "border-amber-300 bg-amber-50/80",
    badge: "bg-amber-600",
    label: "FORKED BLOCK",
    icon: GitFork,
  },
};

interface Props {
  documentId: number;
  instance: ReuseInstance;
  onReload: () => Promise<unknown>;
}

/** A section-attached card rendering one reused / snapshot / forked block. */
export default function ReuseBlockCard({
  documentId,
  instance,
  onReload,
}: Props) {
  const style = STYLE[instance.reuse_mode];
  const Icon = style.icon;
  const isFork = instance.reuse_mode === "forked";
  const isLinked = instance.reuse_mode === "linked";

  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState(false);
  const [body, setBody] = useState(instance.body);
  const [rationale, setRationale] = useState(instance.rationale);
  const [compare, setCompare] = useState<BlockCompare | null>(null);
  const [menu, setMenu] = useState(false);
  const [busy, setBusy] = useState(false);

  const stale =
    isLinked &&
    !!instance.library_version &&
    instance.library_version !== instance.source_version;

  async function run<T>(fn: () => Promise<T>) {
    setBusy(true);
    setMenu(false);
    try {
      await fn();
    } finally {
      setBusy(false);
    }
  }

  const remove = () =>
    run(async () => {
      await api.deleteReuseInstance(documentId, instance.id);
      await onReload();
    });

  const forkAndEdit = () =>
    run(async () => {
      await api.forkBlock(documentId, instance.block_id, instance.section_id);
      await api.deleteReuseInstance(documentId, instance.id);
      await onReload();
    });

  const saveFork = () =>
    run(async () => {
      await api.updateReuseInstance(documentId, instance.id, { body });
      setEditing(false);
      await onReload();
    });

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

  const promote = () =>
    run(async () => {
      if (instance.derived_block_id) {
        await api.promoteBlock(instance.derived_block_id);
        await onReload();
      }
    });

  const subtitle = isLinked
    ? `Source: Reusable Block Library · v${instance.source_version}`
    : instance.reuse_mode === "snapshot"
      ? `Snapshot of ${instance.block_id} · v${instance.source_version}`
      : `Forked from ${instance.block_id} v${instance.source_version}`;

  return (
    <div className={`rounded-lg border ${style.card} shadow-card`}>
      {/* header */}
      <div className="flex items-center gap-2 px-3 pt-2.5">
        <span
          className={`inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-bold tracking-wide text-white ${style.badge}`}
        >
          <Icon size={11} />
          {style.label}
        </span>
        {instance.broken && (
          <span className="inline-flex items-center gap-1 rounded bg-rose-100 px-1.5 py-0.5 text-[10px] font-semibold text-rose-700">
            <TriangleAlert size={11} />
            REFERENCE BROKEN
          </span>
        )}
        <div className="relative ml-auto">
          <button
            className="rounded p-0.5 text-slate-400 hover:bg-black/5 hover:text-slate-700"
            onClick={() => setMenu((v) => !v)}
          >
            <MoreVertical size={16} />
          </button>
          {menu && (
            <div className="absolute right-0 z-20 mt-1 w-40 overflow-hidden rounded-md border border-slate-200 bg-white py-1 shadow-panel">
              {isFork && (
                <MenuItem
                  icon={<Rocket size={13} />}
                  label="Promote to library"
                  onClick={promote}
                />
              )}
              <MenuItem
                icon={<Trash2 size={13} />}
                label="Remove"
                danger
                onClick={remove}
              />
            </div>
          )}
        </div>
      </div>

      {/* title + status */}
      <div className="px-3 pb-2 pt-1">
        <div className="text-sm font-semibold text-slate-800">
          {instance.title}
        </div>
        <div className="mt-0.5 flex flex-wrap items-center gap-2 text-[11px] text-slate-500">
          <span>{subtitle}</span>
          {isLinked &&
            (stale ? (
              <span className="inline-flex items-center gap-1 font-medium text-amber-600">
                <TriangleAlert size={11} />
                Update available · v{instance.library_version}
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 font-medium text-emerald-600">
                <Check size={11} />
                Up to date
              </span>
            ))}
          {isFork && !instance.rationale.trim() && (
            <span className="inline-flex items-center gap-1 font-medium text-amber-600">
              <TriangleAlert size={11} />
              Needs rationale
            </span>
          )}
        </div>
      </div>

      {/* actions */}
      <div className="flex items-center gap-1.5 border-t border-black/5 px-3 py-1.5">
        <CardBtn
          icon={<Eye size={13} />}
          label={open ? "Hide" : "Preview"}
          onClick={() => setOpen((v) => !v)}
        />
        {isLinked && (
          <CardBtn
            icon={<GitFork size={13} />}
            label="Fork & Edit"
            disabled={busy}
            onClick={forkAndEdit}
          />
        )}
        {isFork && !editing && (
          <CardBtn
            icon={<SquarePen size={13} />}
            label="Open"
            onClick={() => setEditing(true)}
          />
        )}
        {isFork && (
          <CardBtn
            icon={<GitCompare size={13} />}
            label={compare ? "Close compare" : "Compare"}
            onClick={runCompare}
          />
        )}
      </div>

      {open && !editing && (
        <pre className="scroll-thin max-h-56 overflow-y-auto whitespace-pre-wrap border-t border-black/5 px-3 py-2 text-xs text-slate-700">
          {instance.body || "(empty)"}
        </pre>
      )}

      {isFork && editing && (
        <div className="border-t border-black/5 p-3">
          <CodeEditor defaultValue={body} onChange={setBody} />
          <div className="mt-2 flex gap-2">
            <button
              className="rounded-md bg-brand px-2.5 py-1 text-xs font-medium text-white disabled:opacity-50"
              disabled={busy}
              onClick={saveFork}
            >
              {busy ? "Saving…" : "Save fork"}
            </button>
            <button
              className="rounded-md border border-slate-300 px-2.5 py-1 text-xs"
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
          <label className="mb-1 block text-[10px] font-semibold uppercase tracking-wide text-slate-400">
            Fork rationale
          </label>
          <input
            className="w-full rounded border border-slate-300 bg-white px-2 py-1 text-xs"
            placeholder="Why was this block forked?"
            value={rationale}
            onChange={(e) => setRationale(e.target.value)}
            onBlur={saveRationale}
          />
        </div>
      )}

      {compare && (
        <div className="grid grid-cols-2 gap-3 border-t border-black/5 p-3">
          {(["source", "derived"] as const).map((side) => {
            const b = compare[side];
            return (
              <div key={side}>
                <p className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-slate-400">
                  {side === "source" ? "Original" : "Fork"}
                  {b ? ` · v${b.version}` : ""}
                </p>
                <pre className="scroll-thin max-h-48 overflow-y-auto whitespace-pre-wrap rounded border border-slate-200 bg-white px-2 py-1 text-xs">
                  {b?.body ?? "(missing)"}
                </pre>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function CardBtn({
  icon,
  label,
  onClick,
  disabled,
}: {
  icon: React.ReactNode;
  label: string;
  onClick: () => void;
  disabled?: boolean;
}) {
  return (
    <button
      className="inline-flex items-center gap-1 rounded-md border border-slate-300 bg-white px-2 py-1 text-[11px] font-medium text-slate-600 hover:bg-slate-50 disabled:opacity-50"
      disabled={disabled}
      onClick={onClick}
    >
      {icon}
      {label}
    </button>
  );
}

function MenuItem({
  icon,
  label,
  onClick,
  danger,
}: {
  icon: React.ReactNode;
  label: string;
  onClick: () => void;
  danger?: boolean;
}) {
  return (
    <button
      className={`flex w-full items-center gap-2 px-3 py-1.5 text-left text-xs hover:bg-slate-50 ${
        danger ? "text-rose-600" : "text-slate-700"
      }`}
      onClick={onClick}
    >
      {icon}
      {label}
    </button>
  );
}
