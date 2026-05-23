export interface Repository {
  id: number;
  slug: string;
  name: string;
  default_branch: string;
  created_at: string;
}

export interface ApplicationGroup {
  id: number;
  repository_id: number;
  slug: string;
  name: string;
  description: string;
  created_at: string;
}

export interface Increment {
  id: number;
  application_group_id: number;
  slug: string;
  name: string;
  status: string;
  created_at: string;
}

export type SectionKind =
  | "template_required"
  | "template_optional"
  | "custom";

export interface Section {
  id: number;
  parent_id: number | null;
  order_index: number;
  number: string;
  title: string;
  content: string;
  kind: SectionKind;
}

export interface Diagram {
  id: number;
  document_id: number;
  section_id: number | null;
  name: string;
  source: string;
  svg: string;
  render_status: "pending" | "rendered" | "error";
  last_error: string;
}

export type ReuseMode = "linked" | "snapshot" | "forked";

export interface ReusableBlock {
  id: number;
  block_id: string;
  title: string;
  category: string;
  version: string;
  status: string;
  owner: string;
  tags: string[];
  body: string;
  scope: string | null;
  derived_from: string | null;
  derived_from_version: string;
  derivation_type: string | null;
  document_id: number | null;
}

export interface ReuseInstance {
  id: number;
  document_id: number;
  section_id: number;
  block_id: string;
  reuse_mode: ReuseMode;
  source_version: string;
  derived_block_id: string | null;
  rationale: string;
  status: string;
  order_index: number;
  title: string;
  body: string;
  library_version: string | null;
  library_status: string | null;
  broken: boolean;
}

export interface BlockCompare {
  source: ReusableBlock | null;
  derived: ReusableBlock | null;
}

export interface HldDocument {
  id: number;
  increment_id: number;
  type: string;
  title: string;
  git_branch: string;
  head_commit: string | null;
  sections: Section[];
  diagrams: Diagram[];
  reuse_instances: ReuseInstance[];
  linked_integrations: LinkedIntegration[];
  integration_ref: LinkedIntegration | null;
  breadcrumb: Record<string, string>;
}

export type IntegrationType =
  | "GRPC"
  | "KAFKA"
  | "MQ"
  | "SOAP"
  | "REST"
  | "FILE"
  | "BATCH";

export interface MetadataFieldSpec {
  key: string;
  label: string;
  kind: "text" | "select" | "bool" | "list";
  options?: string[];
}

export interface LinkedHld {
  document_id: number;
  title: string;
}

export interface IntegrationListItem {
  id: number;
  increment_id: number;
  integration_id: string;
  name: string;
  type: IntegrationType;
  type_label: string;
  source_application: string;
  target_application: string;
  required: boolean;
  status: string;
  document_id: number | null;
  document_filename: string | null;
}

export interface Integration {
  id: number;
  increment_id: number;
  integration_id: string;
  name: string;
  type: IntegrationType;
  type_label: string;
  source_application: string;
  target_application: string;
  required: boolean;
  status: string;
  document_id: number | null;
  metadata: Record<string, unknown>;
  metadata_schema: MetadataFieldSpec[];
  contract_filename: string;
  contract_path: string;
  has_contract: boolean;
  contract_format: string;
  linked_hlds: LinkedHld[];
}

export interface LinkedIntegration {
  id: number;
  integration_id: string;
  name: string;
  type: IntegrationType;
  type_label: string;
  source_application: string;
  target_application: string;
  status: string;
  document_id: number | null;
}

export interface Contract {
  filename: string;
  path: string;
  content: string;
}

export interface IntegrationValidationResponse {
  integration_id: number;
  results: ValidationItem[];
}

export interface CommitInfo {
  hash: string;
  short_hash: string;
  message: string;
  author: string;
  committed_at: string;
}

export interface ExportJob {
  id: number;
  document_id: number;
  format: string;
  status: string;
  artifact_path: string | null;
  error: string;
  created_at: string;
}

export interface ValidationItem {
  severity: "error" | "warning" | "info";
  message: string;
  section_id: number | null;
}

export interface ValidationResponse {
  document_id: number;
  results: ValidationItem[];
}
