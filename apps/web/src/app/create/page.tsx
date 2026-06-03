import { CreateForm } from "@/components/studio/create-form";

export default function CreatePage() {
  return (
    <div className="space-y-8">
      <div className="animate-fade-in border-b border-border pb-5">
        <h1 className="page-title">New Avatar Video</h1>
        <p className="text-sm text-muted-foreground mt-1.5">
          Write or upload a script, pick a stock avatar or upload a custom
          photo/clip, choose a voice, and render a talking-head video stored on
          Backblaze B2.
        </p>
      </div>
      <div className="animate-fade-in-up stagger-2">
        <CreateForm />
      </div>
    </div>
  );
}
