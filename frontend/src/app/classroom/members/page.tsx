"use client";

import React, { useEffect, useState } from "react";
import { fetchRoles } from "../../../lib/auth";
import { fetchWorkspaces } from "../../../lib/workspaces";
import { fetchMembers, checkMemberEmail, addMember, updateMember, updateMemberStatus, deleteMember, updateMemberWorkspaces, Member } from "../../../lib/members";
import { hasPermission, isPermissionsLoaded } from "../../../lib/permissions";
import ForbiddenState from "../components/ForbiddenState";

// ── Types ─────────────────────────────────────────────────────
interface RoleBrief { role_id: string; role_name: string; }

// ── Shared sub-components ─────────────────────────────────────
function FormLabel({ htmlFor, children }: { htmlFor?: string; children: React.ReactNode }) {
  return (
    <label htmlFor={htmlFor} className="block text-xs font-semibold mb-1.5" style={{ color: "var(--on-surface-variant)" }}>
      {children}
    </label>
  );
}

function ModalInput({ className = "", ...props }: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...props}
      className={`ds-input ${className}`}
    />
  );
}

function StatusBadge({ status }: { status: string }) {
  const active = status === "active";
  return (
    <span
      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-bold"
      style={active
        ? { backgroundColor: "rgba(21,69,57,0.08)", color: "var(--primary)" }
        : { backgroundColor: "rgba(220,38,38,0.08)", color: "#dc2626" }
      }
    >
      <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: active ? "var(--primary)" : "#dc2626" }} />
      <span className="capitalize">{status}</span>
    </span>
  );
}

function Avatar({ name, email }: { name: string; email: string }) {
  const letter = name?.[0]?.toUpperCase() || email?.[0]?.toUpperCase() || "?";
  return (
    <div
      className="w-9 h-9 rounded-xl flex items-center justify-center text-sm font-bold shrink-0"
      style={{ backgroundColor: "var(--surface-container-high)", color: "var(--primary)" }}
    >
      {letter}
    </div>
  );
}

// ── Alert banner ──────────────────────────────────────────────
function AlertBanner({ type, message, onDismiss }: { type: "error" | "success"; message: string; onDismiss: () => void }) {
  const isError = type === "error";
  return (
    <div
      className="flex items-center gap-3 p-4 rounded-xl text-sm font-medium animate-fade-in"
      style={{
        backgroundColor: isError ? "rgba(186,26,26,0.06)" : "rgba(21,69,57,0.06)",
        border: `1px solid ${isError ? "rgba(186,26,26,0.2)" : "rgba(21,69,57,0.2)"}`,
        color: isError ? "#ba1a1a" : "var(--primary)",
      }}
    >
      <span className="material-symbols-outlined text-[18px] shrink-0">{isError ? "error" : "check_circle"}</span>
      <span className="flex-1">{message}</span>
      <button onClick={onDismiss} className="shrink-0 cursor-pointer opacity-60 hover:opacity-100 transition-opacity">
        <span className="material-symbols-outlined text-[18px]">close</span>
      </button>
    </div>
  );
}

// ── Modal wrapper ─────────────────────────────────────────────
function Modal({ title, onClose, children }: { title: string; onClose: () => void; children: React.ReactNode }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 animate-fade-in" style={{ backgroundColor: "rgba(0,0,0,0.35)", backdropFilter: "blur(4px)" }}>
      <div className="w-full max-w-lg animate-slide-up" style={{ backgroundColor: "var(--surface)", border: "1px solid color-mix(in srgb, var(--outline-variant) 30%, transparent)", borderRadius: "1.25rem", boxShadow: "0 20px 60px rgba(0,0,0,0.12)" }}>
        <div className="flex items-center justify-between px-7 pt-6 pb-5" style={{ borderBottom: "1px solid color-mix(in srgb, var(--outline-variant) 30%, transparent)" }}>
          <h2 className="text-lg font-bold" style={{ color: "var(--on-surface)" }}>{title}</h2>
          <button onClick={onClose} className="w-8 h-8 rounded-full flex items-center justify-center cursor-pointer transition-colors" style={{ color: "var(--on-surface-variant)" }}
            onMouseEnter={e => (e.currentTarget.style.backgroundColor = "var(--surface-container)")}
            onMouseLeave={e => (e.currentTarget.style.backgroundColor = "transparent")}
          >
            <span className="material-symbols-outlined text-[20px]">close</span>
          </button>
        </div>
        <div className="px-7 py-6">{children}</div>
      </div>
    </div>
  );
}

// ── Workspace checkbox list ───────────────────────────────────
function WorkspaceList({ workspaces, selected, onChange }: { workspaces: any[]; selected: string[]; onChange: (id: string, checked: boolean) => void }) {
  return (
    <div className="max-h-32 overflow-y-auto space-y-2 p-3 rounded-xl" style={{ backgroundColor: "var(--surface-container)", border: "1px solid color-mix(in srgb, var(--outline-variant) 30%, transparent)" }}>
      {workspaces.length === 0 && <p className="text-xs text-center py-2" style={{ color: "var(--on-surface-variant)" }}>No workspaces available.</p>}
      {workspaces.map((ws) => (
        <label key={ws.workspace_id} className="flex items-center gap-3 cursor-pointer">
          <input
            type="checkbox"
            className="w-4 h-4 rounded cursor-pointer"
            checked={selected.includes(ws.workspace_id)}
            onChange={(e) => onChange(ws.workspace_id, e.target.checked)}
          />
          <span className="text-xs font-medium" style={{ color: "var(--on-surface)" }}>{ws.workspace_name}</span>
        </label>
      ))}
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────
export default function MembersManagementPage() {
  // ── Permission Guard ──────────────────────────────────────
  if (!isPermissionsLoaded()) {
    return (
      <div className="p-16 text-center space-y-3">
        <div className="w-8 h-8 border-2 border-t-transparent rounded-full animate-spin mx-auto" style={{ borderColor: "var(--primary)", borderTopColor: "transparent" }} />
        <p className="text-sm font-semibold" style={{ color: "var(--on-surface-variant)" }}>Loading…</p>
      </div>
    );
  }
  if (!hasPermission("member.read")) {
    return <ForbiddenState message="You don't have permission to view organization members." />;
  }
  const [loading, setLoading] = useState(true);
  const [members, setMembers] = useState<Member[]>([]);
  const [roles, setRoles] = useState<RoleBrief[]>([]);
  const [allWorkspaces, setAllWorkspaces] = useState<any[]>([]);

  const [search, setSearch] = useState("");
  const [selectedRole, setSelectedRole] = useState("");
  const [selectedStatus, setSelectedStatus] = useState("");

  const [addDialogOpen, setAddDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [selectedMember, setSelectedMember] = useState<Member | null>(null);

  const [addEmail, setAddEmail] = useState("");
  const [addFirstName, setAddFirstName] = useState("");
  const [addLastName, setAddLastName] = useState("");
  const [addPhone, setAddPhone] = useState("");
  const [addRole, setAddRole] = useState("");
  const [addWorkspaces, setAddWorkspaces] = useState<string[]>([]);
  const [emailCheckResult, setEmailCheckResult] = useState<string | null>(null);
  const [emailChecking, setEmailChecking] = useState(false);

  const [editFirstName, setEditFirstName] = useState("");
  const [editLastName, setEditLastName] = useState("");
  const [editPhone, setEditPhone] = useState("");
  const [editRole, setEditRole] = useState("");
  const [editWorkspaces, setEditWorkspaces] = useState<string[]>([]);

  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const fetchRolesAndWorkspaces = async () => {
    try {
      const rRes = await fetchRoles();
      setRoles(rRes); 
      if (rRes.length > 0) setAddRole(rRes[0].role_id);
      const wRes = await fetchWorkspaces();
      setAllWorkspaces(wRes);
    } catch {}
  };

  const loadMembersList = async () => {
    setLoading(true);
    try {
      const res = await fetchMembers({ search, role_id: selectedRole, status: selectedStatus });
      setMembers(res);
    } catch { setError("Failed to reload members list."); }
    finally { setLoading(false); }
  };

  useEffect(() => {
    const init = async () => {
      await fetchRolesAndWorkspaces();
      await loadMembersList();
    };
    init();
  }, [search, selectedRole, selectedStatus]);

  const handleEmailBlur = async () => {
    if (!addEmail || !addEmail.includes("@")) { setEmailCheckResult(null); return; }
    setEmailChecking(true);
    try {
      const data = await checkMemberEmail(addEmail);
      if (data.exists) {
        setEmailCheckResult("Existing SmartClass user — will be added directly.");
        setAddFirstName(data.first_name || ""); setAddLastName(data.last_name || ""); setAddPhone(data.phone || "");
      } else setEmailCheckResult("New user — a temporary password will be generated.");
    } catch { setEmailCheckResult(null); }
    finally { setEmailChecking(false); }
  };

  const handleAddMember = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null); setSuccess(null);
    try {
      await addMember({ email: addEmail, first_name: addFirstName, last_name: addLastName, phone: addPhone || null, role_id: addRole, workspace_ids: addWorkspaces });
      setSuccess("Member added successfully.");
      setAddDialogOpen(false);
      setAddEmail(""); setAddFirstName(""); setAddLastName(""); setAddPhone(""); setAddWorkspaces([]); setEmailCheckResult(null);
      loadMembersList();
    } catch (err: any) { setError(err.message); }
  };

  const handleOpenEdit = (m: Member) => {
    setSelectedMember(m); setEditFirstName(m.first_name || ""); setEditLastName(m.last_name || "");
    setEditPhone(m.phone || ""); setEditRole(m.role_id); setEditWorkspaces(m.workspaces.map(w => w.workspace_id));
    setEditDialogOpen(true);
  };

  const handleEditMember = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedMember) return;
    setError(null); setSuccess(null);
    try {
      await updateMember(selectedMember.organization_member_id, { first_name: editFirstName, last_name: editLastName, phone: editPhone || null, role_id: editRole });
      await updateMemberWorkspaces(selectedMember.user_id, editWorkspaces);
      setSuccess("Member updated successfully."); setEditDialogOpen(false); loadMembersList();
    } catch (err: any) { setError(err.message); }
  };

  const toggleStatus = async (m: Member) => {
    setError(null); setSuccess(null);
    const newStatus = m.status === "active" ? "suspended" : "active";
    try {
      await updateMemberStatus(m.organization_member_id, newStatus);
      setSuccess(`Member ${newStatus === "active" ? "activated" : "suspended"}.`);
      loadMembersList();
    } catch (err: any) { setError(err.message); }
  };

  const handleDeleteMember = async (m: Member) => {
    if (!confirm(`Remove ${m.first_name} ${m.last_name} from this organization?`)) return;
    setError(null); setSuccess(null);
    try {
      await deleteMember(m.organization_member_id);
      setSuccess("Member removed from organization."); loadMembersList();
    } catch (err: any) { setError(err.message); }
  };

  const toggleWorkspace = (id: string, checked: boolean, mode: "add" | "edit") => {
    if (mode === "add") setAddWorkspaces(checked ? [...addWorkspaces, id] : addWorkspaces.filter(w => w !== id));
    else setEditWorkspaces(checked ? [...editWorkspaces, id] : editWorkspaces.filter(w => w !== id));
  };

  return (
    <div className="space-y-6">
      {/* ── Page Header ─────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight" style={{ color: "var(--on-surface)" }}>Organization Members</h1>
          <p className="text-sm mt-1" style={{ color: "var(--on-surface-variant)" }}>Manage profiles, roles, and workspace assignments.</p>
        </div>
        {hasPermission("member.create") && (
          <button
            onClick={() => setAddDialogOpen(true)}
            className="ds-btn-primary shrink-0 px-5 py-2.5"
          >
            <span className="material-symbols-outlined text-[18px]">person_add</span>
            Add Member
          </button>
        )}
      </div>

      {/* ── Notifications ───────────────────────────────── */}
      {error && <AlertBanner type="error" message={error} onDismiss={() => setError(null)} />}
      {success && <AlertBanner type="success" message={success} onDismiss={() => setSuccess(null)} />}

      {/* ── Filter Bar ──────────────────────────────────── */}
      <div className="ds-card p-4 flex flex-col md:flex-row gap-3 items-stretch md:items-center">
        <div className="relative flex-1">
          <span className="material-symbols-outlined absolute left-3.5 top-1/2 -translate-y-1/2 text-[18px]" style={{ color: "var(--on-surface-variant)" }}>search</span>
          <input
            type="text"
            className="ds-input pl-10"
            placeholder="Search by name or email…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <select
          value={selectedRole}
          onChange={(e) => setSelectedRole(e.target.value)}
          className="ds-input cursor-pointer md:w-44"
          style={{ appearance: "none" }}
        >
          <option value="">All Roles</option>
          {roles.map(r => <option key={r.role_id} value={r.role_id}>{r.role_name}</option>)}
        </select>
        <select
          value={selectedStatus}
          onChange={(e) => setSelectedStatus(e.target.value)}
          className="ds-input cursor-pointer md:w-44"
          style={{ appearance: "none" }}
        >
          <option value="">All Statuses</option>
          <option value="active">Active</option>
          <option value="suspended">Suspended</option>
        </select>
      </div>

      {/* ── Members Table ────────────────────────────────── */}
      <div style={{ backgroundColor: "var(--surface)", border: "1px solid color-mix(in srgb, var(--outline-variant) 30%, transparent)", borderRadius: "1rem", overflow: "hidden" }}>
        {loading ? (
          <div className="p-16 text-center space-y-3">
            <div className="w-8 h-8 border-2 border-t-transparent rounded-full animate-spin mx-auto" style={{ borderColor: "var(--primary)", borderTopColor: "transparent" }} />
            <p className="text-sm font-semibold" style={{ color: "var(--on-surface-variant)" }}>Loading members…</p>
          </div>
        ) : members.length === 0 ? (
          <div className="p-16 text-center space-y-3">
            <span className="material-symbols-outlined text-[40px]" style={{ color: "var(--outline-variant)" }}>group</span>
            <p className="text-sm font-semibold" style={{ color: "var(--on-surface-variant)" }}>No members match your search.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-sm">
              <thead>
                <tr style={{ backgroundColor: "var(--surface-container)" }}>
                  {["Member", "Email", "Role", "Workspaces", "Status", ""].map(h => (
                    <th key={h} className="px-5 py-3.5 text-xs font-bold uppercase tracking-wider" style={{ color: "var(--on-surface-variant)" }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {members.map((m) => (
                  <tr
                    key={m.organization_member_id}
                    style={{ borderTop: "1px solid color-mix(in srgb, var(--outline-variant) 25%, transparent)" }}
                    onMouseEnter={e => (e.currentTarget.style.backgroundColor = "var(--surface-container-low)")}
                    onMouseLeave={e => (e.currentTarget.style.backgroundColor = "transparent")}
                  >
                    <td className="px-5 py-4">
                      <div className="flex items-center gap-3">
                        <Avatar name={`${m.first_name}${m.last_name}`} email={m.email} />
                        <div>
                          <div className="font-semibold" style={{ color: "var(--on-surface)" }}>{m.first_name} {m.last_name}</div>
                          <div className="text-xs mt-0.5" style={{ color: "var(--on-surface-variant)" }}>{m.phone || "—"}</div>
                        </div>
                      </div>
                    </td>
                    <td className="px-5 py-4" style={{ color: "var(--on-surface)" }}>{m.email}</td>
                    <td className="px-5 py-4">
                      <span className="ds-badge ds-badge-neutral">{m.role_name}</span>
                    </td>
                    <td className="px-5 py-4 max-w-[200px]">
                      <div className="flex flex-wrap gap-1">
                        {m.workspaces.map(w => (
                          <span key={w.workspace_id} className="inline-block px-2 py-0.5 rounded-md text-[10px] font-bold" style={{ backgroundColor: "rgba(21,69,57,0.07)", color: "var(--primary)" }}>
                            {w.workspace_name}
                          </span>
                        ))}
                        {m.workspaces.length === 0 && <span className="text-xs italic" style={{ color: "var(--on-surface-variant)" }}>None</span>}
                      </div>
                    </td>
                    <td className="px-5 py-4"><StatusBadge status={m.status} /></td>
                    <td className="px-5 py-4">
                      <div className="flex items-center justify-end gap-2">
                        {hasPermission("member.update") && (
                          <button onClick={() => handleOpenEdit(m)} className="ds-btn-secondary px-3 py-1.5 text-xs">
                            Edit
                          </button>
                        )}
                        {m.role_name.toLowerCase() !== "owner" && (
                          <>
                            {hasPermission("member.update") && (
                              <button
                                onClick={() => toggleStatus(m)}
                                className="px-3 py-1.5 rounded-full text-xs font-semibold border transition-all cursor-pointer"
                                style={m.status === "active"
                                  ? { borderColor: "rgba(220,38,38,0.25)", color: "#dc2626" }
                                  : { borderColor: "rgba(21,69,57,0.25)", color: "var(--primary)" }
                                }
                                onMouseEnter={e => (e.currentTarget.style.backgroundColor = m.status === "active" ? "rgba(220,38,38,0.05)" : "rgba(21,69,57,0.05)")}
                                onMouseLeave={e => (e.currentTarget.style.backgroundColor = "transparent")}
                              >
                                {m.status === "active" ? "Suspend" : "Activate"}
                              </button>
                            )}
                            {hasPermission("member.delete") && (
                              <button onClick={() => handleDeleteMember(m)} className="ds-btn-destructive px-3 py-1.5">
                                Remove
                              </button>
                            )}
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* ── Add Member Modal ─────────────────────────────── */}
      {addDialogOpen && (
        <Modal title="Add New Member" onClose={() => setAddDialogOpen(false)}>
          <form onSubmit={handleAddMember} className="space-y-4">
            <div>
              <FormLabel htmlFor="add-email">Email Address</FormLabel>
              <ModalInput id="add-email" type="email" placeholder="name@school.com" value={addEmail} onChange={(e) => setAddEmail(e.target.value)} onBlur={handleEmailBlur} required />
              {emailChecking && <p className="text-xs mt-1.5 italic" style={{ color: "var(--on-surface-variant)" }}>Checking address…</p>}
              {emailCheckResult && (
                <p className="text-xs mt-1.5 font-medium flex items-center gap-1.5" style={{ color: "var(--primary)" }}>
                  <span className="material-symbols-outlined text-[14px]">info</span>
                  {emailCheckResult}
                </p>
              )}
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <FormLabel htmlFor="add-first">First Name</FormLabel>
                <ModalInput id="add-first" type="text" value={addFirstName} onChange={(e) => setAddFirstName(e.target.value)} required />
              </div>
              <div>
                <FormLabel htmlFor="add-last">Last Name</FormLabel>
                <ModalInput id="add-last" type="text" value={addLastName} onChange={(e) => setAddLastName(e.target.value)} required />
              </div>
            </div>
            <div>
              <FormLabel htmlFor="add-phone">Phone <span style={{ fontWeight: 400, color: "var(--on-surface-variant)" }}>(optional)</span></FormLabel>
              <ModalInput id="add-phone" type="text" value={addPhone} onChange={(e) => setAddPhone(e.target.value)} />
            </div>
            <div>
              <FormLabel htmlFor="add-role">Organization Role</FormLabel>
              <select id="add-role" className="ds-input cursor-pointer" style={{ appearance: "none" }} value={addRole} onChange={(e) => setAddRole(e.target.value)} required>
                {roles.map(r => <option key={r.role_id} value={r.role_id}>{r.role_name}</option>)}
              </select>
            </div>
            <div>
              <FormLabel>Workspace Assignments</FormLabel>
              <WorkspaceList workspaces={allWorkspaces} selected={addWorkspaces} onChange={(id, c) => toggleWorkspace(id, c, "add")} />
            </div>
            <button type="submit" className="ds-btn-primary w-full py-3 mt-1">Save Member</button>
          </form>
        </Modal>
      )}

      {/* ── Edit Member Modal ─────────────────────────────── */}
      {editDialogOpen && selectedMember && (
        <Modal title="Edit Member" onClose={() => setEditDialogOpen(false)}>
          <form onSubmit={handleEditMember} className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <FormLabel htmlFor="edit-first">First Name</FormLabel>
                <ModalInput id="edit-first" type="text" value={editFirstName} onChange={(e) => setEditFirstName(e.target.value)} required />
              </div>
              <div>
                <FormLabel htmlFor="edit-last">Last Name</FormLabel>
                <ModalInput id="edit-last" type="text" value={editLastName} onChange={(e) => setEditLastName(e.target.value)} required />
              </div>
            </div>
            <div>
              <FormLabel htmlFor="edit-phone">Phone</FormLabel>
              <ModalInput id="edit-phone" type="text" value={editPhone} onChange={(e) => setEditPhone(e.target.value)} />
            </div>
            <div>
              <FormLabel htmlFor="edit-role">Organization Role</FormLabel>
              <select
                id="edit-role"
                className="ds-input cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                style={{ appearance: "none" }}
                value={editRole}
                onChange={(e) => setEditRole(e.target.value)}
                disabled={selectedMember.role_name.toLowerCase() === "owner"}
                required
              >
                {roles.map(r => <option key={r.role_id} value={r.role_id}>{r.role_name}</option>)}
              </select>
            </div>
            <div>
              <FormLabel>Workspace Assignments</FormLabel>
              <WorkspaceList workspaces={allWorkspaces} selected={editWorkspaces} onChange={(id, c) => toggleWorkspace(id, c, "edit")} />
            </div>
            <button type="submit" className="ds-btn-primary w-full py-3 mt-1">Apply Changes</button>
          </form>
        </Modal>
      )}
    </div>
  );
}
