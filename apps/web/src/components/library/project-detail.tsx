"use client";

import { useState } from "react";
import { Clapperboard, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/ui/error-state";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { GeneratingLoader } from "@/components/ui/generating-loader";
import { StatusBadge } from "@/components/library/status-badge";
import { TakePlayer } from "@/components/library/take-player";
import { ApiError } from "@/lib/api-client";
import {
  useDeleteProject,
  useProject,
  useRenderAnotherTake,
} from "@/lib/queries";

interface ProjectDetailProps {
  projectId: string;
  onDeleted: () => void;
}

export function ProjectDetail({ projectId, onDeleted }: ProjectDetailProps) {
  const { data: project, isLoading, error, refetch } = useProject(projectId);
  const deleteProject = useDeleteProject();
  const renderTake = useRenderAnotherTake();
  const [confirmOpen, setConfirmOpen] = useState(false);

  if (isLoading) return <Skeleton className="h-80 w-full" />;
  if (error) return <ErrorState error={error} onRetry={() => refetch()} />;
  if (!project) return null;

  const inFlight = project.status === "pending" || project.status === "rendering";

  const onRenderAnother = () => {
    renderTake.mutate(project.id, {
      onSuccess: () => toast.success("New take queued"),
      onError: (err) => {
        const detail =
          err instanceof ApiError ? err.message : "Failed to queue take";
        toast.error(detail);
      },
    });
  };

  const onDelete = () => {
    deleteProject.mutate(project.id, {
      onSuccess: () => {
        toast.success(`${project.title} deleted`);
        onDeleted();
      },
      onError: (err) => {
        const detail = err instanceof ApiError ? err.message : "Failed to delete";
        toast.error(detail);
      },
      onSettled: () => setConfirmOpen(false),
    });
  };

  return (
    <>
      <Card>
        <CardHeader className="flex flex-row items-start justify-between gap-3 border-b border-border py-4 px-5 space-y-0">
          <div className="min-w-0 space-y-1">
            <CardTitle className="card-title truncate">{project.title}</CardTitle>
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <StatusBadge status={project.status} />
              <span>
                {project.renders_complete}/{project.take_count} takes ·{" "}
                {project.total_duration_human}
              </span>
            </div>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <Button
              variant="outline"
              size="sm"
              className="h-8"
              onClick={onRenderAnother}
              disabled={inFlight || renderTake.isPending}
            >
              <Clapperboard className="h-3.5 w-3.5" />
              Render another take
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="h-8 text-destructive"
              onClick={() => setConfirmOpen(true)}
            >
              <Trash2 className="h-3.5 w-3.5" />
            </Button>
          </div>
        </CardHeader>
        <CardContent className="p-5 space-y-4">
          {inFlight && (
            <div className="flex items-center gap-3 rounded-md border border-border bg-muted/30 p-3">
              <GeneratingLoader size="sm" />
              <span className="text-sm text-muted-foreground">
                Rendering your avatar video… this updates automatically.
              </span>
            </div>
          )}
          {project.status === "failed" && project.error && (
            <p className="text-sm text-destructive">{project.error}</p>
          )}
          <TakePlayer projectId={project.id} takes={project.takes} />
        </CardContent>
      </Card>

      <AlertDialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete project?</AlertDialogTitle>
            <AlertDialogDescription>
              This permanently removes <strong>{project.title}</strong> — its
              script, any uploaded avatar, and every rendered take — from B2.
              This cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={onDelete}
              disabled={deleteProject.isPending}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {deleteProject.isPending ? "Deleting…" : "Delete"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
