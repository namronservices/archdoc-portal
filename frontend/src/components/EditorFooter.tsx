import { AlertCircle, Check, GitCommitHorizontal, Loader2 } from "lucide-react";
import type { CommitInfo } from "../types";

interface Props {
  status: string;
  error: string | null;
  commit: CommitInfo | null;
  headCommit: string | null;
}

/** Slim status bar — save state, last commit, autosave indicator. */
export default function EditorFooter({
  status,
  error,
  commit,
  headCommit,
}: Props) {
  const busy = /…|ing/.test(status);
  const sha = commit?.short_hash ?? headCommit;

  return (
    <footer className="flex items-center gap-4 border-t border-slate-200 bg-white px-5 py-1.5 text-xs">
      {error ? (
        <span className="flex items-center gap-1.5 text-rose-600">
          <AlertCircle size={13} />
          {error}
        </span>
      ) : busy ? (
        <span className="flex items-center gap-1.5 text-slate-500">
          <Loader2 size={13} className="animate-spin" />
          {status}
        </span>
      ) : (
        <span className="flex items-center gap-1.5 text-emerald-600">
          <Check size={13} />
          {status || "All changes saved to Git"}
        </span>
      )}

      {sha && (
        <span className="flex items-center gap-1.5 text-slate-400">
          <GitCommitHorizontal size={14} />
          <span>Last commit</span>
          <code className="rounded bg-slate-100 px-1 text-slate-600">
            {sha}
          </code>
          {commit && (
            <span className="truncate">
              {new Date(commit.committed_at).toLocaleString()}
            </span>
          )}
        </span>
      )}

      <span className="ml-auto flex items-center gap-1.5 text-slate-400">
        <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
        Autosave on
      </span>
    </footer>
  );
}
