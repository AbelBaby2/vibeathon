import React, { useRef, useState } from "react";
import {
  AlertCircle,
  FileCheck,
  FileUp,
  Loader2,
  Trash2,
  UploadCloud
} from "lucide-react";
import type { DocumentRole } from "../types";

export interface FileItem {
  id: string;
  file: File;
  role: DocumentRole;
  error?: string;
}

interface FileUploadSectionProps {
  onAnalyze: (tenderFile: File, bidderFiles: File[]) => Promise<void>;
  isAnalyzing: boolean;
  errorMessage: string | null;
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 Bytes";
  const k = 1024;
  const sizes = ["Bytes", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
}

export const FileUploadSection: React.FC<FileUploadSectionProps> = ({
  onAnalyze,
  isAnalyzing,
  errorMessage
}) => {
  const [tenderFile, setTenderFile] = useState<FileItem | null>(null);
  const [bidderFiles, setBidderFiles] = useState<FileItem[]>([]);
  const [validationError, setValidationError] = useState<string | null>(null);

  const tenderInputRef = useRef<HTMLInputElement>(null);
  const bidderInputRef = useRef<HTMLInputElement>(null);

  const handleTenderSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.name.toLowerCase().endsWith(".pdf")) {
      setValidationError("Tender file must be a PDF document.");
      return;
    }

    setValidationError(null);
    setTenderFile({
      id: "tender-" + Date.now(),
      file,
      role: "TENDER"
    });
  };

  const handleBidderSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    const newFiles: FileItem[] = [];
    for (let i = 0; i < files.length; i++) {
      const f = files[i];
      if (!f.name.toLowerCase().endsWith(".pdf")) {
        setValidationError(`"${f.name}" was skipped: Only text-based PDF files are supported.`);
        continue;
      }
      newFiles.push({
        id: "bidder-" + Date.now() + "-" + i,
        file: f,
        role: "BIDDER_SUPPORTING"
      });
    }

    if (newFiles.length > 0) {
      setValidationError(null);
      setBidderFiles((prev) => [...prev, ...newFiles]);
    }
  };

  const removeBidderFile = (id: string) => {
    setBidderFiles((prev) => prev.filter((f) => f.id !== id));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!tenderFile) {
      setValidationError("Please select a primary Tender PDF document.");
      return;
    }
    if (bidderFiles.length === 0) {
      setValidationError("Please upload at least one Bidder Supporting PDF (e.g. credentials, certificate, financial statement).");
      return;
    }

    setValidationError(null);
    await onAnalyze(
      tenderFile.file,
      bidderFiles.map((bf) => bf.file)
    );
  };

  return (
    <div className="card" style={{ marginBottom: "1.75rem" }}>
      <div className="card-header">
        <div>
          <h2 className="card-title">
            <UploadCloud style={{ width: "18px", height: "18px", color: "var(--teal-600)" }} />
            <span>Upload Documents for Compliance Intelligence</span>
          </h2>
          <p className="card-description">
            Upload the client tender document alongside bidder supporting credentials for automated clause-by-clause extraction and verification.
          </p>
        </div>
      </div>

      {/* Notice on Text-based PDFs */}
      <div className="alert alert-info" style={{ marginBottom: "1.25rem", fontSize: "0.76rem" }}>
        <AlertCircle style={{ width: "16px", height: "16px", flexShrink: 0 }} />
        <div>
          <strong>Document Scope Notice:</strong> This version extracts native text layers from text-based PDFs. Optical Character Recognition (OCR) for raster-scanned image documents is not executed. Ensure uploaded files contain selectable text.
        </div>
      </div>

      {(validationError || errorMessage) && (
        <div className="alert alert-danger" role="alert" style={{ marginBottom: "1.25rem" }}>
          <AlertCircle style={{ width: "16px", height: "16px", flexShrink: 0 }} />
          <span>{validationError || errorMessage}</span>
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "1.25rem", marginBottom: "1.25rem" }}>
          {/* Section 1: Tender Document */}
          <div style={{ padding: "1rem", backgroundColor: "var(--navy-50)", borderRadius: "var(--radius-md)", border: "1px solid var(--border-subtle)" }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "0.5rem" }}>
              <strong style={{ fontSize: "0.82rem", color: "var(--navy-900)" }}>
                1. Primary Tender Document (RFP / Scope) *
              </strong>
              <span className="badge" style={{ backgroundColor: "#F1F5F9", color: "var(--navy-700)" }}>
                Role: TENDER (1 file)
              </span>
            </div>
            <p style={{ margin: "0 0 0.75rem", fontSize: "0.75rem", color: "var(--navy-600)" }}>
              The authoritative tender specification containing technical, financial, and HSE requirements.
            </p>

            <input
              type="file"
              ref={tenderInputRef}
              onChange={handleTenderSelect}
              accept=".pdf,application/pdf"
              style={{ display: "none" }}
              id="tender-pdf-input"
            />

            {!tenderFile ? (
              <div
                className="dropzone"
                onClick={() => tenderInputRef.current?.click()}
                tabIndex={0}
                role="button"
                aria-label="Upload Tender PDF"
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") tenderInputRef.current?.click();
                }}
              >
                <FileUp style={{ width: "24px", height: "24px", color: "var(--teal-600)", margin: "0 auto 0.4rem" }} />
                <div style={{ fontSize: "0.82rem", fontWeight: 600, color: "var(--navy-800)" }}>
                  Select Tender PDF
                </div>
                <div style={{ fontSize: "0.72rem", color: "var(--navy-500)", marginTop: "0.2rem" }}>
                  Click to browse .pdf file
                </div>
              </div>
            ) : (
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "0.6rem 0.75rem", backgroundColor: "#FFFFFF", border: "1px solid var(--teal-600)", borderRadius: "var(--radius-md)" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", overflow: "hidden" }}>
                  <FileCheck style={{ width: "18px", height: "18px", color: "var(--teal-600)", flexShrink: 0 }} />
                  <div style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    <div style={{ fontSize: "0.8rem", fontWeight: 600, color: "var(--navy-900)" }}>
                      {tenderFile.file.name}
                    </div>
                    <div style={{ fontSize: "0.7rem", color: "var(--navy-500)" }}>
                      {formatBytes(tenderFile.file.size)} • Role: TENDER
                    </div>
                  </div>
                </div>
                <button
                  type="button"
                  className="btn btn-outline btn-sm"
                  onClick={() => setTenderFile(null)}
                  style={{ color: "#DC2626", borderColor: "#FECACA" }}
                  aria-label="Remove tender file"
                >
                  <Trash2 style={{ width: "14px", height: "14px" }} />
                </button>
              </div>
            )}
          </div>

          {/* Section 2: Bidder Supporting Documents */}
          <div style={{ padding: "1rem", backgroundColor: "var(--navy-50)", borderRadius: "var(--radius-md)", border: "1px solid var(--border-subtle)" }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "0.5rem" }}>
              <strong style={{ fontSize: "0.82rem", color: "var(--navy-900)" }}>
                2. Bidder Supporting Documents *
              </strong>
              <span className="badge" style={{ backgroundColor: "#F1F5F9", color: "var(--navy-700)" }}>
                Role: BIDDER_SUPPORTING ({bidderFiles.length} files)
              </span>
            </div>
            <p style={{ margin: "0 0 0.75rem", fontSize: "0.75rem", color: "var(--navy-600)" }}>
              Certificates (ISO), audited balance sheets, HSE plans, work credentials, and licenses.
            </p>

            <input
              type="file"
              ref={bidderInputRef}
              onChange={handleBidderSelect}
              accept=".pdf,application/pdf"
              multiple
              style={{ display: "none" }}
              id="bidder-pdfs-input"
            />

            <div
              className="dropzone"
              onClick={() => bidderInputRef.current?.click()}
              tabIndex={0}
              role="button"
              aria-label="Upload Bidder Supporting PDFs"
              style={{ padding: "0.85rem", marginBottom: "0.75rem" }}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") bidderInputRef.current?.click();
              }}
            >
              <FileUp style={{ width: "20px", height: "20px", color: "var(--teal-600)", margin: "0 auto 0.25rem" }} />
              <div style={{ fontSize: "0.8rem", fontWeight: 600, color: "var(--navy-800)" }}>
                + Add Bidder Supporting PDFs
              </div>
              <div style={{ fontSize: "0.7rem", color: "var(--navy-500)" }}>
                Select one or multiple files
              </div>
            </div>

            {bidderFiles.length > 0 && (
              <div style={{ display: "flex", flexDirection: "column", gap: "0.4rem", maxHeight: "150px", overflowY: "auto" }}>
                {bidderFiles.map((bf) => (
                  <div
                    key={bf.id}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      padding: "0.45rem 0.65rem",
                      backgroundColor: "#FFFFFF",
                      border: "1px solid var(--border-subtle)",
                      borderRadius: "var(--radius-sm)",
                      fontSize: "0.76rem"
                    }}
                  >
                    <div style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", marginRight: "0.5rem" }}>
                      <span style={{ fontWeight: 500, color: "var(--navy-800)" }}>{bf.file.name}</span>{" "}
                      <span style={{ color: "var(--navy-500)", fontSize: "0.7rem" }}>({formatBytes(bf.file.size)})</span>
                    </div>
                    <button
                      type="button"
                      onClick={() => removeBidderFile(bf.id)}
                      style={{ background: "none", border: "none", color: "#DC2626", cursor: "pointer", padding: "0.2rem" }}
                      aria-label={`Remove ${bf.file.name}`}
                    >
                      <Trash2 style={{ width: "13px", height: "13px" }} />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Submit Actions */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", paddingTop: "0.75rem", borderTop: "1px solid var(--border-subtle)" }}>
          <div style={{ fontSize: "0.75rem", color: "var(--navy-600)" }}>
            {tenderFile && bidderFiles.length > 0 ? (
              <span style={{ color: "#166534", fontWeight: 500 }}>
                ✓ Ready for analysis: 1 Tender PDF + {bidderFiles.length} Bidder Supporting PDF(s)
              </span>
            ) : (
              <span>Upload 1 Tender PDF and at least 1 Bidder PDF to activate intelligence.</span>
            )}
          </div>

          <button
            type="submit"
            className="btn btn-primary"
            disabled={isAnalyzing || !tenderFile || bidderFiles.length === 0}
            id="btn-run-compliance-analysis"
          >
            {isAnalyzing ? (
              <>
                <Loader2 className="btn-spinner" style={{ width: "16px", height: "16px", animation: "spin 1s linear infinite" }} />
                <span>Extracting & Evaluating Compliance...</span>
              </>
            ) : (
              <>
                <UploadCloud style={{ width: "16px", height: "16px" }} />
                <span>Run Compliance Analysis</span>
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
};
