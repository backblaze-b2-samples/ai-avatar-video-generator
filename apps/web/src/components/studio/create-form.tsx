"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Clapperboard, Upload } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { VoicePicker } from "@/components/studio/voice-picker";
import {
  AvatarPicker,
  type AvatarSelection,
} from "@/components/studio/avatar-picker";
import { ApiError } from "@/lib/api-client";
import { useCreateProject } from "@/lib/queries";

export function CreateForm() {
  const router = useRouter();
  const createProject = useCreateProject();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [title, setTitle] = useState("");
  const [script, setScript] = useState("");
  const [voiceId, setVoiceId] = useState("");
  const [avatar, setAvatar] = useState<AvatarSelection>({});
  const [scriptSource, setScriptSource] = useState<"typed" | "upload">("typed");

  const hasAvatar = !!avatar.stockId || !!avatar.file;
  const canSubmit =
    title.trim().length > 0 &&
    script.trim().length > 0 &&
    hasAvatar &&
    !createProject.isPending;

  const onPickScript = async (file: File | undefined) => {
    if (!file) return;
    if (!file.type.startsWith("text/") && !file.name.endsWith(".txt")) {
      toast.error("Please choose a plain-text (.txt) script.");
      return;
    }
    setScript(await file.text());
    setScriptSource("upload");
    if (!title.trim()) setTitle(file.name.replace(/\.[^.]+$/, ""));
  };

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!canSubmit) return;
    createProject.mutate(
      {
        title: title.trim(),
        script,
        voiceId: voiceId || undefined,
        stockAvatarId: avatar.stockId,
        avatarFile: avatar.file,
        scriptSource,
      },
      {
        onSuccess: (project) => {
          toast.success("Render started");
          router.push(`/library?project=${project.id}`);
        },
        onError: (err) => {
          const detail =
            err instanceof ApiError ? err.message : "Failed to start render";
          toast.error(detail);
        },
      },
    );
  };

  return (
    <form onSubmit={onSubmit} className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
      <Card>
        <CardHeader className="border-b border-border py-4 px-5">
          <CardTitle className="card-title">Script</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 p-5">
          <div className="space-y-2">
            <Label htmlFor="title">Title</Label>
            <Input
              id="title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Product launch intro"
              maxLength={200}
            />
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label htmlFor="script">Script</Label>
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="h-7 text-xs"
                onClick={() => fileInputRef.current?.click()}
              >
                <Upload className="h-3.5 w-3.5 mr-1" />
                Load .txt
              </Button>
              <input
                ref={fileInputRef}
                type="file"
                accept=".txt,text/plain"
                className="hidden"
                onChange={(e) => onPickScript(e.target.files?.[0])}
              />
            </div>
            <Textarea
              id="script"
              value={script}
              onChange={(e) => {
                setScript(e.target.value);
                setScriptSource("typed");
              }}
              placeholder="Type what your avatar should say. One take, one voice — render again to iterate."
              className="min-h-[200px] text-sm"
            />
            <p className="text-xs text-muted-foreground">
              {script.length.toLocaleString()} characters
            </p>
          </div>

          <div className="space-y-2">
            <Label>Voice</Label>
            <VoicePicker value={voiceId} onChange={setVoiceId} />
          </div>

          <Button type="submit" disabled={!canSubmit} className="w-full">
            <Clapperboard className="h-4 w-4" />
            {createProject.isPending ? "Starting…" : "Render video"}
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="border-b border-border py-4 px-5">
          <CardTitle className="card-title">Avatar</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 p-5">
          <p className="text-xs text-muted-foreground">
            Pick a stock presenter or upload a custom photo/clip. Custom uploads
            are archived to B2 with the project.
          </p>
          <AvatarPicker value={avatar} onChange={setAvatar} />
        </CardContent>
      </Card>
    </form>
  );
}
