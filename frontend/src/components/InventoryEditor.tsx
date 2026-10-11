"use client";

import { useState } from "react";
import { Minus, Plus, Save, X, Loader2 } from "lucide-react";
import { inventoryApi, ApiError } from "@/lib/api";

interface InventoryEditorProps {
  menuItemId: number;
  currentOnHand: number;
  currentReserved: number;
  onSaved: (onHand: number, reserved: number) => void;
  onError: (msg: string) => void;
  onCancel: () => void;
}

export default function InventoryEditor({
  menuItemId,
  currentOnHand,
  currentReserved,
  onSaved,
  onError,
  onCancel,
}: InventoryEditorProps) {
  const [value, setValue] = useState(currentOnHand);
  const [saving, setSaving] = useState(false);
  const [fieldError, setFieldError] = useState<string | null>(null);

  function change(next: number) {
    const clamped = Math.max(0, next);
    setValue(clamped);
    if (clamped < currentReserved) {
      setFieldError(
        `Minimum is ${currentReserved} (${currentReserved} units are reserved by open orders).`
      );
    } else {
      setFieldError(null);
    }
  }

  async function handleSave() {
    if (fieldError) return;
    setSaving(true);
    try {
      const rec = await inventoryApi.update(menuItemId, {
        quantity_on_hand: value,
      });
      onSaved(rec.quantity_on_hand, rec.quantity_reserved);
    } catch (err) {
      const msg =
        err instanceof ApiError
          ? err.detail
          : "Failed to update inventory.";
      setFieldError(msg);
      onError(msg);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="flex flex-col gap-2">
      {/* Controls row */}
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={() => change(value - 1)}
          disabled={saving || value <= 0}
          aria-label="Decrease quantity"
          className="w-8 h-8 flex items-center justify-center rounded-lg border border-zinc-300 hover:bg-zinc-100 disabled:opacity-40 transition-colors"
        >
          <Minus className="w-3.5 h-3.5" />
        </button>

        <input
          type="number"
          value={value}
          min={0}
          onChange={(e) => change(parseInt(e.target.value, 10) || 0)}
          aria-label="Quantity on hand"
          className={`w-20 text-center rounded-lg border px-2 py-1.5 text-sm font-mono font-medium outline-none focus:ring-2 transition-shadow ${
            fieldError
              ? "border-red-400 focus:ring-red-200"
              : "border-zinc-300 focus:ring-amber-200 focus:border-amber-400"
          }`}
        />

        <button
          type="button"
          onClick={() => change(value + 1)}
          disabled={saving}
          aria-label="Increase quantity"
          className="w-8 h-8 flex items-center justify-center rounded-lg border border-zinc-300 hover:bg-zinc-100 disabled:opacity-40 transition-colors"
        >
          <Plus className="w-3.5 h-3.5" />
        </button>

        <button
          type="button"
          onClick={handleSave}
          disabled={saving || !!fieldError}
          aria-label="Save inventory"
          className="flex items-center gap-1.5 px-3 py-1.5 bg-amber-600 hover:bg-amber-700 disabled:opacity-50 text-white text-xs font-semibold rounded-lg transition-colors"
        >
          {saving ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
          ) : (
            <Save className="w-3.5 h-3.5" />
          )}
          {saving ? "Saving…" : "Save"}
        </button>

        <button
          type="button"
          onClick={onCancel}
          disabled={saving}
          aria-label="Cancel inventory edit"
          className="w-8 h-8 flex items-center justify-center rounded-lg border border-zinc-300 hover:bg-zinc-100 disabled:opacity-40 transition-colors"
        >
          <X className="w-3.5 h-3.5 text-zinc-500" />
        </button>
      </div>

      {/* Validation / API error */}
      {fieldError && (
        <p role="alert" className="text-xs text-red-600">
          {fieldError}
        </p>
      )}

      {currentReserved > 0 && (
        <p className="text-xs text-zinc-400">
          {currentReserved} reserved — available = on-hand − reserved
        </p>
      )}
    </div>
  );
}
