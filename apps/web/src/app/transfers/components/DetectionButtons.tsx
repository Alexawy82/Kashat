"use client"

import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Badge } from "@/components/ui/badge"
import {
  Loader2,
  Scan,
  Brain,
  Sparkles,
  Zap,
  Settings2,
} from "lucide-react"

interface DetectionButtonsProps {
  onDetect: (useAI: boolean) => void
  onEnrich: () => void
  isDetecting: boolean
  isEnriching: boolean
  enrichmentStats?: {
    unclassified: number
    total: number
  }
  onRunFullPipeline?: () => void
  isRunningPipeline?: boolean
}

export function DetectionButtons({
  onDetect,
  onEnrich,
  isDetecting,
  isEnriching,
  enrichmentStats,
  onRunFullPipeline,
  isRunningPipeline,
}: DetectionButtonsProps) {
  const unclassified = enrichmentStats?.unclassified || 0
  const isAnyLoading = isDetecting || isEnriching || isRunningPipeline

  // Run full pipeline: Detect → Enrich
  const handleFullPipeline = async () => {
    if (onRunFullPipeline) {
      onRunFullPipeline()
      return
    }

    // Run detection with AI
    onDetect(true)
  }

  const getPipelineLabel = () => {
    if (isDetecting) return "Detecting..."
    if (isEnriching) return "Enriching..."
    return "Analyze P2P"
  }

  return (
    <div className="flex items-center gap-2">
      {/* Main Action: Full Pipeline */}
      <Button
        onClick={handleFullPipeline}
        disabled={isAnyLoading}
        className="gap-2"
      >
        {isAnyLoading ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" />
            {getPipelineLabel()}
          </>
        ) : (
          <>
            <Zap className="h-4 w-4" />
            Analyze P2P
            <Sparkles className="h-3 w-3" />
          </>
        )}
      </Button>

      {/* Advanced Options Dropdown */}
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="outline" size="icon" disabled={isAnyLoading}>
            <Settings2 className="h-4 w-4" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-56">
          <DropdownMenuItem onClick={() => onDetect(false)}>
            <Scan className="h-4 w-4 mr-2" />
            Quick Detect
            <span className="ml-auto text-xs text-muted-foreground">Fast</span>
          </DropdownMenuItem>
          <DropdownMenuItem onClick={() => onDetect(true)}>
            <Brain className="h-4 w-4 mr-2" />
            AI Detect
            <Sparkles className="h-3 w-3 ml-2 text-purple-500" />
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem onClick={onEnrich}>
            <Brain className="h-4 w-4 mr-2" />
            Enrich Only
            {unclassified > 0 && (
              <Badge variant="secondary" className="ml-auto text-xs">
                {unclassified}
              </Badge>
            )}
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  )
}
