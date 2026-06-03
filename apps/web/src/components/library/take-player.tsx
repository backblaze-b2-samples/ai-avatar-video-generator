"use client";

import { useEffect, useRef, useState } from "react";
import { Download, Play } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/library/status-badge";
import { ApiError, getTakeVideoUrl } from "@/lib/api-client";
import type { TakeDetail } from "@ai-avatar-video-generator/shared";
import { formatDate } from "@/lib/utils";

interface TakePlayerProps {
  projectId: string;
  takes: TakeDetail[];
}

export function TakePlayer({ projectId, takes }: TakePlayerProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [loadingId, setLoadingId] = useState<string | null>(null);
  const [src, setSrc] = useState<string | null>(null);

  // Auto-select the newest completed take so a freshly finished render plays
  // without an extra click.
  useEffect(() => {
    if (activeId) return;
    const newestDone = [...takes]
      .reverse()
      .find((t) => t.status === "complete" && t.video_key);
    if (newestDone) void play(newestDone.take_id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [takes]);

  // Stream the chosen take inline from a presigned B2 URL (no attachment
  // disposition), letting the browser issue Range reads against B2.
  const play = async (takeId: string) => {
    setLoadingId(takeId);
    try {
      const { url } = await getTakeVideoUrl(projectId, takeId);
      setSrc(url);
      setActiveId(takeId);
      requestAnimationFrame(() => {
        videoRef.current?.load();
        videoRef.current?.play().catch(() => undefined);
      });
    } catch (err) {
      const detail =
        err instanceof ApiError ? err.message : "Could not load take video";
      toast.error(detail);
    } finally {
      setLoadingId(null);
    }
  };

  const download = async (takeId: string) => {
    try {
      const { url } = await getTakeVideoUrl(projectId, takeId, true);
      window.open(url, "_blank");
    } catch (err) {
      const detail = err instanceof ApiError ? err.message : "Take not ready";
      toast.error(detail);
    }
  };

  return (
    <div className="space-y-3">
      <video
        ref={videoRef}
        controls
        src={src ?? undefined}
        className="aspect-video w-full rounded-md border border-border bg-black"
      />
      <ul className="divide-y divide-border rounded-md border border-border">
        {takes.map((take, i) => {
          const ready = take.status === "complete" && !!take.video_key;
          const isActive = take.take_id === activeId;
          return (
            <li
              key={take.take_id}
              className={`flex items-center gap-3 px-4 py-2.5 text-sm ${isActive ? "bg-accent/40" : ""}`}
            >
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="h-7 w-7 shrink-0"
                disabled={!ready || loadingId === take.take_id}
                onClick={() => play(take.take_id)}
                aria-label={`Play take ${i + 1}`}
              >
                <Play className="h-3.5 w-3.5" />
              </Button>
              <span className="w-12 font-mono text-xs tabular-nums text-muted-foreground">
                Take {i + 1}
              </span>
              <span className="flex-1 truncate text-xs text-muted-foreground">
                {formatDate(take.created_at)}
              </span>
              {take.status === "complete" ? (
                <span className="whitespace-nowrap font-mono text-xs tabular-nums text-muted-foreground">
                  {take.duration_human ?? "—"}
                </span>
              ) : (
                <StatusBadge status={take.status} />
              )}
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="h-7 w-7 shrink-0"
                disabled={!ready}
                onClick={() => download(take.take_id)}
                aria-label={`Download take ${i + 1}`}
              >
                <Download className="h-3.5 w-3.5" />
              </Button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
