"use client";

import { useState } from "react";
import { HelpCircle, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface PageHeaderProps {
  title: string;
  description: string;
  helpItems?: string[];
  learnMoreUrl?: string;
  action?: React.ReactNode;
  className?: string;
}

export function PageHeader({
  title,
  description,
  helpItems,
  learnMoreUrl,
  action,
  className,
}: PageHeaderProps) {
  const [showHelp, setShowHelp] = useState(false);

  return (
    <div className={cn("mb-6", className)}>
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <h1 className="text-2xl font-bold tracking-tight">{title}</h1>
          <p className="text-muted-foreground mt-1">{description}</p>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          {helpItems && helpItems.length > 0 && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowHelp(!showHelp)}
              className={cn(showHelp && "bg-accent")}
            >
              <HelpCircle className="h-4 w-4 mr-1" />
              Help
            </Button>
          )}
          {action}
        </div>
      </div>

      {showHelp && helpItems && helpItems.length > 0 && (
        <Card className="mt-4 bg-blue-50 dark:bg-blue-950/30 border-blue-200 dark:border-blue-800">
          <CardContent className="pt-4 pb-4">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <h4 className="font-medium text-blue-900 dark:text-blue-100 mb-2">
                  What you can do here:
                </h4>
                <ul className="list-disc list-inside space-y-1 text-sm text-blue-800 dark:text-blue-200">
                  {helpItems.map((item, i) => (
                    <li key={i}>{item}</li>
                  ))}
                </ul>
                {learnMoreUrl && (
                  <a
                    href={learnMoreUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-600 dark:text-blue-400 text-sm mt-3 inline-block hover:underline"
                  >
                    Learn more →
                  </a>
                )}
              </div>
              <Button
                variant="ghost"
                size="icon"
                className="h-6 w-6 text-blue-600 dark:text-blue-400 hover:bg-blue-100 dark:hover:bg-blue-900"
                onClick={() => setShowHelp(false)}
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
