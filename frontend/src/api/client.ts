import type {
  ApplicationGroup,
  CommitInfo,
  Diagram,
  ExportJob,
  HldDocument,
  Increment,
  Repository,
  Section,
  ValidationResponse,
} from "../types";

const BASE_URL =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ??
  "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {
      /* ignore non-JSON error bodies */
    }
    throw new Error(detail);
  }
  return res.status === 204 ? (undefined as T) : ((await res.json()) as T);
}

const body = (data: unknown) => JSON.stringify(data);

export const api = {
  baseUrl: BASE_URL,

  // Repositories & application groups
  listRepositories: () => request<Repository[]>("/api/repositories"),
  createRepository: (name: string) =>
    request<Repository>("/api/repositories", {
      method: "POST",
      body: body({ name }),
    }),
  listApplicationGroups: (repoId: number) =>
    request<ApplicationGroup[]>(
      `/api/repositories/${repoId}/application-groups`,
    ),
  createApplicationGroup: (repoId: number, name: string) =>
    request<ApplicationGroup>(
      `/api/repositories/${repoId}/application-groups`,
      { method: "POST", body: body({ name }) },
    ),

  // Increments
  createIncrement: (applicationGroupId: number, name: string) =>
    request<Increment>("/api/increments", {
      method: "POST",
      body: body({ application_group_id: applicationGroupId, name }),
    }),

  // HLD
  createHld: (incrementId: number) =>
    request<HldDocument>(`/api/increments/${incrementId}/hld`, {
      method: "POST",
      body: body({}),
    }),
  getHld: (documentId: number) =>
    request<HldDocument>(`/api/hlds/${documentId}`),
  updateSection: (
    documentId: number,
    sectionId: number,
    data: { title?: string; content?: string },
  ) =>
    request<Section>(`/api/hlds/${documentId}/sections/${sectionId}`, {
      method: "PUT",
      body: body(data),
    }),
  addChapter: (documentId: number, title: string) =>
    request<HldDocument>(`/api/hlds/${documentId}/chapters`, {
      method: "POST",
      body: body({ title }),
    }),
  addSubchapter: (documentId: number, parentId: number, title: string) =>
    request<HldDocument>(`/api/hlds/${documentId}/subchapters`, {
      method: "POST",
      body: body({ parent_id: parentId, title }),
    }),

  // Diagrams
  createDiagram: (documentId: number, sectionId: number, name: string) =>
    request<Diagram>(`/api/hlds/${documentId}/diagrams`, {
      method: "POST",
      body: body({ section_id: sectionId, name, source: "" }),
    }),
  updateDiagram: (diagramId: number, source: string) =>
    request<Diagram>(`/api/diagrams/${diagramId}`, {
      method: "PUT",
      body: body({ source }),
    }),
  renderDiagram: (diagramId: number) =>
    request<Diagram>(`/api/diagrams/${diagramId}/render`, { method: "POST" }),

  // Document-level
  saveDocument: (documentId: number) =>
    request<CommitInfo>(`/api/documents/${documentId}/save`, {
      method: "POST",
    }),
  exportDocument: (documentId: number, format: "docx" | "pdf") =>
    request<ExportJob>(`/api/documents/${documentId}/export`, {
      method: "POST",
      body: body({ format }),
    }),
  validateDocument: (documentId: number) =>
    request<ValidationResponse>(`/api/documents/${documentId}/validation`),
  exportDownloadUrl: (jobId: number) =>
    `${BASE_URL}/api/exports/${jobId}/download`,
};
