"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Plus,
  RefreshCw,
  Search,
  Package,
  AlertTriangle,
  Coffee,
  UtensilsCrossed,
  Loader2,
} from "lucide-react";
import type { MenuItem } from "@/lib/api";
import { useDashboardStore } from "@/store/dashboard";
import { useToast } from "@/hooks/useToast";
import { ToastContainer } from "@/components/Toast";
import MenuItemCard from "@/components/MenuItemCard";
import MenuItemModal from "@/components/MenuItemModal";
import DeleteConfirmModal from "@/components/DeleteConfirmModal";

// ---------------------------------------------------------------------------
// Category filter list (includes "All" sentinel)
// ---------------------------------------------------------------------------
const CATEGORIES = [
  "All",
  "Coffee",
  "Beverages",
  "Pizza",
  "Burgers",
  "Pasta",
  "Sandwiches",
  "Snacks",
  "Desserts",
];

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function DashboardPage() {
  const { items, loading, error, fetchItems, upsertItem, removeItem, updateInventoryLocal } =
    useDashboardStore();
  const { toasts, dismiss, success, error: toastError } = useToast();

  const [search, setSearch] = useState("");
  const [activeCategory, setActiveCategory] = useState("All");
  const [modalItem, setModalItem] = useState<MenuItem | null | undefined>(
    undefined
  ); // undefined = closed, null = create, MenuItem = edit
  const [deleteTarget, setDeleteTarget] = useState<MenuItem | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  // Initial fetch
  useEffect(() => {
    fetchItems();
  }, [fetchItems]);

  // Manual refresh
  const handleRefresh = useCallback(async () => {
    setRefreshing(true);
    await fetchItems();
    setRefreshing(false);
  }, [fetchItems]);

  // Derived: filtered + searched items
  const filtered = useMemo(() => {
    return items.filter((item) => {
      const matchCat =
        activeCategory === "All" || item.category === activeCategory;
      const term = search.trim().toLowerCase();
      const matchSearch =
        !term ||
        item.name.toLowerCase().includes(term) ||
        item.description.toLowerCase().includes(term) ||
        item.category.toLowerCase().includes(term);
      return matchCat && matchSearch;
    });
  }, [items, search, activeCategory]);

  // Inventory stats
  const stats = useMemo(() => {
    const total = items.length;
    const outOfStock = items.filter(
      (i) => (i.quantity_available ?? 0) === 0
    ).length;
    const lowStock = items.filter((i) => {
      const av = i.quantity_available ?? 0;
      return av > 0 && av <= 5;
    }).length;
    const unavailable = items.filter((i) => !i.is_available).length;
    return { total, outOfStock, lowStock, unavailable };
  }, [items]);

  // ---------------------------------------------------------------------------
  // Event handlers
  // ---------------------------------------------------------------------------

  function handleSaved(item: MenuItem) {
    upsertItem(item);
    setModalItem(undefined);
    success(
      modalItem
        ? `"${item.name}" updated successfully.`
        : `"${item.name}" added to the menu.`
    );
  }

  function handleDeleted(id: number) {
    removeItem(id);
    setDeleteTarget(null);
    success("Menu item deleted.");
  }

  function handleInventorySaved(menuItemId: number, onHand: number, reserved: number) {
    updateInventoryLocal(menuItemId, onHand, reserved);
    success("Stock updated.");
  }

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <div className="flex flex-col min-h-screen bg-zinc-50">
      {/* ------------------------------------------------------------------ */}
      {/* Header */}
      {/* ------------------------------------------------------------------ */}
      <header className="bg-white border-b border-zinc-200 sticky top-0 z-30">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-4 flex items-center justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 bg-amber-600 rounded-xl flex items-center justify-center">
              <Coffee className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-zinc-900 leading-tight">
                DineMate AI
              </h1>
              <p className="text-xs text-zinc-500">Staff Dashboard</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleRefresh}
              disabled={loading || refreshing}
              aria-label="Refresh menu data"
              className="flex items-center gap-2 px-3 py-2 rounded-xl border border-zinc-300 text-sm font-medium text-zinc-600 hover:bg-zinc-50 disabled:opacity-50 transition-colors"
            >
              <RefreshCw
                className={`w-4 h-4 ${refreshing || loading ? "animate-spin" : ""}`}
              />
              <span className="hidden sm:inline">Refresh</span>
            </button>

            <button
              type="button"
              onClick={() => setModalItem(null)}
              className="flex items-center gap-2 px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white text-sm font-semibold rounded-xl transition-colors"
            >
              <Plus className="w-4 h-4" />
              <span>Add Item</span>
            </button>
          </div>
        </div>
      </header>

      {/* ------------------------------------------------------------------ */}
      {/* Page title + stats bar */}
      {/* ------------------------------------------------------------------ */}
      <div className="bg-white border-b border-zinc-100">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-5">
          <h2 className="text-2xl font-bold text-zinc-900 mb-4">
            Menu &amp; Inventory Management
          </h2>

          {/* Stats row */}
          <div className="flex flex-wrap gap-3">
            <StatPill
              icon={<UtensilsCrossed className="w-3.5 h-3.5" />}
              label="Total items"
              value={stats.total}
              color="zinc"
            />
            {stats.outOfStock > 0 && (
              <StatPill
                icon={<AlertTriangle className="w-3.5 h-3.5" />}
                label="Out of stock"
                value={stats.outOfStock}
                color="red"
              />
            )}
            {stats.lowStock > 0 && (
              <StatPill
                icon={<Package className="w-3.5 h-3.5" />}
                label="Low stock (≤5)"
                value={stats.lowStock}
                color="amber"
              />
            )}
            {stats.unavailable > 0 && (
              <StatPill
                icon={<Package className="w-3.5 h-3.5" />}
                label="Marked unavailable"
                value={stats.unavailable}
                color="zinc"
              />
            )}
          </div>
        </div>
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* Search + filters */}
      {/* ------------------------------------------------------------------ */}
      <div className="bg-white border-b border-zinc-100 sticky top-[73px] z-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3 flex flex-col sm:flex-row gap-3 items-start sm:items-center">
          {/* Search */}
          <div className="relative flex-1 max-w-sm w-full">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-400 pointer-events-none" />
            <input
              type="search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search items…"
              aria-label="Search menu items"
              className="w-full pl-9 pr-3 py-2 text-sm rounded-xl border border-zinc-300 focus:outline-none focus:ring-2 focus:ring-amber-200 focus:border-amber-400 transition-shadow"
            />
          </div>

          {/* Category filter pills */}
          <div className="flex flex-wrap gap-1.5">
            {CATEGORIES.map((cat) => (
              <button
                key={cat}
                type="button"
                onClick={() => setActiveCategory(cat)}
                className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-colors ${
                  activeCategory === cat
                    ? "bg-amber-600 border-amber-600 text-white"
                    : "border-zinc-300 text-zinc-600 hover:border-amber-400 hover:text-amber-700"
                }`}
              >
                {cat}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* Main content */}
      {/* ------------------------------------------------------------------ */}
      <main className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 py-6">
        {/* Loading state */}
        {loading && items.length === 0 && (
          <div className="flex flex-col items-center justify-center py-24 gap-4 text-zinc-400">
            <Loader2 className="w-8 h-8 animate-spin text-amber-500" />
            <p className="text-sm font-medium">Loading menu items…</p>
          </div>
        )}

        {/* Error state */}
        {error && !loading && (
          <div
            role="alert"
            className="flex flex-col items-center gap-4 py-20 text-center"
          >
            <div className="w-14 h-14 rounded-2xl bg-red-100 flex items-center justify-center">
              <AlertTriangle className="w-7 h-7 text-red-500" />
            </div>
            <div>
              <p className="font-semibold text-zinc-900 mb-1">
                Could not load menu
              </p>
              <p className="text-sm text-zinc-500 max-w-sm">{error}</p>
            </div>
            <button
              type="button"
              onClick={handleRefresh}
              className="flex items-center gap-2 px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white text-sm font-semibold rounded-xl transition-colors"
            >
              <RefreshCw className="w-4 h-4" />
              Try Again
            </button>
          </div>
        )}

        {/* Item count (when loaded) */}
        {!loading && !error && items.length > 0 && (
          <p className="text-sm text-zinc-500 mb-4">
            Showing{" "}
            <span className="font-semibold text-zinc-800">{filtered.length}</span>{" "}
            of{" "}
            <span className="font-semibold text-zinc-800">{items.length}</span>{" "}
            items
            {activeCategory !== "All" && ` in ${activeCategory}`}
            {search && ` matching "${search}"`}
          </p>
        )}

        {/* Empty state — no items in DB */}
        {!loading && !error && items.length === 0 && (
          <div className="flex flex-col items-center justify-center py-24 gap-4 text-center">
            <div className="w-14 h-14 rounded-2xl bg-amber-100 flex items-center justify-center">
              <UtensilsCrossed className="w-7 h-7 text-amber-500" />
            </div>
            <div>
              <p className="font-semibold text-zinc-900 mb-1">
                No menu items yet
              </p>
              <p className="text-sm text-zinc-500 max-w-xs">
                Add your first item or run the backend seed script to populate the menu.
              </p>
            </div>
            <button
              type="button"
              onClick={() => setModalItem(null)}
              className="flex items-center gap-2 px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white text-sm font-semibold rounded-xl transition-colors"
            >
              <Plus className="w-4 h-4" />
              Add Menu Item
            </button>
          </div>
        )}

        {/* Empty state — filter/search match */}
        {!loading && !error && items.length > 0 && filtered.length === 0 && (
          <div className="flex flex-col items-center justify-center py-20 gap-3 text-center">
            <Search className="w-8 h-8 text-zinc-300" />
            <p className="font-medium text-zinc-600">No items match your filter</p>
            <button
              type="button"
              onClick={() => {
                setSearch("");
                setActiveCategory("All");
              }}
              className="text-sm text-amber-600 hover:underline font-medium"
            >
              Clear filters
            </button>
          </div>
        )}

        {/* Item grid */}
        {filtered.length > 0 && (
          <div className="flex flex-col gap-4">
            {filtered.map((item) => (
              <MenuItemCard
                key={item.id}
                item={item}
                onEdit={(i) => setModalItem(i)}
                onDelete={(i) => setDeleteTarget(i)}
                onInventorySaved={handleInventorySaved}
                onInventoryError={toastError}
              />
            ))}
          </div>
        )}
      </main>

      {/* ------------------------------------------------------------------ */}
      {/* Modals */}
      {/* ------------------------------------------------------------------ */}

      {/* Add / Edit */}
      {modalItem !== undefined && (
        <MenuItemModal
          item={modalItem}
          onClose={() => setModalItem(undefined)}
          onSaved={handleSaved}
          onError={toastError}
        />
      )}

      {/* Delete confirmation */}
      {deleteTarget && (
        <DeleteConfirmModal
          item={deleteTarget}
          onClose={() => setDeleteTarget(null)}
          onDeleted={handleDeleted}
          onError={toastError}
        />
      )}

      {/* ------------------------------------------------------------------ */}
      {/* Auth notice banner */}
      {/* ------------------------------------------------------------------ */}
      <div className="bg-amber-50 border-t border-amber-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-2 flex items-center gap-2">
          <AlertTriangle className="w-3.5 h-3.5 text-amber-600 shrink-0" />
          <p className="text-xs text-amber-700">
            <strong>Staff access only.</strong> Authentication is not yet
            implemented — write endpoints are currently open. Add JWT/session
            middleware before deploying to production.
          </p>
        </div>
      </div>

      {/* Toasts */}
      <ToastContainer toasts={toasts} onDismiss={dismiss} />
    </div>
  );
}

// ---------------------------------------------------------------------------
// StatPill helper
// ---------------------------------------------------------------------------

type PillColor = "zinc" | "red" | "amber" | "green";

const PILL_STYLES: Record<PillColor, string> = {
  zinc: "bg-zinc-100 text-zinc-600",
  red: "bg-red-100 text-red-700",
  amber: "bg-amber-100 text-amber-700",
  green: "bg-emerald-100 text-emerald-700",
};

function StatPill({
  icon,
  label,
  value,
  color,
}: {
  icon: React.ReactNode;
  label: string;
  value: number;
  color: PillColor;
}) {
  return (
    <span
      className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium ${PILL_STYLES[color]}`}
    >
      {icon}
      <span className="font-bold">{value}</span>
      <span>{label}</span>
    </span>
  );
}
