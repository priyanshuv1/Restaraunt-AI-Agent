"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, Loader2 } from "lucide-react";
import type { MenuItem } from "@/lib/api";
import { menuApi, ApiError } from "@/lib/api";

interface DeleteConfirmModalProps {
  item: MenuItem;
  onClose: () => void;
  onDeleted: (id: number) => void;
  onError: (msg: string) => void;
}

export default function DeleteConfirmModal({
  item,
  onClose,
  onDeleted,
  onError,
}: DeleteConfirmModalProps) {
  const [deleting, setDeleting] = useState(false);

  // Close on Escape
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);

  async function handleDelete() {
    setDeleting(true);
    try {
      await menuApi.delete(item.id);
      onDeleted(item.id);
    } catch (err) {
      const msg =
        err instanceof ApiError ? err.detail : "Failed to delete item.";
      onError(msg);
      onClose();
    } finally {
      setDeleting(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="del-title"
        aria-describedby="del-desc"
        className="w-full max-w-sm bg-white rounded-2xl shadow-2xl p-6 space-y-4"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-red-100 flex items-center justify-center shrink-0">
            <AlertTriangle className="w-5 h-5 text-red-600" />
          </div>
          <div>
            <h2 id="del-title" className="font-semibold text-zinc-900">
              Delete Menu Item
            </h2>
            <p id="del-desc" className="text-sm text-zinc-500">
              This action cannot be undone.
            </p>
          </div>
        </div>

        <p className="text-sm text-zinc-700">
          Are you sure you want to delete{" "}
          <span className="font-semibold">{item.name}</span>? The item and its
          inventory record will be permanently removed.
        </p>

        <div className="flex gap-3 pt-1">
          <button
            type="button"
            onClick={onClose}
            disabled={deleting}
            className="flex-1 px-4 py-2.5 rounded-xl border border-zinc-300 text-sm font-medium text-zinc-700 hover:bg-zinc-50 disabled:opacity-50 transition-colors"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleDelete}
            disabled={deleting}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-red-600 hover:bg-red-700 disabled:opacity-60 text-white text-sm font-semibold transition-colors"
          >
            {deleting && <Loader2 className="w-4 h-4 animate-spin" />}
            {deleting ? "Deleting…" : "Delete"}
          </button>
        </div>
      </div>
    </div>
  );
}
