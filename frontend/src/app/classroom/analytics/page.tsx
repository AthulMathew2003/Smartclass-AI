"use client";

import React, { useEffect, useState, useMemo } from "react";
import Link from "next/link";
import {
  fetchMyLearningAnalytics,
  fetchStudentLearningAnalytics,
  fetchSubjectLearningAnalytics,
  fetchSubjectQuestionDifficulty,
  fetchClassPerformanceDashboard,
  updateAssessmentLeaderboardSettings,
  StudentLearningAnalyticsResponse,
  SubjectLearningAnalyticsResponse,
  SubjectQuestionDifficultyResponse,
  ClassPerformanceDashboardResponse,
  ClassStudentPerformanceItem,
  QuestionDifficultyAnalyticsItem,
  ObservedDifficultyBand,
} from "@/lib/assessments";
import { fetchSubjects, Subject } from "@/lib/subjects";
import { fetchMembers, Member } from "@/lib/members";
import { usePermissions } from "@/lib/permissions";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";

export default function LearningAnalyticsPage() {
  const { hasPermission, isLoaded: permLoaded } = usePermissions();

  // Role detection: is teacher or admin?
  const isTeacherOrAdmin = permLoaded && (
    hasPermission("assessment.grade") ||
    hasPermission("assessment.create") ||
    hasPermission("subject.create") ||
    hasPermission("member.update")
  );

  // Active view tab for Teachers/Admins: "class_performance" | "subject_analytics" | "student_inspector" | "my_learning"
  const [activeTab, setActiveTab] = useState<"class_performance" | "subject_analytics" | "student_inspector" | "my_learning">("my_learning");

  // Student Learning Analytics State (Personal or Inspected)
  const [studentAnalytics, setStudentAnalytics] = useState<StudentLearningAnalyticsResponse | null>(null);
  const [loadingStudent, setLoadingStudent] = useState(true);
  const [studentError, setStudentError] = useState<string | null>(null);

  // Teacher Shared Data State
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [selectedSubjectId, setSelectedSubjectId] = useState<string>("");

  // Teacher Class Performance Dashboard State (Step 10.13)
  const [classPerformance, setClassPerformance] = useState<ClassPerformanceDashboardResponse | null>(null);
  const [loadingClassPerf, setLoadingClassPerf] = useState(false);
  const [classPerfError, setClassPerfError] = useState<string | null>(null);
  const [togglingLeaderboardId, setTogglingLeaderboardId] = useState<string | null>(null);

  // Roster Filters
  const [rosterSearch, setRosterSearch] = useState("");
  const [rosterStatusFilter, setRosterStatusFilter] = useState<string>("all");

  // Teacher Subject Analytics State
  const [subjectAnalytics, setSubjectAnalytics] = useState<SubjectLearningAnalyticsResponse | null>(null);
  const [questionDifficulty, setQuestionDifficulty] = useState<SubjectQuestionDifficultyResponse | null>(null);
  const [loadingSubject, setLoadingSubject] = useState(false);
  const [subjectError, setSubjectError] = useState<string | null>(null);

  // Teacher Student Inspector State
  const [members, setMembers] = useState<Member[]>([]);
  const [selectedStudentId, setSelectedStudentId] = useState<string>("");
  const [studentSearch, setStudentSearch] = useState("");
  const [inspectedStudentAnalytics, setInspectedStudentAnalytics] = useState<StudentLearningAnalyticsResponse | null>(null);
  const [loadingInspected, setLoadingInspected] = useState(false);
  const [inspectedError, setInspectedError] = useState<string | null>(null);

  // Filter for question difficulty table
  const [difficultyFilter, setDifficultyFilter] = useState<string>("all");
  const [difficultySearch, setDifficultySearch] = useState("");

  // Load student personal learning analytics
  const loadStudentAnalytics = async () => {
    try {
      setLoadingStudent(true);
      setStudentError(null);
      const data = await fetchMyLearningAnalytics();
      setStudentAnalytics(data);
    } catch (err: any) {
      setStudentError(err?.message || "Failed to load learning analytics.");
    } finally {
      setLoadingStudent(false);
    }
  };

  // Load subject list and members for teachers
  const loadTeacherData = async () => {
    try {
      const [subjectsData, membersData] = await Promise.all([
        fetchSubjects(),
        fetchMembers({}),
      ]);
      setSubjects(subjectsData);
      if (subjectsData.length > 0 && !selectedSubjectId) {
        setSelectedSubjectId(subjectsData[0].subject_id);
      }

      // Filter members strictly to students
      const studentMembers = membersData.filter(m => m.role_name?.toLowerCase() === "student");
      setMembers(studentMembers);
      if (studentMembers.length > 0) {
        setSelectedStudentId(studentMembers[0].user_id);
      } else {
        setSelectedStudentId("");
      }
    } catch (err: any) {
      console.error("Failed to load teacher metadata:", err);
    }
  };

  // Load class performance dashboard for selected subject
  const loadClassPerformanceData = async (subjectId: string) => {
    if (!subjectId) return;
    try {
      setLoadingClassPerf(true);
      setClassPerfError(null);
      const data = await fetchClassPerformanceDashboard(subjectId);
      setClassPerformance(data);
    } catch (err: any) {
      setClassPerfError(err?.message || "Failed to load class performance dashboard.");
    } finally {
      setLoadingClassPerf(false);
    }
  };

  // Quick toggle leaderboard for an assessment
  const handleQuickToggleLeaderboard = async (assessmentId: string, currentEnabled: boolean) => {
    try {
      setTogglingLeaderboardId(assessmentId);
      await updateAssessmentLeaderboardSettings(assessmentId, !currentEnabled);
      if (selectedSubjectId) {
        await loadClassPerformanceData(selectedSubjectId);
      }
    } catch (err: any) {
      alert(err?.message || "Failed to update leaderboard settings.");
    } finally {
      setTogglingLeaderboardId(null);
    }
  };

  // Load selected subject analytics & question difficulty
  const loadSubjectData = async (subjectId: string) => {
    if (!subjectId) return;
    try {
      setLoadingSubject(true);
      setSubjectError(null);
      const [subjData, qDiffData] = await Promise.all([
        fetchSubjectLearningAnalytics(subjectId),
        fetchSubjectQuestionDifficulty(subjectId),
      ]);
      setSubjectAnalytics(subjData);
      setQuestionDifficulty(qDiffData);
    } catch (err: any) {
      setSubjectError(err?.message || "Failed to load subject analytics.");
    } finally {
      setLoadingSubject(false);
    }
  };

  // Load inspected student longitudinal analytics
  const loadInspectedStudent = async (studentId: string) => {
    if (!studentId) return;
    try {
      setLoadingInspected(true);
      setInspectedError(null);
      const data = await fetchStudentLearningAnalytics(studentId);
      setInspectedStudentAnalytics(data);
    } catch (err: any) {
      setInspectedError(err?.message || "Failed to load student analytics.");
    } finally {
      setLoadingInspected(false);
    }
  };

  useEffect(() => {
    loadStudentAnalytics();
    if (isTeacherOrAdmin) {
      loadTeacherData();
      setActiveTab("class_performance");
    }
  }, [permLoaded, isTeacherOrAdmin]);

  useEffect(() => {
    if (selectedSubjectId) {
      if (activeTab === "class_performance") {
        loadClassPerformanceData(selectedSubjectId);
      } else if (activeTab === "subject_analytics") {
        loadSubjectData(selectedSubjectId);
      }
    }
  }, [selectedSubjectId, activeTab]);

  useEffect(() => {
    if (selectedStudentId && activeTab === "student_inspector") {
      loadInspectedStudent(selectedStudentId);
    }
  }, [selectedStudentId, activeTab]);

  // Filtered roster for class performance
  const filteredRoster = useMemo(() => {
    if (!classPerformance?.student_roster) return [];
    return classPerformance.student_roster.filter((s) => {
      const matchesSearch =
        !rosterSearch.trim() ||
        s.student_name.toLowerCase().includes(rosterSearch.toLowerCase()) ||
        (s.student_email && s.student_email.toLowerCase().includes(rosterSearch.toLowerCase()));

      let matchesStatus = true;
      if (rosterStatusFilter === "passing") {
        matchesStatus = s.status_label === "Passing";
      } else if (rosterStatusFilter === "below") {
        matchesStatus = s.status_label === "Below Passing Threshold";
      } else if (rosterStatusFilter === "pending") {
        matchesStatus = s.status_label === "Pending Review";
      } else if (rosterStatusFilter === "none") {
        matchesStatus = s.status_label === "No Submissions";
      }

      return matchesSearch && matchesStatus;
    });
  }, [classPerformance, rosterSearch, rosterStatusFilter]);

  // Filtered members list for dropdown/search
  const filteredMembers = useMemo(() => {
    if (!studentSearch) return members;
    const term = studentSearch.toLowerCase();
    return members.filter(
      (m) =>
        m.first_name?.toLowerCase().includes(term) ||
        m.last_name?.toLowerCase().includes(term) ||
        m.email?.toLowerCase().includes(term)
    );
  }, [members, studentSearch]);

  // Filtered questions for difficulty analysis
  const filteredQuestions = useMemo(() => {
    if (!questionDifficulty?.questions) return [];
    return questionDifficulty.questions.filter((q) => {
      const matchesFilter =
        difficultyFilter === "all" || q.difficulty_band === difficultyFilter;
      const matchesSearch =
        !difficultySearch ||
        q.question_text.toLowerCase().includes(difficultySearch.toLowerCase());
      return matchesFilter && matchesSearch;
    });
  }, [questionDifficulty, difficultyFilter, difficultySearch]);

  // Difficulty badge helper
  const getDifficultyBadge = (band: ObservedDifficultyBand, label: string) => {
    switch (band) {
      case "easier_observed":
        return (
          <Badge className="bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30 text-xs font-semibold px-2.5 py-1">
            <span className="material-symbols-outlined text-[14px] mr-1">check_circle</span>
            {label}
          </Badge>
        );
      case "moderate_observed":
        return (
          <Badge className="bg-amber-500/15 text-amber-600 dark:text-amber-400 border border-amber-500/30 text-xs font-semibold px-2.5 py-1">
            <span className="material-symbols-outlined text-[14px] mr-1">balance</span>
            {label}
          </Badge>
        );
      case "harder_observed":
        return (
          <Badge className="bg-rose-500/15 text-rose-600 dark:text-rose-400 border border-rose-500/30 text-xs font-semibold px-2.5 py-1">
            <span className="material-symbols-outlined text-[14px] mr-1">priority_high</span>
            {label}
          </Badge>
        );
      case "insufficient_sample":
      default:
        return (
          <Badge className="bg-slate-500/15 text-slate-600 dark:text-slate-400 border border-slate-500/30 text-xs font-medium px-2.5 py-1">
            <span className="material-symbols-outlined text-[14px] mr-1">info</span>
            {label}
          </Badge>
        );
    }
  };

  // Helper renderer for student profile view (used by both personal and teacher inspector)
  const renderStudentAnalyticsDashboard = (data: StudentLearningAnalyticsResponse, isInspector: boolean) => (
    <div className="space-y-8 animate-in fade-in duration-300">
      {/* Student Profile Info (Inspector mode) */}
      {isInspector && (
        <div className="bg-card border border-border/60 rounded-2xl p-5 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-11 h-11 rounded-full bg-primary/10 text-primary flex items-center justify-center font-bold text-lg border border-primary/20">
              {data.student_name ? data.student_name.charAt(0).toUpperCase() : "S"}
            </div>
            <div>
              <h2 className="text-lg font-bold text-foreground">
                {data.student_name || "Student Learning Profile"}
              </h2>
              <p className="text-xs text-muted-foreground">{data.student_email || "Enrolled Student"}</p>
            </div>
          </div>
          <Badge variant="outline" className="text-xs px-3 py-1 bg-muted/40 font-mono">
            ID: {data.student_id.substring(0, 8)}...
          </Badge>
        </div>
      )}

      {/* Student Overview KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <div className="bg-card border border-border/60 rounded-2xl p-5 shadow-sm space-y-2">
          <div className="flex items-center justify-between text-muted-foreground">
            <span className="text-xs font-semibold uppercase tracking-wider">Overall Average</span>
            <span className="material-symbols-outlined text-primary text-xl">analytics</span>
          </div>
          <div className="text-3xl font-bold text-foreground">
            {data.overview.average_percentage !== null && data.overview.average_percentage !== undefined
              ? `${data.overview.average_percentage}%`
              : "—"}
          </div>
          <div className="text-xs text-muted-foreground flex items-center gap-1">
            {data.trend.improvement_from_previous !== null && data.trend.improvement_from_previous !== undefined ? (
              data.trend.improvement_from_previous >= 0 ? (
                <span className="text-emerald-600 dark:text-emerald-400 font-semibold flex items-center">
                  <span className="material-symbols-outlined text-[14px]">trending_up</span>
                  +{data.trend.improvement_from_previous}% vs previous
                </span>
              ) : (
                <span className="text-rose-600 dark:text-rose-400 font-semibold flex items-center">
                  <span className="material-symbols-outlined text-[14px]">trending_down</span>
                  {data.trend.improvement_from_previous}% vs previous
                </span>
              )
            ) : (
              "Baseline assessment score"
            )}
          </div>
        </div>

        <div className="bg-card border border-border/60 rounded-2xl p-5 shadow-sm space-y-2">
          <div className="flex items-center justify-between text-muted-foreground">
            <span className="text-xs font-semibold uppercase tracking-wider">Assessments Completed</span>
            <span className="material-symbols-outlined text-emerald-500 text-xl">task_alt</span>
          </div>
          <div className="text-3xl font-bold text-foreground">
            {data.overview.total_assessments_completed}
          </div>
          <div className="text-xs text-muted-foreground">
            {data.overview.total_passed_count} passed
            {data.overview.total_failed_count > 0 && ` • ${data.overview.total_failed_count} need review`}
          </div>
        </div>

        <div className="bg-card border border-border/60 rounded-2xl p-5 shadow-sm space-y-2">
          <div className="flex items-center justify-between text-muted-foreground">
            <span className="text-xs font-semibold uppercase tracking-wider">Best Score</span>
            <span className="material-symbols-outlined text-amber-500 text-xl">military_tech</span>
          </div>
          <div className="text-3xl font-bold text-amber-600 dark:text-amber-400">
            {data.overview.best_percentage !== null && data.overview.best_percentage !== undefined
              ? `${data.overview.best_percentage}%`
              : "—"}
          </div>
          <div className="text-xs text-muted-foreground">
            Highest percentage achieved across all attempts
          </div>
        </div>

        <div className="bg-card border border-border/60 rounded-2xl p-5 shadow-sm space-y-2">
          <div className="flex items-center justify-between text-muted-foreground">
            <span className="text-xs font-semibold uppercase tracking-wider">Recent Trend (5)</span>
            <span className="material-symbols-outlined text-indigo-500 text-xl">timeline</span>
          </div>
          <div className="text-3xl font-bold text-indigo-600 dark:text-indigo-400">
            {data.trend.recent_average_percentage !== null && data.trend.recent_average_percentage !== undefined
              ? `${data.trend.recent_average_percentage}%`
              : "—"}
          </div>
          <div className="text-xs text-muted-foreground">
            Recent window average vs history
          </div>
        </div>
      </div>

      {/* Chronological Score Progression (SVG Chart) */}
      <div className="bg-card border border-border/60 rounded-2xl p-6 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <h2 className="text-lg font-bold text-foreground flex items-center gap-2">
              <span className="material-symbols-outlined text-primary">show_chart</span>
              Score Progression Over Time
            </h2>
            <p className="text-xs text-muted-foreground">
              Chronological scores achieved across completed assessments.
            </p>
          </div>
        </div>

        {data.performance_progression.length === 0 ? (
          <div className="py-12 text-center text-muted-foreground">
            <span className="material-symbols-outlined text-4xl mb-2 text-muted-foreground/50">monitoring</span>
            <p className="text-sm font-medium">No completed assessments recorded yet.</p>
            <p className="text-xs">Assessments completed by this student will build their longitudinal curve.</p>
          </div>
        ) : (
          <div className="space-y-4 pt-2">
            <div className="h-64 w-full relative">
              <svg className="w-full h-full overflow-visible" viewBox="0 0 700 200" preserveAspectRatio="none">
                <defs>
                  <linearGradient id="scoreGradDynamic" x1="0%" y1="0%" x2="0%" y2="100%">
                    <stop offset="0%" stopColor="var(--primary)" stopOpacity="0.25" />
                    <stop offset="100%" stopColor="var(--primary)" stopOpacity="0.0" />
                  </linearGradient>
                </defs>

                {/* Grid Lines */}
                {[0, 25, 50, 75, 100].map((level) => {
                  const y = 200 - (level / 100) * 180 - 10;
                  return (
                    <g key={level}>
                      <line x1="0" y1={y} x2="700" y2={y} stroke="currentColor" strokeDasharray="3 3" className="text-border/40" />
                      <text x="5" y={y - 4} fontSize="10" fill="currentColor" className="text-muted-foreground/70">{level}%</text>
                    </g>
                  );
                })}

                {/* Draw Progression Path */}
                {(() => {
                  const points = data.performance_progression.map((item, idx) => {
                    const total = data.performance_progression.length;
                    const x = total > 1 ? 40 + (idx / (total - 1)) * 620 : 350;
                    const pct = Math.min(Math.max(item.percentage || 0, 0), 100);
                    const y = 200 - (pct / 100) * 180 - 10;
                    return { x, y, item };
                  });

                  const d = points.reduce((acc, pt, idx) => `${acc} ${idx === 0 ? "M" : "L"} ${pt.x} ${pt.y}`, "");
                  const areaD = points.length > 0 ? `${d} L ${points[points.length - 1].x} 190 L ${points[0].x} 190 Z` : "";

                  return (
                    <>
                      {areaD && <path d={areaD} fill="url(#scoreGradDynamic)" />}
                      {d && <path d={d} fill="none" stroke="var(--primary)" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />}
                      {points.map((pt, idx) => (
                        <g key={idx} className="group">
                          <circle cx={pt.x} cy={pt.y} r="5" className="fill-background stroke-primary stroke-[3]" />
                          <circle cx={pt.x} cy={pt.y} r="8" className="fill-primary/20 opacity-0 group-hover:opacity-100 transition-opacity" />
                        </g>
                      ))}
                    </>
                  );
                })()}
              </svg>
            </div>

            {/* Timeline Pills */}
            <div className="flex items-center gap-2 overflow-x-auto pb-2 pt-1 scrollbar-thin">
              {data.performance_progression.map((item, idx) => (
                <div
                  key={idx}
                  className="px-3 py-1.5 rounded-xl border border-border/50 bg-card flex items-center gap-2 shrink-0 text-xs shadow-xs"
                >
                  <span className="w-5 h-5 rounded-full bg-primary/15 text-primary flex items-center justify-center font-bold text-[10px]">
                    {idx + 1}
                  </span>
                  <div>
                    <p className="font-semibold text-foreground truncate max-w-[160px]">
                      {item.assessment_title}
                    </p>
                    <p className="text-[10px] text-muted-foreground">
                      {item.subject_name} • {new Date(item.date).toLocaleDateString()}
                    </p>
                  </div>
                  <Badge
                    className={`ml-2 text-[10px] font-bold ${
                      (item.percentage || 0) >= 70
                        ? "bg-emerald-500/15 text-emerald-600 border-emerald-500/30"
                        : (item.percentage || 0) >= 50
                        ? "bg-amber-500/15 text-amber-600 border-amber-500/30"
                        : "bg-rose-500/15 text-rose-600 border-rose-500/30"
                    }`}
                  >
                    {item.percentage !== null ? `${item.percentage}%` : "Pending"}
                  </Badge>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Subject Mastery & Question-Type Breakdown Grids */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="bg-card border border-border/60 rounded-2xl p-6 shadow-sm space-y-4">
          <div>
            <h2 className="text-lg font-bold text-foreground flex items-center gap-2">
              <span className="material-symbols-outlined text-primary">menu_book</span>
              Subject Performance Breakdown
            </h2>
            <p className="text-xs text-muted-foreground">
              Cumulative performance across subjects evaluated.
            </p>
          </div>

          {data.subject_performance.length === 0 ? (
            <p className="py-8 text-center text-xs text-muted-foreground">No subject data recorded.</p>
          ) : (
            <div className="space-y-4">
              {data.subject_performance.map((s) => (
                <div key={s.subject_id} className="p-4 rounded-xl border border-border/40 bg-muted/20 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-sm text-foreground">{s.subject_name}</span>
                    <span className="text-xs font-bold text-primary">
                      {s.average_percentage !== null ? `${s.average_percentage}% Avg` : "No attempts"}
                    </span>
                  </div>

                  <div className="w-full bg-muted/60 h-2 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-primary rounded-full transition-all duration-500"
                      style={{ width: `${Math.min(s.average_percentage || 0, 100)}%` }}
                    />
                  </div>

                  <div className="flex items-center justify-between text-[11px] text-muted-foreground pt-1">
                    <span>{s.assessments_completed} assessments completed</span>
                    <span>{s.passed_count} passed • {s.failed_count} need review</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="bg-card border border-border/60 rounded-2xl p-6 shadow-sm space-y-4">
          <div>
            <h2 className="text-lg font-bold text-foreground flex items-center gap-2">
              <span className="material-symbols-outlined text-primary">grid_view</span>
              Question Type Accuracy Matrix
            </h2>
            <p className="text-xs text-muted-foreground">
              Accuracy rates aggregated across question formats.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
            {data.question_type_performance.map((qt) => {
              const label = qt.question_type === "mcq_single"
                ? "Multiple Choice (Single)"
                : qt.question_type === "mcq_multiple"
                ? "Multiple Choice (Multi)"
                : qt.question_type === "true_false"
                ? "True / False"
                : "Short Answer";

              const icon = qt.question_type === "mcq_single"
                ? "radio_button_checked"
                : qt.question_type === "mcq_multiple"
                ? "check_box"
                : qt.question_type === "true_false"
                ? "toggle_on"
                : "edit_note";

              return (
                <div key={qt.question_type} className="p-4 rounded-xl border border-border/40 bg-card space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-foreground flex items-center gap-1.5">
                      <span className="material-symbols-outlined text-primary text-[16px]">{icon}</span>
                      {label}
                    </span>
                    <span className="text-sm font-bold text-foreground">
                      {qt.accuracy_percentage !== null ? `${qt.accuracy_percentage}%` : "—"}
                    </span>
                  </div>

                  <div className="w-full bg-muted/60 h-1.5 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-primary rounded-full"
                      style={{ width: `${Math.min(qt.accuracy_percentage || 0, 100)}%` }}
                    />
                  </div>

                  <div className="flex items-center justify-between text-[10px] text-muted-foreground pt-0.5">
                    <span>{qt.evaluated_count} evaluated</span>
                    <p className="truncate">
                      {qt.correct_count} correct
                      {qt.pending_count > 0 && ` • ${qt.pending_count} pending`}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );

  return (
    <div className="flex-1 p-6 md:p-8 max-w-7xl mx-auto w-full space-y-8">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-border/40">
        <div>
          <div className="flex items-center gap-3">
            <div
              className="w-10 h-10 rounded-xl flex items-center justify-center text-white shadow-md"
              style={{ backgroundColor: "var(--primary)" }}
            >
              <span className="material-symbols-outlined text-2xl">insights</span>
            </div>
            <div>
              <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-foreground">
                Class Performance & Analytics
              </h1>
              <p className="text-sm text-muted-foreground">
                Consolidated class performance dashboard, configurable leaderboards, and learning insights.
              </p>
            </div>
          </div>
        </div>

        {/* Tab switcher for Teachers/Admins */}
        {isTeacherOrAdmin && (
          <div className="flex items-center bg-muted/50 p-1 rounded-xl border border-border/50 shrink-0 flex-wrap">
            <button
              onClick={() => setActiveTab("class_performance")}
              className={`px-3.5 py-2 text-xs md:text-sm font-semibold rounded-lg transition-all flex items-center gap-2 ${
                activeTab === "class_performance"
                  ? "bg-background text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <span className="material-symbols-outlined text-[18px]">dashboard</span>
              Class Performance
            </button>
            <button
              onClick={() => setActiveTab("subject_analytics")}
              className={`px-3.5 py-2 text-xs md:text-sm font-semibold rounded-lg transition-all flex items-center gap-2 ${
                activeTab === "subject_analytics"
                  ? "bg-background text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <span className="material-symbols-outlined text-[18px]">menu_book</span>
              Subject & Difficulty
            </button>
            <button
              onClick={() => setActiveTab("student_inspector")}
              className={`px-3.5 py-2 text-xs md:text-sm font-semibold rounded-lg transition-all flex items-center gap-2 ${
                activeTab === "student_inspector"
                  ? "bg-background text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <span className="material-symbols-outlined text-[18px]">badge</span>
              Student Inspector
            </button>
            <button
              onClick={() => setActiveTab("my_learning")}
              className={`px-3.5 py-2 text-xs md:text-sm font-semibold rounded-lg transition-all flex items-center gap-2 ${
                activeTab === "my_learning"
                  ? "bg-background text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <span className="material-symbols-outlined text-[18px]">person</span>
              My Profile
            </button>
          </div>
        )}
      </div>

      {/* ── TEACHER / ADMIN VIEW: CLASS PERFORMANCE DASHBOARD (Step 10.13) ── */}
      {isTeacherOrAdmin && activeTab === "class_performance" && (
        <div className="space-y-8 animate-in fade-in duration-300">
          {/* Subject Selector Bar */}
          <div className="bg-card border border-border/60 rounded-2xl p-5 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <span className="text-sm font-semibold text-foreground">Select Subject:</span>
              <Select
                value={selectedSubjectId}
                onValueChange={(val) => setSelectedSubjectId(val)}
              >
                <SelectTrigger className="w-[280px] bg-background">
                  <SelectValue placeholder="Choose a subject..." />
                </SelectTrigger>
                <SelectContent>
                  {subjects.map((s) => (
                    <SelectItem key={s.subject_id} value={s.subject_id}>
                      {s.subject_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <Button
              variant="outline"
              size="sm"
              onClick={() => loadClassPerformanceData(selectedSubjectId)}
              disabled={loadingClassPerf}
              className="gap-2"
            >
              <span className="material-symbols-outlined text-[16px]">refresh</span>
              Refresh Dashboard
            </Button>
          </div>

          {loadingClassPerf ? (
            <div className="py-16 text-center text-muted-foreground flex flex-col items-center justify-center gap-3">
              <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin" />
              <p className="text-sm font-medium">Aggregating class performance and leaderboard metrics...</p>
            </div>
          ) : classPerfError ? (
            <div className="p-6 bg-destructive/10 border border-destructive/20 text-destructive rounded-2xl flex items-center gap-3">
              <span className="material-symbols-outlined">error</span>
              <span>{classPerfError}</span>
            </div>
          ) : classPerformance ? (
            <>
              {/* Overview KPI Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
                <div className="bg-card border border-border/60 rounded-2xl p-5 shadow-sm space-y-2">
                  <div className="flex items-center justify-between text-muted-foreground">
                    <span className="text-xs font-semibold uppercase tracking-wider">Class Participation</span>
                    <span className="material-symbols-outlined text-primary text-xl">groups</span>
                  </div>
                  <div className="text-3xl font-bold text-foreground">
                    {classPerformance.participation_rate_percentage}%
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {classPerformance.participating_students} of {classPerformance.total_students} students attempted
                  </div>
                </div>

                <div className="bg-card border border-border/60 rounded-2xl p-5 shadow-sm space-y-2">
                  <div className="flex items-center justify-between text-muted-foreground">
                    <span className="text-xs font-semibold uppercase tracking-wider">Class Average</span>
                    <span className="material-symbols-outlined text-blue-500 text-xl">analytics</span>
                  </div>
                  <div className="text-3xl font-bold text-foreground">
                    {classPerformance.class_average_percentage !== null && classPerformance.class_average_percentage !== undefined
                      ? `${classPerformance.class_average_percentage}%`
                      : "—"}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    Median score: {classPerformance.class_median_percentage !== null && classPerformance.class_median_percentage !== undefined ? `${classPerformance.class_median_percentage}%` : "—"}
                  </div>
                </div>

                <div className="bg-card border border-border/60 rounded-2xl p-5 shadow-sm space-y-2">
                  <div className="flex items-center justify-between text-muted-foreground">
                    <span className="text-xs font-semibold uppercase tracking-wider">Class Pass Rate</span>
                    <span className="material-symbols-outlined text-emerald-500 text-xl">check_circle</span>
                  </div>
                  <div className="text-3xl font-bold text-emerald-600 dark:text-emerald-400">
                    {classPerformance.class_pass_rate_percentage !== null && classPerformance.class_pass_rate_percentage !== undefined
                      ? `${classPerformance.class_pass_rate_percentage}%`
                      : "—"}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    Across {classPerformance.completed_evaluations} completed evaluations
                  </div>
                </div>

                <div className="bg-card border border-border/60 rounded-2xl p-5 shadow-sm space-y-2">
                  <div className="flex items-center justify-between text-muted-foreground">
                    <span className="text-xs font-semibold uppercase tracking-wider">Pending Grading</span>
                    <span className="material-symbols-outlined text-amber-500 text-xl">pending_actions</span>
                  </div>
                  <div className={`text-3xl font-bold ${classPerformance.total_pending_manual_grading > 0 ? "text-amber-600 dark:text-amber-400" : "text-foreground"}`}>
                    {classPerformance.total_pending_manual_grading}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {classPerformance.total_pending_manual_grading > 0 ? "Requires teacher manual grading" : "All evaluations up to date"}
                  </div>
                </div>
              </div>

              {/* Assessment Performance Grid & Quick Leaderboard Controls */}
              <div className="bg-card border border-border/60 rounded-2xl p-6 shadow-sm space-y-4">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <div>
                    <h2 className="text-lg font-bold text-foreground flex items-center gap-2">
                      <span className="material-symbols-outlined text-primary">quiz</span>
                      Assessment Performance & Leaderboard Settings
                    </h2>
                    <p className="text-xs text-muted-foreground">
                      Overview of assessments, average scores, and leaderboard ranking configuration.
                    </p>
                  </div>
                </div>

                {classPerformance.assessment_summaries.length === 0 ? (
                  <p className="py-8 text-center text-xs text-muted-foreground">No assessments created for this subject yet.</p>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs text-foreground">
                      <thead className="bg-muted/40 text-muted-foreground uppercase text-[10px] font-semibold border-b border-border/40">
                        <tr>
                          <th className="py-3 px-4">Assessment Title</th>
                          <th className="py-3 px-3">Status</th>
                          <th className="py-3 px-3">Participants</th>
                          <th className="py-3 px-3">Average %</th>
                          <th className="py-3 px-3">Median %</th>
                          <th className="py-3 px-3">Pass Rate</th>
                          <th className="py-3 px-3">Pending</th>
                          <th className="py-3 px-4 text-right">Leaderboard</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border/30">
                        {classPerformance.assessment_summaries.map((asm) => (
                          <tr key={asm.assessment_id} className="hover:bg-muted/20 transition-colors">
                            <td className="py-3 px-4 font-semibold text-sm">
                              <Link
                                href={`/classroom/assessments/${asm.assessment_id}`}
                                className="text-foreground hover:text-primary transition-colors flex items-center gap-1.5"
                              >
                                {asm.title}
                                <span className="material-symbols-outlined text-[14px] text-muted-foreground">open_in_new</span>
                              </Link>
                            </td>
                            <td className="py-3 px-3">
                              <Badge variant="outline" className="text-[10px] capitalize">
                                {asm.status}
                              </Badge>
                            </td>
                            <td className="py-3 px-3 font-mono">{asm.participants}</td>
                            <td className="py-3 px-3 font-semibold text-primary">
                              {asm.average_percentage !== null ? `${asm.average_percentage}%` : "—"}
                            </td>
                            <td className="py-3 px-3 font-mono">
                              {asm.median_percentage !== null ? `${asm.median_percentage}%` : "—"}
                            </td>
                            <td className="py-3 px-3 font-semibold text-emerald-600 dark:text-emerald-400">
                              {asm.pass_rate_percentage !== null ? `${asm.pass_rate_percentage}%` : "—"}
                            </td>
                            <td className="py-3 px-3">
                              {asm.pending_grading > 0 ? (
                                <Badge className="bg-amber-500/15 text-amber-600 dark:text-amber-400 text-[10px]">
                                  {asm.pending_grading} pending
                                </Badge>
                              ) : (
                                <span className="text-muted-foreground">0</span>
                              )}
                            </td>
                            <td className="py-3 px-4 text-right">
                              <Button
                                size="sm"
                                variant={asm.leaderboard_enabled ? "default" : "outline"}
                                onClick={() => handleQuickToggleLeaderboard(asm.assessment_id, asm.leaderboard_enabled)}
                                disabled={togglingLeaderboardId === asm.assessment_id}
                                className={`text-[11px] h-7 px-2.5 rounded-lg gap-1.5 font-semibold ${
                                  asm.leaderboard_enabled
                                    ? "bg-emerald-600 hover:bg-emerald-700 text-white"
                                    : "text-muted-foreground"
                                }`}
                              >
                                {togglingLeaderboardId === asm.assessment_id ? (
                                  <div className="w-3 h-3 border-2 border-t-transparent border-current rounded-full animate-spin" />
                                ) : (
                                  <span className="material-symbols-outlined text-[14px]">
                                    {asm.leaderboard_enabled ? "trophy" : "toggle_off"}
                                  </span>
                                )}
                                {asm.leaderboard_enabled ? "Enabled" : "Disabled"}
                              </Button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>

              {/* Student Performance Roster Table */}
              <div className="bg-card border border-border/60 rounded-2xl p-6 shadow-sm space-y-4">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  <div>
                    <h2 className="text-lg font-bold text-foreground flex items-center gap-2">
                      <span className="material-symbols-outlined text-primary">groups</span>
                      Student Performance Roster ({filteredRoster.length} students)
                    </h2>
                    <p className="text-xs text-muted-foreground">
                      Consolidated student roster performance and completion statuses.
                    </p>
                  </div>

                  <div className="flex flex-col sm:flex-row sm:items-center gap-2.5">
                    <Input
                      placeholder="Search student by name or email..."
                      value={rosterSearch}
                      onChange={(e) => setRosterSearch(e.target.value)}
                      className="w-full sm:w-[220px] h-8 text-xs bg-background"
                    />

                    <Select value={rosterStatusFilter} onValueChange={setRosterStatusFilter}>
                      <SelectTrigger className="w-full sm:w-[160px] h-8 text-xs bg-background">
                        <SelectValue placeholder="Filter by status..." />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">All Statuses</SelectItem>
                        <SelectItem value="passing">Passing</SelectItem>
                        <SelectItem value="below">Below Threshold</SelectItem>
                        <SelectItem value="pending">Pending Review</SelectItem>
                        <SelectItem value="none">No Submissions</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                {filteredRoster.length === 0 ? (
                  <p className="py-8 text-center text-xs text-muted-foreground">No students match your filter criteria.</p>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs text-foreground">
                      <thead className="bg-muted/40 text-muted-foreground uppercase text-[10px] font-semibold border-b border-border/40">
                        <tr>
                          <th className="py-3 px-4">Student</th>
                          <th className="py-3 px-3">Completed</th>
                          <th className="py-3 px-3">Average %</th>
                          <th className="py-3 px-3">Best %</th>
                          <th className="py-3 px-3">Latest %</th>
                          <th className="py-3 px-3">Passed</th>
                          <th className="py-3 px-4 text-right">Status</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border/30">
                        {filteredRoster.map((std) => (
                          <tr key={std.student_id} className="hover:bg-muted/20 transition-colors">
                            <td className="py-3 px-4">
                              <div className="font-semibold text-sm text-foreground">{std.student_name}</div>
                              {std.student_email && (
                                <div className="text-[10px] text-muted-foreground">{std.student_email}</div>
                              )}
                            </td>
                            <td className="py-3 px-3 font-mono">{std.assessments_completed}</td>
                            <td className="py-3 px-3 font-bold text-primary">
                              {std.average_percentage !== null ? `${std.average_percentage}%` : "—"}
                            </td>
                            <td className="py-3 px-3 font-semibold text-amber-600 dark:text-amber-400">
                              {std.best_percentage !== null ? `${std.best_percentage}%` : "—"}
                            </td>
                            <td className="py-3 px-3 font-mono">
                              {std.latest_percentage !== null ? `${std.latest_percentage}%` : "—"}
                            </td>
                            <td className="py-3 px-3 font-semibold text-emerald-600 dark:text-emerald-400">
                              {std.passed_count}
                            </td>
                            <td className="py-3 px-4 text-right">
                              <Badge
                                className={`text-[10px] font-semibold px-2 py-0.5 ${
                                  std.status_label === "Passing"
                                    ? "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30"
                                    : std.status_label === "Below Passing Threshold"
                                    ? "bg-rose-500/15 text-rose-600 dark:text-rose-400 border border-rose-500/30"
                                    : std.status_label === "Pending Review"
                                    ? "bg-amber-500/15 text-amber-600 dark:text-amber-400 border border-amber-500/30"
                                    : "bg-muted/50 text-muted-foreground border border-border/40"
                                }`}
                              >
                                {std.status_label}
                              </Badge>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </>
          ) : null}
        </div>
      )}

      {/* ── TEACHER / ADMIN VIEW: SUBJECT ANALYTICS & QUESTION DIFFICULTY ── */}
      {isTeacherOrAdmin && activeTab === "subject_analytics" && (
        <div className="space-y-8 animate-in fade-in duration-300">
          {/* Subject Selector Bar */}
          <div className="bg-card border border-border/60 rounded-2xl p-5 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <span className="text-sm font-semibold text-foreground">Select Subject:</span>
              <Select
                value={selectedSubjectId}
                onValueChange={(val) => setSelectedSubjectId(val)}
              >
                <SelectTrigger className="w-[280px] bg-background">
                  <SelectValue placeholder="Choose a subject..." />
                </SelectTrigger>
                <SelectContent>
                  {subjects.map((s) => (
                    <SelectItem key={s.subject_id} value={s.subject_id}>
                      {s.subject_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <Button
              variant="outline"
              size="sm"
              onClick={() => loadSubjectData(selectedSubjectId)}
              disabled={loadingSubject}
              className="gap-2"
            >
              <span className="material-symbols-outlined text-[16px]">refresh</span>
              Refresh Data
            </Button>
          </div>

          {loadingSubject ? (
            <div className="py-16 text-center text-muted-foreground flex flex-col items-center justify-center gap-3">
              <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin" />
              <p className="text-sm font-medium">Analyzing subject performance and question difficulty...</p>
            </div>
          ) : subjectError ? (
            <div className="p-6 bg-destructive/10 border border-destructive/20 text-destructive rounded-2xl flex items-center gap-3">
              <span className="material-symbols-outlined">error</span>
              <span>{subjectError}</span>
            </div>
          ) : subjectAnalytics ? (
            <>
              {/* Subject KPIs */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
                <div className="bg-card border border-border/60 rounded-2xl p-5 shadow-sm space-y-2">
                  <div className="flex items-center justify-between text-muted-foreground">
                    <span className="text-xs font-semibold uppercase tracking-wider">Total Assessments</span>
                    <span className="material-symbols-outlined text-primary text-xl">quiz</span>
                  </div>
                  <div className="text-2xl font-bold text-foreground">
                    {subjectAnalytics.total_assessments}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {subjectAnalytics.total_evaluations_completed} student submissions evaluated
                  </div>
                </div>

                <div className="bg-card border border-border/60 rounded-2xl p-5 shadow-sm space-y-2">
                  <div className="flex items-center justify-between text-muted-foreground">
                    <span className="text-xs font-semibold uppercase tracking-wider">Subject Average</span>
                    <span className="material-symbols-outlined text-primary text-xl">analytics</span>
                  </div>
                  <div className="text-2xl font-bold text-foreground">
                    {subjectAnalytics.average_subject_percentage !== null
                      ? `${subjectAnalytics.average_subject_percentage}%`
                      : "—"}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    Combined average across all assessments
                  </div>
                </div>

                <div className="bg-card border border-border/60 rounded-2xl p-5 shadow-sm space-y-2">
                  <div className="flex items-center justify-between text-muted-foreground">
                    <span className="text-xs font-semibold uppercase tracking-wider">Pass Rate</span>
                    <span className="material-symbols-outlined text-emerald-500 text-xl">check_circle</span>
                  </div>
                  <div className="text-2xl font-bold text-emerald-600 dark:text-emerald-400">
                    {subjectAnalytics.pass_rate_percentage !== null
                      ? `${subjectAnalytics.pass_rate_percentage}%`
                      : "—"}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    Passing marks threshold achieved
                  </div>
                </div>

                <div className="bg-card border border-border/60 rounded-2xl p-5 shadow-sm space-y-2">
                  <div className="flex items-center justify-between text-muted-foreground">
                    <span className="text-xs font-semibold uppercase tracking-wider">Participation</span>
                    <span className="material-symbols-outlined text-amber-500 text-xl">group</span>
                  </div>
                  <div className="text-2xl font-bold text-foreground">
                    {subjectAnalytics.total_students_attempted} / {subjectAnalytics.total_students_enrolled}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    Students attempted at least one assessment
                  </div>
                </div>
              </div>

              {/* Observed Question Difficulty Summary Card */}
              {questionDifficulty && (
                <div className="bg-card border border-border/60 rounded-2xl p-6 shadow-sm space-y-6">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    <div>
                      <h2 className="text-lg font-bold text-foreground flex items-center gap-2">
                        <span className="material-symbols-outlined text-primary">psychology</span>
                        Question Difficulty Analytics (Empirical)
                      </h2>
                      <p className="text-xs text-muted-foreground">
                        Observed student accuracy across {questionDifficulty.total_questions_analyzed} questions in this subject.
                      </p>
                    </div>

                    {/* Difficulty Distribution Pills */}
                    <div className="flex items-center gap-2 flex-wrap">
                      <Badge className="bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30 text-xs px-2.5 py-1 font-semibold">
                        {questionDifficulty.easier_count} Easier
                      </Badge>
                      <Badge className="bg-amber-500/15 text-amber-600 dark:text-amber-400 border border-amber-500/30 text-xs px-2.5 py-1 font-semibold">
                        {questionDifficulty.moderate_count} Moderate
                      </Badge>
                      <Badge className="bg-rose-500/15 text-rose-600 dark:text-rose-400 border border-rose-500/30 text-xs px-2.5 py-1 font-semibold">
                        {questionDifficulty.harder_count} Harder
                      </Badge>
                      <Badge className="bg-slate-500/15 text-slate-600 dark:text-slate-400 border border-slate-500/30 text-xs px-2.5 py-1 font-medium">
                        {questionDifficulty.insufficient_sample_count} Insufficient Data
                      </Badge>
                    </div>
                  </div>

                  {/* Filter & Search Bar */}
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-2">
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-muted-foreground">Band:</span>
                      <Select value={difficultyFilter} onValueChange={setDifficultyFilter}>
                        <SelectTrigger className="w-[180px] h-8 text-xs bg-background">
                          <SelectValue placeholder="All Bands" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="all">All Bands</SelectItem>
                          <SelectItem value="harder_observed">Harder Observed (&lt;50%)</SelectItem>
                          <SelectItem value="moderate_observed">Moderate (50-75%)</SelectItem>
                          <SelectItem value="easier_observed">Easier (&gt;75%)</SelectItem>
                          <SelectItem value="insufficient_sample">Insufficient Sample (&lt;3)</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>

                    <Input
                      placeholder="Search question text..."
                      value={difficultySearch}
                      onChange={(e) => setDifficultySearch(e.target.value)}
                      className="w-full sm:w-[240px] h-8 text-xs bg-background"
                    />
                  </div>

                  {/* Question Difficulty Table */}
                  <div className="overflow-x-auto border border-border/40 rounded-xl">
                    <table className="w-full text-left text-xs text-foreground">
                      <thead className="bg-muted/40 text-muted-foreground uppercase text-[10px] font-semibold border-b border-border/40">
                        <tr>
                          <th className="py-3 px-4">Question</th>
                          <th className="py-3 px-3">Type</th>
                          <th className="py-3 px-3">Evaluated</th>
                          <th className="py-3 px-3">Correct / Total</th>
                          <th className="py-3 px-3">Accuracy</th>
                          <th className="py-3 px-4 text-right">Difficulty Classification</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border/30">
                        {filteredQuestions.length === 0 ? (
                          <tr>
                            <td colSpan={6} className="py-8 text-center text-muted-foreground">
                              No questions found matching your filter criteria.
                            </td>
                          </tr>
                        ) : (
                          filteredQuestions.map((q) => (
                            <tr key={q.question_id} className="hover:bg-muted/20 transition-colors">
                              <td className="py-3 px-4 max-w-sm">
                                <div className="font-semibold text-foreground line-clamp-2">
                                  {q.question_text}
                                </div>
                                <div className="text-[10px] text-muted-foreground mt-0.5">
                                  {q.marks_available} marks available
                                </div>
                              </td>
                              <td className="py-3 px-3">
                                <Badge variant="outline" className="text-[10px] uppercase font-mono">
                                  {q.question_type.replace("_", " ")}
                                </Badge>
                              </td>
                              <td className="py-3 px-3 font-mono">{q.evaluated_count}</td>
                              <td className="py-3 px-3">
                                <span className="text-emerald-600 font-semibold">{q.correct_count}</span>
                                <span className="text-muted-foreground"> / {q.evaluated_count}</span>
                                {q.pending_count > 0 && (
                                  <span className="text-[10px] text-amber-500 block">
                                    +{q.pending_count} pending
                                  </span>
                                )}
                              </td>
                              <td className="py-3 px-3 font-bold">
                                {q.accuracy_percentage !== null && q.accuracy_percentage !== undefined ? (
                                  <span
                                    className={
                                      q.accuracy_percentage >= 75
                                        ? "text-emerald-600"
                                        : q.accuracy_percentage >= 50
                                        ? "text-amber-600"
                                        : "text-rose-600"
                                    }
                                  >
                                    {q.accuracy_percentage}%
                                  </span>
                                ) : (
                                  <span className="text-muted-foreground">—</span>
                                )}
                              </td>
                              <td className="py-3 px-4 text-right">
                                {getDifficultyBadge(q.difficulty_band, q.difficulty_label)}
                              </td>
                            </tr>
                          ))
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </>
          ) : null}
        </div>
      )}

      {/* ── TEACHER / ADMIN VIEW: STUDENT INSPECTOR ── */}
      {isTeacherOrAdmin && activeTab === "student_inspector" && (
        <div className="space-y-8 animate-in fade-in duration-300">
          {/* Student Selector Bar */}
          <div className="bg-card border border-border/60 rounded-2xl p-5 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="flex flex-col sm:flex-row sm:items-center gap-3 w-full md:w-auto">
              <span className="text-sm font-semibold text-foreground shrink-0">Inspect Student:</span>
              <Select
                value={selectedStudentId}
                onValueChange={(val) => setSelectedStudentId(val)}
              >
                <SelectTrigger className="w-full sm:w-[320px] bg-background">
                  <SelectValue placeholder="Choose a student..." />
                </SelectTrigger>
                <SelectContent className="max-h-64">
                  {filteredMembers.length === 0 ? (
                    <div className="p-3 text-xs text-muted-foreground text-center">
                      No enrolled students found.
                    </div>
                  ) : (
                    filteredMembers.map((m) => (
                      <SelectItem key={m.user_id} value={m.user_id}>
                        {m.first_name} {m.last_name} ({m.email})
                      </SelectItem>
                    ))
                  )}
                </SelectContent>
              </Select>
            </div>

            <Button
              variant="outline"
              size="sm"
              onClick={() => loadInspectedStudent(selectedStudentId)}
              disabled={loadingInspected || !selectedStudentId}
              className="gap-2"
            >
              <span className="material-symbols-outlined text-[16px]">refresh</span>
              Reload Profile
            </Button>
          </div>

          {loadingInspected ? (
            <div className="py-16 text-center text-muted-foreground flex flex-col items-center justify-center gap-3">
              <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin" />
              <p className="text-sm font-medium">Loading student learning curve and mastery records...</p>
            </div>
          ) : inspectedError ? (
            <div className="p-6 bg-destructive/10 border border-destructive/20 text-destructive rounded-2xl flex items-center gap-3">
              <span className="material-symbols-outlined">error</span>
              <span>{inspectedError}</span>
            </div>
          ) : inspectedStudentAnalytics ? (
            renderStudentAnalyticsDashboard(inspectedStudentAnalytics, true)
          ) : (
            <div className="py-12 text-center text-muted-foreground bg-card border border-border/40 rounded-2xl p-8">
              <span className="material-symbols-outlined text-4xl mb-2 text-muted-foreground/50">person_search</span>
              <p className="text-sm font-medium text-foreground">No student selected</p>
              <p className="text-xs text-muted-foreground mt-1">
                Select an enrolled student from the dropdown above to inspect their longitudinal performance, score curve, and question accuracy.
              </p>
            </div>
          )}
        </div>
      )}

      {/* ── STUDENT VIEW / MY LEARNING PROFILE ── */}
      {(!isTeacherOrAdmin || activeTab === "my_learning") && (
        <div className="space-y-8 animate-in fade-in duration-300">
          {loadingStudent ? (
            <div className="py-16 text-center text-muted-foreground flex flex-col items-center justify-center gap-3">
              <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin" />
              <p className="text-sm font-medium">Loading your personalized learning progression...</p>
            </div>
          ) : studentError ? (
            <div className="p-6 bg-destructive/10 border border-destructive/20 text-destructive rounded-2xl flex items-center gap-3">
              <span className="material-symbols-outlined">error</span>
              <span>{studentError}</span>
            </div>
          ) : studentAnalytics ? (
            <>
              {renderStudentAnalyticsDashboard(studentAnalytics, false)}
              {/* Privacy Notice Card */}
              <div className="p-4 rounded-2xl bg-muted/30 border border-border/40 flex items-center gap-3 text-xs text-muted-foreground">
                <span className="material-symbols-outlined text-primary text-[20px]">shield</span>
                <span>
                  <strong>Privacy Protected:</strong> Your learning analytics and performance history are strictly private to you and your assigned instructors. Peer comparisons and class rankings are not displayed.
                </span>
              </div>
            </>
          ) : null}
        </div>
      )}
    </div>
  );
}
