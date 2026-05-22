import { Building2, FileText, GitBranch, Layers, Package } from "lucide-react";
import type { HldDocument } from "../types";
import { Badge, Chip } from "./ui";

interface Props {
  document: HldDocument;
}

/** Document title band — icon, title, type, and architecture metadata chips. */
export default function DocumentHeader({ document }: Props) {
  const b = document.breadcrumb;
  return (
    <div className="border-b border-slate-200 bg-white px-5 py-3">
      <div className="flex items-center gap-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-soft text-brand-fg">
          <FileText size={20} />
        </div>
        <h1 className="text-lg font-semibold text-slate-900">
          {document.title}
        </h1>
        <Badge tone="indigo">{document.type}</Badge>
        <Badge tone="amber">Draft</Badge>
      </div>

      <div className="mt-2.5 flex flex-wrap items-center gap-2">
        {b.repository && (
          <Chip
            label="Repository"
            value={b.repository}
            icon={<Building2 size={13} />}
          />
        )}
        {b.application_group && (
          <Chip
            label="Application Group"
            value={b.application_group}
            icon={<Package size={13} />}
          />
        )}
        {b.increment && (
          <Chip
            label="Increment"
            value={b.increment}
            icon={<Layers size={13} />}
          />
        )}
        <Chip
          label="Branch"
          value={document.git_branch}
          icon={<GitBranch size={13} />}
        />
      </div>
    </div>
  );
}
