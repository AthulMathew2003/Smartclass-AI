"use client";

import React, { useEffect, useState, useCallback, useRef } from "react";
import Link from "next/link";
import {
  Workspace,
  WorkspaceStudent,
  fetchWorkspaceStudents,
} from "@/lib/workspaces";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

interface WorkspaceStudentsDrawerProps {
  workspace: Workspace | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export default function WorkspaceStudentsDrawer({
  workspace,
  open,
  onOpenChange,
}: WorkspaceStudentsDrawerProps) {
  const [students, setStudents] = useState<WorkspaceStudent[]>([]);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Debounce search input
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(search);
      setPage(1); // reset to page 1 on new search
    }, 350);
    return () => clearTimeout(timer);
  }, [search]);

  // Load students
  const loadStudents = useCallback(async () => {
    if (!workspace) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetchWorkspaceStudents(workspace.workspace_id, {
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
  }, [workspace, debouncedSearch, page, pageSize]);

  useEffect(() => {
    if (open && workspace) {
      loadStudents();
    }
  }, [open, workspace, loadStudents]);

  // Reset state when workspace changes
  useEffect(() => {
    if (workspace) {
      setSearch("");
      setDebouncedSearch("");
      setPage(1);
    }
  }, [workspace?.workspace_id]);

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
    if (!isoString) return null;
    try {
      const d = new Date(isoString);
      return d.toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
      });
    } catch {
      return null;
    }
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="w-full sm:max-w-xl md:max-w-2xl flex flex-col p-0 gap-0 border-l overflow-hidden bg-[var(--surface)] text-[var(--on-surface)]"
        style={{
          borderColor: "var(--outline-variant)",
        }}
      >
        {/* ── Top Header ────────────────────────────────────────── */}
        <div
          className="p-6 border-b shrink-0 space-y-3"
          style={{
            backgroundColor: "var(--surface-container-low)",
            borderColor: "color-mix(in srgb, var(--outline-variant) 30%, transparent)",
          }}
        >
          <div className="flex items-center gap-2">
            <span
              className="w-2.5 h-2.5 rounded-full"
              style={{ backgroundColor: "var(--primary)" }}
            />
            <span
              className="text-xs font-bold uppercase tracking-wider"
              style={{ color: "var(--secondary)" }}
            >
              Workspace Directory
            </span>
          </div>

          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div>
              <SheetTitle className="text-xl font-bold tracking-tight text-[var(--on-surface)]">
                {workspace?.workspace_name || "Workspace"}
              </SheetTitle>
              <SheetDescription className="text-xs text-[var(--on-surface-variant)] mt-0.5">
                Enrolled students registered in this workspace.
              </SheetDescription>
            </div>

            <div className="flex items-center gap-2 self-start sm:self-auto flex-wrap">
              <Badge
                className="px-2.5 py-1 text-xs font-bold rounded-lg border-0"
                style={{
                  backgroundColor: "rgba(21,69,57,0.12)",
                  color: "var(--primary)",
                }}
              >
                <span className="material-symbols-outlined text-[15px] mr-1">school</span>
                {total} {total === 1 ? "Student" : "Students"}
              </Badge>
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
              {workspace?.workspace_id && (
                <Link
                  href={`/classroom/workspaces/${workspace.workspace_id}/students`}
                  className="p-1.5 rounded-lg hover:bg-[var(--surface-container-high)] text-[var(--on-surface-variant)] hover:text-[var(--primary)] transition-colors inline-flex items-center"
                  title="Open full page"
                >
                  <span className="material-symbols-outlined text-[18px]">open_in_new</span>
                </Link>
              )}
            </div>
          </div>

          {/* ── Search Input Bar ──────────────────────────────── */}
          <div className="relative pt-1">
            <span
              className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-[18px]"
              style={{ color: "var(--on-surface-variant)" }}
            >
              search
            </span>
            <Input
              type="text"
              placeholder="Search students by name or email..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9 pr-8 py-2 rounded-xl text-xs h-9 bg-[var(--surface)] border-[var(--outline-variant)]/40 text-[var(--on-surface)] placeholder:text-[var(--on-surface-variant)]/70"
            />
            {search && (
              <button
                onClick={() => setSearch("")}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 p-0.5 rounded-full hover:bg-[var(--surface-container-high)] text-[var(--on-surface-variant)] cursor-pointer"
                title="Clear search"
              >
                <span className="material-symbols-outlined text-[16px]">close</span>
              </button>
            )}
          </div>
        </div>

        {/* ── Main Content Area ─────────────────────────────────── */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {/* Error State */}
          {error && (
            <div className="p-4 rounded-2xl flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-xs font-semibold bg-red-500/10 text-red-600 dark:text-red-400 border border-red-500/20">
              <div className="flex items-center gap-2.5">
                <span className="material-symbols-outlined text-[20px] shrink-0">error</span>
                <span>{error}</span>
              </div>
              <Button
                size="sm"
                variant="outline"
                onClick={loadStudents}
                className="text-xs font-bold border-red-500/30 hover:bg-red-500/10 shrink-0 self-end sm:self-auto"
              >
                Retry
              </Button>
            </div>
          )}

          {/* Loading Skeleton */}
          {loading ? (
            <div className="space-y-3">
              {[1, 2, 3, 4, 5].map((i) => (
                <div
                  key={i}
                  className="p-3.5 rounded-2xl border border-[var(--outline-variant)]/20 bg-[var(--surface-container-low)] animate-pulse flex items-center justify-between gap-3"
                >
                  <div className="flex items-center gap-3 flex-1">
                    <div className="w-10 h-10 rounded-xl bg-[var(--surface-container-high)] shrink-0" />
                    <div className="space-y-1.5 flex-1">
                      <div className="w-1/3 h-4 rounded bg-[var(--surface-container-high)]" />
                      <div className="w-1/2 h-3 rounded bg-[var(--surface-container-high)]" />
                    </div>
                  </div>
                  <div className="w-16 h-6 rounded-full bg-[var(--surface-container-high)] shrink-0" />
                </div>
              ))}
            </div>
          ) : students.length === 0 ? (
            /* Empty State */
            <div
              className="p-10 rounded-3xl text-center space-y-3 border border-dashed my-6"
              style={{
                backgroundColor: "var(--surface-container-low)",
                borderColor: "color-mix(in srgb, var(--outline-variant) 40%, transparent)",
              }}
            >
              <div
                className="w-14 h-14 rounded-2xl flex items-center justify-center mx-auto"
                style={{
                  backgroundColor: "rgba(21,69,57,0.08)",
                  color: "var(--primary)",
                }}
              >
                <span className="material-symbols-outlined text-[28px]">
                  {search ? "search_off" : "person_search"}
                </span>
              </div>
              <div>
                <h4 className="text-sm font-bold text-[var(--on-surface)]">
                  {search ? "No students match your search" : "No students in this workspace"}
                </h4>
                <p className="text-xs text-[var(--on-surface-variant)] mt-1 max-w-sm mx-auto leading-relaxed">
                  {search
                    ? `No students found matching "${search}". Try searching by another name or email.`
                    : "There are currently no members with the Student role assigned to this workspace."}
                </p>
              </div>
              {search && (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setSearch("")}
                  className="text-xs font-bold gap-1 mt-2"
                >
                  <span className="material-symbols-outlined text-[15px]">clear</span>
                  Clear search
                </Button>
              )}
            </div>
          ) : (
            /* Students List */
            <div className="space-y-2.5">
              {students.map((student) => {
                const isSuspended =
                  student.status?.toLowerCase() === "suspended" ||
                  student.status?.toLowerCase() === "inactive";
                const initials = getInitials(student);
                const joinedDate = formatDate(student.joined_at);

                return (
                  <div
                    key={student.id}
                    className="p-3.5 rounded-2xl border transition-all duration-150 flex items-center justify-between gap-3 hover:border-[var(--primary)] hover:shadow-xs group"
                    style={{
                      backgroundColor: "var(--surface-container-low)",
                      borderColor: "color-mix(in srgb, var(--outline-variant) 25%, transparent)",
                    }}
                  >
                    {/* Left: Avatar + Identity */}
                    <div className="flex items-center gap-3.5 min-w-0 flex-1">
                      {student.avatar_url ? (
                        <img
                          src={student.avatar_url}
                          alt={student.name}
                          className="w-10 h-10 rounded-xl object-cover shrink-0 border border-[var(--outline-variant)]/30"
                        />
                      ) : (
                        <div
                          className="w-10 h-10 rounded-xl flex items-center justify-center text-xs font-bold shrink-0 transition-transform group-hover:scale-105"
                          style={{
                            backgroundColor: "var(--tertiary-fixed)",
                            color: "var(--on-tertiary-fixed)",
                          }}
                        >
                          {initials}
                        </div>
                      )}

                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <p className="text-sm font-bold truncate text-[var(--on-surface)] group-hover:text-[var(--primary)] transition-colors">
                            {student.name}
                          </p>
                        </div>
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

                    {/* Right: Status & Joined Date */}
                    <div className="flex flex-col items-end shrink-0 gap-1">
                      <Badge
                        className={`text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 border-0 ${
                          isSuspended
                            ? "bg-amber-500/10 text-amber-600 dark:text-amber-400"
                            : "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                        }`}
                      >
                        {student.status || "Active"}
                      </Badge>
                      {joinedDate && (
                        <span className="text-[10px] text-[var(--on-surface-variant)]/80">
                          Joined {joinedDate}
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* ── Footer with Pagination ────────────────────────────── */}
        <div
          className="p-4 border-t shrink-0 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs"
          style={{
            backgroundColor: "var(--surface-container-low)",
            borderColor: "color-mix(in srgb, var(--outline-variant) 30%, transparent)",
          }}
        >
          <div className="text-[var(--on-surface-variant)] text-center sm:text-left">
            {total > 0 ? (
              <span>
                Showing{" "}
                <span className="font-bold text-[var(--on-surface)]">
                  {Math.min((page - 1) * pageSize + 1, total)}–
                  {Math.min(page * pageSize, total)}
                </span>{" "}
                of <span className="font-bold text-[var(--on-surface)]">{total}</span>{" "}
                students
              </span>
            ) : (
              <span>0 students found</span>
            )}
          </div>

          <div className="flex items-center gap-2">
            <Button
              size="sm"
              variant="outline"
              disabled={page <= 1 || loading}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              className="text-xs h-8 px-2.5 gap-1 font-bold"
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
              className="text-xs h-8 px-2.5 gap-1 font-bold"
            >
              Next
              <span className="material-symbols-outlined text-[16px]">chevron_right</span>
            </Button>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}
