import type {
  ApplicationGroup,
  ApplicationLink,
  ArchitectureContext,
  BlockCompare,
  Capability,
  CommitInfo,
  ContextObjectType,
  Contract,
  Dashboard,
  DataDomain,
  DataObject,
  Diagram,
  Domain,
  EnterpriseApplication,
  EnterpriseSyncResponse,
  ExportJob,
  HldDocument,
  Increment,
  Integration,
  IntegrationListItem,
  IntegrationType,
  IntegrationValidationResponse,
  LinkedIntegration,
  Principle,
  Repository,
  ReusableBlock,
  ReuseInstance,
  Section,
  Standard,
  StartIncrementResponse,
  TechnologyPlatform,
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
  listIncrements: (applicationGroupId: number) =>
    request<Increment[]>(
      `/api/increments?application_group_id=${applicationGroupId}`,
    ),
  getIncrement: (incrementId: number) =>
    request<Increment>(`/api/increments/${incrementId}`),
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
  getIncrementHld: (incrementId: number) =>
    request<HldDocument>(`/api/increments/${incrementId}/hld`),
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
  updateStructure: (
    documentId: number,
    items: { id: number; parent_id: number | null; order_index: number }[],
  ) =>
    request<HldDocument>(`/api/hlds/${documentId}/structure`, {
      method: "PUT",
      body: body({ items }),
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

  // Reusable blocks
  listReusableBlocks: (category?: string, q?: string) => {
    const params = new URLSearchParams();
    if (category) params.set("category", category);
    if (q) params.set("q", q);
    const qs = params.toString();
    return request<ReusableBlock[]>(
      `/api/reusable-blocks${qs ? `?${qs}` : ""}`,
    );
  },
  getReusableBlock: (blockId: string) =>
    request<ReusableBlock>(`/api/reusable-blocks/${blockId}`),
  compareBlocks: (blockId: string, derivedBlockId: string) =>
    request<BlockCompare>(
      `/api/reusable-blocks/${blockId}/compare/${derivedBlockId}`,
    ),
  promoteBlock: (blockId: string) =>
    request<ReusableBlock>(`/api/reusable-blocks/${blockId}/promote`, {
      method: "POST",
    }),

  // Reuse instances
  insertLinked: (documentId: number, blockId: string, sectionId: number) =>
    request<HldDocument>(
      `/api/hlds/${documentId}/reuse/${blockId}/insert-linked`,
      { method: "POST", body: body({ section_id: sectionId }) },
    ),
  insertSnapshot: (documentId: number, blockId: string, sectionId: number) =>
    request<HldDocument>(
      `/api/hlds/${documentId}/reuse/${blockId}/insert-snapshot`,
      { method: "POST", body: body({ section_id: sectionId }) },
    ),
  forkBlock: (
    documentId: number,
    blockId: string,
    sectionId: number,
    title?: string,
  ) =>
    request<HldDocument>(`/api/hlds/${documentId}/reuse/${blockId}/fork`, {
      method: "POST",
      body: body({ section_id: sectionId, title }),
    }),
  updateReuseInstance: (
    documentId: number,
    instanceId: number,
    data: { body?: string; rationale?: string; status?: string },
  ) =>
    request<ReuseInstance>(`/api/hlds/${documentId}/reuse/${instanceId}`, {
      method: "PUT",
      body: body(data),
    }),
  deleteReuseInstance: (documentId: number, instanceId: number) =>
    request<HldDocument>(`/api/hlds/${documentId}/reuse/${instanceId}`, {
      method: "DELETE",
    }),

  // Integrations
  getDocument: (documentId: number) =>
    request<HldDocument>(`/api/hlds/${documentId}`),
  listIntegrations: (incrementId: number) =>
    request<IntegrationListItem[]>(
      `/api/increments/${incrementId}/integration-docs`,
    ),
  createIntegration: (
    incrementId: number,
    data: {
      type: IntegrationType;
      name: string;
      integration_id?: string;
      source_application?: string;
      target_application?: string;
      required?: boolean;
      create_document?: boolean;
    },
  ) =>
    request<Integration>(
      `/api/increments/${incrementId}/integration-docs`,
      { method: "POST", body: body(data) },
    ),
  createMissingIntegrationDocs: (incrementId: number) =>
    request<{ created: IntegrationListItem[] }>(
      `/api/increments/${incrementId}/integration-docs/create-missing`,
      { method: "POST" },
    ),
  getIntegration: (integrationId: number) =>
    request<Integration>(`/api/integrations/${integrationId}`),
  updateIntegration: (
    integrationId: number,
    data: {
      name?: string;
      source_application?: string;
      target_application?: string;
      required?: boolean;
      status?: string;
      metadata?: Record<string, unknown>;
    },
  ) =>
    request<Integration>(`/api/integrations/${integrationId}`, {
      method: "PUT",
      body: body(data),
    }),
  createIntegrationDocument: (integrationId: number) =>
    request<Integration>(`/api/integrations/${integrationId}/document`, {
      method: "POST",
    }),
  getContract: (integrationId: number) =>
    request<Contract>(`/api/integrations/${integrationId}/contract`),
  setContract: (
    integrationId: number,
    data: { filename: string; content: string },
  ) =>
    request<Contract>(`/api/integrations/${integrationId}/contract`, {
      method: "POST",
      body: body(data),
    }),
  validateIntegration: (integrationId: number) =>
    request<IntegrationValidationResponse>(
      `/api/integrations/${integrationId}/validate`,
      { method: "POST" },
    ),
  getIntegrationValidation: (integrationId: number) =>
    request<IntegrationValidationResponse>(
      `/api/integrations/${integrationId}/validation`,
    ),
  linkIntegrationToHld: (documentId: number, integrationId: number) =>
    request<HldDocument>(
      `/api/hlds/${documentId}/linked-references/integrations/${integrationId}`,
      { method: "POST" },
    ),
  unlinkIntegrationFromHld: (documentId: number, integrationId: number) =>
    request<HldDocument>(
      `/api/hlds/${documentId}/linked-references/integrations/${integrationId}`,
      { method: "DELETE" },
    ),
  listLinkedIntegrations: (documentId: number) =>
    request<LinkedIntegration[]>(
      `/api/hlds/${documentId}/linked-integrations`,
    ),

  // --- Phase 4: Enterprise repository (TOGAF) --------------------------
  getDashboard: () => request<Dashboard>("/api/enterprise/dashboard"),
  syncEnterprise: () =>
    request<EnterpriseSyncResponse>("/api/enterprise/sync", {
      method: "POST",
    }),
  startIncrement: (
    groupSlug: string,
    data: {
      increment_name: string;
      increment_slug?: string;
      hld_title?: string;
    },
  ) =>
    request<StartIncrementResponse>(
      `/api/enterprise/application-groups/${groupSlug}/start-increment`,
      { method: "POST", body: body(data) },
    ),

  listDomains: () => request<Domain[]>("/api/enterprise/domains"),
  createDomain: (data: Partial<Domain> & { name: string }) =>
    request<Domain>("/api/enterprise/domains", {
      method: "POST",
      body: body(data),
    }),
  updateDomain: (slug: string, data: Partial<Domain> & { name: string }) =>
    request<Domain>(`/api/enterprise/domains/${slug}`, {
      method: "PUT",
      body: body(data),
    }),

  listCapabilities: (domainSlug?: string) => {
    const qs = domainSlug
      ? `?domain_slug=${encodeURIComponent(domainSlug)}`
      : "";
    return request<Capability[]>(`/api/enterprise/capabilities${qs}`);
  },
  createCapability: (data: Partial<Capability> & { name: string }) =>
    request<Capability>("/api/enterprise/capabilities", {
      method: "POST",
      body: body(data),
    }),
  updateCapability: (
    slug: string,
    data: Partial<Capability> & { name: string },
  ) =>
    request<Capability>(`/api/enterprise/capabilities/${slug}`, {
      method: "PUT",
      body: body(data),
    }),

  listEnterpriseApplications: (filters?: {
    domain_slug?: string;
    application_group_slug?: string;
  }) => {
    const params = new URLSearchParams();
    if (filters?.domain_slug) params.set("domain_slug", filters.domain_slug);
    if (filters?.application_group_slug)
      params.set("application_group_slug", filters.application_group_slug);
    const qs = params.toString();
    return request<EnterpriseApplication[]>(
      `/api/enterprise/applications${qs ? `?${qs}` : ""}`,
    );
  },
  createEnterpriseApplication: (
    data: Partial<EnterpriseApplication> & { name: string },
  ) =>
    request<EnterpriseApplication>("/api/enterprise/applications", {
      method: "POST",
      body: body(data),
    }),
  updateEnterpriseApplication: (
    slug: string,
    data: Partial<EnterpriseApplication> & { name: string },
  ) =>
    request<EnterpriseApplication>(`/api/enterprise/applications/${slug}`, {
      method: "PUT",
      body: body(data),
    }),

  listApplicationLinks: () =>
    request<ApplicationLink[]>("/api/enterprise/application-links"),
  createApplicationLink: (
    data: Partial<ApplicationLink> & {
      source_app_slug: string;
      target_app_slug: string;
    },
  ) =>
    request<ApplicationLink>("/api/enterprise/application-links", {
      method: "POST",
      body: body(data),
    }),

  listDataObjects: () =>
    request<DataObject[]>("/api/enterprise/data-objects"),
  createDataObject: (data: Partial<DataObject> & { name: string }) =>
    request<DataObject>("/api/enterprise/data-objects", {
      method: "POST",
      body: body(data),
    }),

  listDataDomains: () =>
    request<DataDomain[]>("/api/enterprise/data-domains"),
  createDataDomain: (data: Partial<DataDomain> & { name: string }) =>
    request<DataDomain>("/api/enterprise/data-domains", {
      method: "POST",
      body: body(data),
    }),

  listTechnologyPlatforms: () =>
    request<TechnologyPlatform[]>("/api/enterprise/technology-platforms"),
  createTechnologyPlatform: (
    data: Partial<TechnologyPlatform> & { name: string },
  ) =>
    request<TechnologyPlatform>("/api/enterprise/technology-platforms", {
      method: "POST",
      body: body(data),
    }),

  listStandards: () => request<Standard[]>("/api/enterprise/standards"),
  createStandard: (data: Partial<Standard> & { title: string }) =>
    request<Standard>("/api/enterprise/standards", {
      method: "POST",
      body: body(data),
    }),

  listPrinciples: () => request<Principle[]>("/api/enterprise/principles"),
  createPrinciple: (data: Partial<Principle> & { title: string }) =>
    request<Principle>("/api/enterprise/principles", {
      method: "POST",
      body: body(data),
    }),

  listEnterpriseApplicationGroups: () =>
    request<
      (ApplicationGroup & {
        domain_slug: string | null;
        archimate_type: string | null;
      })[]
    >("/api/enterprise/application-groups"),
  createEnterpriseApplicationGroup: (data: {
    name: string;
    slug?: string;
    domain_slug?: string | null;
    description?: string;
    archimate_type?: string | null;
  }) =>
    request<ApplicationGroup>("/api/enterprise/application-groups", {
      method: "POST",
      body: body(data),
    }),

  // --- HLD architecture context ----------------------------------------
  getArchitectureContext: (documentId: number) =>
    request<ArchitectureContext>(
      `/api/hlds/${documentId}/architecture-context`,
    ),
  addContextLink: (
    documentId: number,
    objectType: ContextObjectType,
    objectSlug: string,
  ) =>
    request<ArchitectureContext>(
      `/api/hlds/${documentId}/links/${objectType}/${encodeURIComponent(
        objectSlug,
      )}`,
      { method: "POST" },
    ),
  removeContextLink: (
    documentId: number,
    objectType: ContextObjectType,
    objectSlug: string,
  ) =>
    request<ArchitectureContext>(
      `/api/hlds/${documentId}/links/${objectType}/${encodeURIComponent(
        objectSlug,
      )}`,
      { method: "DELETE" },
    ),
};
