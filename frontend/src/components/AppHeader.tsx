import { useState } from "react";
import {
  Boxes,
  ChevronRight,
  Download,
  MessageSquare,
  Plug,
  Save,
} from "lucide-react";
import { Button } from "./ui";

interface Props {
  breadcrumb: Record<string, string>;
  onSave: () => void;
  onExport: (format: "docx" | "pdf") => void;
  onOpenIntegrations?: () => void;
}

/** Slim global header — brand, breadcrumb, primary document actions. */
export default function AppHeader({
  breadcrumb,
  onSave,
  onExport,
  onOpenIntegrations,
}: Props) {
  const [exportOpen, setExportOpen] = useState(false);
  const crumbs = [
    "Workspaces",
    breadcrumb.repository,
    breadcrumb.increment,
    breadcrumb.document,
  ].filter(Boolean);

  return (
    <header className="flex items-center gap-4 border-b border-slate-200 bg-white px-4 py-2">
      <div className="flex items-center gap-2">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand text-white">
          <Boxes size={18} />
        </div>
        <div className="leading-tight">
          <div className="text-sm font-semibold text-slate-800">
            ArchDoc Portal
          </div>
          <div className="text-[10px] uppercase tracking-wide text-slate-400">
            Architecture Authoring
          </div>
        </div>
      </div>

      <nav className="flex min-w-0 items-center gap-1 text-sm text-slate-500">
        {crumbs.map((c, i) => (
          <span key={i} className="flex items-center gap-1">
            {i > 0 && <ChevronRight size={14} className="text-slate-300" />}
            <span
              className={
                i === crumbs.length - 1
                  ? "truncate font-semibold text-slate-800"
                  : "truncate"
              }
            >
              {c}
            </span>
          </span>
        ))}
      </nav>

      <div className="ml-auto flex items-center gap-2">
        {onOpenIntegrations && (
          <Button variant="secondary" onClick={onOpenIntegrations}>
            <Plug size={15} />
            Integration Docs
          </Button>
        )}
        <Button variant="primary" onClick={onSave}>
          <Save size={15} />
          Save
        </Button>
        <div className="relative">
          <Button
            variant="secondary"
            onClick={() => setExportOpen((v) => !v)}
          >
            <Download size={15} />
            Export
          </Button>
          {exportOpen && (
            <div className="absolute right-0 z-20 mt-1 w-32 overflow-hidden rounded-md border border-slate-200 bg-white shadow-panel">
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
        <Button
          variant="secondary"
          disabled
          title="Review is planned for a later phase"
        >
          <MessageSquare size={15} />
          Review
        </Button>
      </div>
    </header>
  );
}
