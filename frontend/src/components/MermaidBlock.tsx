import { useState } from "react";
import { api } from "../api/client";
import type { Diagram } from "../types";
import CodeEditor from "./CodeEditor";

const SAMPLE = `graph TD
  A[Client] --> B[API Gateway]
  B --> C[Service]`;

interface Props {
  diagram: Diagram;
}

/** Mermaid diagram block: source editing + server-rendered SVG preview. */
export default function MermaidBlock({ diagram }: Props) {
  const [source, setSource] = useState(diagram.source || "");
  const [svg, setSvg] = useState(diagram.svg);
  const [error, setError] = useState(diagram.last_error);
  const [status, setStatus] = useState(diagram.render_status);
  const [busy, setBusy] = useState(false);

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

  return (
    <div className="rounded-lg border border-slate-200">
      <div className="flex items-center justify-between border-b border-slate-200 bg-slate-50 px-3 py-1.5">
        <span className="text-xs font-semibold text-slate-600">
          Mermaid diagram · {diagram.name}
        </span>
        <div className="flex items-center gap-2">
          {source.trim() === "" && (
            <button
              className="text-xs text-slate-500 hover:underline"
              onClick={() => setSource(SAMPLE)}
            >
              Insert sample
            </button>
          )}
          <button
            className="rounded bg-slate-800 px-2 py-1 text-xs text-white disabled:opacity-50"
            disabled={busy}
            onClick={render}
          >
            {busy ? "Rendering…" : "Render"}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 p-3">
        <div>
          <p className="mb-1 text-[11px] uppercase text-slate-400">Source</p>
          <CodeEditor defaultValue={source} onChange={setSource} />
        </div>
        <div>
          <p className="mb-1 text-[11px] uppercase text-slate-400">Preview</p>
          <div className="flex min-h-[120px] items-center justify-center rounded border border-dashed border-slate-300 p-2">
            {status === "error" ? (
              <pre className="whitespace-pre-wrap text-xs text-red-600">
                {error || "Invalid Mermaid syntax"}
              </pre>
            ) : svg ? (
              <div
                className="max-w-full"
                dangerouslySetInnerHTML={{ __html: svg }}
              />
            ) : (
              <span className="text-xs text-slate-400">
                Not rendered yet — edit the source and click Render.
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
