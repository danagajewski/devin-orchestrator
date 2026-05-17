import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { OrchestratedSession } from "@/lib/api";

interface CostChartProps {
  sessions: OrchestratedSession[];
}

const STATUS_COLORS: Record<string, string> = {
  completed: "#22c55e",
  running: "#3b82f6",
  pending: "#eab308",
  failed: "#ef4444",
  suspended: "#6b7280",
  merged: "#a855f7",
};

function formatMinutes(mins: number): string {
  if (mins < 1) return "<1m";
  if (mins < 60) return `${Math.round(mins)}m`;
  const h = Math.floor(mins / 60);
  const m = Math.round(mins % 60);
  return `${h}h ${m}m`;
}

export default function CostChart({ sessions }: CostChartProps) {
  if (sessions.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">
            Session Duration (last 20)
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center h-48 text-muted-foreground text-sm">
            No session data yet
          </div>
        </CardContent>
      </Card>
    );
  }

  const hasRealAcus = sessions.some((s) => s.acus_consumed > 0);
  const hasEstimatedAcus = sessions.some((s) => (s.estimated_acus ?? 0) > 0);
  const hasAcus = hasRealAcus || hasEstimatedAcus;

  const data = sessions
    .slice(0, 20)
    .reverse()
    .map((s) => {
      let value: number;
      if (hasRealAcus) {
        value = Number(s.acus_consumed.toFixed(2));
      } else if (hasEstimatedAcus) {
        value = Number((s.estimated_acus ?? 0).toFixed(2));
      } else {
        value = Number(((s.duration_seconds ?? 0) / 60).toFixed(1));
      }
      return {
        name: `#${s.github_issue_number}`,
        value,
        status: s.status,
        durationSeconds: s.duration_seconds,
        estimatedAcus: s.estimated_acus,
        devinMessages: s.num_devin_messages,
        sessionSize: s.session_size,
      };
    });

  const label = hasRealAcus
    ? "ACU Cost"
    : hasEstimatedAcus
      ? "Est. ACUs"
      : "Duration";
  const unit = hasAcus ? "ACUs" : "min";
  const titleText = hasRealAcus
    ? "ACU Cost per Session (last 20)"
    : hasEstimatedAcus
      ? "Est. ACU Cost per Session (last 20)"
      : "Session Duration (last 20)";

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium">
          {titleText}
        </CardTitle>
        {hasEstimatedAcus && !hasRealAcus && (
          <p className="text-xs text-muted-foreground">
            Based on message count &amp; session size
          </p>
        )}
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={240}>
          <BarChart data={data}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
            <XAxis
              dataKey="name"
              fontSize={12}
              tickLine={false}
              axisLine={false}
            />
            <YAxis
              fontSize={12}
              tickLine={false}
              axisLine={false}
              tickFormatter={(v) => `${v}`}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "hsl(var(--card))",
                border: "1px solid hsl(var(--border))",
                borderRadius: "8px",
                fontSize: "12px",
              }}
              formatter={(
                value: number,
                _name: string,
                props: {
                  payload?: {
                    durationSeconds?: number | null;
                    estimatedAcus?: number | null;
                    devinMessages?: number | null;
                    sessionSize?: string | null;
                  };
                },
              ) => {
                const p = props.payload;
                if (hasRealAcus) return [`${value} ACUs`, "Cost"];
                if (hasEstimatedAcus) {
                  const details = [
                    `~${value} ACUs`,
                    p?.devinMessages != null ? `${p.devinMessages} msgs` : null,
                    p?.sessionSize ? `size: ${p.sessionSize}` : null,
                  ]
                    .filter(Boolean)
                    .join(" · ");
                  return [details, label];
                }
                const secs = p?.durationSeconds;
                return [secs ? formatMinutes(secs / 60) : "—", label];
              }}
            />
            <Bar dataKey="value" name={unit} radius={[4, 4, 0, 0]}>
              {data.map((entry, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={STATUS_COLORS[entry.status] || "#6b7280"}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
