"use client";

import React, { useEffect, useState } from "react";
import {
  SubjectMaterial,
  getMaterialDownloadUrl,
  getMaterialIcon,
  formatFileSize,
  isBrowserViewable,
} from "@/lib/materials";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

interface MaterialViewerModalProps {
  material: SubjectMaterial | null;
  onClose: () => void;
  onDownload: (material: SubjectMaterial) => Promise<void>;
}

export default function MaterialViewerModal({
  material,
  onClose,
  onDownload,
}: MaterialViewerModalProps) {
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!material) {
      setDownloadUrl(null);
      setError(null);
      return;
    }

    let isMounted = true;
    setLoading(true);
    setError(null);

    getMaterialDownloadUrl(material.subject_id, material.material_id)
      .then((res) => {
        if (isMounted) {
          setDownloadUrl(res.download_url);
        }
      })
      .catch((err) => {
        if (isMounted) {
          setError(err?.message || "Failed to load material preview.");
        }
      })
      .finally(() => {
        if (isMounted) setLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [material]);

  if (!material) return null;

  const isPdf =
    material.original_filename.toLowerCase().endsWith(".pdf") ||
    material.content_type.toLowerCase().includes("pdf");

  const isImage =
    material.original_filename.toLowerCase().match(/\.(png|jpe?g|webp|gif)$/) !== null ||
    material.content_type.toLowerCase().startsWith("image/");

  const isVideo =
    material.original_filename.toLowerCase().match(/\.(mp4|webm)$/) !== null ||
    material.content_type.toLowerCase().startsWith("video/");

  const isTextOrCsv =
    material.original_filename.toLowerCase().match(/\.(txt|csv|md|json|log)$/) !== null ||
    material.content_type.toLowerCase().startsWith("text/");

  const viewable = isBrowserViewable(material.original_filename, material.content_type);
  const icon = getMaterialIcon(material.original_filename, material.content_type);

  return (
    <Dialog open={!!material} onOpenChange={(open) => { if (!open) onClose(); }}>
      <DialogContent className="max-w-4xl w-[95vw] h-[88vh] flex flex-col p-0 overflow-hidden bg-[var(--surface)] border-[var(--outline-variant)]">
        {/* Header */}
        <DialogHeader className="p-4 border-b border-[var(--outline-variant)] flex flex-row items-center justify-between space-y-0 shrink-0">
          <div className="flex items-center gap-3 truncate max-w-[65%]">
            <span className="material-symbols-outlined text-[26px] text-primary shrink-0">
              {icon}
            </span>
            <div className="truncate">
              <div className="flex items-center gap-2">
                <DialogTitle className="text-sm font-bold truncate">
                  {material.title}
                </DialogTitle>
                <Badge variant="outline" className="text-[10px] font-semibold uppercase shrink-0">
                  {material.category}
                </Badge>
              </div>
              <p className="text-[11px] text-muted-foreground font-mono mt-0.5 truncate">
                {material.original_filename} • {formatFileSize(material.file_size)}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 mr-6">
            {downloadUrl && (
              <Button
                size="sm"
                variant="outline"
                onClick={() => window.open(downloadUrl, "_blank")}
                className="h-8 text-xs gap-1.5 font-semibold cursor-pointer"
                title="Open in new window / tab"
              >
                <span className="material-symbols-outlined text-[16px]">open_in_new</span>
                <span className="hidden sm:inline">Open in Tab</span>
              </Button>
            )}
            <Button
              size="sm"
              onClick={() => onDownload(material)}
              className="h-8 text-xs gap-1.5 font-bold cursor-pointer bg-primary text-white hover:opacity-90"
              title="Download file"
            >
              <span className="material-symbols-outlined text-[16px]">download</span>
              <span className="hidden sm:inline">Download</span>
            </Button>
          </div>
        </DialogHeader>

        {/* Content Area */}
        <div className="flex-1 overflow-auto p-4 flex items-center justify-center bg-muted/20">
          {loading ? (
            <div className="flex flex-col items-center justify-center gap-3 py-16">
              <div className="w-8 h-8 border-3 border-t-transparent border-primary rounded-full animate-spin" />
              <p className="text-xs font-semibold text-muted-foreground">Preparing preview...</p>
            </div>
          ) : error ? (
            <div className="text-center p-8 max-w-md space-y-3">
              <span className="material-symbols-outlined text-[48px] text-destructive">
                error
              </span>
              <p className="text-sm font-semibold text-destructive">{error}</p>
              <Button size="sm" variant="outline" onClick={onClose}>
                Close
              </Button>
            </div>
          ) : downloadUrl ? (
            <>
              {isPdf ? (
                <iframe
                  src={downloadUrl}
                  className="w-full h-full rounded-xl border border-[var(--outline-variant)] bg-white shadow-xs"
                  title={material.title}
                />
              ) : isImage ? (
                <div className="flex items-center justify-center w-full h-full p-2">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={downloadUrl}
                    alt={material.title}
                    className="max-h-full max-w-full object-contain rounded-xl shadow-md"
                  />
                </div>
              ) : isVideo ? (
                <div className="flex items-center justify-center w-full h-full p-2 bg-black/90 rounded-xl">
                  <video
                    src={downloadUrl}
                    controls
                    autoPlay
                    className="max-h-full max-w-full rounded-lg"
                  >
                    Your browser does not support the video tag.
                  </video>
                </div>
              ) : isTextOrCsv ? (
                <iframe
                  src={downloadUrl}
                  className="w-full h-full rounded-xl border border-[var(--outline-variant)] bg-card p-4 font-mono text-xs shadow-xs"
                  title={material.title}
                />
              ) : (
                <div className="text-center p-8 space-y-4 max-w-md">
                  <span className="material-symbols-outlined text-[56px] text-muted-foreground opacity-60">
                    {icon}
                  </span>
                  <div>
                    <h3 className="text-base font-bold text-foreground">
                      Direct In-Browser Preview Not Supported
                    </h3>
                    <p className="text-xs text-muted-foreground mt-1">
                      This file format ({material.original_filename.split(".").pop()?.toUpperCase()}) cannot be directly rendered inside the browser viewport.
                    </p>
                  </div>
                  <div className="flex justify-center gap-3 pt-2">
                    <Button
                      variant="outline"
                      onClick={() => window.open(downloadUrl, "_blank")}
                      className="gap-1.5 text-xs font-semibold cursor-pointer"
                    >
                      <span className="material-symbols-outlined text-[16px]">open_in_new</span>
                      Try Open In Tab
                    </Button>
                    <Button
                      onClick={() => onDownload(material)}
                      className="gap-1.5 text-xs font-bold cursor-pointer"
                    >
                      <span className="material-symbols-outlined text-[16px]">download</span>
                      Download File
                    </Button>
                  </div>
                </div>
              )}
            </>
          ) : null}
        </div>
      </DialogContent>
    </Dialog>
  );
}
