import { X } from "lucide-react";
import type { Toast } from "../types";

type ToastStackProps = {
  toasts: Toast[];
  onDismiss: (toastId: number) => void;
};

export function ToastStack({ toasts, onDismiss }: ToastStackProps) {
  if (toasts.length === 0) {
    return null;
  }

  return (
    <div className="toastStack" aria-live="polite" aria-label="Notifications">
      {toasts.map((toast) => (
        <div className="toastNotice" role="status" key={toast.id}>
          <span>{toast.message}</span>
          <button type="button" onClick={() => onDismiss(toast.id)} aria-label="Dismiss notification">
            <X size={15} aria-hidden="true" />
          </button>
        </div>
      ))}
    </div>
  );
}
