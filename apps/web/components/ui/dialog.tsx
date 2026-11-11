"use client";

import * as React from "react";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import { cn } from "../../lib/utils";

export const Dialog = DialogPrimitive.Root;
export const DialogTrigger = DialogPrimitive.Trigger;
export const DialogClose = DialogPrimitive.Close;
export const DialogTitle = DialogPrimitive.Title;
export const DialogDescription = DialogPrimitive.Description;

// shadcn/ui composition: Radix owns modal semantics, focus trapping and return.
export function DialogContent({ children, className, onOpenAutoFocus, onCloseAutoFocus, ...props }: React.ComponentProps<typeof DialogPrimitive.Content>) {
  const returnFocus = React.useRef<HTMLElement | null>(null);
  return <DialogPrimitive.Portal>
    <DialogPrimitive.Overlay className="dialog-overlay" />
    <DialogPrimitive.Content className={cn("dialog-content", className)} {...props}
      onOpenAutoFocus={(event) => { returnFocus.current = document.activeElement as HTMLElement | null; onOpenAutoFocus?.(event); }}
      onCloseAutoFocus={(event) => { onCloseAutoFocus?.(event); if (!event.defaultPrevented && returnFocus.current?.isConnected) { event.preventDefault(); returnFocus.current.focus(); } }}>
      {children}
      <DialogPrimitive.Close className="dialog-close" aria-label="Close"><X size={20} aria-hidden="true" /></DialogPrimitive.Close>
    </DialogPrimitive.Content>
  </DialogPrimitive.Portal>;
}
