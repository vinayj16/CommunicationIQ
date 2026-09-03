"use client";
import { useState } from "react";
import { Check, UserPlus, X, Eye, EyeOff, Pencil, Key, Power, Upload, Users } from "lucide-react";
import { RequireAuth } from "@/components/RequireAuth";
import {
  Avatar, Badge, ErrorNote, PageHeader, Section, Skeleton, Table, Tabs,
} from "@/components/ui";
import { api, adminApi, type UserRow } from "@/lib/api";
import { ROLE_LABEL } from "@/lib/roles";
import { useData } from "@/lib/useData";
import { useToast } from "@/components/Toast";

export default function TenantUsersPage() {
  return (
    <RequireAuth roles={["tenant_admin"]}>
      <People />
    </RequireAuth>
  );
}

function People() {
  const { toast } = useToast();
  const [tab, setTab] = useState("student");
  const { data, loading, error, reload } = useData(() => api.tenantUsers(tab === "all" ? undefined : tab), [tab]);
  const [showCreate, setShowCreate] = useState(false);
  const [showBulk, setShowBulk] = useState(false);
  const [editingUser, setEditingUser] = useState<UserRow | null>(null);
  const [resettingUser, setResettingUser] = useState<UserRow | null>(null);

  return (
    <>
      <PageHeader
        title="People"
        sub="Everyone in your institution. Create users, assign roles, and manage access."
        action={
          <div className="flex gap-2">
            <button className="btn btn-primary btn-sm" onClick={() => setShowBulk(true)}>
              <Users size={14} /> Bulk Users
            </button>
            <button className="btn btn-primary btn-sm" onClick={() => setShowCreate(true)}>
              <UserPlus size={14} /> Add User
            </button>
          </div>
        }
      />

      <Tabs
        active={tab}
        onChange={setTab}
        tabs={[
          { id: "student", label: "Students" },
          { id: "tenant_admin", label: "Admins" },
          { id: "all", label: "Everyone" },
        ]}
      />

      <Section>
        {loading ? <Skeleton rows={6} /> : error ? <ErrorNote message={error} /> : (
          <Table
            columns={["Name", "Email", "Role", "Roll", "Branch", "Status", ""]}
            rows={(data ?? []).map((u) => [
              <span key="n" className="flex items-center gap-2">
                <Avatar name={u.full_name} size={22} />
                <span className="font-medium">{u.full_name}</span>
              </span>,
              <span key="e" className="text-muted">{u.email}</span>,
              ROLE_LABEL[u.role as keyof typeof ROLE_LABEL] ?? u.role,
              u.roll_number || "—",
              u.branch || "—",
              u.active
                ? <Badge key="s" tone="var(--rag-green)">Active</Badge>
                : <Badge key="s" tone="var(--muted)">Inactive</Badge>,
              <div key="a" className="flex items-center gap-1">
                <button className="btn btn-icon btn-ghost btn-sm" title="Edit" onClick={() => setEditingUser(u)}>
                  <Pencil size={14} />
                </button>
                <button className="btn btn-icon btn-ghost btn-sm" title="Reset Password" onClick={() => setResettingUser(u)}>
                  <Key size={14} />
                </button>
                <button className="btn btn-icon btn-ghost btn-sm" title={u.active ? "Deactivate" : "Activate"}
                  onClick={async () => {
                    try {
                      await adminApi.updateUser(u.id, { active: !u.active });
                      toast("success", `User ${u.active ? "deactivated" : "activated"}`);
                      reload();
                    } catch (err) {
                      toast("error", err instanceof Error ? err.message : "Failed to update user");
                    }
                  }}>
                  <Power size={14} style={{ color: u.active ? "var(--rag-red)" : "var(--rag-green)" }} />
                </button>
              </div>,
            ])}
          />
        )}
      </Section>

      {showCreate && <CreateUserModal onClose={() => setShowCreate(false)} onCreated={reload} />}
      {showBulk && <BulkUsersModal onClose={() => setShowBulk(false)} onCreated={reload} />}
      {editingUser && <EditUserModal user={editingUser} onClose={() => setEditingUser(null)} onSaved={reload} />}
      {resettingUser && <ResetPasswordDialog user={resettingUser} onClose={() => setResettingUser(null)} />}
    </>
  );
}

function CreateUserModal({ onClose, onCreated }: { onClose: () => void; onCreated: () => void }) {
  const { toast } = useToast();
  const [form, setForm] = useState({ full_name: "", email: "", role: "student", password: "" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [showPw, setShowPw] = useState(false);

  const ROLE_PERMISSIONS: Record<string, { label: string; desc: string; permissions: string[] }> = {
    student: {
      label: "Student",
      desc: "Can take tests, practise, view own reports",
      permissions: ["Take assigned tests", "View own results & reports", "Practice drills & quizzes"],
    },
    tenant_admin: {
      label: "Institution Admin",
      desc: "Full access to manage users, assessments, and reports",
      permissions: ["Create & manage users", "Import users in bulk", "Create & publish assessments", "View all institution reports", "Manage placement season"],
    },
  };

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await adminApi.createUser({
        full_name: form.full_name,
        email: form.email,
        role: form.role,
        password: form.password,
      });
      toast("success", `User ${form.full_name} created successfully`);
      onCreated();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create user");
      setBusy(false);
    }
  }

  const selectedRole = ROLE_PERMISSIONS[form.role];

  return (
    <div className="modal-scrim" onClick={onClose}>
      <div className="modal-panel" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-bold">Add User</h3>
          <button onClick={onClose} className="btn btn-icon btn-ghost btn-sm"><X size={14} /></button>
        </div>

        <form onSubmit={submit} className="space-y-3">
          <div>
            <label className="ds-label">Full Name</label>
            <input className="ds-input" value={form.full_name} required
              onChange={(e) => setForm({ ...form, full_name: e.target.value })} />
          </div>
          <div>
            <label className="ds-label">Email</label>
            <input className="ds-input" type="email" required value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })} />
          </div>
          <div>
            <label className="ds-label">Role &amp; Permissions</label>
            <select className="ds-select" value={form.role}
              onChange={(e) => setForm({ ...form, role: e.target.value })}>
              <option value="student">Student</option>

              <option value="tenant_admin">Institution Admin</option>
            </select>
            {selectedRole && (
              <div className="mt-2 p-3 rounded-lg" style={{ background: "var(--surface)", border: "1px solid var(--border)" }}>
                <div className="text-[11px] font-semibold mb-1">{selectedRole.label} — {selectedRole.desc}</div>
                <ul className="space-y-0.5">
                  {selectedRole.permissions.map((p) => (
                    <li key={p} className="text-[10px] flex items-center gap-1.5" style={{ color: "var(--rag-green)" }}>
                      <Check size={10} /> {p}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
          <div>
            <label className="ds-label">Password</label>
            <div className="relative">
              <input className="ds-input pr-10" type={showPw ? "text" : "password"} required value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })} />
              <button type="button" className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-muted hover:text-text"
                      onClick={() => setShowPw(!showPw)} tabIndex={-1}>
                {showPw ? <EyeOff size={14} /> : <Eye size={14} />}
              </button>
            </div>
          </div>
          {error && <div className="text-xs font-medium" style={{ color: "var(--rag-red)" }}>{error}</div>}
          <div className="flex justify-end gap-2 pt-2">
            <button type="button" className="btn btn-ghost btn-sm" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary btn-sm" disabled={busy}>
              {busy ? "Creating…" : "Create User"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function EditUserModal({ user, onClose, onSaved }: { user: UserRow; onClose: () => void; onSaved: () => void }) {
  const { toast } = useToast();
  const [form, setForm] = useState({ full_name: user.full_name, role: user.role });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await adminApi.updateUser(user.id, { full_name: form.full_name, role: form.role });
      toast("success", "User updated successfully");
      onSaved();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update user");
      setBusy(false);
    }
  }

  return (
    <div className="modal-scrim" onClick={onClose}>
      <div className="modal-panel" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-bold">Edit User</h3>
          <button onClick={onClose} className="btn btn-icon btn-ghost btn-sm"><X size={14} /></button>
        </div>

        <form onSubmit={submit} className="space-y-3">
          <div>
            <label className="ds-label">Full Name</label>
            <input className="ds-input" value={form.full_name} required
              onChange={(e) => setForm({ ...form, full_name: e.target.value })} />
          </div>
          <div>
            <label className="ds-label">Role</label>
            <select className="ds-select" value={form.role}
              onChange={(e) => setForm({ ...form, role: e.target.value })}>
              <option value="student">Student</option>
              <option value="tenant_admin">Institution Admin</option>
            </select>
          </div>
          {error && <div className="text-xs font-medium" style={{ color: "var(--rag-red)" }}>{error}</div>}
          <div className="flex justify-end gap-2 pt-2">
            <button type="button" className="btn btn-ghost btn-sm" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary btn-sm" disabled={busy}>
              {busy ? "Saving…" : "Save"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function ResetPasswordDialog({ user, onClose }: { user: UserRow; onClose: () => void }) {
  const { toast } = useToast();
  const [busy, setBusy] = useState(false);
  const [newPassword, setNewPassword] = useState<string | null>(null);
  const [error, setError] = useState("");

  async function confirm() {
    setBusy(true);
    setError("");
    try {
      const res = await adminApi.resetPassword(user.id);
      setNewPassword(res.temporary_password);
      toast("success", "Password reset successfully");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to reset password");
      setBusy(false);
    }
  }

  return (
    <div className="modal-scrim" onClick={onClose}>
      <div className="modal-panel" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-bold">Reset Password</h3>
          <button onClick={onClose} className="btn btn-icon btn-ghost btn-sm"><X size={14} /></button>
        </div>

        {newPassword ? (
          <div className="space-y-3">
            <p className="text-xs text-muted">Password has been reset for <strong>{user.full_name}</strong>.</p>
            <div className="p-3 rounded-lg" style={{ background: "var(--surface)", border: "1px solid var(--border)" }}>
              <div className="text-[10px] font-semibold text-muted mb-1">Temporary Password</div>
              <code className="text-sm font-mono font-medium select-all">{newPassword}</code>
            </div>
            <div className="flex justify-end pt-2">
              <button className="btn btn-primary btn-sm" onClick={onClose}>Done</button>
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            <p className="text-xs text-muted">Are you sure you want to reset the password for <strong>{user.full_name}</strong>? A new temporary password will be generated.</p>
            {error && <div className="text-xs font-medium" style={{ color: "var(--rag-red)" }}>{error}</div>}
            <div className="flex justify-end gap-2 pt-2">
              <button className="btn btn-ghost btn-sm" onClick={onClose} disabled={busy}>Cancel</button>
              <button className="btn btn-primary btn-sm" onClick={confirm} disabled={busy}>
                {busy ? "Resetting…" : "Reset Password"}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function BulkUsersModal({ onClose, onCreated }: { onClose: () => void; onCreated: () => void }) {
  const { toast } = useToast();
  const [lines, setLines] = useState("");
  const [sharedPassword, setSharedPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<{ created: number; errors: string[] } | null>(null);
  const [showPw, setShowPw] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!lines.trim() || !sharedPassword.trim()) return;
    setBusy(true);
    setResult(null);

    // Parse lines: each line is either "Name, email" or just "email"
    const entries = lines.trim().split("\n")
      .map((l) => l.trim())
      .filter(Boolean)
      .map((l) => {
        const parts = l.split(/[\t,;|]+/).map((s) => s.trim());
        if (parts.length >= 2) return { full_name: parts[0], email: parts[1] };
        return { full_name: parts[0].split("@")[0], email: parts[0] };
      });

    let created = 0;
    const errors: string[] = [];

    for (const entry of entries) {
      try {
        await adminApi.createUser({
          full_name: entry.full_name,
          email: entry.email,
          role: "student",
          password: sharedPassword,
        });
        created++;
      } catch (err) {
        errors.push(`${entry.email}: ${err instanceof Error ? err.message : "Failed"}`);
      }
    }

    setResult({ created, errors });
    setBusy(false);
    if (created > 0) {
      toast("success", `${created} user${created !== 1 ? "s" : ""} created successfully`);
      onCreated();
    }
  }

  return (
    <div className="modal-scrim" onClick={onClose}>
      <div className="modal-panel" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 500 }}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-bold">Bulk Create Users</h3>
          <button onClick={onClose} className="btn btn-icon btn-ghost btn-sm"><X size={14} /></button>
        </div>

        <p className="text-xs text-muted leading-relaxed mb-3">
          Enter one user per line. Format: <code>Name, email</code> or just <code>email</code>.
          All users will be created as students with the same password.
        </p>

        {result ? (
          <div className="space-y-3">
            <div className="p-3 rounded-lg" style={{ background: "color-mix(in srgb, var(--rag-green) 10%, transparent)", border: "1px solid var(--rag-green)" }}>
              <div className="text-sm font-bold" style={{ color: "var(--rag-green)" }}>{result.created} users created</div>
            </div>
            {result.errors.length > 0 && (
              <div className="p-3 rounded-lg" style={{ background: "color-mix(in srgb, var(--rag-red) 10%, transparent)", border: "1px solid var(--rag-red)" }}>
                <div className="text-xs font-semibold mb-1" style={{ color: "var(--rag-red)" }}>Errors:</div>
                {result.errors.map((e, i) => (
                  <div key={i} className="text-[11px] text-muted">{e}</div>
                ))}
              </div>
            )}
            <div className="flex justify-end pt-2">
              <button className="btn btn-primary btn-sm" onClick={onClose}>Done</button>
            </div>
          </div>
        ) : (
          <form onSubmit={submit} className="space-y-3">
            <div>
              <label className="ds-label">Users (one per line)</label>
              <textarea className="ds-input" rows={8} value={lines}
                onChange={(e) => setLines(e.target.value)}
                placeholder={"Aarav Reddy, aarav@college.ac.in\nPriya Sharma, priya@college.ac.in\nRahul Verma, rahul@college.ac.in"}
                style={{ fontFamily: "monospace", fontSize: 12 }} />
              <div className="text-[10px] text-muted mt-1">
                {lines.trim() ? lines.trim().split("\n").filter(Boolean).length : 0} users detected
              </div>
            </div>
            <div>
              <label className="ds-label">Shared Password</label>
              <div className="relative">
                <input className="ds-input pr-10" type={showPw ? "text" : "password"} required value={sharedPassword}
                  onChange={(e) => setSharedPassword(e.target.value)}
                  placeholder="Minimum 6 characters" minLength={6} />
                <button type="button" className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-muted hover:text-text"
                        onClick={() => setShowPw(!showPw)} tabIndex={-1}>
                  {showPw ? <EyeOff size={14} /> : <Eye size={14} />}
                </button>
              </div>
              <div className="text-[10px] text-muted mt-1">All users will share this password. They can change it from Settings.</div>
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button type="button" className="btn btn-ghost btn-sm" onClick={onClose}>Cancel</button>
              <button type="submit" className="btn btn-primary btn-sm" disabled={busy || !lines.trim() || !sharedPassword.trim()}>
                {busy ? "Creating…" : `Create Users`}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
