"use client";

import { Loader2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import type { RenderStatus } from "@ai-avatar-video-generator/shared";

const LABELS: Record<RenderStatus, string> = {
  pending: "Queued",
  rendering: "Rendering",
  complete: "Complete",
  failed: "Failed",
};

const VARIANTS: Record<
  RenderStatus,
  "default" | "secondary" | "outline" | "destructive"
> = {
  pending: "secondary",
  rendering: "secondary",
  complete: "default",
  failed: "destructive",
};

export function StatusBadge({ status }: { status: RenderStatus }) {
  const inFlight = status === "pending" || status === "rendering";
  return (
    <Badge variant={VARIANTS[status]} className="gap-1">
      {inFlight && <Loader2 className="h-3 w-3 animate-spin" />}
      {LABELS[status]}
    </Badge>
  );
}
