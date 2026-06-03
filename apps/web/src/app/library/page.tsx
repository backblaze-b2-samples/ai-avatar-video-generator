"use client";

import { Suspense, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Clapperboard } from "lucide-react";

import { Button } from "@/components/ui/button";
import { ProjectGrid } from "@/components/library/project-grid";
import { ProjectDetail } from "@/components/library/project-detail";

function LibraryView() {
  const params = useSearchParams();
  const initial = params.get("project");
  const [selectedId, setSelectedId] = useState<string | null>(initial);

  return (
    <div className="space-y-8">
      <div className="animate-fade-in border-b border-border pb-5 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="page-title">Library</h1>
          <p className="text-sm text-muted-foreground mt-1.5">
            Your avatar videos, scoped to the <code>avatar-projects/</code>{" "}
            prefix. Play takes inline, render another take, or download.
          </p>
        </div>
        <Button asChild size="sm" className="h-8">
          <Link href="/create">
            <Clapperboard className="h-3.5 w-3.5" />
            New avatar video
          </Link>
        </Button>
      </div>

      {selectedId && (
        <div className="animate-fade-in-up">
          <ProjectDetail
            projectId={selectedId}
            onDeleted={() => setSelectedId(null)}
          />
        </div>
      )}

      <div className="animate-fade-in-up stagger-2">
        <ProjectGrid selectedId={selectedId} onSelect={setSelectedId} />
      </div>
    </div>
  );
}

export default function LibraryPage() {
  return (
    <Suspense fallback={null}>
      <LibraryView />
    </Suspense>
  );
}
