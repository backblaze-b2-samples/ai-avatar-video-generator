import Link from "next/link";
import { Clapperboard } from "lucide-react";

import { Button } from "@/components/ui/button";
import { StatsCards } from "@/components/dashboard/stats-cards";
import { RecentRendersTable } from "@/components/dashboard/recent-renders-table";
import { RendersChart } from "@/components/dashboard/renders-chart";

export default function DashboardPage() {
  return (
    <div className="space-y-8">
      <div className="animate-fade-in border-b border-border pb-5 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="page-title">Dashboard</h1>
          <p className="text-sm text-muted-foreground mt-1.5">
            Your avatar-video projects and render activity, backed by Backblaze B2.
          </p>
        </div>
        <Button asChild size="sm" className="h-8">
          <Link href="/create">
            <Clapperboard className="h-3.5 w-3.5" />
            New avatar video
          </Link>
        </Button>
      </div>
      <StatsCards />
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="animate-fade-in-up stagger-3">
          <RendersChart />
        </div>
        <div className="animate-fade-in-up stagger-4">
          <RecentRendersTable />
        </div>
      </div>
    </div>
  );
}
