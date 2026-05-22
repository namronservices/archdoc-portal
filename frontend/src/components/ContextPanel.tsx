import type { ValidationItem } from "../types";

const SEVERITY_STYLE: Record<string, string> = {
  error: "border-rose-300 bg-rose-50 text-rose-700",
  warning: "border-amber-300 bg-amber-50 text-amber-700",
  info: "border-sky-300 bg-sky-50 text-sky-700",
};

interface Props {
  validation: ValidationItem[];
  onValidate: () => Promise<void>;
}

export default function ContextPanel({ validation, onValidate }: Props) {
  return (
    <aside className="flex w-72 flex-col border-l border-slate-200 bg-panel">
      <section className="border-b border-slate-200 p-3">
        <h2 className="mb-1 text-sm font-semibold">Architecture Context</h2>
        <p className="text-xs text-slate-400">
          Linking to Enterprise Repository objects arrives in a later phase.
        </p>
      </section>

      <section className="border-b border-slate-200 p-3">
        <h2 className="mb-1 text-sm font-semibold">Linked References</h2>
        <p className="text-xs text-slate-400">
          Reusable architecture blocks arrive in a later phase.
        </p>
      </section>

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
    </aside>
  );
}
