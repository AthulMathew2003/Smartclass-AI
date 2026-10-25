"use client";

import React, { useEffect, useState, useCallback, Suspense } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  fetchWorkspace,
  fetchWorkspaceStudents,
  Workspace,
  WorkspaceStudent,
} from "@/lib/workspaces";
import { usePermissions } from "@/lib/permissions";
import ForbiddenState from "../../../components/ForbiddenState";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";

function WorkspaceStudentsContent() {
  const { id } = useParams() as { id: string };
  const router = useRouter();
  const { hasPermission, isLoaded: permLoaded } = usePermissions();

  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [students, setStudents] = useState<WorkspaceStudent[]>([]);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [wsLoading, setWsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Debounce search input
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(search);
      setPage(1);
    }, 350);
    return () => clearTimeout(timer);
  }, [search]);

  // Load workspace details
  const loadWorkspace = useCallback(async () => {
    if (!id) return;
    setWsLoading(true);
    try {
      const data = await fetchWorkspace(id);
      setWorkspace(data);
    } catch (err: any) {
      console.error("Failed to load workspace details:", err);
    } finally {
      setWsLoading(false);
    }
  }, [id]);

  // Load students directory
  const loadStudents = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetchWorkspaceStudents(id, {
        search: debouncedSearch,
        page,
        page_size: pageSize,
      });
      if (res.success && res.data) {
        setStudents(res.data.items);
        setTotal(res.data.total);
        setTotalPages(res.data.total_pages);
      } else {
        throw new Error(res.message || "Failed to load students.");
      }
    } catch (err: any) {
      setError(err?.message || "Failed to load workspace students. Please try again.");
    } finally {
      setLoading(false);
    }
  }, [id, debouncedSearch, page, pageSize]);

  useEffect(() => {
    if (permLoaded && hasPermission("workspace.read")) {
      loadWorkspace();
      loadStudents();
    }
  }, [permLoaded, id, loadWorkspace, loadStudents]);

  if (!permLoaded) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <div className="flex items-center gap-3 text-sm font-semibold text-[var(--on-surface-variant)]">
          <div className="w-6 h-6 border-2 border-t-transparent border-[var(--primary)] rounded-full animate-spin" />
          Checking permissions...
        </div>
      </div>
    );
  }

  if (!hasPermission("workspace.read")) {
    return (
      <ForbiddenState message="You do not have permission to view this workspace's students." />
    );
  }

  const getInitials = (student: WorkspaceStudent) => {
    if (student.first_name || student.last_name) {
      const f = student.first_name ? student.first_name[0] : "";
      const l = student.last_name ? student.last_name[0] : "";
      return (f + l).toUpperCase() || "S";
    }
    if (student.name && student.name !== student.email) {
      const parts = student.name.trim().split(/\s+/);
      if (parts.length >= 2) {
        return (parts[0][0] + parts[1][0]).toUpperCase();
      }
      return parts[0].slice(0, 2).toUpperCase();
    }
    return (student.email ? student.email[0] : "S").toUpperCase();
  };

  const formatDate = (isoString?: string | null) => {
    if (!isoString) return "—";
    try {
      const d = new Date(isoString);
      return d.toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
      });
    } catch {
      return "—";
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-16">
      {/* ── Breadcrumb & Back Navigation ───────────────────────── */}
      <div className="flex items-center justify-between gap-4">
        <nav className="flex items-center gap-2 text-xs font-semibold text-[var(--on-surface-variant)]">
          <Link
            href="/classroom/workspaces"
            className="hover:text-[var(--primary)] transition-colors flex items-center gap-1"
          >
            <span className="material-symbols-outlined text-[16px]">workspaces</span>
            Workspaces
          </Link>
          <span className="opacity-50">/</span>
          <span className="truncate max-w-[200px] text-[var(--on-surface)]">
            {workspace?.workspace_name || "Workspace"}
          </span>
          <span className="opacity-50">/</span>
          <span className="text-[var(--primary)] font-bold">Students</span>
        </nav>

        <Link
          href="/classroom/workspaces"
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold border border-[var(--outline-variant)]/40 hover:bg-[var(--surface-container-high)] text-[var(--on-surface-variant)] transition-colors"
        >
          <span className="material-symbols-outlined text-[16px]">arrow_back</span>
          Back to Workspaces
        </Link>
      </div>

      {/* ── Page Header ────────────────────────────────────────── */}
      <div
        className="p-6 rounded-3xl border flex flex-col md:flex-row md:items-center justify-between gap-4"
        style={{
          backgroundColor: "var(--surface-container)",
          borderColor: "color-mix(in srgb, var(--outline-variant) 30%, transparent)",
        }}
      >
        <div className="flex items-start gap-4">
          <div
            className="w-14 h-14 rounded-2xl flex items-center justify-center font-bold shrink-0 shadow-xs"
            style={{
              backgroundColor: "rgba(21,69,57,0.1)",
              color: "var(--primary)",
            }}
          >
            <span className="material-symbols-outlined text-[28px]">school</span>
          </div>
          <div>
            <div className="flex items-center gap-2 mb-1 flex-wrap">
              <h1
                className="text-2xl font-bold tracking-tight"
                style={{ color: "var(--on-surface)" }}
              >
                {workspace?.workspace_name || "Workspace Students"}
              </h1>
              {workspace?.workspace_status && (
                <Badge
                  className={`text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 border-0 ${
                    workspace.workspace_status === "archived"
                      ? "bg-amber-500/10 text-amber-600 dark:text-amber-400"
                      : "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                  }`}
                >
                  {workspace.workspace_status}
                </Badge>
              )}
            </div>
            <p
              className="text-xs leading-relaxed max-w-2xl"
              style={{ color: "var(--on-surface-variant)" }}
            >
              {workspace?.workspace_description ||
                "Authoritative directory of enrolled students in this workspace."}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3 self-start md:self-auto shrink-0">
          <Badge
            className="px-3 py-1.5 text-xs font-bold rounded-xl border-0"
            style={{
              backgroundColor: "rgba(21,69,57,0.12)",
              color: "var(--primary)",
            }}
          >
            <span className="material-symbols-outlined text-[16px] mr-1.5">school</span>
            {total} {total === 1 ? "Enrolled Student" : "Enrolled Students"}
          </Badge>
          <Button
            size="sm"
            variant="outline"
            onClick={loadStudents}
            disabled={loading}
            className="rounded-xl text-xs font-bold gap-1.5 h-8.5 px-3 border-[var(--outline-variant)]/40 hover:bg-[var(--surface-container-high)] cursor-pointer"
            title="Refresh directory"
          >
            <span className={`material-symbols-outlined text-[16px] ${loading ? "animate-spin" : ""}`}>
              refresh
            </span>
            Refresh
          </Button>
        </div>
      </div>

      {/* ── Search & Filter Controls ────────────────────────────── */}
      <div className="flex flex-col sm:flex-row gap-3 items-stretch sm:items-center justify-between">
        <div className="relative flex-1 max-w-md">
          <span
            className="material-symbols-outlined absolute left-3.5 top-1/2 -translate-y-1/2 text-[18px]"
            style={{ color: "var(--on-surface-variant)" }}
          >
            search
          </span>
          <Input
            placeholder="Search students by name or email..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-10 pr-9 py-2 rounded-xl text-xs h-10 border-[var(--outline-variant)]/40 bg-[var(--surface-container-low)] focus:bg-[var(--surface)] text-[var(--on-surface)]"
          />
          {search && (
            <button
              onClick={() => setSearch("")}
              className="absolute right-3 top-1/2 -translate-y-1/2 p-0.5 rounded-full hover:bg-[var(--surface-container-high)] text-[var(--on-surface-variant)] cursor-pointer"
              title="Clear search"
            >
              <span className="material-symbols-outlined text-[16px]">close</span>
            </button>
          )}
        </div>

        <div className="flex items-center gap-2 self-end sm:self-auto">
          <span
            className="text-xs font-semibold text-[var(--on-surface-variant)]"
          >
            Per page:
          </span>
          {[10, 25, 50].map((size) => (
            <button
              key={size}
              onClick={() => {
                setPageSize(size);
                setPage(1);
              }}
              className={`px-2.5 py-1 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                pageSize === size
                  ? "bg-[var(--primary)] text-[var(--on-primary)] shadow-2xs"
                  : "bg-[var(--surface-container-high)] text-[var(--on-surface-variant)] hover:bg-[var(--surface-container-highest)]"
              }`}
            >
              {size}
            </button>
          ))}
        </div>
      </div>

      {/* ── Error Banner ────────────────────────────────────────── */}
      {error && (
        <div className="p-4 rounded-2xl flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-xs font-semibold bg-red-500/10 text-red-600 dark:text-red-400 border border-red-500/20 animate-fade-in">
          <div className="flex items-center gap-2.5">
            <span className="material-symbols-outlined text-[20px] shrink-0">error</span>
            <span>{error}</span>
          </div>
          <Button
            size="sm"
            variant="outline"
            onClick={loadStudents}
            className="text-xs font-bold border-red-500/30 hover:bg-red-500/10 shrink-0 self-end sm:self-auto cursor-pointer"
          >
            Retry
          </Button>
        </div>
      )}

      {/* ── Student Directory Table / View ──────────────────────── */}
      {loading ? (
        /* Loading Skeleton */
        <div
          className="rounded-3xl border overflow-hidden p-6 space-y-4"
          style={{
            backgroundColor: "var(--surface-container)",
            borderColor: "color-mix(in srgb, var(--outline-variant) 30%, transparent)",
          }}
        >
          {[1, 2, 3, 4, 5].map((i) => (
            <div
              key={i}
              className="p-3.5 rounded-2xl border border-[var(--outline-variant)]/20 bg-[var(--surface-container-low)] animate-pulse flex items-center justify-between gap-4"
            >
              <div className="flex items-center gap-3 flex-1">
                <div className="w-10 h-10 rounded-xl bg-[var(--surface-container-high)] shrink-0" />
                <div className="space-y-1.5 flex-1">
                  <div className="w-1/3 h-4 rounded bg-[var(--surface-container-high)]" />
                  <div className="w-1/2 h-3 rounded bg-[var(--surface-container-high)]" />
                </div>
              </div>
              <div className="w-16 h-6 rounded-full bg-[var(--surface-container-high)] shrink-0" />
              <div className="w-24 h-4 rounded bg-[var(--surface-container-high)] shrink-0 hidden sm:block" />
            </div>
          ))}
        </div>
      ) : students.length === 0 ? (
        /* Empty State */
        <div
          className="p-12 rounded-3xl text-center space-y-4 border border-dashed my-4"
          style={{
            backgroundColor: "var(--surface-container-low)",
            borderColor: "color-mix(in srgb, var(--outline-variant) 40%, transparent)",
          }}
        >
          <div
            className="w-16 h-16 rounded-3xl flex items-center justify-center mx-auto"
            style={{
              backgroundColor: "rgba(21,69,57,0.08)",
              color: "var(--primary)",
            }}
          >
            <span className="material-symbols-outlined text-[32px]">
              {search ? "search_off" : "school"}
            </span>
          </div>
          <div className="max-w-md mx-auto space-y-1">
            <h3 className="text-base font-bold text-[var(--on-surface)]">
              {search ? "No students match your search" : "No students in this workspace"}
            </h3>
            <p className="text-xs text-[var(--on-surface-variant)] leading-relaxed">
              {search
                ? `No students found matching "${search}". Try searching with a different name or email.`
                : "This workspace does not currently have any enrolled students assigned to it."}
            </p>
          </div>
          {search && (
            <Button
              size="sm"
              variant="outline"
              onClick={() => setSearch("")}
              className="text-xs font-bold gap-1 mt-2 cursor-pointer"
            >
              <span className="material-symbols-outlined text-[15px]">clear</span>
              Clear search filter
            </Button>
          )}
        </div>
      ) : (
        /* Directory Data Card / Table */
        <div
          className="rounded-3xl border overflow-hidden shadow-xs"
          style={{
            backgroundColor: "var(--surface-container)",
            borderColor: "color-mix(in srgb, var(--outline-variant) 30%, transparent)",
          }}
        >
          {/* Table Header (Desktop) */}
          <div className="hidden sm:grid grid-cols-12 gap-4 px-6 py-3.5 border-b text-[11px] font-bold uppercase tracking-wider text-[var(--on-surface-variant)] bg-[var(--surface-container-high)]/40 border-[var(--outline-variant)]/20">
            <div className="col-span-6">Student</div>
            <div className="col-span-3">Status</div>
            <div className="col-span-3 text-right">Enrolled Date</div>
          </div>

          {/* Table Rows */}
          <div className="divide-y divide-[var(--outline-variant)]/15">
            {students.map((student) => {
              const isSuspended =
                student.status?.toLowerCase() === "suspended" ||
                student.status?.toLowerCase() === "inactive";
              const initials = getInitials(student);

              return (
                <div
                  key={student.id}
                  className="px-6 py-4 flex flex-col sm:grid sm:grid-cols-12 gap-3 sm:gap-4 sm:items-center hover:bg-[var(--surface-container-high)]/30 transition-colors"
                >
                  {/* Student Identity */}
                  <div className="sm:col-span-6 flex items-center gap-3.5 min-w-0">
                    {student.avatar_url ? (
                      <img
                        src={student.avatar_url}
                        alt={student.name}
                        className="w-10 h-10 rounded-xl object-cover shrink-0 border border-[var(--outline-variant)]/30"
                      />
                    ) : (
                      <div
                        className="w-10 h-10 rounded-xl flex items-center justify-center text-xs font-bold shrink-0 shadow-2xs"
                        style={{
                          backgroundColor: "var(--tertiary-fixed)",
                          color: "var(--on-tertiary-fixed)",
                        }}
                      >
                        {initials}
                      </div>
                    )}
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-bold text-[var(--on-surface)] truncate">
                        {student.name}
                      </p>
                      {student.email && (
                        <p className="text-xs text-[var(--on-surface-variant)] truncate flex items-center gap-1 mt-0.5">
                          <span className="material-symbols-outlined text-[13px] opacity-70">
                            mail
                          </span>
                          <span>{student.email}</span>
                        </p>
                      )}
                    </div>
                  </div>

                  {/* Status */}
                  <div className="sm:col-span-3 flex items-center">
                    <Badge
                      className={`text-[10px] uppercase font-bold tracking-wider px-2.5 py-0.5 border-0 ${
                        isSuspended
                          ? "bg-amber-500/10 text-amber-600 dark:text-amber-400"
                          : "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                      }`}
                    >
                      {student.status || "Active"}
                    </Badge>
                  </div>

                  {/* Joined Date */}
                  <div className="sm:col-span-3 text-left sm:text-right text-xs text-[var(--on-surface-variant)]">
                    <span className="sm:hidden font-semibold mr-1.5">Enrolled:</span>
                    <span>{formatDate(student.joined_at)}</span>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Table Footer / Pagination */}
          <div className="p-4 border-t border-[var(--outline-variant)]/20 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs bg-[var(--surface-container-low)]">
            <div className="text-[var(--on-surface-variant)] text-center sm:text-left">
              Showing{" "}
              <span className="font-bold text-[var(--on-surface)]">
                {Math.min((page - 1) * pageSize + 1, total)}–
                {Math.min(page * pageSize, total)}
              </span>{" "}
              of <span className="font-bold text-[var(--on-surface)]">{total}</span> students
            </div>

            <div className="flex items-center gap-2">
              <Button
                size="sm"
                variant="outline"
                disabled={page <= 1 || loading}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                className="text-xs h-8 px-2.5 gap-1 font-bold cursor-pointer"
              >
                <span className="material-symbols-outlined text-[16px]">chevron_left</span>
                Previous
              </Button>

              <span className="px-2 font-bold text-xs text-[var(--on-surface)]">
                {page} / {totalPages || 1}
              </span>

              <Button
                size="sm"
                variant="outline"
                disabled={page >= totalPages || loading}
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                className="text-xs h-8 px-2.5 gap-1 font-bold cursor-pointer"
              >
                Next
                <span className="material-symbols-outlined text-[16px]">chevron_right</span>
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function WorkspaceStudentsPage() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center min-h-[50vh]">
          <div className="flex items-center gap-3 text-sm font-semibold text-[var(--on-surface-variant)]">
            <div className="w-6 h-6 border-2 border-t-transparent border-[var(--primary)] rounded-full animate-spin" />
            Loading workspace student directory...
          </div>
        </div>
      }
    >
      <WorkspaceStudentsContent />
    </Suspense>
  );
}
