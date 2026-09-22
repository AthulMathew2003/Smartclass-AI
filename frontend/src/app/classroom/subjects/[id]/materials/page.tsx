"use client";

import React, { useEffect, useState, useCallback } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import {
  SubjectMaterial,
  fetchSubjectMaterials,
  requestMaterialUploadUrl,
  confirmMaterialUpload,
  updateSubjectMaterial,
  archiveSubjectMaterial,
  getMaterialDownloadUrl,
  uploadFileToS3,
  formatFileSize,
  getMaterialIcon,
  isBrowserViewable,
  MATERIAL_CATEGORIES,
} from "@/lib/materials";
import { fetchSubject, Subject } from "@/lib/subjects";
import { usePermissions } from "@/lib/permissions";
import ForbiddenState from "../../../components/ForbiddenState";
import MaterialViewerModal from "../../../components/MaterialViewerModal";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

export default function SubjectMaterialsPage() {
  const params = useParams();
  const id = params?.id as string;
  const searchParams = useSearchParams();
  const workspaceIdFromQuery = searchParams.get("workspace_id");
  const router = useRouter();

  const { hasPermission, isLoaded: permLoaded } = usePermissions();

  const [subject, setSubject] = useState<Subject | null>(null);
  const [materials, setMaterials] = useState<SubjectMaterial[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isForbidden, setIsForbidden] = useState(false);

  // Filters & Search
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<string>("all");

  // Modals & Active Material State
  const [previewMaterial, setPreviewMaterial] = useState<SubjectMaterial | null>(null);

  // Upload Modal State
  const [uploadOpen, setUploadOpen] = useState(false);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadTitle, setUploadTitle] = useState("");
  const [uploadDescription, setUploadDescription] = useState("");
  const [uploadCategory, setUploadCategory] = useState<string>("Notes");
  const [uploadProgress, setUploadProgress] = useState<number | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);

  // Edit Modal State
  const [editOpen, setEditDialogOpen] = useState(false);
  const [editingMaterial, setEditingMaterial] = useState<SubjectMaterial | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [editDescription, setEditDescription] = useState("");
  const [editCategory, setEditCategory] = useState("Notes");
  const [editError, setEditError] = useState<string | null>(null);
  const [savingEdit, setSavingEdit] = useState(false);

  // Archive Modal State
  const [archiveOpen, setArchiveOpen] = useState(false);
  const [materialToArchive, setMaterialToArchive] = useState<SubjectMaterial | null>(null);
  const [archiving, setArchiving] = useState(false);

  const canCreate = hasPermission("subject.material.create");
  const canUpdate = hasPermission("subject.material.update");
  const canDelete = hasPermission("subject.material.delete");
  const isTeacherOrAdmin = canCreate || canUpdate || canDelete;

  const loadData = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    setIsForbidden(false);

    try {
      const [subjData, matsData] = await Promise.all([
        fetchSubject(id, workspaceIdFromQuery || undefined),
        fetchSubjectMaterials(id, {
          category: selectedCategory !== "all" ? selectedCategory : undefined,
          search: searchQuery.trim() || undefined,
        }),
      ]);
      setSubject(subjData);
      setMaterials(matsData);
    } catch (err: any) {
      const msg = err?.message || "Failed to load course materials.";
      if (
        msg.toLowerCase().includes("permission") ||
        msg.toLowerCase().includes("denied") ||
        msg.includes("403")
      ) {
        setIsForbidden(true);
      } else {
        setError(msg);
      }
    } finally {
      setLoading(false);
    }
  }, [id, workspaceIdFromQuery, selectedCategory, searchQuery]);

  useEffect(() => {
    if (permLoaded && hasPermission("subject.material.read")) {
      loadData();
    }
  }, [permLoaded, loadData, hasPermission]);

  // Direct file download trigger helper
  const handleDownload = async (mat: SubjectMaterial) => {
    try {
      const res = await getMaterialDownloadUrl(mat.subject_id, mat.material_id);
      try {
        const response = await fetch(res.download_url);
        const blob = await response.blob();
        const blobUrl = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = blobUrl;
        a.download = mat.original_filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(blobUrl);
      } catch {
        const a = document.createElement("a");
        a.href = res.download_url;
        a.target = "_blank";
        a.download = mat.original_filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
      }
    } catch (err: any) {
      alert(err?.message || "Failed to download course material.");
    }
  };

  // Upload handler
  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setUploadFile(file);
      if (!uploadTitle.trim()) {
        const nameWithoutExt = file.name.substring(0, file.name.lastIndexOf(".")) || file.name;
        setUploadTitle(nameWithoutExt);
      }
      setUploadError(null);
    }
  };

  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!uploadFile) {
      setUploadError("Please select a file to upload.");
      return;
    }
    if (!uploadTitle.trim()) {
      setUploadError("Material title is required.");
      return;
    }

    setUploading(true);
    setUploadError(null);
    setUploadProgress(0);

    try {
      const contentType = uploadFile.type || "application/octet-stream";

      // 1. Request presigned upload URL from backend
      const presigned = await requestMaterialUploadUrl(id, {
        title: uploadTitle.trim(),
        description: uploadDescription.trim() || undefined,
        category: uploadCategory,
        original_filename: uploadFile.name,
        content_type: contentType,
        file_size: uploadFile.size,
      });

      // 2. Direct S3 upload with progress
      await uploadFileToS3(presigned.upload_url, uploadFile, contentType, (pct) => {
        setUploadProgress(pct);
      });

      // 3. Confirm upload on backend to mark active
      await confirmMaterialUpload(id, presigned.material_id, {
        s3_key: presigned.s3_key,
      });

      // Reset and reload
      setUploadOpen(false);
      setUploadFile(null);
      setUploadTitle("");
      setUploadDescription("");
      setUploadCategory("Notes");
      setUploadProgress(null);
      await loadData();
    } catch (err: any) {
      setUploadError(err?.message || "Upload failed. Please check file format and try again.");
    } finally {
      setUploading(false);
      setUploadProgress(null);
    }
  };

  // Edit handler
  const handleEditClick = (mat: SubjectMaterial) => {
    setEditingMaterial(mat);
    setEditTitle(mat.title);
    setEditDescription(mat.description || "");
    setEditCategory(mat.category);
    setEditError(null);
    setEditDialogOpen(true);
  };

  const handleEditSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingMaterial) return;
    if (!editTitle.trim()) {
      setEditError("Title is required.");
      return;
    }

    setSavingEdit(true);
    setEditError(null);
    try {
      await updateSubjectMaterial(id, editingMaterial.material_id, {
        title: editTitle.trim(),
        description: editDescription.trim() || undefined,
        category: editCategory,
      });
      setEditDialogOpen(false);
      setEditingMaterial(null);
      await loadData();
    } catch (err: any) {
      setEditError(err?.message || "Failed to update material metadata.");
    } finally {
      setSavingEdit(false);
    }
  };

  // Archive handler
  const handleArchiveConfirm = async () => {
    if (!materialToArchive) return;
    setArchiving(true);
    try {
      await archiveSubjectMaterial(id, materialToArchive.material_id);
      setArchiveOpen(false);
      setMaterialToArchive(null);
      await loadData();
    } catch (err: any) {
      alert(err?.message || "Failed to archive material.");
    } finally {
      setArchiving(false);
    }
  };

  if (!permLoaded || loading) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <div className="flex items-center gap-3 text-sm font-semibold text-muted-foreground">
          <div className="w-6 h-6 border-2 border-t-transparent border-primary rounded-full animate-spin" />
          Loading course materials...
        </div>
      </div>
    );
  }

  if (!hasPermission("subject.material.read") || isForbidden) {
    return <ForbiddenState message="You do not have permission to access course materials for this subject." />;
  }

  if (error || !subject) {
    return (
      <div className="p-6 max-w-6xl mx-auto space-y-4">
        <div className="p-4 rounded-xl bg-destructive/10 text-destructive text-sm border border-destructive/20">
          {error || "Subject not found"}
        </div>
        <Button variant="outline" onClick={() => router.push("/classroom/subjects")}>
          &larr; Back to Subjects
        </Button>
      </div>
    );
  }

  const isSubjectArchived = subject.subject_status === "archived";

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Navigation Breadcrumbs */}
      <div className="flex items-center gap-2 text-xs font-semibold text-muted-foreground">
        <Link href="/classroom/subjects" className="hover:text-primary transition-colors">
          Subjects
        </Link>
        <span>/</span>
        <Link
          href={workspaceIdFromQuery ? `/classroom/subjects/${id}?workspace_id=${workspaceIdFromQuery}` : `/classroom/subjects/${id}`}
          className="hover:text-primary transition-colors"
        >
          {subject.subject_name}
        </Link>
        <span>/</span>
        <span className="text-foreground">Course Materials</span>
      </div>

      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-6 rounded-2xl bg-[var(--surface-container-low)] border border-[var(--outline-variant)]">
        <div>
          <div className="flex items-center gap-3">
            <span className="material-symbols-outlined text-[32px] text-primary">folder_open</span>
            <div>
              <h1 className="text-2xl font-black tracking-tight text-foreground">Course Materials</h1>
              <p className="text-xs text-muted-foreground mt-0.5">
                Reference resources, lecture slides, and notes for <strong className="text-foreground">{subject.subject_name}</strong>
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2.5">
          {canCreate && !isSubjectArchived && (
            <Button
              onClick={() => {
                setUploadError(null);
                setUploadOpen(true);
              }}
              className="bg-primary text-white font-bold shadow-xs hover:opacity-90 gap-1.5 cursor-pointer"
            >
              <span className="material-symbols-outlined text-[18px]">upload_file</span>
              Upload Material
            </Button>
          )}
        </div>
      </div>

      {/* Filters and Search Bar */}
      <div className="flex flex-col sm:flex-row items-center gap-3 justify-between">
        <div className="flex items-center gap-2 w-full sm:w-auto overflow-x-auto pb-1 sm:pb-0">
          <Button
            size="sm"
            variant={selectedCategory === "all" ? "default" : "outline"}
            onClick={() => setSelectedCategory("all")}
            className="rounded-full text-xs font-semibold h-8"
          >
            All Categories
          </Button>
          {MATERIAL_CATEGORIES.map((cat) => (
            <Button
              key={cat}
              size="sm"
              variant={selectedCategory === cat ? "default" : "outline"}
              onClick={() => setSelectedCategory(cat)}
              className="rounded-full text-xs font-semibold h-8 shrink-0"
            >
              {cat}
            </Button>
          ))}
        </div>

        <div className="relative w-full sm:w-72">
          <span className="material-symbols-outlined absolute left-3 top-2.5 text-muted-foreground text-[18px]">
            search
          </span>
          <Input
            placeholder="Search materials..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9 h-9 text-xs"
          />
        </div>
      </div>

      {/* Material Grid / Cards */}
      {materials.length === 0 ? (
        <div className="p-12 text-center rounded-2xl border border-dashed border-[var(--outline-variant)] bg-[var(--surface-container-lowest)] space-y-4">
          <span className="material-symbols-outlined text-[56px] text-muted-foreground opacity-40">
            auto_stories
          </span>
          <div>
            <h3 className="text-base font-bold text-foreground">No Course Materials Found</h3>
            <p className="text-xs text-muted-foreground max-w-sm mx-auto mt-1">
              {searchQuery || selectedCategory !== "all"
                ? "No materials matched your filter criteria. Try clearing search filters."
                : "No course materials or lecture notes have been published for this subject yet."}
            </p>
          </div>
          {canCreate && !isSubjectArchived && !searchQuery && selectedCategory === "all" && (
            <Button
              size="sm"
              onClick={() => setUploadOpen(true)}
              className="bg-primary text-white font-semibold text-xs gap-1.5"
            >
              <span className="material-symbols-outlined text-[16px]">upload_file</span>
              Upload First Material
            </Button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {materials.map((mat) => {
            const icon = getMaterialIcon(mat.original_filename, mat.content_type);
            const viewable = isBrowserViewable(mat.original_filename, mat.content_type);

            return (
              <div
                key={mat.material_id}
                className="group p-5 rounded-2xl border border-[var(--outline-variant)] bg-[var(--surface-container-lowest)] hover:border-primary/50 transition-all flex flex-col justify-between shadow-xs hover:shadow-md"
              >
                <div>
                  <div className="flex items-start justify-between gap-3 mb-3">
                    <div className="flex items-center gap-3 truncate">
                      <div className="w-10 h-10 rounded-xl bg-primary/10 text-primary flex items-center justify-center shrink-0">
                        <span className="material-symbols-outlined text-[24px]">{icon}</span>
                      </div>
                      <div className="truncate">
                        <h4
                          onClick={() => viewable && setPreviewMaterial(mat)}
                          className={`font-bold text-sm text-foreground truncate ${
                            viewable ? "hover:text-primary cursor-pointer transition-colors" : ""
                          }`}
                          title={mat.title}
                        >
                          {mat.title}
                        </h4>
                        <p className="text-[11px] text-muted-foreground font-mono truncate">
                          {mat.original_filename}
                        </p>
                      </div>
                    </div>

                    <Badge variant="outline" className="text-[10px] font-bold uppercase shrink-0">
                      {mat.category}
                    </Badge>
                  </div>

                  {mat.description && (
                    <p className="text-xs text-muted-foreground line-clamp-2 mb-4 leading-relaxed">
                      {mat.description}
                    </p>
                  )}
                </div>

                <div className="pt-3 border-t border-[var(--outline-variant)] flex items-center justify-between mt-2">
                  <div className="text-[10px] text-muted-foreground">
                    <p className="font-semibold text-foreground font-mono">
                      {formatFileSize(mat.file_size)}
                    </p>
                    <p>
                      {new Date(mat.created_at).toLocaleDateString()}
                      {mat.uploaded_by?.first_name ? ` • by ${mat.uploaded_by.first_name}` : ""}
                    </p>
                  </div>

                  <div className="flex items-center gap-1">
                    {viewable && (
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => setPreviewMaterial(mat)}
                        title="View / Preview file"
                        className="h-8 px-2.5 text-xs font-bold text-primary hover:bg-primary/10 cursor-pointer gap-1"
                      >
                        <span className="material-symbols-outlined text-[16px]">visibility</span>
                        View
                      </Button>
                    )}

                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => handleDownload(mat)}
                      title="Download file"
                      className="h-8 px-2.5 text-xs font-bold text-muted-foreground hover:text-foreground cursor-pointer gap-1"
                    >
                      <span className="material-symbols-outlined text-[16px]">download</span>
                      Download
                    </Button>

                    {isTeacherOrAdmin && !isSubjectArchived && (
                      <>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => handleEditClick(mat)}
                          title="Edit metadata"
                          className="h-8 w-8 p-0 text-muted-foreground hover:text-foreground cursor-pointer"
                        >
                          <span className="material-symbols-outlined text-[16px]">edit</span>
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => {
                            setMaterialToArchive(mat);
                            setArchiveOpen(true);
                          }}
                          title="Archive material"
                          className="h-8 w-8 p-0 text-destructive/80 hover:text-destructive hover:bg-destructive/10 cursor-pointer"
                        >
                          <span className="material-symbols-outlined text-[16px]">archive</span>
                        </Button>
                      </>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Upload Material Modal */}
      <Dialog open={uploadOpen} onOpenChange={setUploadOpen}>
        <DialogContent className="sm:max-w-[550px]">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <span className="material-symbols-outlined text-primary text-[22px]">upload_file</span>
              Upload Course Material
            </DialogTitle>
            <DialogDescription>
              Upload documents, slides, spreadsheets, images, or videos directly for students of this subject.
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleUploadSubmit} className="space-y-4 py-2">
            {uploadError && (
              <div className="p-3 text-xs font-semibold text-destructive bg-destructive/10 border border-destructive/20 rounded-xl">
                {uploadError}
              </div>
            )}

            {/* File Dropzone */}
            <div className="space-y-1.5">
              <Label className="text-xs font-bold">Select File *</Label>
              <div className="border-2 border-dashed border-[var(--outline-variant)] rounded-2xl p-6 text-center hover:border-primary/50 transition-colors bg-muted/10 cursor-pointer relative">
                <input
                  type="file"
                  onChange={handleFileSelect}
                  className="absolute inset-0 opacity-0 cursor-pointer"
                  disabled={uploading}
                />
                <span className="material-symbols-outlined text-[36px] text-primary/80 mb-1">
                  cloud_upload
                </span>
                {uploadFile ? (
                  <div>
                    <p className="text-xs font-bold text-foreground truncate">{uploadFile.name}</p>
                    <p className="text-[10px] text-muted-foreground font-mono mt-0.5">
                      {formatFileSize(uploadFile.size)}
                    </p>
                  </div>
                ) : (
                  <div>
                    <p className="text-xs font-bold text-foreground">Click to browse or drag & drop file</p>
                    <p className="text-[10px] text-muted-foreground mt-1">
                      PDF, DOCX, PPTX, XLSX, CSV, TXT, Images (PNG, JPG, WebP), Video (MP4, WebM), ZIP
                    </p>
                  </div>
                )}
              </div>
            </div>

            {/* Title */}
            <div className="space-y-1.5">
              <Label className="text-xs font-bold">Title *</Label>
              <Input
                placeholder="e.g. Chapter 1 - Introduction Slides"
                value={uploadTitle}
                onChange={(e) => setUploadTitle(e.target.value)}
                disabled={uploading}
                className="text-xs"
              />
            </div>

            {/* Category */}
            <div className="space-y-1.5">
              <Label className="text-xs font-bold">Category *</Label>
              <Select
                value={uploadCategory}
                onValueChange={(val) => setUploadCategory(val)}
                disabled={uploading}
              >
                <SelectTrigger className="text-xs">
                  <SelectValue placeholder="Select Category" />
                </SelectTrigger>
                <SelectContent>
                  {MATERIAL_CATEGORIES.map((cat) => (
                    <SelectItem key={cat} value={cat} className="text-xs">
                      {cat}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Description */}
            <div className="space-y-1.5">
              <Label className="text-xs font-bold">Description (Optional)</Label>
              <Textarea
                placeholder="Provide details, summary, or topics covered..."
                value={uploadDescription}
                onChange={(e) => setUploadDescription(e.target.value)}
                rows={2}
                disabled={uploading}
                className="text-xs"
              />
            </div>

            {/* Progress Bar */}
            {uploadProgress !== null && (
              <div className="space-y-1.5">
                <div className="flex justify-between text-[11px] font-bold text-muted-foreground">
                  <span>Uploading directly to storage...</span>
                  <span>{uploadProgress}%</span>
                </div>
                <div className="w-full bg-muted rounded-full h-2 overflow-hidden">
                  <div
                    className="bg-primary h-2 rounded-full transition-all duration-200"
                    style={{ width: `${uploadProgress}%` }}
                  />
                </div>
              </div>
            )}

            <DialogFooter className="pt-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => setUploadOpen(false)}
                disabled={uploading}
                className="text-xs"
              >
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={uploading || !uploadFile || !uploadTitle.trim()}
                className="bg-primary text-white font-bold text-xs gap-1.5"
              >
                {uploading ? (
                  <>
                    <div className="w-4 h-4 border-2 border-t-transparent border-white rounded-full animate-spin" />
                    Uploading...
                  </>
                ) : (
                  <>
                    <span className="material-symbols-outlined text-[16px]">cloud_upload</span>
                    Confirm & Upload
                  </>
                )}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Edit Material Modal */}
      <Dialog open={editOpen} onOpenChange={setEditDialogOpen}>
        <DialogContent className="sm:max-w-[480px]">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <span className="material-symbols-outlined text-primary text-[20px]">edit</span>
              Edit Material Details
            </DialogTitle>
            <DialogDescription>
              Update title, category, or description for this course resource.
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleEditSubmit} className="space-y-4 py-2">
            {editError && (
              <div className="p-3 text-xs font-semibold text-destructive bg-destructive/10 border border-destructive/20 rounded-xl">
                {editError}
              </div>
            )}

            <div className="space-y-1.5">
              <Label className="text-xs font-bold">Title *</Label>
              <Input
                value={editTitle}
                onChange={(e) => setEditTitle(e.target.value)}
                disabled={savingEdit}
                className="text-xs"
              />
            </div>

            <div className="space-y-1.5">
              <Label className="text-xs font-bold">Category *</Label>
              <Select
                value={editCategory}
                onValueChange={(val) => setEditCategory(val)}
                disabled={savingEdit}
              >
                <SelectTrigger className="text-xs">
                  <SelectValue placeholder="Select Category" />
                </SelectTrigger>
                <SelectContent>
                  {MATERIAL_CATEGORIES.map((cat) => (
                    <SelectItem key={cat} value={cat} className="text-xs">
                      {cat}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1.5">
              <Label className="text-xs font-bold">Description</Label>
              <Textarea
                value={editDescription}
                onChange={(e) => setEditDescription(e.target.value)}
                rows={3}
                disabled={savingEdit}
                className="text-xs"
              />
            </div>

            <DialogFooter className="pt-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => setEditDialogOpen(false)}
                disabled={savingEdit}
                className="text-xs"
              >
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={savingEdit || !editTitle.trim()}
                className="bg-primary text-white font-bold text-xs"
              >
                {savingEdit ? "Saving..." : "Save Changes"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Archive / Delete Confirmation Dialog */}
      <Dialog open={archiveOpen} onOpenChange={setArchiveOpen}>
        <DialogContent className="sm:max-w-[420px]">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-destructive">
              <span className="material-symbols-outlined text-[22px]">archive</span>
              Archive Course Material
            </DialogTitle>
            <DialogDescription>
              Are you sure you want to archive <strong>{materialToArchive?.title}</strong>? Students will no longer see this file in the materials list.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="gap-2 pt-3">
            <Button
              type="button"
              variant="outline"
              onClick={() => setArchiveOpen(false)}
              disabled={archiving}
              className="text-xs"
            >
              Cancel
            </Button>
            <Button
              type="button"
              variant="destructive"
              onClick={handleArchiveConfirm}
              disabled={archiving}
              className="font-bold text-xs"
            >
              {archiving ? "Archiving..." : "Yes, Archive"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* In-App Material Preview Modal */}
      <MaterialViewerModal
        material={previewMaterial}
        onClose={() => setPreviewMaterial(null)}
        onDownload={handleDownload}
      />
    </div>
  );
}
