"use client";
import { useState } from "react";
import { ChevronLeft, ChevronRight, ShieldCheck, LogIn, LogOut } from "lucide-react";
import { RequireAuth } from "@/components/RequireAuth";
import { Badge, EmptyState, ErrorNote, PageHeader, Section, Skeleton, Table } from "@/components/ui";
import { API_BASE, getToken } from "@/lib/api";
import { useData } from "@/lib/useData";

const PAGE_SIZE = 15;

export default function TenantAuditPage() {
  return (
    <RequireAuth roles={["tenant_admin"]}>
      <TenantAudit />
    </RequireAuth>
  );
}

function TenantAudit() {
  const { data, loading, error } = useData(async () => {
    const token = getToken();
    const res = await fetch(`${API_BASE}/tenant/audit?limit=500`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!res.ok) throw new Error("Failed to load audit log");
    return res.json();
  });
  const [page, setPage] = useState(0);
  const [actionFilter, setActionFilter] = useState<string>("");

  const allEvents = data ?? [];
  const events = actionFilter
    ? allEvents.filter((a: any) => a.action === actionFilter)
    : allEvents;
  const totalPages = Math.ceil(events.length / PAGE_SIZE);
  const pageItems = events.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

  const uniqueActions = Array.from(new Set(allEvents.map((a: any) => a.action))).sort();

  return (
    <>
      <PageHeader
        title="Activity Log"
        sub="Login and logout events for students and admins in your institution."
      />

      {/* Filter */}
      <Section className="mb-4" compact>
        <div className="flex items-center gap-4 flex-wrap">
          <div>
            <label className="text-[10px] font-bold uppercase tracking-wider text-muted mb-1 block">Action</label>
            <select className="ds-input text-xs" value={actionFilter} onChange={(e) => { setActionFilter(e.target.value); setPage(0); }}>
              <option value="">All events</option>
              <option value="auth.login">Login</option>
              <option value="auth.logout">Logout</option>
            </select>
          </div>
          <div className="text-xs text-muted self-end">
            {events.length} event{events.length !== 1 ? "s" : ""}
          </div>
        </div>
      </Section>

      <Section>
        {loading ? <Skeleton rows={5} /> : error ? <ErrorNote message={error} /> :
         events.length === 0 ? (
          <EmptyState
            title="No activity yet"
            desc="Login events will appear here as users access the platform."
          />
        ) : (
          <>
            <Table
              columns={["When", "User", "Action", "IP Address", "Type"]}
              rows={pageItems.map((a: any) => [
                new Date(a.at).toLocaleString("en-IN", {
                  day: "numeric", month: "short", year: "numeric",
                  hour: "2-digit", minute: "2-digit",
                }),
                <span key="u" className="flex items-center gap-2">
                  {a.action === "auth.login"
                    ? <LogIn size={14} style={{ color: "var(--rag-green)" }} />
                    : <LogOut size={14} style={{ color: "var(--rag-amber)" }} />}
                  <span className="font-medium">{a.actor_label || "Unknown"}</span>
                </span>,
                <code key="a" className="kbd">{a.action}</code>,
                <span key="ip" className="text-[10px] text-muted font-mono">{a.ip_address || "--"}</span>,
                <Badge key="t" tone="var(--muted)">{a.entity || "user"}</Badge>,
              ])}
            />

            {totalPages > 1 && (
              <div className="flex items-center justify-between p-3 border-t" style={{ borderColor: "var(--border)" }}>
                <span className="text-[11px] text-muted">
                  Showing {page * PAGE_SIZE + 1}–{Math.min((page + 1) * PAGE_SIZE, events.length)} of {events.length}
                </span>
                <div className="flex items-center gap-1">
                  <button disabled={page === 0} onClick={() => setPage(page - 1)}
                    className="p-1 rounded disabled:opacity-30 hover:bg-surface2"><ChevronLeft size={14} /></button>
                  {Array.from({ length: Math.min(totalPages, 7) }, (_, i) => {
                    let pIdx = i;
                    if (totalPages > 7) {
                      if (page < 3) pIdx = i;
                      else if (page > totalPages - 4) pIdx = totalPages - 7 + i;
                      else pIdx = page - 3 + i;
                    }
                    return (
                      <button key={pIdx} onClick={() => setPage(pIdx)}
                        className="w-6 h-6 rounded text-[11px] font-medium"
                        style={{ background: pIdx === page ? "var(--primary)" : "transparent", color: pIdx === page ? "white" : "var(--muted)" }}>
                        {pIdx + 1}
                      </button>
                    );
                  })}
                  <button disabled={page >= totalPages - 1} onClick={() => setPage(page + 1)}
                    className="p-1 rounded disabled:opacity-30 hover:bg-surface2"><ChevronRight size={14} /></button>
                </div>
              </div>
            )}
          </>
        )}
      </Section>
    </>
  );
}
