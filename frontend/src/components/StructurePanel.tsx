import { useState } from "react";
import {
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Circle,
  IndentDecrease,
  IndentIncrease,
  MoreHorizontal,
  Pencil,
  Plus,
} from "lucide-react";
import { api } from "../api/client";
import type { HldDocument, Section, SectionKind, ValidationItem } from "../types";
import { Badge } from "./ui";

interface Props {
  document: HldDocument;
  selectedId: number | null;
  validation: ValidationItem[];
  onSelect: (id: number) => void;
  onReload: () => Promise<HldDocument>;
}

type StructureItem = {
  id: number;
  parent_id: number | null;
  order_index: number;
};

const LEGEND: { label: string; cls: string }[] = [
  { label: "Template", cls: "bg-slate-300" },
  { label: "Custom", cls: "bg-indigo-400" },
  { label: "Required", cls: "bg-rose-400" },
  { label: "Optional", cls: "bg-slate-200" },
  { label: "Reused", cls: "bg-indigo-500" },
  { label: "Forked", cls: "bg-amber-500" },
  { label: "Snapshot", cls: "bg-slate-500" },
];

export default function StructurePanel({
  document,
  selectedId,
  validation,
  onSelect,
  onReload,
}: Props) {
  const [busy, setBusy] = useState(false);
  const [menuFor, setMenuFor] = useState<number | null>(null);
  // Inline-edit target: a section id (rename), "chapter", or "sub:<parentId>".
  const [editing, setEditing] = useState<string | null>(null);
  const [draft, setDraft] = useState("");

  const chapters = [...document.sections]
    .filter((s) => s.parent_id === null)
    .sort((a, b) => a.order_index - b.order_index);
  const childMap = new Map<number, Section[]>();
  for (const ch of chapters) {
    childMap.set(
      ch.id,
      document.sections
        .filter((s) => s.parent_id === ch.id)
        .sort((a, b) => a.order_index - b.order_index),
    );
  }

  const severityFor = (id: number) =>
    validation.find((v) => v.section_id === id)?.severity ?? null;
  const hasReuse = (id: number) =>
    document.reuse_instances.some((r) => r.section_id === id);

  async function commitStructure(
    orderedChapters: Section[],
    map: Map<number, Section[]>,
  ) {
    const items: StructureItem[] = [];
    orderedChapters.forEach((ch, ci) => {
      items.push({ id: ch.id, parent_id: null, order_index: ci });
      (map.get(ch.id) ?? []).forEach((sub, si) => {
        items.push({ id: sub.id, parent_id: ch.id, order_index: si });
      });
    });
    setBusy(true);
    setMenuFor(null);
    try {
      await api.updateStructure(document.id, items);
      await onReload();
    } finally {
      setBusy(false);
    }
  }

  function swap<T>(arr: T[], i: number, j: number): T[] {
    const next = [...arr];
    [next[i], next[j]] = [next[j], next[i]];
    return next;
  }

  function moveChapter(idx: number, dir: -1 | 1) {
    const j = idx + dir;
    if (j < 0 || j >= chapters.length) return;
    commitStructure(swap(chapters, idx, j), childMap);
  }

  function moveSub(chapterId: number, idx: number, dir: -1 | 1) {
    const kids = childMap.get(chapterId) ?? [];
    const j = idx + dir;
    if (j < 0 || j >= kids.length) return;
    const map = new Map(childMap);
    map.set(chapterId, swap(kids, idx, j));
    commitStructure(chapters, map);
  }

  function promote(sub: Section) {
    const parentIdx = chapters.findIndex((c) => c.id === sub.parent_id);
    if (parentIdx < 0) return;
    const map = new Map(childMap);
    map.set(
      sub.parent_id!,
      (map.get(sub.parent_id!) ?? []).filter((s) => s.id !== sub.id),
    );
    const next = [...chapters];
    next.splice(parentIdx + 1, 0, sub);
    commitStructure(next, map);
  }

  function demote(chapter: Section, idx: number) {
    if (idx === 0 || (childMap.get(chapter.id)?.length ?? 0) > 0) return;
    const prev = chapters[idx - 1];
    const map = new Map(childMap);
    map.set(prev.id, [...(map.get(prev.id) ?? []), chapter]);
    commitStructure(
      chapters.filter((c) => c.id !== chapter.id),
      map,
    );
  }

  function startEdit(key: string, value: string) {
    setMenuFor(null);
    setEditing(key);
    setDraft(value);
  }

  async function submitEdit() {
    const key = editing;
    const value = draft.trim();
    setEditing(null);
    if (!value || !key) return;
    setBusy(true);
    try {
      if (key === "chapter") {
        await api.addChapter(document.id, value);
      } else if (key.startsWith("sub:")) {
        await api.addSubchapter(document.id, Number(key.slice(4)), value);
      } else {
        await api.updateSection(document.id, Number(key), { title: value });
      }
      await onReload();
    } finally {
      setBusy(false);
    }
  }

  function StatusIcon({ section }: { section: Section }) {
    const sev = severityFor(section.id);
    if (sev === "error")
      return <AlertCircle size={15} className="text-rose-500" />;
    if (sev === "warning")
      return <AlertTriangle size={15} className="text-amber-500" />;
    if (section.content.trim())
      return <CheckCircle2 size={15} className="text-emerald-500" />;
    if (section.kind === "template_required")
      return <Circle size={15} className="text-rose-300" />;
    return <Circle size={15} className="text-slate-300" />;
  }

  function kindBadge(kind: SectionKind) {
    if (kind === "custom") return <Badge tone="indigo">Custom</Badge>;
    if (kind === "template_required")
      return <Badge tone="rose">Required</Badge>;
    return null;
  }

  function EditInput({ onCancel }: { onCancel: () => void }) {
    return (
      <input
        autoFocus
        className="w-full rounded border border-brand px-2 py-1 text-sm outline-none"
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") submitEdit();
          if (e.key === "Escape") onCancel();
        }}
        onBlur={() => (editing?.match(/^\d+$/) ? submitEdit() : onCancel())}
      />
    );
  }

  function Row({
    section,
    depth,
    idx,
    siblingCount,
  }: {
    section: Section;
    depth: number;
    idx: number;
    siblingCount: number;
  }) {
    const selected = section.id === selectedId;
    const isChapter = section.parent_id === null;
    const editKey = String(section.id);
    const menuOpen = menuFor === section.id;

    if (editing === editKey) {
      return (
        <div style={{ paddingLeft: 10 + depth * 16 }} className="px-2 py-1">
          <EditInput onCancel={() => setEditing(null)} />
        </div>
      );
    }

    return (
      <div>
        <div
          className={`group flex items-center gap-1.5 pr-1.5 ${
            selected
              ? "border-l-2 border-brand bg-brand-soft"
              : "border-l-2 border-transparent hover:bg-slate-100"
          }`}
          style={{ paddingLeft: 8 + depth * 16 }}
        >
          <button
            className="flex min-w-0 flex-1 items-center gap-1.5 py-1.5 text-left"
            onClick={() => onSelect(section.id)}
          >
            <StatusIcon section={section} />
            <span className="w-7 shrink-0 text-xs tabular-nums text-slate-400">
              {section.number}
            </span>
            <span
              className={`truncate text-sm ${
                selected
                  ? "font-semibold text-slate-900"
                  : "text-slate-700"
              }`}
            >
              {section.title}
            </span>
            {hasReuse(section.id) && (
              <span
                title="Contains reused blocks"
                className="h-1.5 w-1.5 shrink-0 rounded-full bg-indigo-500"
              />
            )}
          </button>
          {kindBadge(section.kind)}
          <button
            className="opacity-0 transition group-hover:opacity-100"
            onClick={() => setMenuFor(menuOpen ? null : section.id)}
          >
            <MoreHorizontal
              size={15}
              className="text-slate-400 hover:text-slate-700"
            />
          </button>
        </div>

        {menuOpen && (
          <div
            className="flex flex-wrap gap-1 bg-slate-50 py-1.5"
            style={{ paddingLeft: 24 + depth * 16, paddingRight: 8 }}
          >
            <MenuBtn
              icon={<Pencil size={12} />}
              label="Rename"
              onClick={() => startEdit(editKey, section.title)}
            />
            <MenuBtn
              icon={<ChevronUp size={12} />}
              label="Up"
              disabled={idx === 0}
              onClick={() =>
                isChapter
                  ? moveChapter(idx, -1)
                  : moveSub(section.parent_id!, idx, -1)
              }
            />
            <MenuBtn
              icon={<ChevronDown size={12} />}
              label="Down"
              disabled={idx === siblingCount - 1}
              onClick={() =>
                isChapter
                  ? moveChapter(idx, 1)
                  : moveSub(section.parent_id!, idx, 1)
              }
            />
            {isChapter ? (
              <MenuBtn
                icon={<IndentIncrease size={12} />}
                label="Demote"
                disabled={
                  idx === 0 || (childMap.get(section.id)?.length ?? 0) > 0
                }
                onClick={() => demote(section, idx)}
              />
            ) : (
              <MenuBtn
                icon={<IndentDecrease size={12} />}
                label="Promote"
                onClick={() => promote(section)}
              />
            )}
            {isChapter && (
              <MenuBtn
                icon={<Plus size={12} />}
                label="Subchapter"
                onClick={() => startEdit(`sub:${section.id}`, "")}
              />
            )}
          </div>
        )}

        {editing === `sub:${section.id}` && (
          <div
            style={{ paddingLeft: 24 + depth * 16 }}
            className="px-2 py-1"
          >
            <EditInput onCancel={() => setEditing(null)} />
          </div>
        )}
      </div>
    );
  }

  return (
    <aside className="flex w-72 flex-col border-r border-slate-200 bg-panel">
      <div className="flex items-center justify-between border-b border-slate-200 px-3 py-2.5">
        <h2 className="text-sm font-semibold text-slate-700">HLD Structure</h2>
        <button
          className="inline-flex items-center gap-1 rounded-md border border-slate-300 bg-white px-2 py-1 text-xs font-medium text-slate-600 hover:bg-slate-50 disabled:opacity-50"
          disabled={busy}
          onClick={() => startEdit("chapter", "")}
        >
          <Plus size={13} />
          Add Chapter
        </button>
      </div>

      <div className="scroll-thin min-h-0 flex-1 overflow-y-auto py-1">
        {chapters.map((chapter, ci) => {
          const kids = childMap.get(chapter.id) ?? [];
          return (
            <div key={chapter.id}>
              <Row
                section={chapter}
                depth={0}
                idx={ci}
                siblingCount={chapters.length}
              />
              {kids.map((sub, si) => (
                <Row
                  key={sub.id}
                  section={sub}
                  depth={1}
                  idx={si}
                  siblingCount={kids.length}
                />
              ))}
            </div>
          );
        })}
        {editing === "chapter" && (
          <div className="px-2 py-1 pl-3">
            <EditInput onCancel={() => setEditing(null)} />
          </div>
        )}
      </div>

      <div className="border-t border-slate-200 px-3 py-2">
        <div className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-slate-400">
          Legend
        </div>
        <div className="flex flex-wrap gap-x-3 gap-y-1">
          {LEGEND.map((l) => (
            <span
              key={l.label}
              className="flex items-center gap-1 text-[10px] text-slate-500"
            >
              <span className={`h-2 w-2 rounded-sm ${l.cls}`} />
              {l.label}
            </span>
          ))}
        </div>
      </div>
    </aside>
  );
}

function MenuBtn({
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
      className="inline-flex items-center gap-1 rounded border border-slate-200 bg-white px-1.5 py-1 text-[11px] text-slate-600 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40"
      disabled={disabled}
      onClick={onClick}
    >
      {icon}
      {label}
    </button>
  );
}
