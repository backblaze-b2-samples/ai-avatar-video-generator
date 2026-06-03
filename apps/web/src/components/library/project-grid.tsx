"use client";

import { Clapperboard } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { StatusBadge } from "@/components/library/status-badge";
import { useProjects } from "@/lib/queries";
import { formatDate } from "@/lib/utils";

interface ProjectGridProps {
  selectedId: string | null;
  onSelect: (id: string) => void;
}

export function ProjectGrid({ selectedId, onSelect }: ProjectGridProps) {
  const { data: projects = [], isLoading, error, refetch } = useProjects();

  if (isLoading) {
    return (
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-28 w-full" />
        ))}
      </div>
    );
  }

  if (error) return <ErrorState error={error} onRetry={() => refetch()} />;

  if (projects.length === 0) {
    return (
      <EmptyState
        icon={Clapperboard}
        title="No avatar videos yet"
        description="Create one from the New Avatar Video page to get started."
      />
    );
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
      {projects.map((project) => {
        const isActive = project.id === selectedId;
        return (
          <Card
            key={project.id}
            role="button"
            tabIndex={0}
            onClick={() => onSelect(project.id)}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                onSelect(project.id);
              }
            }}
            className={`card-hover cursor-pointer ${isActive ? "ring-2 ring-primary" : ""}`}
          >
            <CardContent className="p-4 space-y-3">
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-2 min-w-0">
                  <div className="stat-icon-wrap">
                    <Clapperboard className="h-4 w-4" />
                  </div>
                  <span className="font-medium truncate">{project.title}</span>
                </div>
                <StatusBadge status={project.status} />
              </div>
              <div className="flex items-center justify-between text-xs text-muted-foreground tabular-nums">
                <span>
                  {project.renders_complete}/{project.take_count} takes
                </span>
                <span>{project.total_duration_human}</span>
                <span>{formatDate(project.created_at)}</span>
              </div>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
