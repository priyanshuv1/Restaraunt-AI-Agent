"use client";

import { useEffect, useRef, useState } from "react";
import { X, Loader2 } from "lucide-react";
import { z } from "zod";
import { type MenuItem, menuApi, ApiError } from "@/lib/api";
// ---------------------------------------------------------------------------
// Validation schema (mirrors backend constraints)
// ---------------------------------------------------------------------------

const schema = z.object({
  name: z.string().min(1, "Name is required").max(120),
  category: z.string().min(1, "Category is required").max(50),
  description: z.string().max(1000).default(""),
  price: z
    .string()
    .min(1, "Price is required")
    .refine((v) => !isNaN(parseFloat(v)) && parseFloat(v) > 0, {
      message: "Price must be greater than 0",
    }),
  is_available: z.boolean().default(true),
  dietary_tags: z.string().default(""),
});

type FormFields = z.infer<typeof schema>;

// ---------------------------------------------------------------------------
// Category options from the existing seed data
// ---------------------------------------------------------------------------

const CATEGORIES = [
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
// Props
// ---------------------------------------------------------------------------

interface MenuItemModalProps {
  item?: MenuItem | null; // null/undefined = create mode
  onClose: () => void;
  onSaved: (item: MenuItem) => void;
  onError: (msg: string) => void;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function MenuItemModal({
  item,
  onClose,
  onSaved,
  onError,
}: MenuItemModalProps) {
  const isEdit = !!item;
  const dialogRef = useRef<HTMLDialogElement>(null);

  const [fields, setFields] = useState<FormFields>({
    name: item?.name ?? "",
    category: item?.category ?? "",
    description: item?.description ?? "",
    price: item?.price ?? "",
    is_available: item?.is_available ?? true,
    dietary_tags: item?.dietary_tags?.join(", ") ?? "",
  });
  const [errors, setErrors] = useState<Partial<Record<keyof FormFields, string>>>({});
  const [saving, setSaving] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  // Trap focus inside the dialog
  useEffect(() => {
    dialogRef.current?.focus();
  }, []);

  // Close on Escape
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);

  function set(key: keyof FormFields, value: string | boolean) {
    setFields((prev) => ({ ...prev, [key]: value }));
    setErrors((prev) => ({ ...prev, [key]: undefined }));
    setSubmitError(null);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitError(null);

    const result = schema.safeParse(fields);
    if (!result.success) {
      const errs: Partial<Record<keyof FormFields, string>> = {};
      for (const issue of result.error.issues) {
        const key = issue.path[0] as keyof FormFields;
        errs[key] = issue.message;
      }
      setErrors(errs);
      return;
    }

    const { name, category, description, price, is_available, dietary_tags } =
      result.data;

    const tags = dietary_tags
      .split(",")
      .map((t) => t.trim().toLowerCase())
      .filter(Boolean);

    setSaving(true);
    try {
      let saved: MenuItem;
      if (isEdit) {
        saved = await menuApi.update(item!.id, {
          name,
          category,
          description,
          price,
          is_available,
          dietary_tags: tags,
        });
      } else {
        saved = await menuApi.create({
          name,
          category,
          description,
          price,
          is_available,
          dietary_tags: tags,
        });
      }
      onSaved(saved);
    } catch (err) {
      const msg =
        err instanceof ApiError
          ? err.detail
          : "Something went wrong. Please try again.";
      setSubmitError(msg);
      onError(msg);
    } finally {
      setSaving(false);
    }
  }

  return (
    /* Backdrop */
    <div
      className="fixed inset-0 z-40 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <dialog
        ref={dialogRef}
        open
        aria-modal="true"
        aria-label={isEdit ? "Edit menu item" : "Add menu item"}
        tabIndex={-1}
        className="relative w-full max-w-lg bg-white rounded-2xl shadow-2xl p-0 outline-none overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 pt-5 pb-4 border-b border-zinc-100">
          <h2 className="text-lg font-semibold text-zinc-900">
            {isEdit ? "Edit Menu Item" : "Add Menu Item"}
          </h2>
          <button
            onClick={onClose}
            aria-label="Close dialog"
            className="p-2 rounded-xl hover:bg-zinc-100 transition-colors"
          >
            <X className="w-4 h-4 text-zinc-500" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} noValidate>
          <div className="px-6 py-5 space-y-4 max-h-[70vh] overflow-y-auto">
            {/* Name */}
            <Field label="Name" error={errors.name} required>
              <input
                type="text"
                value={fields.name}
                onChange={(e) => set("name", e.target.value)}
                placeholder="e.g. Cappuccino"
                maxLength={120}
                className={inputClass(!!errors.name)}
                aria-invalid={!!errors.name}
                aria-describedby={errors.name ? "name-err" : undefined}
              />
              {errors.name && (
                <FieldError id="name-err" msg={errors.name} />
              )}
            </Field>

            {/* Category */}
            <Field label="Category" error={errors.category} required>
              <div className="flex gap-2 flex-wrap">
                {CATEGORIES.map((cat) => (
                  <button
                    key={cat}
                    type="button"
                    onClick={() => set("category", cat)}
                    className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-colors ${
                      fields.category === cat
                        ? "bg-amber-600 border-amber-600 text-white"
                        : "border-zinc-300 text-zinc-600 hover:border-amber-400 hover:text-amber-700"
                    }`}
                  >
                    {cat}
                  </button>
                ))}
              </div>
              <input
                type="text"
                value={fields.category}
                onChange={(e) => set("category", e.target.value)}
                placeholder="Or type a custom category"
                maxLength={50}
                className={`mt-2 ${inputClass(!!errors.category)}`}
                aria-invalid={!!errors.category}
                aria-describedby={errors.category ? "cat-err" : undefined}
              />
              {errors.category && (
                <FieldError id="cat-err" msg={errors.category} />
              )}
            </Field>

            {/* Description */}
            <Field label="Description" error={errors.description}>
              <textarea
                value={fields.description}
                onChange={(e) => set("description", e.target.value)}
                placeholder="Short description of the item"
                rows={2}
                maxLength={1000}
                className={`resize-none ${inputClass(!!errors.description)}`}
              />
            </Field>

            {/* Price */}
            <Field label="Price (₹)" error={errors.price} required>
              <input
                type="number"
                value={fields.price}
                onChange={(e) => set("price", e.target.value)}
                placeholder="0.00"
                min="0.01"
                step="0.01"
                className={inputClass(!!errors.price)}
                aria-invalid={!!errors.price}
                aria-describedby={errors.price ? "price-err" : undefined}
              />
              {errors.price && (
                <FieldError id="price-err" msg={errors.price} />
              )}
            </Field>

            {/* Dietary tags */}
            <Field label="Dietary Tags" error={errors.dietary_tags}>
              <input
                type="text"
                value={fields.dietary_tags}
                onChange={(e) => set("dietary_tags", e.target.value)}
                placeholder="e.g. vegetarian, vegan, gluten-free"
                className={inputClass(false)}
              />
              <p className="mt-1 text-xs text-zinc-400">
                Comma-separated tags.
              </p>
            </Field>

            {/* Availability */}
            <div className="flex items-center gap-3">
              <button
                type="button"
                role="switch"
                aria-checked={fields.is_available}
                onClick={() => set("is_available", !fields.is_available)}
                className={`relative inline-flex h-6 w-11 shrink-0 rounded-full transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-amber-500 ${
                  fields.is_available ? "bg-amber-600" : "bg-zinc-300"
                }`}
              >
                <span
                  className={`inline-block h-5 w-5 mt-0.5 rounded-full bg-white shadow transition-transform ${
                    fields.is_available ? "translate-x-5" : "translate-x-0.5"
                  }`}
                />
              </button>
              <label className="text-sm text-zinc-700 font-medium select-none">
                Available to order
              </label>
            </div>

            {/* Submit error */}
            {submitError && (
              <p
                role="alert"
                className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg border border-red-200"
              >
                {submitError}
              </p>
            )}
          </div>

          {/* Footer */}
          <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-zinc-100 bg-zinc-50">
            <button
              type="button"
              onClick={onClose}
              disabled={saving}
              className="px-4 py-2 text-sm font-medium text-zinc-600 hover:text-zinc-900 disabled:opacity-50 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="flex items-center gap-2 px-5 py-2 bg-amber-600 hover:bg-amber-700 disabled:opacity-60 text-white text-sm font-semibold rounded-xl transition-colors"
            >
              {saving && <Loader2 className="w-4 h-4 animate-spin" />}
              {saving ? "Saving…" : isEdit ? "Save Changes" : "Add Item"}
            </button>
          </div>
        </form>
      </dialog>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Small helpers
// ---------------------------------------------------------------------------

function inputClass(hasError: boolean) {
  return `w-full rounded-xl border px-3 py-2 text-sm text-zinc-900 placeholder:text-zinc-400 outline-none focus:ring-2 transition-shadow ${
    hasError
      ? "border-red-400 focus:ring-red-200"
      : "border-zinc-300 focus:ring-amber-200 focus:border-amber-400"
  }`;
}

function Field({
  label,
  required,
  children,
}: {
  label: string;
  error?: string;
  required?: boolean;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1.5">
      <label className="block text-sm font-medium text-zinc-700">
        {label}
        {required && <span className="text-red-500 ml-0.5">*</span>}
      </label>
      {children}
    </div>
  );
}

function FieldError({ id, msg }: { id: string; msg: string }) {
  return (
    <p id={id} role="alert" className="text-xs text-red-600 mt-1">
      {msg}
    </p>
  );
}
