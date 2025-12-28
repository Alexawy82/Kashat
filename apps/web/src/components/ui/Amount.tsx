import { cn } from "@/lib/utils";

interface AmountProps {
  value: number;
  currency?: string;
  showSign?: boolean;
  className?: string;
  size?: "sm" | "md" | "lg";
}

export function Amount({
  value,
  currency = "USD",
  showSign = false,
  className,
  size = "md",
}: AmountProps) {
  const isNegative = value < 0;
  const absValue = Math.abs(value);

  const formatted = new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(absValue);

  const sign = showSign ? (isNegative ? "-" : "+") : isNegative ? "-" : "";
  const displayValue = sign + formatted.replace("-", "");

  // Accessible label for screen readers
  const accessibleLabel = `${isNegative ? "expense" : "income"} of ${formatted}`;

  const sizeClasses = {
    sm: "text-sm",
    md: "text-base",
    lg: "text-lg font-semibold",
  };

  return (
    <span
      className={cn(
        sizeClasses[size],
        isNegative ? "text-red-600 dark:text-red-400" : "text-green-600 dark:text-green-400",
        className
      )}
      aria-label={accessibleLabel}
      role="text"
    >
      {displayValue}
    </span>
  );
}

// Currency-only display without color coding
export function Currency({
  value,
  currency = "USD",
  className,
}: {
  value: number;
  currency?: string;
  className?: string;
}) {
  const formatted = new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);

  return (
    <span className={className} aria-label={`${formatted}`}>
      {formatted}
    </span>
  );
}
