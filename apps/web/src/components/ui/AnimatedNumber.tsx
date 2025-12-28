"use client";

import { useEffect, useRef, useState } from "react";
import { cn } from "@/lib/utils";

interface AnimatedNumberProps {
  value: number;
  duration?: number;
  formatOptions?: Intl.NumberFormatOptions;
  className?: string;
  prefix?: string;
  suffix?: string;
}

export function AnimatedNumber({
  value,
  duration = 1000,
  formatOptions,
  className,
  prefix = "",
  suffix = "",
}: AnimatedNumberProps) {
  const [displayValue, setDisplayValue] = useState(0);
  const previousValue = useRef(0);
  const animationRef = useRef<number | null>(null);

  useEffect(() => {
    const startValue = previousValue.current;
    const endValue = value;
    const startTime = performance.now();

    const animate = (currentTime: number) => {
      const elapsed = currentTime - startTime;
      const progress = Math.min(elapsed / duration, 1);

      // Easing function (ease-out cubic)
      const eased = 1 - Math.pow(1 - progress, 3);

      const current = startValue + (endValue - startValue) * eased;
      setDisplayValue(current);

      if (progress < 1) {
        animationRef.current = requestAnimationFrame(animate);
      } else {
        previousValue.current = endValue;
      }
    };

    animationRef.current = requestAnimationFrame(animate);

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [value, duration]);

  const formatted = new Intl.NumberFormat("en-US", formatOptions).format(
    displayValue
  );

  return (
    <span className={cn("tabular-nums", className)} aria-label={`${prefix}${formatted}${suffix}`}>
      {prefix}
      {formatted}
      {suffix}
    </span>
  );
}

// Specialized currency animated number
export function AnimatedCurrency({
  value,
  currency = "USD",
  duration = 1000,
  className,
  showSign = false,
}: {
  value: number;
  currency?: string;
  duration?: number;
  className?: string;
  showSign?: boolean;
}) {
  const isNegative = value < 0;
  const sign = showSign ? (isNegative ? "-" : "+") : "";

  return (
    <AnimatedNumber
      value={Math.abs(value)}
      duration={duration}
      formatOptions={{
        style: "currency",
        currency,
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      }}
      prefix={sign}
      className={cn(
        className,
        isNegative
          ? "text-red-600 dark:text-red-400"
          : "text-green-600 dark:text-green-400"
      )}
    />
  );
}

// Animated percentage
export function AnimatedPercentage({
  value,
  duration = 1000,
  className,
  decimals = 1,
}: {
  value: number;
  duration?: number;
  className?: string;
  decimals?: number;
}) {
  return (
    <AnimatedNumber
      value={value}
      duration={duration}
      formatOptions={{
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals,
      }}
      suffix="%"
      className={className}
    />
  );
}

// Animated count (whole numbers)
export function AnimatedCount({
  value,
  duration = 800,
  className,
}: {
  value: number;
  duration?: number;
  className?: string;
}) {
  return (
    <AnimatedNumber
      value={value}
      duration={duration}
      formatOptions={{
        minimumFractionDigits: 0,
        maximumFractionDigits: 0,
      }}
      className={className}
    />
  );
}
