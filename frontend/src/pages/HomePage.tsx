import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Boxes } from "lucide-react";
import { api } from "../api/client";
import type { ApplicationGroup, Increment, Repository } from "../types";

/** Inline create-or-pick form used for each setup step. */
function StepCard({
  step,
  title,
  active,
  done,
  children,
}: {
  step: number;
  title: string;
  active: boolean;
  done: boolean;
  children: React.ReactNode;
}) {
  return (
    <div
      className={`rounded-xl border p-5 ${
        active
          ? "border-brand bg-white shadow-card"
          : "border-slate-200 bg-slate-50"
      }`}
    >
      <div className="mb-3 flex items-center gap-2">
        <span
          className={`flex h-6 w-6 items-center justify-center rounded-full text-xs font-semibold ${
            done
              ? "bg-emerald-600 text-white"
              : active
                ? "bg-brand text-white"
                : "bg-slate-300 text-slate-600"
          }`}
        >
          {done ? "✓" : step}
        </span>
        <h2 className="font-semibold">{title}</h2>
      </div>
      {(active || done) && children}
    </div>
  );
}

function CreateRow({
  placeholder,
  onCreate,
}: {
  placeholder: string;
  onCreate: (name: string) => Promise<void>;
}) {
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit() {
    if (!name.trim()) return;
    setBusy(true);
    try {
      await onCreate(name.trim());
      setName("");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex gap-2">
      <input
        className="flex-1 rounded border border-slate-300 px-3 py-1.5 text-sm"
        placeholder={placeholder}
        value={name}
        onChange={(e) => setName(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && submit()}
      />
      <button
        className="rounded-md bg-brand px-3 py-1.5 text-sm font-medium text-white hover:bg-brand-fg disabled:opacity-50"
        disabled={busy || !name.trim()}
        onClick={submit}
      >
        Create
      </button>
    </div>
  );
}

export default function HomePage() {
  const navigate = useNavigate();
  const [repos, setRepos] = useState<Repository[]>([]);
  const [repo, setRepo] = useState<Repository | null>(null);
  const [groups, setGroups] = useState<ApplicationGroup[]>([]);
  const [group, setGroup] = useState<ApplicationGroup | null>(null);
  const [increments, setIncrements] = useState<Increment[]>([]);
  const [increment, setIncrement] = useState<Increment | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.listRepositories().then(setRepos).catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    setGroups([]);
    setGroup(null);
    setIncrements([]);
    setIncrement(null);
    if (repo) {
      api
        .listApplicationGroups(repo.id)
        .then(setGroups)
        .catch((e) => setError(e.message));
    }
  }, [repo]);

  useEffect(() => {
    setIncrements([]);
    setIncrement(null);
    if (group) {
      api
        .listIncrements(group.id)
        .then(setIncrements)
        .catch((e) => setError(e.message));
    }
  }, [group]);

  const guard = async (fn: () => Promise<void>) => {
    setError(null);
    try {
      await fn();
    } catch (e) {
      setError((e as Error).message);
    }
  };

  async function createHld() {
    if (!increment) return;
    setBusy(true);
    try {
      const doc = await api.createHld(increment.id);
      navigate(`/hld/${doc.id}`);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl px-6 py-12">
      <div className="mb-6 flex items-center gap-3">
        <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-brand text-white">
          <Boxes size={24} />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-slate-900">ArchDoc Portal</h1>
          <p className="text-sm text-slate-500">
            Set up a workspace, then author a High-Level Design.
          </p>
        </div>
      </div>

      {error && (
        <div className="mb-4 rounded border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="space-y-3">
        <StepCard step={1} title="Repository" active={!repo} done={!!repo}>
          <div className="space-y-2">
            {repos.map((r) => (
              <button
                key={r.id}
                className={`block w-full rounded border px-3 py-1.5 text-left text-sm ${
                  repo?.id === r.id
                    ? "border-brand bg-brand-soft"
                    : "border-slate-200 hover:bg-slate-50"
                }`}
                onClick={() => setRepo(r)}
              >
                {r.name}
              </button>
            ))}
            <CreateRow
              placeholder="New repository name"
              onCreate={(name) =>
                guard(async () => {
                  const r = await api.createRepository(name);
                  setRepos((prev) => [...prev, r]);
                  setRepo(r);
                })
              }
            />
          </div>
        </StepCard>

        <StepCard
          step={2}
          title="Application Group"
          active={!!repo && !group}
          done={!!group}
        >
          <div className="space-y-2">
            {groups.map((g) => (
              <button
                key={g.id}
                className={`block w-full rounded border px-3 py-1.5 text-left text-sm ${
                  group?.id === g.id
                    ? "border-brand bg-brand-soft"
                    : "border-slate-200 hover:bg-slate-50"
                }`}
                onClick={() => setGroup(g)}
              >
                {g.name}
              </button>
            ))}
            <CreateRow
              placeholder="New application group name"
              onCreate={(name) =>
                guard(async () => {
                  const g = await api.createApplicationGroup(repo!.id, name);
                  setGroups((prev) => [...prev, g]);
                  setGroup(g);
                })
              }
            />
          </div>
        </StepCard>

        <StepCard
          step={3}
          title="Architecture Increment"
          active={!!group && !increment}
          done={!!increment}
        >
          <div className="space-y-2">
            {increments.map((i) => (
              <button
                key={i.id}
                className={`block w-full rounded border px-3 py-1.5 text-left text-sm ${
                  increment?.id === i.id
                    ? "border-brand bg-brand-soft"
                    : "border-slate-200 hover:bg-slate-50"
                }`}
                onClick={() => setIncrement(i)}
              >
                {i.name}
              </button>
            ))}
            <CreateRow
              placeholder="New increment name (e.g. MVP2)"
              onCreate={(name) =>
                guard(async () => {
                  const inc = await api.createIncrement(group!.id, name);
                  setIncrements((prev) => [...prev, inc]);
                  setIncrement(inc);
                })
              }
            />
          </div>
        </StepCard>

        <StepCard
          step={4}
          title="High-Level Design"
          active={!!increment}
          done={false}
        >
          <button
            className="rounded-md bg-brand px-4 py-2 text-sm font-medium text-white hover:bg-brand-fg disabled:opacity-50"
            disabled={busy || !increment}
            onClick={createHld}
          >
            Create HLD from template
          </button>
        </StepCard>

        <StepCard
          step={5}
          title="Integration Documents"
          active={!!increment}
          done={false}
        >
          <button
            className="rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
            disabled={!increment}
            onClick={() =>
              increment &&
              navigate(`/increment/${increment.id}/integrations`)
            }
          >
            Open Integration Docs
          </button>
        </StepCard>
      </div>
    </div>
  );
}
