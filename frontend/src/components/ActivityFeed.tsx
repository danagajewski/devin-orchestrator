import {
  CheckCircle2,
  CircleDot,
  Eye,
  GitMerge,
  GitPullRequest,
  XCircle,
  Zap,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { OrchestratedSession } from "@/lib/api";

interface ActivityFeedProps {
  sessions: OrchestratedSession[];
}

function timeAgo(ts: number): string {
  const diff = Math.floor(Date.now() / 1000 - ts);
  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

interface FeedItem {
  id: string;
  time: number;
  icon: React.ReactNode;
  message: string;
  url: string;
}

function buildFeedItems(sessions: OrchestratedSession[]): FeedItem[] {
  const items: FeedItem[] = [];

  for (const s of sessions) {
    items.push({
      id: `${s.session_id}-created`,
      time: s.created_at,
      icon: <CircleDot className="h-4 w-4 text-blue-500" />,
      message: `Session started for issue #${s.github_issue_number}: ${s.github_issue_title}`,
      url: s.devin_url,
    });

    if (s.status === "completed" && s.completed_at) {
      items.push({
        id: `${s.session_id}-completed`,
        time: s.completed_at,
        icon: <CheckCircle2 className="h-4 w-4 text-green-500" />,
        message: `Issue #${s.github_issue_number} resolved (${s.acus_consumed.toFixed(1)} ACUs)`,
        url: s.devin_url,
      });
    }

    if (s.status === "failed" && s.completed_at) {
      items.push({
        id: `${s.session_id}-failed`,
        time: s.completed_at,
        icon: <XCircle className="h-4 w-4 text-red-500" />,
        message: `Session failed for issue #${s.github_issue_number}`,
        url: s.devin_url,
      });
    }

    for (const pr of s.pull_requests) {
      items.push({
        id: `${s.session_id}-pr-${pr.number || 0}`,
        time: s.completed_at || s.created_at,
        icon: <GitPullRequest className="h-4 w-4 text-purple-500" />,
        message: `PR ${pr.number ? `#${pr.number}` : ""} opened for issue #${s.github_issue_number}`,
        url: pr.url,
      });

      if (pr.merged) {
        items.push({
          id: `${s.session_id}-merged-${pr.number || 0}`,
          time: s.issue_closed_at || s.completed_at || s.created_at,
          icon: <GitMerge className="h-4 w-4 text-purple-600" />,
          message: `PR ${pr.number ? `#${pr.number}` : ""} merged for issue #${s.github_issue_number}`,
          url: pr.url,
        });
      }
    }

    if (s.merge_strategy === "auto_merged") {
      items.push({
        id: `${s.session_id}-auto-merged`,
        time: s.issue_closed_at || s.completed_at || s.created_at,
        icon: <Zap className="h-4 w-4 text-emerald-500" />,
        message: `PR auto-merged for issue #${s.github_issue_number}`,
        url: s.pull_requests[0]?.url || s.devin_url,
      });
    } else if (s.merge_strategy === "review_requested") {
      items.push({
        id: `${s.session_id}-review-requested`,
        time: s.completed_at || s.created_at,
        icon: <Eye className="h-4 w-4 text-amber-500" />,
        message: `Human review requested for issue #${s.github_issue_number}`,
        url: s.pull_requests[0]?.url || s.devin_url,
      });
    }

    if (s.issue_closed && s.issue_closed_at) {
      items.push({
        id: `${s.session_id}-issue-closed`,
        time: s.issue_closed_at,
        icon: <CheckCircle2 className="h-4 w-4 text-emerald-500" />,
        message: `Issue #${s.github_issue_number} closed (resolved)`,
        url: s.github_issue_url,
      });
    }
  }

  return items.sort((a, b) => b.time - a.time).slice(0, 15);
}

export default function ActivityFeed({ sessions }: ActivityFeedProps) {
  const items = buildFeedItems(sessions);

  if (items.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">
            Recent Activity
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center h-48 text-muted-foreground text-sm">
            No activity yet
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium">Recent Activity</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-3 max-h-64 overflow-y-auto">
          {items.map((item) => (
            <a
              key={item.id}
              href={item.url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-start gap-3 p-2 rounded-md hover:bg-muted/50 transition-colors"
            >
              <div className="mt-0.5 shrink-0">{item.icon}</div>
              <div className="min-w-0 flex-1">
                <p className="text-sm truncate">{item.message}</p>
                <p className="text-xs text-muted-foreground">
                  {timeAgo(item.time)}
                </p>
              </div>
            </a>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
