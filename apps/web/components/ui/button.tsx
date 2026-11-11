import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "../../lib/utils";

// shadcn/ui button pattern, styled with the approved SourcePilot tokens.
const buttonVariants = cva("inline-flex min-h-11 items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold disabled:pointer-events-none disabled:opacity-60", {
  variants: { variant: {
    default: "bg-primary text-primary-foreground hover:bg-primary-hover",
    outline: "border border-input bg-background text-foreground hover:bg-muted",
    ghost: "bg-transparent text-primary hover:bg-accent",
    destructive: "border border-destructive bg-background text-destructive hover:bg-muted",
  } }, defaultVariants: { variant: "default" },
});
export function Button({ className, variant, asChild = false, ...props }: React.ComponentProps<"button"> & VariantProps<typeof buttonVariants> & { asChild?: boolean }) {
  const Comp = asChild ? Slot : "button";
  return <Comp data-slot="button" className={cn(buttonVariants({ variant, className }))} {...props} />;
}
