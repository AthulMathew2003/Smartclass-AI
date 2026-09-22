import { apiFetch } from "./api";

export interface MaterialUploader {
  user_id: string;
  email: string;
  first_name?: string | null;
  last_name?: string | null;
}

export interface SubjectMaterial {
  material_id: string;
  subject_id: string;
  title: string;
  description?: string | null;
  category: string;
  original_filename: string;
  content_type: string;
  file_size: number;
  status: "active" | "archived";
  s3_key: string;
  uploaded_by?: MaterialUploader | null;
  created_at: string;
  updated_at: string;
}

export interface MaterialUploadUrlPayload {
  title: string;
  description?: string;
  category: string;
  original_filename: string;
  content_type: string;
  file_size: number;
}

export interface MaterialUploadUrlResponse {
  material_id: string;
  s3_key: string;
  upload_url: string;
  expires_in: number;
}

export interface MaterialConfirmPayload {
  s3_key: string;
}

export interface MaterialUpdatePayload {
  title?: string;
  description?: string;
  category?: string;
}

export interface MaterialDownloadUrlResponse {
  download_url: string;
  expires_in: number;
  original_filename: string;
  content_type: string;
}

export const MATERIAL_CATEGORIES = [
  "Notes",
  "Lecture",
  "Reference",
  "Lab",
  "Study Material",
  "Assignment Material",
  "Syllabus",
  "Other",
] as const;

// ── API Methods ──────────────────────────────────────────────────

export async function fetchSubjectMaterials(
  subjectId: string,
  params?: { category?: string; search?: string; status?: string }
): Promise<SubjectMaterial[]> {
  const queryParts: string[] = [];
  if (params?.category && params.category !== "all") {
    queryParts.push(`category=${encodeURIComponent(params.category)}`);
  }
  if (params?.search && params.search.trim()) {
    queryParts.push(`search=${encodeURIComponent(params.search.trim())}`);
  }
  if (params?.status) {
    queryParts.push(`status=${encodeURIComponent(params.status)}`);
  }
  const queryString = queryParts.length > 0 ? `?${queryParts.join("&")}` : "";

  return await apiFetch<SubjectMaterial[]>(
    `/subjects/${encodeURIComponent(subjectId)}/materials${queryString}`
  );
}

export async function fetchSubjectMaterial(
  subjectId: string,
  materialId: string
): Promise<SubjectMaterial> {
  return await apiFetch<SubjectMaterial>(
    `/subjects/${encodeURIComponent(subjectId)}/materials/${encodeURIComponent(materialId)}`
  );
}

export async function requestMaterialUploadUrl(
  subjectId: string,
  payload: MaterialUploadUrlPayload
): Promise<MaterialUploadUrlResponse> {
  return await apiFetch<MaterialUploadUrlResponse>(
    `/subjects/${encodeURIComponent(subjectId)}/materials/upload-url`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    }
  );
}

export async function confirmMaterialUpload(
  subjectId: string,
  materialId: string,
  payload: MaterialConfirmPayload
): Promise<SubjectMaterial> {
  return await apiFetch<SubjectMaterial>(
    `/subjects/${encodeURIComponent(subjectId)}/materials/${encodeURIComponent(materialId)}/confirm`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    }
  );
}

export async function updateSubjectMaterial(
  subjectId: string,
  materialId: string,
  payload: MaterialUpdatePayload
): Promise<SubjectMaterial> {
  return await apiFetch<SubjectMaterial>(
    `/subjects/${encodeURIComponent(subjectId)}/materials/${encodeURIComponent(materialId)}`,
    {
      method: "PATCH",
      body: JSON.stringify(payload),
    }
  );
}

export async function archiveSubjectMaterial(
  subjectId: string,
  materialId: string
): Promise<{ message: string }> {
  return await apiFetch<{ message: string }>(
    `/subjects/${encodeURIComponent(subjectId)}/materials/${encodeURIComponent(materialId)}`,
    {
      method: "DELETE",
    }
  );
}

export async function getMaterialDownloadUrl(
  subjectId: string,
  materialId: string
): Promise<MaterialDownloadUrlResponse> {
  return await apiFetch<MaterialDownloadUrlResponse>(
    `/subjects/${encodeURIComponent(subjectId)}/materials/${encodeURIComponent(materialId)}/download-url`
  );
}

// ── S3 Upload Helper ─────────────────────────────────────────────

export async function uploadFileToS3(
  uploadUrl: string,
  file: File,
  contentType: string,
  onProgress?: (progress: number) => void
): Promise<void> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("PUT", uploadUrl);
    xhr.setRequestHeader("Content-Type", contentType);

    if (xhr.upload && onProgress) {
      xhr.upload.onprogress = (event) => {
        if (event.lengthComputable) {
          const percent = Math.round((event.loaded / event.total) * 100);
          onProgress(percent);
        }
      };
    }

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve();
      } else {
        reject(new Error(`S3 upload failed with status ${xhr.status}: ${xhr.statusText}`));
      }
    };

    xhr.onerror = () => {
      reject(new Error("Network error during S3 file upload."));
    };

    xhr.send(file);
  });
}

// ── Format and UI Utilities ──────────────────────────────────────

export function isBrowserViewable(filename: string, contentType?: string): boolean {
  const name = filename.toLowerCase();
  const mime = (contentType || "").toLowerCase();

  // PDF
  if (name.endsWith(".pdf") || mime === "application/pdf") return true;

  // Images
  if (name.match(/\.(png|jpe?g|webp|gif)$/) || mime.startsWith("image/")) return true;

  // Video
  if (name.match(/\.(mp4|webm)$/) || mime.startsWith("video/")) return true;

  // Text & Code & CSV
  if (name.match(/\.(txt|csv|md|json|log)$/) || mime.startsWith("text/")) return true;

  return false;
}

export function getMaterialIcon(filename: string, contentType?: string): string {
  const name = filename.toLowerCase();
  const mime = (contentType || "").toLowerCase();

  if (name.endsWith(".pdf") || mime.includes("pdf")) return "picture_as_pdf";
  if (name.match(/\.(png|jpe?g|webp|gif)$/) || mime.startsWith("image/")) return "image";
  if (name.match(/\.(mp4|webm)$/) || mime.startsWith("video/")) return "smart_display";
  if (name.match(/\.(doc|docx)$/) || mime.includes("word")) return "description";
  if (name.match(/\.(xls|xlsx|csv)$/) || mime.includes("spreadsheet") || mime.includes("excel")) return "table_chart";
  if (name.match(/\.(ppt|pptx)$/) || mime.includes("presentation") || mime.includes("powerpoint")) return "slideshow";
  if (name.endsWith(".zip") || mime.includes("zip")) return "folder_zip";
  if (name.match(/\.(txt|md)$/) || mime.startsWith("text/")) return "article";

  return "draft";
}

export function formatFileSize(bytes: number): string {
  if (!bytes || bytes <= 0) return "0 B";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}
