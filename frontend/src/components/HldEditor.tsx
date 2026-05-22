import { useRef, useState } from "react";
import { Plus, Workflow } from "lucide-react";
import { api } from "../api/client";
import type { HldDocument, Section, SectionKind } from "../types";
import MilkdownEditor from "./MilkdownEditor";
import MermaidBlock from "./MermaidBlock";
import ReuseBlockCard from "./ReuseBlockCard";
import { Badge } from "./ui";
import type { Tone } from "./ui";

const KIND: Record<SectionKind, { label: string; tone: Tone }> = {
  template_required: { label: "Required template chapter", tone: "rose" },
  template_optional: { label: "Template chapter", tone: "slate" },
  custom: { label: "Custom section", tone: "indigo" },
};

interface Props {
  document: HldDocument;
  section: Section;
  onReload: () => Promise<HldDocument>;
}

/** Center panel: document-like WYSIWYG editor for one section. */
export default function HldEditor({ document, section, onReload }: Props) {
  const [title, setTitle] = useState(section.title);
  const [saveState, setSaveState] = useState<"idle" | "saving" | "saved">(
    "idle",
  );
  const timer = useRef<number | undefined>(undefined);
  const contentRef = useRef(section.content);

  const diagrams = document.diagrams.filter((d) => d.section_id === section.id);
  const reuseInstances = document.reuse_instances
    .filter((r) => r.section_id === section.id)
    .sort((a, b) => a.order_index - b.order_index);
  const kind = KIND[section.kind];

  function scheduleSave(content: string, nextTitle: string) {
    setSaveState("saving");
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(async () => {
      try {
        await api.updateSection(document.id, section.id, {
          title: nextTitle,
          content,
        });
        setSaveState("saved");
      } catch {
        setSaveState("idle");
      }
    }, 800);
  }

  function handleContentChange(markdown: string) {
    contentRef.current = markdown;
    scheduleSave(markdown, title);
  }

  async function handleTitleBlur() {
    if (title === section.title) return;
    await api.updateSection(document.id, section.id, { title });
    await onReload();
  }

  async function addDiagram() {
    const name = window.prompt("Diagram name", "system-context");
    if (!name?.trim()) return;
    await api.createDiagram(document.id, section.id, name.trim());
    await onReload();
  }

  return (
    <div className="mx-auto max-w-3xl px-6 py-6">
      <article className="rounded-xl border border-slate-200 bg-white px-8 py-7 shadow-card">
        <div className="mb-3 flex items-center gap-2">
          <span className="rounded-md bg-slate-100 px-2 py-0.5 text-sm font-semibold tabular-nums text-slate-500">
            {section.number}
          </span>
          <Badge tone={kind.tone}>{kind.label}</Badge>
          <span className="ml-auto text-xs text-slate-400">
            {saveState === "saving"
              ? "Saving…"
              : saveState === "saved"
                ? "Saved"
                : ""}
          </span>
        </div>

        <input
          className="mb-5 w-full border-b border-transparent pb-1 text-2xl font-bold text-slate-900 outline-none transition focus:border-slate-300"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          onBlur={handleTitleBlur}
        />

        <MilkdownEditor
          defaultValue={section.content}
          onChange={handleContentChange}
        />

        {reuseInstances.length > 0 && (
          <div className="mt-6 space-y-3">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-400">
              Reused blocks
            </h3>
            {reuseInstances.map((r) => (
              <ReuseBlockCard
                key={r.id}
                documentId={document.id}
                instance={r}
                onReload={onReload}
              />
            ))}
          </div>
        )}

        <div className="mt-8 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-slate-400">
              <Workflow size={13} />
              Diagrams
            </h3>
            <button
              className="inline-flex items-center gap-1 rounded-md border border-slate-300 px-2 py-1 text-xs font-medium text-slate-600 hover:bg-slate-50"
              onClick={addDiagram}
            >
              <Plus size={13} />
              Add Mermaid diagram
            </button>
          </div>
          {diagrams.length === 0 && (
            <p className="text-xs text-slate-400">
              No diagrams in this section yet.
            </p>
          )}
          {diagrams.map((d) => (
            <MermaidBlock key={d.id} diagram={d} />
          ))}
        </div>
      </article>
    </div>
  );
}
