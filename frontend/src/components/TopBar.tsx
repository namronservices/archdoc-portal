import { useState } from "react";
import type { CommitInfo } from "../types";

interface Props {
  breadcrumb: Record<string, string>;
  headCommit: string | null;
  commit: CommitInfo | null;
  status: string;
  error: string | null;
  onSave: () => void;
  onExport: (format: "docx" | "pdf") => void;
}

export default function TopBar({
  breadcrumb,
  headCommit,
  commit,
  status,
  error,
  onSave,
  onExport,
}: Props) {
  const [exportOpen, setExportOpen] = useState(false);
  const crumbs = [
    breadcrumb.repository,
    breadcrumb.application_group,
    breadcrumb.increment,
    breadcrumb.document,
  ].filter(Boolean);

  return (
    <header className="border-b border-slate-200 bg-white">
      <div className="flex items-center justify-between px-4 py-2">
        <nav className="flex items-center gap-1.5 text-sm text-slate-600">
          {crumbs.map((c, i) => (
            <span key={i} className="flex items-center gap-1.5">
              {i > 0 && <span className="text-slate-300">›</span>}
              <span
                className={
                  i === crumbs.length - 1
                    ? "font-semibold text-slate-900"
                    : ""
                }
              >
                {c}
              </span>
            </span>
          ))}
        </nav>

        <div className="flex items-center gap-2">
          <button
            className="rounded bg-slate-800 px-3 py-1.5 text-sm text-white hover:bg-slate-700"
            onClick={onSave}
          >
            Save
          </button>
          <div className="relative">
            <button
              className="rounded border border-slate-300 px-3 py-1.5 text-sm hover:bg-slate-50"
              onClick={() => setExportOpen((v) => !v)}
            >
              Export ▾
            </button>
            {exportOpen && (
              <div className="absolute right-0 z-10 mt-1 w-32 rounded border border-slate-200 bg-white shadow">
                {(["docx", "pdf"] as const).map((fmt) => (
                  <button
                    key={fmt}
                    className="block w-full px-3 py-1.5 text-left text-sm hover:bg-slate-50"
                    onClick={() => {
                      setExportOpen(false);
                      onExport(fmt);
                    }}
                  >
                    {fmt.toUpperCase()}
                  </button>
                ))}
              </div>
            )}
          </div>
          <button
            className="rounded border border-slate-200 px-3 py-1.5 text-sm text-slate-400"
            title="Review is planned for a later phase"
            disabled
          >
            Review
          </button>
        </div>
      </div>

      <div className="flex items-center gap-3 border-t border-slate-100 px-4 py-1 text-xs">
        <span className="text-slate-500">
          Commit:{" "}
          <code className="rounded bg-slate-100 px-1">
            {commit?.short_hash ?? headCommit ?? "—"}
          </code>
          {commit && (
            <span className="ml-1 text-slate-400">
              {commit.message} · {new Date(commit.committed_at).toLocaleString()}
            </span>
          )}
        </span>
        {status && <span className="text-emerald-600">{status}</span>}
        {error && <span className="text-red-600">{error}</span>}
      </div>
    </header>
  );
}
