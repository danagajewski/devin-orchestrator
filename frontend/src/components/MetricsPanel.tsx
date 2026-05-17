import {
  Activity,
  CheckCircle2,
  Clock,
  DollarSign,
  Loader2,
  XCircle,
  Zap,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { Metrics } from "@/lib/api";

interface MetricsPanelProps {
  metrics: Metrics | null;
  loading: boolean;
}

function formatDuration(seconds: number | null): string {
  if (seconds === null) return "—";
  if (seconds < 60) return `${Math.round(seconds)}s`;
  if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
  const hours = Math.floor(seconds / 3600);
  const mins = Math.round((seconds % 3600) / 60);
  return `${hours}h ${mins}m`;
}

export default function MetricsPanel({ metrics, loading }: MetricsPanelProps) {
  if (loading || !metrics) {
    return (
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {[...Array(4)].map((_, i) => (
          <Card key={i} className="animate-pulse">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <div className="h-4 w-24 rounded bg-muted" />
            </CardHeader>
            <CardContent>
              <div className="h-8 w-16 rounded bg-muted" />
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  const cards = [
    {
      title: "Total Sessions",
      value: metrics.total_sessions,
      subtitle: `${metrics.active_sessions} active now`,
      icon: Activity,
      color: "text-blue-500",
    },
    {
      title: "Success Rate",
      value: `${metrics.success_rate}%`,
      subtitle: `${metrics.completed_sessions} completed, ${metrics.failed_sessions} failed`,
      icon: metrics.success_rate >= 80 ? CheckCircle2 : XCircle,
      color: metrics.success_rate >= 80 ? "text-green-500" : "text-red-500",
    },
    {
      title: metrics.total_acus > 0 ? "Total ACUs" : "Est. ACUs",
      value:
        metrics.total_acus > 0
          ? metrics.total_acus.toFixed(1)
          : metrics.total_estimated_acus > 0
            ? `~${metrics.total_estimated_acus.toFixed(1)}`
            : "—",
      subtitle:
        metrics.total_acus > 0
          ? `~${metrics.avg_acus_per_session.toFixed(1)} avg per session`
          : metrics.total_estimated_acus > 0
            ? `~${metrics.avg_estimated_acus.toFixed(1)} avg per session`
            : "awaiting data",
      icon: DollarSign,
      color: "text-amber-500",
    },
    {
      title: "Avg Resolution",
      value: formatDuration(metrics.avg_resolution_seconds),
      subtitle: "time to complete",
      icon: metrics.avg_resolution_seconds ? Clock : Zap,
      color: "text-purple-500",
    },
  ];

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      {cards.map((card) => (
        <Card key={card.title}>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              {card.title}
            </CardTitle>
            <card.icon className={`h-4 w-4 ${card.color}`} />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{card.value}</div>
            <p className="text-xs text-muted-foreground mt-1">
              {loading ? (
                <Loader2 className="h-3 w-3 animate-spin inline mr-1" />
              ) : null}
              {card.subtitle}
            </p>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
