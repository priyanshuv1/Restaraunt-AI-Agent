/**
 * Zustand store for the staff dashboard.
 *
 * Keeps menu items (with embedded inventory fields) in a single flat list.
 * Inventory quantities are updated in-place after a successful PATCH so the
 * dashboard re-renders without a full refetch.
 */

import { create } from "zustand";
import { type MenuItem, menuApi, ApiError } from "@/lib/api";

interface DashboardState {
  items: MenuItem[];
  loading: boolean;
  error: string | null;

  // Fetch all menu items (includes inventory fields in each item)
  fetchItems: () => Promise<void>;

  // Optimistically update a single item after a successful API call
  upsertItem: (item: MenuItem) => void;
  removeItem: (id: number) => void;

  // In-place inventory update (does not re-fetch the full list)
  updateInventoryLocal: (
    menuItemId: number,
    onHand: number,
    reserved: number
  ) => void;

  clearError: () => void;
}

export const useDashboardStore = create<DashboardState>((set, get) => ({
  items: [],
  loading: false,
  error: null,

  fetchItems: async () => {
    set({ loading: true, error: null });
    try {
      const items = await menuApi.list();
      set({ items, loading: false });
    } catch (err) {
      const msg =
        err instanceof ApiError
          ? `API error ${err.status}: ${err.detail}`
          : "Failed to load menu items. Is the backend running?";
      set({ loading: false, error: msg });
    }
  },

  upsertItem: (item) => {
    const items = get().items;
    const idx = items.findIndex((i) => i.id === item.id);
    if (idx >= 0) {
      const next = [...items];
      next[idx] = item;
      set({ items: next });
    } else {
      set({ items: [...items, item] });
    }
  },

  removeItem: (id) => {
    set({ items: get().items.filter((i) => i.id !== id) });
  },

  updateInventoryLocal: (menuItemId, onHand, reserved) => {
    const items = get().items.map((item) =>
      item.id === menuItemId
        ? {
            ...item,
            quantity_on_hand: onHand,
            quantity_reserved: reserved,
            quantity_available: onHand - reserved,
          }
        : item
    );
    set({ items });
  },

  clearError: () => set({ error: null }),
}));
