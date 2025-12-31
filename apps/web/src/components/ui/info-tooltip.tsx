"use client";

import { Info } from "lucide-react";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

interface InfoTooltipProps {
  term: string;
  explanation: string;
  className?: string;
}

export function InfoTooltip({ term, explanation, className }: InfoTooltipProps) {
  return (
    <TooltipProvider>
      <Tooltip delayDuration={300}>
        <TooltipTrigger
          className={cn(
            "inline-flex items-center gap-1 border-b border-dotted border-muted-foreground/50 cursor-help",
            className
          )}
        >
          {term}
          <Info className="h-3 w-3 text-muted-foreground" />
        </TooltipTrigger>
        <TooltipContent className="max-w-xs text-sm">
          {explanation}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

// Pre-defined tooltips for common financial terms
export const FINANCIAL_TERMS = {
  committedExpenses: {
    term: "Committed expenses",
    explanation:
      "Fixed bills that you must pay each month, like rent, utilities, and subscriptions",
  },
  flexibleSpending: {
    term: "Flexible spending",
    explanation:
      "Discretionary spending that varies month to month, like dining out, entertainment, and shopping",
  },
  pace: {
    term: "Pace",
    explanation:
      "How fast you're spending compared to your budget. 'On track' means you'll finish under budget at this rate",
  },
  recurringSeries: {
    term: "Recurring series",
    explanation:
      "A group of transactions that happen regularly, like monthly Netflix charges",
  },
  netWorth: {
    term: "Net worth",
    explanation:
      "Your total assets minus your total liabilities - a snapshot of your overall financial position",
  },
  merchantMemory: {
    term: "Merchant memory",
    explanation:
      "The system remembers how you categorize merchants and applies the same category to future transactions",
  },
  confidence: {
    term: "Confidence",
    explanation:
      "How certain the AI is about its categorization. Higher confidence means more accurate detection",
  },
  cadence: {
    term: "Cadence",
    explanation:
      "How often a recurring payment happens - weekly, biweekly, monthly, etc.",
  },
} as const;

// Helper component for pre-defined terms
export function FinancialTerm({
  termKey,
  className,
}: {
  termKey: keyof typeof FINANCIAL_TERMS;
  className?: string;
}) {
  const { term, explanation } = FINANCIAL_TERMS[termKey];
  return <InfoTooltip term={term} explanation={explanation} className={className} />;
}
