import { useCallback, useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import MetricsPanel from "@/components/MetricsPanel";
import SessionList from "@/components/SessionList";
import CostChart from "@/components/CostChart";
import ActivityFeed from "@/components/ActivityFeed";
import type { Metrics, OrchestratedSession } from "@/lib/api";
import { getMetrics, getSessions } from "@/lib/api";

const POLL_INTERVAL = 10_000;

export default function App() {
  const [sessions, setSessions] = useState<OrchestratedSession[]>([]);
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState("all");
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const fetchData = useCallback(async (showLoading = false) => {
    if (showLoading) setLoading(true);
    try {
      const [sessionsData, metricsData] = await Promise.all([
        getSessions(),
        getMetrics(),
      ]);
      setSessions(sessionsData);
      setMetrics(metricsData);
      setError(null);
      setLastUpdated(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch data");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData(true);
    const interval = setInterval(() => fetchData(false), POLL_INTERVAL);
    return () => clearInterval(interval);
  }, [fetchData]);

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b bg-card">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold tracking-tight">
              Devin Orchestrator
            </h1>
            <p className="text-sm text-muted-foreground">
              Automated issue resolution for{" "}
              <a
                href="https://github.com/danagajewski/superset"
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-600 hover:underline"
              >
                danagajewski/superset
              </a>
            </p>
          </div>
          <div className="flex items-center gap-3">
            {lastUpdated && (
              <span className="text-xs text-muted-foreground">
                Updated {lastUpdated.toLocaleTimeString()}
              </span>
            )}
            <Button
              variant="outline"
              size="sm"
              onClick={() => fetchData(false)}
              disabled={loading}
            >
              <RefreshCw
                className={`h-4 w-4 mr-1 ${loading ? "animate-spin" : ""}`}
              />
              Refresh
            </Button>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-6 space-y-6">
        {error && (
          <div className="rounded-md bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 p-4">
            <p className="text-sm text-red-700 dark:text-red-300">
              <strong>Error:</strong> {error}
            </p>
            <p className="text-xs text-red-600 dark:text-red-400 mt-1">
              Make sure the backend is running and accessible.
            </p>
          </div>
        )}

        <MetricsPanel metrics={metrics} loading={loading} />

        <div className="grid gap-6 lg:grid-cols-3">
          <div className="lg:col-span-2">
            <CostChart sessions={sessions} />
          </div>
          <ActivityFeed sessions={sessions} />
        </div>

        <div>
          <Tabs value={filter} onValueChange={setFilter}>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold">Sessions</h2>
              <TabsList>
                <TabsTrigger value="all">All</TabsTrigger>
                <TabsTrigger value="running">Running</TabsTrigger>
                <TabsTrigger value="completed">Completed</TabsTrigger>
                <TabsTrigger value="failed">Failed</TabsTrigger>
              </TabsList>
            </div>
            <TabsContent value={filter} className="mt-0">
              <SessionList
                sessions={sessions}
                loading={loading}
                filter={filter}
              />
            </TabsContent>
          </Tabs>
        </div>
      </main>

      <footer className="border-t mt-8 py-4">
        <div className="container mx-auto px-4 text-center text-xs text-muted-foreground">
          Devin Orchestrator &middot; Powered by{" "}
          <a
            href="https://devin.ai"
            target="_blank"
            rel="noopener noreferrer"
            className="hover:underline"
          >
            Devin API
          </a>{" "}
          &middot; Monitoring{" "}
          <a
            href="https://github.com/danagajewski/superset"
            target="_blank"
            rel="noopener noreferrer"
            className="hover:underline"
          >
            Apache Superset
          </a>
        </div>
      </footer>
    </div>
  );
}
