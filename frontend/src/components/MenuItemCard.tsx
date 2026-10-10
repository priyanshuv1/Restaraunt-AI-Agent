"use client";

import { Minus, Plus } from "lucide-react";
import type { MenuItem } from "@/lib/api";

interface MenuItemCardProps {
  item: MenuItem;
  quantityOnHand: number;
  onQuantityChange: (menuItemId: number, nextOnHand: number) => void;
  onEdit: (item: MenuItem) => void;
  onDelete: (item: MenuItem) => void;
}

export default function MenuItemCard({
  item,
  quantityOnHand,
  onQuantityChange,
  onEdit,
  onDelete,
}: MenuItemCardProps) {
  const onHand = quantityOnHand;
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

  function change(delta: number) {
    const next = onHand + delta;
    if (next < reserved) return;
    onQuantityChange(item.id, next);
  }

  return (
    <article
      className={`w-full min-h-20 bg-white rounded-xl border border-zinc-200 border-t-2 border-r-2 ${borderColor} px-4 py-3 grid grid-cols-[1fr_auto_1fr] items-center gap-4`}
    >
      {/* Left: name */}
      <h3 className="text-left text-base font-semibold text-zinc-900 truncate">
        {item.name}
      </h3>

      {/* Center: local-only quantity controls */}
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={() => change(-1)}
          disabled={onHand - 1 < reserved}
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
          aria-label={`Increase stock for ${item.name}`}
          className="w-9 h-9 rounded-lg bg-zinc-100 border border-zinc-400 text-zinc-900 flex items-center justify-center hover:bg-zinc-200"
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
