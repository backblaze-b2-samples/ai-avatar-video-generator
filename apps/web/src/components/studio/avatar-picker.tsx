"use client";

import { useRef } from "react";
import Image from "next/image";
import { ImagePlus, User } from "lucide-react";
import { toast } from "sonner";

import { Skeleton } from "@/components/ui/skeleton";
import { useAvatars } from "@/lib/queries";

export interface AvatarSelection {
  stockId?: string;
  file?: File;
}

interface AvatarPickerProps {
  value: AvatarSelection;
  onChange: (selection: AvatarSelection) => void;
}

const ACCEPT = "image/png,image/jpeg,image/webp,video/mp4,video/quicktime";

export function AvatarPicker({ value, onChange }: AvatarPickerProps) {
  const { data: avatars, isLoading, error } = useAvatars();
  const fileRef = useRef<HTMLInputElement>(null);

  const onPickFile = (file: File | undefined) => {
    if (!file) return;
    const ok = /^(image\/(png|jpeg|webp)|video\/(mp4|quicktime))$/.test(file.type);
    if (!ok) {
      toast.error("Use a PNG/JPEG/WEBP photo or an MP4/MOV clip.");
      return;
    }
    onChange({ file });
  };

  if (isLoading) {
    return (
      <div className="grid grid-cols-3 gap-3 sm:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="aspect-square w-full rounded-lg" />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <p className="text-sm text-muted-foreground">
        Stock avatars unavailable — check that your provider key is configured.
        You can still upload a custom photo or clip.
      </p>
    );
  }

  const tileBase =
    "relative flex aspect-square w-full flex-col items-center justify-center gap-1.5 rounded-lg border text-xs transition-colors";

  return (
    <div className="grid grid-cols-3 gap-3 sm:grid-cols-4">
      {(avatars ?? []).map((a) => {
        const active = value.stockId === a.id && !value.file;
        return (
          <button
            key={a.id}
            type="button"
            onClick={() => onChange({ stockId: a.id })}
            className={`${tileBase} ${
              active
                ? "border-primary ring-2 ring-primary bg-accent/40"
                : "border-border hover:bg-accent/30"
            }`}
          >
            {a.thumbnail_url ? (
              <Image
                src={a.thumbnail_url}
                alt={a.name}
                fill
                sizes="120px"
                className="rounded-lg object-cover"
              />
            ) : (
              <User className="h-6 w-6 text-muted-foreground" />
            )}
            <span className="truncate px-1 font-medium">{a.name}</span>
          </button>
        );
      })}

      <button
        type="button"
        onClick={() => fileRef.current?.click()}
        className={`${tileBase} ${
          value.file
            ? "border-primary ring-2 ring-primary bg-accent/40"
            : "border-dashed border-border hover:bg-accent/30"
        }`}
      >
        <ImagePlus className="h-6 w-6 text-muted-foreground" />
        <span className="truncate px-1 font-medium">
          {value.file ? value.file.name : "Upload custom"}
        </span>
      </button>
      <input
        ref={fileRef}
        type="file"
        accept={ACCEPT}
        className="hidden"
        onChange={(e) => onPickFile(e.target.files?.[0])}
      />
    </div>
  );
}
