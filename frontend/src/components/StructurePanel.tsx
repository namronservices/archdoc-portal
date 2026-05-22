import { useState } from "react";
import { api } from "../api/client";
import type { HldDocument, Section, SectionKind, ValidationItem } from "../types";

const KIND_BADGE: Record<SectionKind, { label: string; cls: string }> = {
  template_required: {
    label: "Required",
    cls: "bg-rose-100 text-rose-700",
  },
  template_optional: {
    label: "Template",
    cls: "bg-slate-200 text-slate-600",
  },
  custom: {
    label: "Custom",
    cls: "bg-indigo-100 text-indigo-700",
  },
};

interface Props {
  document: HldDocument;
  selectedId: number | null;
  validation: ValidationItem[];
  onSelect: (id: number) => void;
  onReload: () => Promise<HldDocument>;
}

export default function StructurePanel({
  document,
  selectedId,
  validation,
  onSelect,
  onReload,
}: Props) {
  const [busy, setBusy] = useState(false);

  const chapters = document.sections.filter((s) => s.parent_id === null);
  const childrenOf = (id: number) =>
    document.sections.filter((s) => s.parent_id === id);

  const severityFor = (sectionId: number): string | null => {
    const hit = validation.find((v) => v.section_id === sectionId);
    return hit ? hit.severity : null;
  };

  async function addChapter() {
    const title = window.prompt("New chapter title");
    if (!title?.trim()) return;
    setBusy(true);
    try {
      await api.addChapter(document.id, title.trim());
      await onReload();
    } finally {
      setBusy(false);
    }
  }

  async function addSubchapter(parent: Section) {
    const title = window.prompt(`New sub-chapter under "${parent.title}"`);
    if (!title?.trim()) return;
    setBusy(true);
    try {
      await api.addSubchapter(document.id, parent.id, title.trim());
      await onReload();
    } finally {
      setBusy(false);
    }
  }

  function row(section: Section, depth: number) {
    const badge = KIND_BADGE[section.kind];
    const severity = severityFor(section.id);
    const selected = section.id === selectedId;
    return (
      <button
        key={section.id}
        onClick={() => onSelect(section.id)}
        style={{ paddingLeft: 12 + depth * 16 }}
        className={`flex w-full items-center gap-2 py-1.5 pr-2 text-left text-sm ${
          selected ? "bg-slate-200" : "hover:bg-slate-100"
        }`}
      >
        <span className="text-slate-400">{section.number}</span>
        <span className="flex-1 truncate">{section.title}</span>
        {severity === "error" && <span title="Has errors">🔴</span>}
        {severity === "warning" && <span title="Has warnings">🟡</span>}
        <span
          className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${badge.cls}`}
        >
          {badge.label}
        </span>
      </button>
    );
  }

  return (
    <aside className="flex w-72 flex-col border-r border-slate-200 bg-panel">
      <div className="flex items-center justify-between border-b border-slate-200 px-3 py-2">
        <h2 className="text-sm font-semibold">HLD Structure</h2>
        <button
          className="rounded bg-slate-800 px-2 py-1 text-xs text-white disabled:opacity-50"
          disabled={busy}
          onClick={addChapter}
        >
          + Chapter
        </button>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto py-1">
        {chapters.map((chapter) => (
          <div key={chapter.id}>
            {row(chapter, 0)}
            {childrenOf(chapter.id).map((sub) => row(sub, 1))}
            <button
              onClick={() => addSubchapter(chapter)}
              disabled={busy}
              style={{ paddingLeft: 28 }}
              className="block w-full py-1 text-left text-xs text-slate-400 hover:text-slate-700 disabled:opacity-50"
            >
              + Add Subchapter
            </button>
          </div>
        ))}
      </div>

      <div className="border-t border-slate-200 px-3 py-2 text-[11px] text-slate-400">
        Required · Template · Custom markers
      </div>
    </aside>
  );
}
