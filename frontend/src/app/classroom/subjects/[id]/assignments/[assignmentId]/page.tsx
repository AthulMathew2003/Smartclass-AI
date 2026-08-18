"use client";

import React, { useEffect } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";

export default function SubjectAssignmentDetailPage() {
  const { id: subjectId, assignmentId } = useParams() as {
    id: string;
    assignmentId: string;
  };
  const searchParams = useSearchParams();
  const workspaceIdFromQuery = searchParams.get("workspace_id");
  const router = useRouter();

  useEffect(() => {
    if (assignmentId) {
      const query = new URLSearchParams();
      if (subjectId) query.set("subject_id", subjectId);
      if (workspaceIdFromQuery) query.set("workspace_id", workspaceIdFromQuery);
      router.replace(`/classroom/assignments/${assignmentId}?${query.toString()}`);
    }
  }, [assignmentId, subjectId, workspaceIdFromQuery, router]);

  return (
    <div className="flex items-center justify-center p-12 text-muted-foreground text-xs">
      Loading assignment...
    </div>
  );
}
