"use client";

import React, { useEffect, useState } from "react";
import { getMemoryAccessToken, API_BASE_URL } from "../../../lib/auth";

interface WorkspaceBrief {
  workspace_id: string;
  workspace_name: string;
}

interface Member {
  user_id: string;
  email: string;
  first_name: string;
  last_name: string;
  phone: string | null;
  organization_member_id: string;
  status: string;
  role_id: string;
  role_name: string;
  workspaces: WorkspaceBrief[];
}

interface RoleBrief {
  role_id: string;
  role_name: string;
}

export default function MembersManagementPage() {
  const [loading, setLoading] = useState(true);
  const [members, setMembers] = useState<Member[]>([]);
  const [roles, setRoles] = useState<RoleBrief[]>([]);
  const [allWorkspaces, setAllWorkspaces] = useState<any[]>([]);

  // Filter & Search State
  const [search, setSearch] = useState("");
  const [selectedRole, setSelectedRole] = useState("");
  const [selectedStatus, setSelectedStatus] = useState("");

  // Dialog / Modal State
  const [addDialogOpen, setAddDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [selectedMember, setSelectedMember] = useState<Member | null>(null);

  // Add Member Form State
  const [addEmail, setAddEmail] = useState("");
  const [addFirstName, setAddFirstName] = useState("");
  const [addLastName, setAddLastName] = useState("");
  const [addPhone, setAddPhone] = useState("");
  const [addRole, setAddRole] = useState("");
  const [addWorkspaces, setAddWorkspaces] = useState<string[]>([]);
  
  // Email check status
  const [emailCheckResult, setEmailCheckResult] = useState<string | null>(null);
  const [emailChecking, setEmailChecking] = useState(false);

  // Edit Member Form State
  const [editFirstName, setEditFirstName] = useState("");
  const [editLastName, setEditLastName] = useState("");
  const [editPhone, setEditPhone] = useState("");
  const [editRole, setEditRole] = useState("");
  const [editWorkspaces, setEditWorkspaces] = useState<string[]>([]);

  // General Notification
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const fetchRolesAndWorkspaces = async (token: string, orgId: string) => {
    try {
      // 1. Roles
      const rRes = await fetch(`${API_BASE_URL}/organizations/roles`, {
        headers: {
          Authorization: `Bearer ${token}`,
          "X-Organization-Id": orgId,
        },
      });
      if (rRes.ok) {
        const rData = await rRes.json();
        setRoles(rData);
        if (rData.length > 0) setAddRole(rData[0].role_id);
      }

      // 2. Workspaces
      const wRes = await fetch(`${API_BASE_URL}/workspaces`, {
        headers: {
          Authorization: `Bearer ${token}`,
          "X-Organization-Id": orgId,
        },
      });
      if (wRes.ok) {
        setAllWorkspaces(await wRes.json());
      }
    } catch (err) {}
  };

  const loadMembersList = async () => {
    setLoading(true);
    let token = getMemoryAccessToken();
    const orgId = typeof window !== "undefined" ? localStorage.getItem("activeOrganizationId") : null;
    
    if (!token) {
      const { refreshAuthSession } = await import("../../../lib/auth");
      const session = await refreshAuthSession();
      token = session?.accessToken || null;
    }

    if (!token || !orgId) {
      setLoading(false);
      return;
    }

    try {
      let url = `${API_BASE_URL}/organizations/members?`;
      if (search) url += `search=${encodeURIComponent(search)}&`;
      if (selectedRole) url += `role_id=${encodeURIComponent(selectedRole)}&`;
      if (selectedStatus) url += `status=${encodeURIComponent(selectedStatus)}&`;

      const res = await fetch(url, {
        headers: {
          Authorization: `Bearer ${token}`,
          "X-Organization-Id": orgId,
        },
      });

      if (res.ok) {
        setMembers(await res.json());
      }
    } catch (err) {
      setError("Failed to reload members list.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const init = async () => {
      let token = getMemoryAccessToken();
      const orgId = typeof window !== "undefined" ? localStorage.getItem("activeOrganizationId") : null;
      if (!token) {
        const { refreshAuthSession } = await import("../../../lib/auth");
        const session = await refreshAuthSession();
        token = session?.accessToken || null;
      }
      if (token && orgId) {
        fetchRolesAndWorkspaces(token, orgId);
        loadMembersList();
      } else {
        setLoading(false);
      }
    };
    init();
  }, [search, selectedRole, selectedStatus]);

  // Handle Email field blur (loss of focus)
  const handleEmailBlur = async () => {
    if (!addEmail || !addEmail.includes("@")) {
      setEmailCheckResult(null);
      return;
    }

    setEmailChecking(true);
    try {
      const res = await fetch(
        `${API_BASE_URL}/organizations/members/check-email?email=${encodeURIComponent(addEmail)}`
      );
      if (res.ok) {
        const data = await res.json();
        if (data.exists) {
          setEmailCheckResult("Existing SmartClass user found. Will be added directly to this organization.");
          setAddFirstName(data.first_name || "");
          setAddLastName(data.last_name || "");
          setAddPhone(data.phone || "");
        } else {
          setEmailCheckResult("New account will be created. A temporary password will be generated automatically.");
        }
      }
    } catch (err) {
      setEmailCheckResult(null);
    } finally {
      setEmailChecking(false);
    }
  };

  const handleAddMember = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);

    const token = getMemoryAccessToken();
    const orgId = typeof window !== "undefined" ? localStorage.getItem("activeOrganizationId") : null;
    if (!token || !orgId) return;

    try {
      const res = await fetch(`${API_BASE_URL}/organizations/members`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
          "X-Organization-Id": orgId,
        },
        body: JSON.stringify({
          email: addEmail,
          first_name: addFirstName,
          last_name: addLastName,
          phone: addPhone || null,
          role_id: addRole,
          workspace_ids: addWorkspaces,
        }),
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || "Failed to add member.");
      }

      setSuccess("Member added successfully.");
      setAddDialogOpen(false);
      
      // Reset form
      setAddEmail("");
      setAddFirstName("");
      setAddLastName("");
      setAddPhone("");
      setAddWorkspaces([]);
      setEmailCheckResult(null);

      loadMembersList();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleOpenEdit = (m: Member) => {
    setSelectedMember(m);
    setEditFirstName(m.first_name || "");
    setEditLastName(m.last_name || "");
    setEditPhone(m.phone || "");
    setEditRole(m.role_id);
    setEditWorkspaces(m.workspaces.map((w) => w.workspace_id));
    setEditDialogOpen(true);
  };

  const handleEditMember = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedMember) return;
    setError(null);
    setSuccess(null);

    const token = getMemoryAccessToken();
    const orgId = typeof window !== "undefined" ? localStorage.getItem("activeOrganizationId") : null;
    if (!token || !orgId) return;

    try {
      // 1. Update Profile & Role
      const res = await fetch(`${API_BASE_URL}/organizations/members/${selectedMember.organization_member_id}`, {
        method: "PATCH",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
          "X-Organization-Id": orgId,
        },
        body: JSON.stringify({
          first_name: editFirstName,
          last_name: editLastName,
          phone: editPhone || null,
          role_id: editRole,
        }),
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || "Failed to update member details.");
      }

      // 2. Synchronize Workspaces
      const wsRes = await fetch(
        `${API_BASE_URL}/organizations/members/${selectedMember.user_id}/workspaces`,
        {
          method: "PATCH",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
            "X-Organization-Id": orgId,
          },
          body: JSON.stringify(editWorkspaces),
        }
      );

      if (!wsRes.ok) {
        throw new Error("Failed to synchronize workspace assignments.");
      }

      setSuccess("Member details updated successfully.");
      setEditDialogOpen(false);
      loadMembersList();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const toggleStatus = async (m: Member) => {
    setError(null);
    setSuccess(null);

    const token = getMemoryAccessToken();
    const orgId = typeof window !== "undefined" ? localStorage.getItem("activeOrganizationId") : null;
    if (!token || !orgId) return;

    const newStatus = m.status === "active" ? "suspended" : "active";

    try {
      const res = await fetch(
        `${API_BASE_URL}/organizations/members/${m.organization_member_id}/status`,
        {
          method: "PATCH",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
            "X-Organization-Id": orgId,
          },
          body: JSON.stringify({ status: newStatus }),
        }
      );

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || "Failed to modify member status.");
      }

      setSuccess(`Member status updated to ${newStatus}.`);
      loadMembersList();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleDeleteMember = async (m: Member) => {
    if (!confirm(`Are you sure you want to remove ${m.first_name} ${m.last_name} from this organization?`)) {
      return;
    }
    setError(null);
    setSuccess(null);

    const token = getMemoryAccessToken();
    const orgId = typeof window !== "undefined" ? localStorage.getItem("activeOrganizationId") : null;
    if (!token || !orgId) return;

    try {
      const res = await fetch(
        `${API_BASE_URL}/organizations/members/${m.organization_member_id}`,
        {
          method: "DELETE",
          headers: {
            Authorization: `Bearer ${token}`,
            "X-Organization-Id": orgId,
          },
        }
      );

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || "Failed to remove member.");
      }

      setSuccess("Member removed from organization.");
      loadMembersList();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleWorkspaceCheck = (id: string, isChecked: boolean, mode: "add" | "edit") => {
    if (mode === "add") {
      if (isChecked) {
        setAddWorkspaces([...addWorkspaces, id]);
      } else {
        setAddWorkspaces(addWorkspaces.filter((w) => w !== id));
      }
    } else {
      if (isChecked) {
        setEditWorkspaces([...editWorkspaces, id]);
      } else {
        setEditWorkspaces(editWorkspaces.filter((w) => w !== id));
      }
    }
  };

  return (
    <main className="p-8 space-y-8 bg-[var(--background)] text-[var(--on-surface)] min-h-screen">
      {/* Header Row */}
      <header className="flex flex-col sm:flex-row justify-between sm:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-[var(--primary)]">Organization Members</h1>
          <p className="text-sm text-[var(--on-surface-variant)]">Manage profiles, role levels, and workspace privileges.</p>
        </div>
        <button
          onClick={() => setAddDialogOpen(true)}
          className="bg-[var(--primary)] text-[var(--on-primary)] px-6 py-3.5 rounded-full font-bold hover:bg-[var(--primary-container)] transition-all cursor-pointer flex items-center justify-center gap-2 shadow-md shrink-0 active:scale-95"
        >
          <span className="material-symbols-outlined text-[20px]">person_add</span>
          <span>Add Member</span>
        </button>
      </header>

      {/* Notifications */}
      {error && (
        <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/30 text-red-500 text-sm font-semibold flex items-center gap-2">
          <span className="material-symbols-outlined text-[20px]">error</span>
          <span>{error}</span>
        </div>
      )}
      {success && (
        <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-600 text-sm font-semibold flex items-center gap-2">
          <span className="material-symbols-outlined text-[20px]">check_circle</span>
          <span>{success}</span>
        </div>
      )}

      {/* Filters Card */}
      <section className="bg-white dark:bg-[#1b211e] p-6 rounded-[24px] border border-[var(--outline-variant)]/20 shadow-sm flex flex-col md:flex-row gap-4 items-center">
        {/* Search */}
        <div className="relative flex-grow w-full">
          <input
            type="text"
            className="w-full pl-12 pr-6 py-3.5 bg-[var(--surface-container)] rounded-full text-sm outline-none border border-transparent focus:border-[var(--primary)] text-[var(--on-surface)]"
            placeholder="Search by name or email..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-[var(--on-surface-variant)] text-[20px]">
            search
          </span>
        </div>

        {/* Role Filter */}
        <div className="w-full md:w-[200px]">
          <select
            value={selectedRole}
            onChange={(e) => setSelectedRole(e.target.value)}
            className="w-full px-5 py-3.5 bg-[var(--surface-container)] rounded-full text-sm outline-none border border-transparent focus:border-[var(--primary)] cursor-pointer text-[var(--on-surface)]"
          >
            <option value="">All Roles</option>
            {roles.map((r) => (
              <option key={r.role_id} value={r.role_id}>
                {r.role_name}
              </option>
            ))}
          </select>
        </div>

        {/* Status Filter */}
        <div className="w-full md:w-[200px]">
          <select
            value={selectedStatus}
            onChange={(e) => setSelectedStatus(e.target.value)}
            className="w-full px-5 py-3.5 bg-[var(--surface-container)] rounded-full text-sm outline-none border border-transparent focus:border-[var(--primary)] cursor-pointer text-[var(--on-surface)]"
          >
            <option value="">All Statuses</option>
            <option value="active">Active</option>
            <option value="suspended">Suspended</option>
          </select>
        </div>
      </section>

      {/* Members List Table */}
      <section className="bg-white dark:bg-[#1b211e] rounded-[32px] border border-[var(--outline-variant)]/20 shadow-md overflow-hidden">
        {loading ? (
          <div className="p-16 text-center space-y-3">
            <div className="w-10 h-10 border-4 border-[var(--primary)] border-t-transparent rounded-full animate-spin mx-auto"></div>
            <p className="text-sm font-semibold">Updating members index...</p>
          </div>
        ) : members.length === 0 ? (
          <div className="p-16 text-center text-[var(--on-surface-variant)]">
            <span className="material-symbols-outlined text-[48px] mb-3 text-outline/30">people</span>
            <p className="font-semibold">No members match the search query.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-sm">
              <thead>
                <tr className="border-b border-[var(--outline-variant)]/30 bg-[var(--surface-container)]/30">
                  <th className="p-5 font-semibold text-[var(--on-surface-variant)]">Name</th>
                  <th className="p-5 font-semibold text-[var(--on-surface-variant)]">Email</th>
                  <th className="p-5 font-semibold text-[var(--on-surface-variant)]">Role</th>
                  <th className="p-5 font-semibold text-[var(--on-surface-variant)]">Workspaces</th>
                  <th className="p-5 font-semibold text-[var(--on-surface-variant)]">Status</th>
                  <th className="p-5 font-semibold text-[var(--on-surface-variant)] text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--outline-variant)]/20">
                {members.map((m) => (
                  <tr key={m.organization_member_id} className="hover:bg-[var(--surface-container)]/10 transition-colors">
                    {/* Name / Avatar */}
                    <td className="p-5 flex items-center gap-3">
                      <div className="w-10 h-10 bg-[var(--primary)]/10 text-[var(--primary)] font-bold rounded-full flex items-center justify-center">
                        {m.first_name ? m.first_name[0] : m.email[0].toUpperCase()}
                      </div>
                      <div>
                        <div className="font-bold text-[var(--on-surface)]">
                          {m.first_name} {m.last_name}
                        </div>
                        <div className="text-xs text-[var(--on-surface-variant)]">{m.phone || "No Phone"}</div>
                      </div>
                    </td>

                    {/* Email */}
                    <td className="p-5 text-[var(--on-surface)]">{m.email}</td>

                    {/* Role */}
                    <td className="p-5">
                      <span className="inline-block px-3 py-1 rounded-full bg-[var(--surface-container)] text-[var(--on-surface)] font-semibold text-xs border border-[var(--outline-variant)]/20">
                        {m.role_name}
                      </span>
                    </td>

                    {/* Workspaces */}
                    <td className="p-5 max-w-[220px]">
                      <div className="flex flex-wrap gap-1">
                        {m.workspaces.map((w) => (
                          <span
                            key={w.workspace_id}
                            className="text-[10px] font-bold px-2 py-0.5 rounded-md bg-[var(--primary)]/10 text-[var(--primary)]"
                          >
                            {w.workspace_name}
                          </span>
                        ))}
                        {m.workspaces.length === 0 && (
                          <span className="text-xs text-[var(--on-surface-variant)] italic">None</span>
                        )}
                      </div>
                    </td>

                    {/* Status */}
                    <td className="p-5">
                      <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold ${
                        m.status === "active"
                          ? "bg-emerald-500/10 text-emerald-500"
                          : "bg-red-500/10 text-red-500"
                      }`}>
                        <span className={`w-1.5 h-1.5 rounded-full ${
                          m.status === "active" ? "bg-emerald-500" : "bg-red-500"
                        }`}></span>
                        <span className="capitalize">{m.status}</span>
                      </span>
                    </td>

                    {/* Actions */}
                    <td className="p-5 text-right space-x-2 shrink-0">
                      <button
                        onClick={() => handleOpenEdit(m)}
                        className="px-3.5 py-1.5 rounded-full border border-[var(--outline-variant)]/40 hover:bg-[var(--surface-container-high)] text-xs font-semibold text-[var(--on-surface)] transition-all cursor-pointer"
                      >
                        Edit
                      </button>
                      {m.role_name.toLowerCase() !== "owner" && (
                        <>
                          <button
                            onClick={() => toggleStatus(m)}
                            className={`px-3.5 py-1.5 rounded-full text-xs font-semibold border transition-all cursor-pointer ${
                              m.status === "active"
                                ? "border-red-500/30 text-red-500 hover:bg-red-500/10"
                                : "border-emerald-500/30 text-emerald-500 hover:bg-emerald-500/10"
                            }`}
                          >
                            {m.status === "active" ? "Suspend" : "Activate"}
                          </button>
                          <button
                            onClick={() => handleDeleteMember(m)}
                            className="px-3.5 py-1.5 rounded-full border border-red-500/20 text-red-500 hover:bg-red-500/10 text-xs font-semibold transition-all cursor-pointer"
                          >
                            Remove
                          </button>
                        </>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Add Member Dialog Modal */}
      {addDialogOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm animate-fade-in">
          <div className="w-full max-w-lg bg-white dark:bg-[#1b211e] rounded-[32px] p-8 border border-[var(--outline-variant)]/20 shadow-2xl relative">
            <header className="flex justify-between items-center mb-6">
              <h2 className="text-xl font-bold text-[var(--primary)]">Add New Member</h2>
              <button
                onClick={() => setAddDialogOpen(false)}
                className="w-8 h-8 rounded-full flex items-center justify-center hover:bg-[var(--surface-container)] text-[var(--on-surface-variant)] cursor-pointer"
              >
                <span className="material-symbols-outlined">close</span>
              </button>
            </header>

            <form onSubmit={handleAddMember} className="space-y-4">
              {/* Email */}
              <div className="space-y-1">
                <label className="text-xs font-semibold text-[var(--on-surface-variant)]">Email Address</label>
                <input
                  type="email"
                  className="w-full px-5 py-3 bg-[var(--surface-container)] rounded-full text-sm outline-none border border-transparent focus:border-[var(--primary)] text-[var(--on-surface)]"
                  placeholder="name@school.com"
                  value={addEmail}
                  onChange={(e) => setAddEmail(e.target.value)}
                  onBlur={handleEmailBlur}
                  required
                />
                {emailChecking && <p className="text-[10px] text-[var(--on-surface-variant)] italic">Checking address...</p>}
                {emailCheckResult && <p className="text-[10px] font-semibold text-[var(--primary)]">{emailCheckResult}</p>}
              </div>

              {/* First & Last Name */}
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-[var(--on-surface-variant)]">First Name</label>
                  <input
                    type="text"
                    className="w-full px-5 py-3 bg-[var(--surface-container)] rounded-full text-sm outline-none border border-transparent focus:border-[var(--primary)] text-[var(--on-surface)]"
                    value={addFirstName}
                    onChange={(e) => setAddFirstName(e.target.value)}
                    required
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-[var(--on-surface-variant)]">Last Name</label>
                  <input
                    type="text"
                    className="w-full px-5 py-3 bg-[var(--surface-container)] rounded-full text-sm outline-none border border-transparent focus:border-[var(--primary)] text-[var(--on-surface)]"
                    value={addLastName}
                    onChange={(e) => setAddLastName(e.target.value)}
                    required
                  />
                </div>
              </div>

              {/* Phone */}
              <div className="space-y-1">
                <label className="text-xs font-semibold text-[var(--on-surface-variant)]">Phone (Optional)</label>
                <input
                  type="text"
                  className="w-full px-5 py-3 bg-[var(--surface-container)] rounded-full text-sm outline-none border border-transparent focus:border-[var(--primary)] text-[var(--on-surface)]"
                  value={addPhone}
                  onChange={(e) => setAddPhone(e.target.value)}
                />
              </div>

              {/* Role */}
              <div className="space-y-1">
                <label className="text-xs font-semibold text-[var(--on-surface-variant)]">Organization Role</label>
                <select
                  value={addRole}
                  onChange={(e) => setAddRole(e.target.value)}
                  className="w-full px-5 py-3 bg-[var(--surface-container)] rounded-full text-sm outline-none border border-transparent focus:border-[var(--primary)] cursor-pointer text-[var(--on-surface)]"
                  required
                >
                  {roles.map((r) => (
                    <option key={r.role_id} value={r.role_id}>
                      {r.role_name}
                    </option>
                  ))}
                </select>
              </div>

              {/* Workspace Assignments */}
              <div className="space-y-2">
                <label className="text-xs font-semibold text-[var(--on-surface-variant)]">Workspace Assignments</label>
                <div className="max-h-[120px] overflow-y-auto space-y-2 p-2 bg-[var(--surface-container)] rounded-2xl">
                  {allWorkspaces.map((ws) => (
                    <div key={ws.workspace_id} className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        id={`ws-add-${ws.workspace_id}`}
                        className="w-4 h-4 text-[var(--primary)] rounded border-[var(--outline-variant)] focus:ring-[var(--primary)]"
                        checked={addWorkspaces.includes(ws.workspace_id)}
                        onChange={(e) => handleWorkspaceCheck(ws.workspace_id, e.target.checked, "add")}
                      />
                      <label htmlFor={`ws-add-${ws.workspace_id}`} className="text-xs text-[var(--on-surface)] cursor-pointer select-none">
                        {ws.workspace_name}
                      </label>
                    </div>
                  ))}
                </div>
              </div>

              <button
                type="submit"
                className="w-full py-4 rounded-full bg-[var(--primary)] text-[var(--on-primary)] font-bold hover:bg-[var(--primary-container)] cursor-pointer transition-colors active:scale-98"
              >
                Save Member Details
              </button>
            </form>
          </div>
        </div>
      )}

      {/* Edit Member Dialog Modal */}
      {editDialogOpen && selectedMember && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm animate-fade-in">
          <div className="w-full max-w-lg bg-white dark:bg-[#1b211e] rounded-[32px] p-8 border border-[var(--outline-variant)]/20 shadow-2xl relative">
            <header className="flex justify-between items-center mb-6">
              <h2 className="text-xl font-bold text-[var(--primary)]">Edit Member Settings</h2>
              <button
                onClick={() => setEditDialogOpen(false)}
                className="w-8 h-8 rounded-full flex items-center justify-center hover:bg-[var(--surface-container)] text-[var(--on-surface-variant)] cursor-pointer"
              >
                <span className="material-symbols-outlined">close</span>
              </button>
            </header>

            <form onSubmit={handleEditMember} className="space-y-4">
              {/* First & Last Name */}
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-[var(--on-surface-variant)]">First Name</label>
                  <input
                    type="text"
                    className="w-full px-5 py-3 bg-[var(--surface-container)] rounded-full text-sm outline-none border border-transparent focus:border-[var(--primary)] text-[var(--on-surface)]"
                    value={editFirstName}
                    onChange={(e) => setEditFirstName(e.target.value)}
                    required
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-[var(--on-surface-variant)]">Last Name</label>
                  <input
                    type="text"
                    className="w-full px-5 py-3 bg-[var(--surface-container)] rounded-full text-sm outline-none border border-transparent focus:border-[var(--primary)] text-[var(--on-surface)]"
                    value={editLastName}
                    onChange={(e) => setEditLastName(e.target.value)}
                    required
                  />
                </div>
              </div>

              {/* Phone */}
              <div className="space-y-1">
                <label className="text-xs font-semibold text-[var(--on-surface-variant)]">Phone</label>
                <input
                  type="text"
                  className="w-full px-5 py-3 bg-[var(--surface-container)] rounded-full text-sm outline-none border border-transparent focus:border-[var(--primary)] text-[var(--on-surface)]"
                  value={editPhone}
                  onChange={(e) => setEditPhone(e.target.value)}
                />
              </div>

              {/* Role */}
              <div className="space-y-1">
                <label className="text-xs font-semibold text-[var(--on-surface-variant)]">Organization Role</label>
                <select
                  value={editRole}
                  onChange={(e) => setEditRole(e.target.value)}
                  className="w-full px-5 py-3 bg-[var(--surface-container)] rounded-full text-sm outline-none border border-transparent focus:border-[var(--primary)] cursor-pointer text-[var(--on-surface)] disabled:opacity-60 disabled:cursor-not-allowed"
                  disabled={selectedMember?.role_name.toLowerCase() === "owner"}
                  required
                >
                  {roles.map((r) => (
                    <option key={r.role_id} value={r.role_id}>
                      {r.role_name}
                    </option>
                  ))}
                </select>
              </div>

              {/* Workspace Assignments */}
              <div className="space-y-2">
                <label className="text-xs font-semibold text-[var(--on-surface-variant)]">Workspace Assignments</label>
                <div className="max-h-[120px] overflow-y-auto space-y-2 p-2 bg-[var(--surface-container)] rounded-2xl">
                  {allWorkspaces.map((ws) => (
                    <div key={ws.workspace_id} className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        id={`ws-edit-${ws.workspace_id}`}
                        className="w-4 h-4 text-[var(--primary)] rounded border-[var(--outline-variant)] focus:ring-[var(--primary)]"
                        checked={editWorkspaces.includes(ws.workspace_id)}
                        onChange={(e) => handleWorkspaceCheck(ws.workspace_id, e.target.checked, "edit")}
                      />
                      <label htmlFor={`ws-edit-${ws.workspace_id}`} className="text-xs text-[var(--on-surface)] cursor-pointer select-none">
                        {ws.workspace_name}
                      </label>
                    </div>
                  ))}
                </div>
              </div>

              <button
                type="submit"
                className="w-full py-4 rounded-full bg-[var(--primary)] text-[var(--on-primary)] font-bold hover:bg-[var(--primary-container)] cursor-pointer transition-colors active:scale-98"
              >
                Apply Changes
              </button>
            </form>
          </div>
        </div>
      )}
    </main>
  );
}
