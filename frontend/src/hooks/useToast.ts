"use client";

import { useCallback, useState } from "react";
import type { ToastMessage, ToastVariant } from "@/components/Toast";

let _counter = 0;

export function useToast() {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const push = useCallback((variant: ToastVariant, message: string) => {
    const id = String(++_counter);
    setToasts((prev) => [...prev, { id, variant, message }]);
  }, []);

  const dismiss = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const success = useCallback(
    (msg: string) => push("success", msg),
    [push]
  );
  const error = useCallback(
    (msg: string) => push("error", msg),
    [push]
  );

  return { toasts, dismiss, success, error };
}
