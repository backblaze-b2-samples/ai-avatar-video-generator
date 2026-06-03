export type FileStatus = "uploading" | "complete" | "error";

export interface FileMetadata {
  key: string;
  filename: string;
  folder: string;
  size_bytes: number;
  size_human: string;
  content_type: string;
  uploaded_at: string;
  url: string | null;
}

export interface FileMetadataDetail {
  filename: string;
  size_bytes: number;
  size_human: string;
  mime_type: string;
  extension: string;
  md5: string;
  sha256: string;
  uploaded_at: string;
  // Video (rendered takes) — duration parsed from the MP4 container header.
  duration_seconds: number | null;
  duration_human: string | null;
}

export interface FileUploadResponse {
  key: string;
  filename: string;
  size_bytes: number;
  size_human: string;
  content_type: string;
  uploaded_at: string;
  url: string | null;
  metadata: FileMetadataDetail | null;
}

export interface DailyUploadCount {
  date: string;
  uploads: number;
}

export interface UploadStats {
  total_files: number;
  total_size_bytes: number;
  total_size_human: string;
  uploads_today: number;
  total_downloads: number;
}

// ----- Avatar-video domain (mirrors services/api/app/types/projects.py) -----

export type RenderStatus = "pending" | "rendering" | "complete" | "failed";

export type AvatarSource = "stock" | "upload";
export type ScriptSource = "typed" | "upload";

export interface Avatar {
  id: string;
  name: string;
  thumbnail_url: string | null;
  source: AvatarSource;
}

export interface Voice {
  id: string;
  name: string;
  description: string | null;
  language: string | null;
}

export interface AvatarRef {
  source: AvatarSource;
  provider_avatar_id: string | null;
  image_key: string | null;
}

export interface TakeDetail {
  take_id: string;
  status: RenderStatus;
  provider: string;
  video_key: string | null;
  duration_seconds: number | null;
  duration_human: string | null;
  error: string | null;
  created_at: string;
}

export interface Project {
  id: string;
  title: string;
  status: RenderStatus;
  script_source: ScriptSource;
  avatar: AvatarRef;
  voice_id: string;
  take_count: number;
  renders_complete: number;
  total_duration_seconds: number;
  total_duration_human: string;
  created_at: string;
  updated_at: string;
  error: string | null;
  takes: TakeDetail[];
}

export interface ProjectSummary {
  id: string;
  title: string;
  status: RenderStatus;
  avatar: AvatarRef;
  take_count: number;
  renders_complete: number;
  total_duration_seconds: number;
  total_duration_human: string;
  created_at: string;
}

export interface ProjectStats {
  total_projects: number;
  total_renders: number;
  total_duration_seconds: number;
  total_duration_human: string;
  total_size_bytes: number;
  total_size_human: string;
}

export interface DailyRendersCount {
  date: string;
  renders: number;
}
