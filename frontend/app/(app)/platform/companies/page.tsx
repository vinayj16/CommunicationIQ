"use client";
import { useCallback, useEffect, useState } from "react";
import {
  Building2, Plus, Pencil, Trash2, X, Loader2, ChevronDown, ChevronRight,
  BarChart3, BookOpen, Mic, Headphones, PenLine, FileText,
} from "lucide-react";
import { RequireAuth } from "@/components/RequireAuth";
import { useToast } from "@/components/Toast";
import { ErrorNote, PageHeader, Section, Skeleton } from "@/components/ui";
import { PLATFORM_ROLES } from "@/lib/roles";
import { API_BASE, getToken } from "@/lib/api";

interface Company {
  id: string; name: string; slug: string; color: string;
  description: string; is_active: boolean;
  question_counts: Record<string, number>;
}

export default function CompaniesPage() {
  return (
    <RequireAuth roles={PLATFORM_ROLES}>
      <Companies />
    </RequireAuth>
  );
}

function Companies() {
  const { toast } = useToast();
  const [companies, setCompanies] = useState<Company[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [editing, setEditing] = useState<Company | null>(null);

  const loadCompanies = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const token = getToken();
      const res = await fetch(`${API_BASE}/platform/companies`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!res.ok) throw new Error("Failed to load companies");
      const data = await res.json();
      setCompanies(data);
    } catch {
      setError("Could not load companies");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadCompanies(); }, [loadCompanies]);

  async function handleCreate(name: string, color: string, description: string) {
    try {
      const token = getToken();
      const res = await fetch(`${API_BASE}/platform/companies`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ name, color, description }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to create");
      toast("success", `Company "${name}" created`);
      setShowCreate(false);
      loadCompanies();
    } catch (e: any) {
      toast("error", e.message);
    }
  }

  async function handleUpdate(id: string, body: Record<string, unknown>) {
    try {
      const token = getToken();
      const res = await fetch(`${API_BASE}/platform/companies/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error("Failed to update");
      toast("success", "Company updated");
      setEditing(null);
      loadCompanies();
    } catch (e: any) {
      toast("error", e.message);
    }
  }

  async function handleDelete(id: string, name: string) {
    if (!confirm(`Deactivate "${name}"? It will be hidden from students but questions remain.`)) return;
    try {
      const token = getToken();
      const res = await fetch(`${API_BASE}/platform/companies/${id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Failed to delete");
      toast("success", `Company "${name}" deactivated`);
      loadCompanies();
    } catch (e: any) {
      toast("error", e.message);
    }
  }

  const totalQuestions = companies.reduce((sum, c) => sum + (c.question_counts?.total || 0), 0);

  if (loading) return <Skeleton rows={5} />;
  if (error) return <ErrorNote message={error} />;

  return (
    <>
      <PageHeader
        title="Company Management"
        sub={`${companies.filter(c => c.is_active).length} active companies · ${totalQuestions} total questions across all companies`}
        action={
          <button onClick={() => setShowCreate(true)}
            className="btn btn-primary btn-sm flex items-center gap-1.5">
            <Plus size={14} /> Add Company
          </button>
        }
      />

      {/* Summary stats */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-6">
        {[
          { icon: BookOpen, label: "Reading", key: "reading", color: "var(--rag-green)" },
          { icon: Headphones, label: "Listening", key: "listening", color: "var(--rag-amber)" },
          { icon: Mic, label: "Speaking", key: "speaking", color: "var(--secondary)" },
          { icon: PenLine, label: "Writing", key: "writing", color: "var(--accent)" },
          { icon: FileText, label: "Quiz", key: "quiz", color: "var(--primary)" },
        ].map(({ icon: Icon, label, key, color }) => {
          const total = companies.reduce((sum, c) => sum + (c.question_counts?.[key] || 0), 0);
          return (
            <div key={key} className="ds-card p-3 text-center">
              <Icon size={18} style={{ color }} className="mx-auto mb-1" />
              <div className="text-2xl font-bold" style={{ color }}>{total}</div>
              <div className="text-[11px] text-muted">{label}</div>
            </div>
          );
        })}
      </div>

      {/* Company cards */}
      <div className="space-y-3">
        {companies.map((company) => {
          const counts = company.question_counts || {};
          return (
            <div key={company.id} className={`ds-card overflow-hidden ${!company.is_active ? "opacity-50" : ""}`}>
              <div className="flex items-center gap-4 p-4">
                <div className="w-10 h-10 rounded-lg flex items-center justify-center shrink-0"
                  style={{ background: company.color + "20" }}>
                  <Building2 size={20} style={{ color: company.color }} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-bold">{company.name}</span>
                    {!company.is_active && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-gray-200 text-gray-500">Inactive</span>
                    )}
                    <span className="text-[10px] px-1.5 py-0.5 rounded-full font-medium"
                      style={{ background: company.color + "20", color: company.color }}>
                      {counts.total || 0} questions
                    </span>
                  </div>
                  {company.description && (
                    <p className="text-[11px] text-muted mt-1 truncate">{company.description}</p>
                  )}
                  <div className="flex gap-3 mt-2">
                    {[
                      { label: "Reading", val: counts.reading },
                      { label: "Listening", val: counts.listening },
                      { label: "Speaking", val: counts.speaking },
                      { label: "Writing", val: counts.writing },
                      { label: "Quiz", val: counts.quiz },
                    ].map(({ label, val }) => (
                      <span key={label} className="text-[10px] text-muted">
                        {label}: <strong>{val || 0}</strong>
                      </span>
                    ))}
                  </div>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <button onClick={() => setEditing(company)}
                    className="p-2 rounded hover:bg-surface2 transition-colors text-muted hover:text-text"
                    title="Edit">
                    <Pencil size={14} />
                  </button>
                  <button onClick={() => handleDelete(company.id, company.name)}
                    className="p-2 rounded hover:bg-surface2 transition-colors text-muted hover:text-red-500"
                    title="Deactivate">
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Create Modal */}
      {showCreate && (
        <CompanyModal
          onClose={() => setShowCreate(false)}
          onSave={handleCreate}
        />
      )}

      {/* Edit Modal */}
      {editing && (
        <CompanyModal
          company={editing}
          onClose={() => setEditing(null)}
          onSave={(name, color, desc) => handleUpdate(editing.id, { name, color, description: desc })}
        />
      )}
    </>
  );
}

function CompanyModal({
  company,
  onClose,
  onSave,
}: {
  company?: Company;
  onClose: () => void;
  onSave: (name: string, color: string, description: string) => void;
}) {
  const [name, setName] = useState(company?.name || "");
  const [color, setColor] = useState(company?.color || "#6366f1");
  const [description, setDescription] = useState(company?.description || "");
  const [busy, setBusy] = useState(false);

  async function handleSave() {
    if (!name.trim()) return;
    setBusy(true);
    await onSave(name.trim(), color, description);
    setBusy(false);
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="ds-card p-6 w-full max-w-md" style={{ background: "var(--surface)" }}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-bold">{company ? "Edit Company" : "Add New Company"}</h3>
          <button onClick={onClose} className="p-1 rounded hover:bg-surface2"><X size={16} /></button>
        </div>

        <div className="space-y-4">
          <div>
            <label className="text-xs font-semibold mb-1 block">Company Name *</label>
            <input value={name} onChange={(e) => setName(e.target.value)}
              className="w-full text-sm p-2 rounded border bg-transparent"
              style={{ borderColor: "var(--border)" }}
              placeholder="e.g., Google, Microsoft, Amazon" autoFocus />
          </div>

          <div>
            <label className="text-xs font-semibold mb-1 block">Brand Color</label>
            <div className="flex items-center gap-2">
              <input type="color" value={color} onChange={(e) => setColor(e.target.value)}
                className="w-8 h-8 rounded cursor-pointer border-0" />
              <input value={color} onChange={(e) => setColor(e.target.value)}
                className="flex-1 text-sm p-2 rounded border bg-transparent font-mono"
                style={{ borderColor: "var(--border)" }}
                placeholder="#6366f1" />
            </div>
          </div>

          <div>
            <label className="text-xs font-semibold mb-1 block">Description</label>
            <textarea value={description} onChange={(e) => setDescription(e.target.value)}
              rows={3}
              className="w-full text-sm p-2 rounded border bg-transparent resize-none"
              style={{ borderColor: "var(--border)" }}
              placeholder="Brief description of this company's exam pattern..." />
          </div>
        </div>

        <div className="flex gap-2 mt-6">
          <button onClick={onClose}
            className="btn btn-ghost flex-1">Cancel</button>
          <button onClick={handleSave} disabled={!name.trim() || busy}
            className="btn btn-primary flex-1">
            {busy ? <Loader2 size={14} className="animate-spin inline mr-1" /> : null}
            {company ? "Save Changes" : "Create Company"}
          </button>
        </div>
      </div>
    </div>
  );
}
