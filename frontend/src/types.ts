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

export interface HldDocument {
  id: number;
  increment_id: number;
  type: string;
  title: string;
  git_branch: string;
  head_commit: string | null;
  sections: Section[];
  diagrams: Diagram[];
  breadcrumb: Record<string, string>;
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
