import { useState } from "react";
import { Code2, Play, Workflow } from "lucide-react";
import { api } from "../api/client";
import type { Diagram } from "../types";
import CodeEditor from "./CodeEditor";

const SAMPLE = `graph TD
  A[Client] --> B[API Gateway]
  B --> C[Service]`;

interface Props {
  diagram: Diagram;
}

/** Mermaid diagram block — collapsed preview by default, split editor on demand. */
export default function MermaidBlock({ diagram }: Props) {
  const [source, setSource] = useState(diagram.source || "");
  const [svg, setSvg] = useState(diagram.svg);
  const [error, setError] = useState(diagram.last_error);
  const [status, setStatus] = useState(diagram.render_status);
  const [busy, setBusy] = useState(false);
  const [editing, setEditing] = useState(false);

  async function render() {
    setBusy(true);
    setError("");
    try {
      await api.updateDiagram(diagram.id, source);
      const updated = await api.renderDiagram(diagram.id);
      setSvg(updated.svg);
      setError(updated.last_error);
      setStatus(updated.render_status);
    } catch (e) {
      setError((e as Error).message);
      setStatus("error");
    } finally {
      setBusy(false);
    }
  }

  const preview = (
    <div className="flex min-h-[140px] items-center justify-center rounded-lg border border-dashed border-slate-300 bg-slate-50/60 p-3">
      {status === "error" ? (
        <pre className="whitespace-pre-wrap text-xs text-rose-600">
          {error || "Invalid Mermaid syntax"}
        </pre>
      ) : svg ? (
        <div className="max-w-full" dangerouslySetInnerHTML={{ __html: svg }} />
      ) : (
        <span className="text-xs text-slate-400">
          Not rendered yet — edit the source and click Render.
        </span>
      )}
    </div>
  );

  return (
    <div className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-card">
      <div className="flex items-center gap-2 border-b border-slate-100 bg-slate-50 px-3 py-1.5">
        <Workflow size={14} className="text-indigo-500" />
        <span className="text-xs font-semibold text-slate-700">
          {diagram.name}
        </span>
        <span className="rounded bg-indigo-100 px-1.5 py-0.5 text-[10px] font-medium text-indigo-700">
          Mermaid
        </span>
        <span className="text-[10px] text-slate-400">{diagram.name}.mmd</span>
        <div className="ml-auto flex items-center gap-1.5">
          {source.trim() === "" && (
            <button
              className="text-[11px] text-slate-500 hover:underline"
              onClick={() => setSource(SAMPLE)}
            >
              Insert sample
            </button>
          )}
          <button
            className="inline-flex items-center gap-1 rounded border border-slate-300 bg-white px-2 py-1 text-[11px] font-medium text-slate-600 hover:bg-slate-50"
            onClick={() => setEditing((v) => !v)}
          >
            <Code2 size={12} />
            {editing ? "Done" : "Edit Source"}
          </button>
          <button
            className="inline-flex items-center gap-1 rounded bg-brand px-2 py-1 text-[11px] font-medium text-white disabled:opacity-50"
            disabled={busy}
            onClick={render}
          >
            <Play size={12} />
            {busy ? "Rendering…" : "Render"}
          </button>
        </div>
      </div>

      {editing ? (
        <div className="grid grid-cols-2 gap-3 p-3">
          <div>
            <p className="mb-1 text-[10px] font-semibold uppercase text-slate-400">
              Source
            </p>
            <CodeEditor defaultValue={source} onChange={setSource} />
          </div>
          <div>
            <p className="mb-1 text-[10px] font-semibold uppercase text-slate-400">
              Preview
            </p>
            {preview}
          </div>
        </div>
      ) : (
        <div className="p-3">{preview}</div>
      )}
    </div>
  );
}
