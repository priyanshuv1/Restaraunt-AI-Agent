/**
 * DineMate AI — API client
 *
 * All requests go to the FastAPI backend. The base URL is configurable via
 * NEXT_PUBLIC_API_URL (defaults to http://localhost:8000).
 *
 * Responses are typed; callers receive typed data or throw an ApiError.
 */

export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ---------------------------------------------------------------------------
// Types mirroring backend Pydantic schemas
// ---------------------------------------------------------------------------

export interface MenuItem {
  id: number;
  name: string;
  category: string;
  description: string;
  price: string; // Decimal serialised as string by FastAPI
  is_available: boolean;
  dietary_tags: string[];
  created_at: string;
  updated_at: string;
  // Inventory fields (null when inventory row missing – shouldn't happen post-migration)
  quantity_on_hand: number | null;
  quantity_reserved: number | null;
  quantity_available: number | null;
}

export interface InventoryRecord {
  menu_item_id: number;
  quantity_on_hand: number;
  quantity_reserved: number;
  quantity_available: number;
  updated_at: string;
  item_id: number;
  item_name: string;
  item_category: string;
  item_description: string;
  item_price: string;
  item_is_available: boolean;
  item_dietary_tags: string[];
}

export interface MenuItemCreate {
  name: string;
  category: string;
  description?: string;
  price: string;
  is_available?: boolean;
  dietary_tags?: string[];
}

export interface MenuItemUpdate {
  name?: string;
  category?: string;
  description?: string;
  price?: string;
  is_available?: boolean;
  dietary_tags?: string[];
}

export interface InventoryUpdate {
  quantity_on_hand: number;
}

// ---------------------------------------------------------------------------
// Error class
// ---------------------------------------------------------------------------

export class ApiError extends Error {
  constructor(
    public status: number,
    public detail: string
  ) {
    super(detail);
    this.name = "ApiError";
  }
}

// ---------------------------------------------------------------------------
// Internal fetch wrapper
// ---------------------------------------------------------------------------

async function request<T>(
  path: string,
  init: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init.headers ?? {}),
    },
  });

  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      detail = body?.detail ?? JSON.stringify(body);
    } catch {
      // ignore parse errors
    }
    throw new ApiError(res.status, detail);
  }

  // 204 No Content
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

// ---------------------------------------------------------------------------
// Menu endpoints
// ---------------------------------------------------------------------------

export const menuApi = {
  list(params?: { category?: string; search?: string; available_only?: boolean }) {
    const qs = new URLSearchParams();
    if (params?.category) qs.set("category", params.category);
    if (params?.search) qs.set("search", params.search);
    if (params?.available_only) qs.set("available_only", "true");
    const query = qs.toString();
    return request<MenuItem[]>(`/api/menu${query ? `?${query}` : ""}`);
  },

  get(id: number) {
    return request<MenuItem>(`/api/menu/${id}`);
  },

  create(payload: MenuItemCreate) {
    return request<MenuItem>("/api/menu", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  update(id: number, payload: MenuItemUpdate) {
    return request<MenuItem>(`/api/menu/${id}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
  },

  delete(id: number) {
    return request<void>(`/api/menu/${id}`, { method: "DELETE" });
  },
};

// ---------------------------------------------------------------------------
// Inventory endpoints
// ---------------------------------------------------------------------------

export const inventoryApi = {
  list() {
    return request<InventoryRecord[]>("/api/inventory");
  },

  get(menuItemId: number) {
    return request<InventoryRecord>(`/api/inventory/${menuItemId}`);
  },

  update(menuItemId: number, payload: InventoryUpdate) {
    return request<InventoryRecord>(`/api/inventory/${menuItemId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
  },
};
