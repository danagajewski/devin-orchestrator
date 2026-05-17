import { CheckCircle2, ExternalLink, GitMerge, GitPullRequest, Loader2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { OrchestratedSession } from "@/lib/api";

interface SessionListProps {
  sessions: OrchestratedSession[];
  loading: boolean;
  filter: string;
}

const STATUS_STYLES: Record<string, string> = {
  pending: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200",
  running: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200",
  completed: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
  failed: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200",
  suspended: "bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200",
  merged: "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200",
};

function formatTime(ts: number): string {
  return new Date(ts * 1000).toLocaleString();
}

function formatDuration(seconds: number | null): string {
  if (seconds === null) return "—";
  if (seconds < 60) return `${Math.round(seconds)}s`;
  if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
  const hours = Math.floor(seconds / 3600);
  const mins = Math.round((seconds % 3600) / 60);
  return `${hours}h ${mins}m`;
}

export default function SessionList({
  sessions,
  loading,
  filter,
}: SessionListProps) {
  const filtered =
    filter === "all"
      ? sessions
      : sessions.filter((s) => s.status === filter);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (filtered.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
        <p className="text-lg">No sessions found</p>
        <p className="text-sm mt-1">
          {filter === "all"
            ? "Create a GitHub issue to trigger a Devin session"
            : `No ${filter} sessions`}
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-md border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-20">Issue</TableHead>
            <TableHead>Title</TableHead>
            <TableHead className="w-28">Status</TableHead>
            <TableHead className="w-24 text-right">ACUs</TableHead>
            <TableHead className="w-28">Duration</TableHead>
            <TableHead className="w-20">PR</TableHead>
            <TableHead className="w-40">Created</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {filtered.map((session) => (
            <TableRow key={session.session_id}>
              <TableCell>
                <a
                  href={session.github_issue_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 hover:underline font-mono"
                >
                  #{session.github_issue_number}
                </a>
              </TableCell>
              <TableCell>
                <div className="flex items-center gap-2">
                  <a
                    href={session.devin_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="hover:underline font-medium truncate max-w-xs"
                    title={session.github_issue_title}
                  >
                    {session.github_issue_title}
                  </a>
                  <a
                    href={session.devin_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-muted-foreground hover:text-foreground"
                  >
                    <ExternalLink className="h-3 w-3" />
                  </a>
                </div>
                {session.github_issue_labels.length > 0 && (
                  <div className="flex gap-1 mt-1">
                    {session.github_issue_labels.map((label) => (
                      <Badge
                        key={label}
                        variant="outline"
                        className="text-xs"
                      >
                        {label}
                      </Badge>
                    ))}
                  </div>
                )}
              </TableCell>
              <TableCell>
                <Badge className={STATUS_STYLES[session.status] || ""}>
                  {session.status === "running" && (
                    <Loader2 className="h-3 w-3 animate-spin mr-1" />
                  )}
                  {session.status}
                </Badge>
                {session.error && (
                  <p className="text-xs text-red-500 mt-1 truncate max-w-28" title={session.error}>
                    {session.error}
                  </p>
                )}
              </TableCell>
              <TableCell className="text-right font-mono">
                {session.acus_consumed.toFixed(1)}
              </TableCell>
              <TableCell className="font-mono">
                {formatDuration(session.duration_seconds)}
              </TableCell>
              <TableCell>
                {session.pull_requests.length > 0 ? (
                  <div className="flex flex-col gap-1">
                    {session.pull_requests.map((pr, i) => (
                      <a
                        key={i}
                        href={pr.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className={`inline-flex items-center gap-1 ${
                          pr.merged
                            ? "text-purple-600 hover:text-purple-700"
                            : "text-green-600 hover:text-green-700"
                        }`}
                      >
                        {pr.merged ? (
                          <GitMerge className="h-3 w-3" />
                        ) : (
                          <GitPullRequest className="h-3 w-3" />
                        )}
                        <span className="text-xs">
                          {pr.number ? `#${pr.number}` : "PR"}
                          {pr.merged && " merged"}
                        </span>
                      </a>
                    ))}
                  </div>
                ) : (
                  <span className="text-muted-foreground text-xs">—</span>
                )}
                {session.issue_closed && (
                  <div className="flex items-center gap-1 mt-1 text-emerald-600">
                    <CheckCircle2 className="h-3 w-3" />
                    <span className="text-xs">Issue closed</span>
                  </div>
                )}
              </TableCell>
              <TableCell className="text-xs text-muted-foreground">
                {formatTime(session.created_at)}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
