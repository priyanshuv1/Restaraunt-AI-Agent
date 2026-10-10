"use client";

import { useState } from "react";
import { Minus, Plus } from "lucide-react";
import type { MenuItem } from "@/lib/api";
import { inventoryApi, ApiError } from "@/lib/api";

interface MenuItemCardProps {
  item: MenuItem;
  onEdit: (item: MenuItem) => void;
  onDelete: (item: MenuItem) => void;
  onInventorySaved: (menuItemId: number, onHand: number, reserved: number) => void;
  onInventoryError: (msg: string) => void;
}

export default function MenuItemCard({
  item,
  onEdit,
  onDelete,
  onInventorySaved,
  onInventoryError,
}: MenuItemCardProps) {
  const [saving, setSaving] = useState(false);

  const onHand = item.quantity_on_hand ?? 0;
  const reserved = item.quantity_reserved ?? 0;

  const isNonVeg = item.dietary_tags.includes("non_vegetarian");
  const isVeg =
    item.dietary_tags.includes("vegetarian") ||
    item.dietary_tags.includes("vegan");

  const borderColor = isNonVeg
    ? "border-t-red-500 border-r-red-500"
    : isVeg
    ? "border-t-green-500 border-r-green-500"
    : "";

  async function change(delta: number) {
    const next = onHand + delta;
    if (next < reserved || saving) return;
    setSaving(true);
    try {
      const rec = await inventoryApi.update(item.id, { quantity_on_hand: next });
      onInventorySaved(item.id, rec.quantity_on_hand, rec.quantity_reserved);
    } catch (err) {
      onInventoryError(
        err instanceof ApiError ? err.detail : "Failed to update inventory."
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <article
      className={`w-full min-h-20 bg-white rounded-xl border border-zinc-200 border-t-2 border-r-2 ${borderColor} px-4 py-3 grid grid-cols-[1fr_auto_1fr] items-center gap-4`}
    >
      {/* Left: name */}
      <h3 className="text-left text-base font-semibold text-zinc-900 truncate">
        {item.name}
      </h3>

      {/* Center: quantity */}
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={() => change(-1)}
          disabled={saving || onHand - 1 < reserved}
          aria-label={`Decrease stock for ${item.name}`}
          className="w-9 h-9 rounded-lg bg-zinc-100 border border-zinc-400 text-zinc-900 flex items-center justify-center hover:bg-zinc-200 disabled:opacity-40"
        >
          <Minus className="w-4 h-4 text-zinc-900" strokeWidth={2.5} />
        </button>

        <span className="min-w-8 text-center text-base font-semibold text-zinc-900">
          {onHand}
        </span>

        <button
          type="button"
          onClick={() => change(1)}
          disabled={saving}
          aria-label={`Increase stock for ${item.name}`}
          className="w-9 h-9 rounded-lg bg-zinc-100 border border-zinc-400 text-zinc-900 flex items-center justify-center hover:bg-zinc-200 disabled:opacity-40"
        >
          <Plus className="w-4 h-4 text-zinc-900" strokeWidth={2.5} />
        </button>
      </div>

      {/* Right: edit / delete */}
      <div className="flex items-center justify-end gap-2">
        <button
          type="button"
          onClick={() => onEdit(item)}
          className="px-3 py-1.5 rounded-lg text-sm font-medium text-zinc-700 hover:bg-zinc-100"
        >
          Edit
        </button>
        <button
          type="button"
          onClick={() => onDelete(item)}
          className="px-3 py-1.5 rounded-lg text-sm font-medium text-red-600 hover:bg-red-50"
        >
          Delete
        </button>
      </div>
    </article>
  );
}