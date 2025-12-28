import { cn } from "@/lib/utils";
import { Loader2 } from "lucide-react";

interface LoadingSpinnerProps {
  size?: "sm" | "md" | "lg";
  className?: string;
  label?: string;
}

export function LoadingSpinner({
  size = "md",
  className,
  label = "Loading...",
}: LoadingSpinnerProps) {
  const sizeClasses = {
    sm: "h-4 w-4",
    md: "h-6 w-6",
    lg: "h-8 w-8",
  };

  return (
    <div
      role="status"
      aria-live="polite"
      className={cn("flex items-center justify-center", className)}
    >
      <Loader2
        className={cn("animate-spin text-muted-foreground", sizeClasses[size])}
        aria-hidden="true"
      />
      <span className="sr-only">{label}</span>
    </div>
  );
}

// Full page loading overlay
export function LoadingOverlay({ label = "Loading..." }: { label?: string }) {
  return (
    <div
      role="status"
      aria-live="polite"
      className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm"
    >
      <div className="flex flex-col items-center gap-3">
        <Loader2 className="h-10 w-10 animate-spin text-primary" aria-hidden="true" />
        <p className="text-sm text-muted-foreground">{label}</p>
      </div>
    </div>
  );
}

// Card skeleton for loading states
export function CardSkeleton({ className }: { className?: string }) {
  return (
    <div
      role="status"
      aria-label="Loading content"
      className={cn(
        "rounded-xl border bg-card p-6 space-y-4 animate-pulse",
        className
      )}
    >
      <div className="h-4 w-24 bg-muted rounded" />
      <div className="h-8 w-32 bg-muted rounded" />
      <div className="h-20 w-full bg-muted rounded" />
      <span className="sr-only">Loading...</span>
    </div>
  );
}

// Transaction row skeleton
export function TransactionSkeleton() {
  return (
    <div
      role="status"
      aria-label="Loading transaction"
      className="flex items-center gap-4 p-4 animate-pulse"
    >
      <div className="h-10 w-10 rounded-full bg-muted" />
      <div className="space-y-2 flex-1">
        <div className="h-4 w-48 bg-muted rounded" />
        <div className="h-3 w-24 bg-muted rounded" />
      </div>
      <div className="h-4 w-20 bg-muted rounded" />
      <span className="sr-only">Loading transaction...</span>
    </div>
  );
}
