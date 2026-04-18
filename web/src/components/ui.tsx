import * as React from "react";
import { cn } from "@/lib/utils";

type BtnVariant = "primary" | "secondary" | "ghost" | "danger";
type BtnSize = "sm" | "md" | "lg";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: BtnVariant;
  size?: BtnSize;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "primary", size = "md", ...props }, ref) => {
    const base =
      "inline-flex items-center justify-center gap-1.5 font-medium transition-colors disabled:opacity-40 disabled:pointer-events-none";
    const sizes: Record<BtnSize, string> = {
      sm: "h-8 px-3 text-[13px] rounded-lg",
      md: "h-10 px-4 text-sm rounded-lg",
      lg: "h-12 px-5 text-[15px] rounded-xl",
    };
    const variants: Record<BtnVariant, string> = {
      primary: "bg-ink text-white hover:bg-black",
      secondary: "bg-surface text-ink border border-border hover:bg-white",
      ghost: "text-ink hover:bg-surface",
      danger: "text-red-600 hover:bg-red-50",
    };
    return (
      <button
        ref={ref}
        className={cn(base, sizes[size], variants[variant], className)}
        {...props}
      />
    );
  }
);
Button.displayName = "Button";

export const Input = React.forwardRef<
  HTMLInputElement,
  React.InputHTMLAttributes<HTMLInputElement>
>(({ className, ...props }, ref) => (
  <input
    ref={ref}
    className={cn(
      "h-10 w-full rounded-lg border border-border bg-white px-3 text-sm placeholder:text-subtle",
      "focus:border-ink focus:outline-none transition-colors",
      className
    )}
    {...props}
  />
));
Input.displayName = "Input";

export const Textarea = React.forwardRef<
  HTMLTextAreaElement,
  React.TextareaHTMLAttributes<HTMLTextAreaElement>
>(({ className, ...props }, ref) => (
  <textarea
    ref={ref}
    className={cn(
      "w-full rounded-lg border border-border bg-white px-3 py-2.5 text-sm placeholder:text-subtle resize-none",
      "focus:border-ink focus:outline-none transition-colors",
      className
    )}
    {...props}
  />
));
Textarea.displayName = "Textarea";

export function Card({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "rounded-xl border border-border bg-white",
        className
      )}
      {...props}
    />
  );
}
