import { useRef, useState } from "react";
import { api } from "../api/client";
import type { HldDocument, Section, SectionKind } from "../types";
import MilkdownEditor from "./MilkdownEditor";
import MermaidBlock from "./MermaidBlock";

const KIND_LABEL: Record<SectionKind, string> = {
  template_required: "Required template chapter",
  template_optional: "Template chapter",
  custom: "Custom section",
};

interface Props {
  document: HldDocument;
  section: Section;
  onReload: () => Promise<HldDocument>;
}

/** Center panel: focused WYSIWYG editor for one section plus its diagrams. */
export default function HldEditor({ document, section, onReload }: Props) {
  const [title, setTitle] = useState(section.title);
  const [saveState, setSaveState] = useState<"idle" | "saving" | "saved">(
    "idle",
  );
  const timer = useRef<number | undefined>(undefined);

  const diagrams = document.diagrams.filter(
    (d) => d.section_id === section.id,
  );
  const isCustom = section.kind === "custom";

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

  const contentRef = useRef(section.content);

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
    <div className="mx-auto max-w-3xl px-8 py-6">
      <div className="mb-1 flex items-center gap-2">
        <span className="text-sm text-slate-400">{section.number}</span>
        <span
          className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${
            isCustom
              ? "bg-indigo-100 text-indigo-700"
              : section.kind === "template_required"
                ? "bg-rose-100 text-rose-700"
                : "bg-slate-200 text-slate-600"
          }`}
        >
          {KIND_LABEL[section.kind]}
        </span>
        <span className="ml-auto text-xs text-slate-400">
          {saveState === "saving"
            ? "Saving…"
            : saveState === "saved"
              ? "Saved"
              : ""}
        </span>
      </div>

      <input
        className="mb-4 w-full border-b border-transparent text-2xl font-bold outline-none focus:border-slate-300"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        onBlur={handleTitleBlur}
      />

      <MilkdownEditor
        defaultValue={section.content}
        onChange={handleContentChange}
      />

      <div className="mt-8 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-slate-600">
            Diagrams
          </h3>
          <button
            className="rounded border border-slate-300 px-2 py-1 text-xs hover:bg-slate-50"
            onClick={addDiagram}
          >
            + Add Mermaid diagram
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
    </div>
  );
}
