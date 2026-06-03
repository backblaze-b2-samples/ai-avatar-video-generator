"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ApiError,
  type CreateProjectInput,
  createProject,
  deleteFile,
  deleteProject,
  getAvatars,
  getFiles,
  getFileStats,
  getPreviewUrl,
  getProject,
  getProjectActivity,
  getProjects,
  getProjectStats,
  getUploadActivity,
  getVoices,
  renderAnotherTake,
} from "@/lib/api-client";
import type { FileMetadata, Project } from "@ai-avatar-video-generator/shared";

// Single source of truth for query keys. Keep these tightly scoped so that
// invalidating "files" doesn't blow away unrelated caches, and so an IDE
// "find usages" of `qk.files` reveals every consumer.
export const qk = {
  all: ["b2"] as const,
  files: (prefix?: string, limit?: number) =>
    [...qk.all, "files", prefix ?? "", limit ?? 100] as const,
  stats: () => [...qk.all, "stats"] as const,
  uploadActivity: (days: number) =>
    [...qk.all, "stats", "activity", days] as const,
  preview: (key: string) => [...qk.all, "preview", key] as const,
  projects: () => [...qk.all, "projects"] as const,
  project: (id: string) => [...qk.all, "projects", id] as const,
  projectStats: () => [...qk.all, "projects", "stats"] as const,
  projectActivity: (days: number) =>
    [...qk.all, "projects", "activity", days] as const,
  avatars: () => [...qk.all, "avatars"] as const,
  voices: () => [...qk.all, "voices"] as const,
};

// A project/take is "in flight" while a render is queued or running — poll it.
function isInFlight(status: string): boolean {
  return status === "pending" || status === "rendering";
}

export function useFiles(prefix = "", limit = 100) {
  return useQuery<FileMetadata[], ApiError>({
    queryKey: qk.files(prefix, limit),
    queryFn: () => getFiles(prefix, limit),
  });
}

export function useFileStats() {
  return useQuery({
    queryKey: qk.stats(),
    queryFn: getFileStats,
  });
}

export function useUploadActivity(days = 7) {
  return useQuery({
    queryKey: qk.uploadActivity(days),
    queryFn: () => getUploadActivity(days),
  });
}

// Presigned preview URL — only fetched when `enabled` is true (e.g., when
// the dialog opens for a specific file). Kept short-lived (60s) because
// the URL itself has a presigned expiry and is cheap to regenerate.
export function usePreviewUrl(key: string | undefined, enabled: boolean) {
  return useQuery({
    queryKey: qk.preview(key ?? ""),
    queryFn: () => getPreviewUrl(key as string),
    enabled: enabled && !!key,
    staleTime: 60_000,
  });
}

export function useDeleteFile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (fileKey: string) => deleteFile(fileKey),
    // After delete, blow away every cached file list + stats. Cheap and
    // correct — the dashboard re-fetches lazily as components remount.
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.all });
    },
  });
}

// ----- Avatar-video hooks -----

export function useAvatars() {
  return useQuery({
    queryKey: qk.avatars(),
    queryFn: getAvatars,
    staleTime: 5 * 60_000,
  });
}

export function useVoices() {
  return useQuery({
    queryKey: qk.voices(),
    queryFn: getVoices,
    staleTime: 5 * 60_000,
  });
}

export function useProjects() {
  return useQuery({
    queryKey: qk.projects(),
    queryFn: getProjects,
    // Poll the library while any project is still rendering so progress
    // updates without a manual refresh.
    refetchInterval: (query) => {
      const data = query.state.data as { status: string }[] | undefined;
      return data?.some((p) => isInFlight(p.status)) ? 3000 : false;
    },
  });
}

export function useProject(id: string | undefined) {
  return useQuery<Project, ApiError>({
    queryKey: qk.project(id ?? ""),
    queryFn: () => getProject(id as string),
    enabled: !!id,
    refetchInterval: (query) =>
      query.state.data && isInFlight(query.state.data.status) ? 2000 : false,
  });
}

export function useProjectStats() {
  return useQuery({
    queryKey: qk.projectStats(),
    queryFn: getProjectStats,
  });
}

export function useProjectActivity(days = 7) {
  return useQuery({
    queryKey: qk.projectActivity(days),
    queryFn: () => getProjectActivity(days),
  });
}

export function useCreateProject() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: CreateProjectInput) => createProject(input),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.projects() });
      qc.invalidateQueries({ queryKey: qk.projectStats() });
    },
  });
}

export function useRenderAnotherTake() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => renderAnotherTake(id),
    onSuccess: (_data, id) => {
      qc.invalidateQueries({ queryKey: qk.project(id) });
      qc.invalidateQueries({ queryKey: qk.projects() });
    },
  });
}

export function useDeleteProject() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteProject(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.all });
    },
  });
}
