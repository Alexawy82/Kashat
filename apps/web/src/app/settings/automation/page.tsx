"use client"

import { useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Alert, AlertDescription } from "@/components/ui/alert"
import {
  Zap, Plus, Trash2, Sparkles, Loader2, Play, RefreshCw,
  CheckCircle, Settings
} from "lucide-react"
import {
  useRules,
  useRuleSuggestions,
  useCreateRule,
  useDeleteRule,
  useApplyRule,
  useApplyAllRules
} from "@/hooks/useAutomation"
import { useCategories } from "@/hooks/useCategories"

export default function AutomationSettingsPage() {
  const [newPattern, setNewPattern] = useState('')
  const [selectedCategory, setSelectedCategory] = useState('')

  const { data: rules, isLoading } = useRules()
  const { data: suggestions } = useRuleSuggestions()
  const { data: categories } = useCategories()

  const createRule = useCreateRule()
  const deleteRule = useDeleteRule()
  const applyRule = useApplyRule()
  const applyAllRules = useApplyAllRules()

  const handleCreateFromSuggestion = (suggestion: any) => {
    if (!selectedCategory) return

    const category = categories?.find((c: any) => c.id === selectedCategory)
    createRule.mutate({
      priority: 100,
      predicate: suggestion.recommended_predicate,
      action: {
        assign_category_id: selectedCategory,
        category_name: category?.name || 'Unknown'
      },
      enabled: true
    })
  }

  const handleQuickCreate = () => {
    if (!newPattern.trim() || !selectedCategory) return

    const category = categories?.find((c: any) => c.id === selectedCategory)
    createRule.mutate({
      priority: 100,
      predicate: { description_regex: newPattern.toLowerCase() },
      action: {
        assign_category_id: selectedCategory,
        category_name: category?.name || 'Unknown'
      },
      enabled: true
    }, {
      onSuccess: () => {
        setNewPattern('')
        setSelectedCategory('')
      }
    })
  }

  const handleDelete = (ruleId: string) => {
    if (confirm('Delete this rule?')) {
      deleteRule.mutate(ruleId)
    }
  }

  const handleApplyAll = () => {
    applyAllRules.mutate(undefined, {
      onSuccess: (data: any) => {
        alert(`Applied rules: ${data?.rules_matched || 0} rules matched, ${data?.transactions_updated || 0} transactions updated`)
      }
    })
  }

  return (
    <div className="space-y-6">
      {/* Action Bar */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          Automate your categorization with pattern-based rules.
        </p>
        <Button
          variant="outline"
          size="sm"
          onClick={handleApplyAll}
          disabled={applyAllRules.isPending}
        >
          {applyAllRules.isPending ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <RefreshCw className="mr-2 h-4 w-4" />
          )}
          Apply All Rules
        </Button>
      </div>

      {/* Success Alert */}
      {createRule.isSuccess && (
        <Alert className="bg-green-50 border-green-200">
          <CheckCircle className="h-4 w-4 text-green-600" />
          <AlertDescription className="text-green-800">
            Rule created successfully!
          </AlertDescription>
        </Alert>
      )}

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Active Rules */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Settings className="h-5 w-5" />
              Active Rules
            </CardTitle>
            <CardDescription>
              {rules?.length || 0} rules controlling your categorization
            </CardDescription>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="flex justify-center p-8">
                <Loader2 className="h-6 w-6 animate-spin" />
              </div>
            ) : (
              <div className="max-h-[350px] overflow-y-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Pattern</TableHead>
                      <TableHead>Category</TableHead>
                      <TableHead>Priority</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {rules?.map((rule: any) => (
                      <TableRow key={rule.id}>
                        <TableCell>
                          <code className="text-xs bg-muted px-2 py-1 rounded">
                            {rule.predicate?.description_regex ||
                             rule.predicate?.payee_contains ||
                             JSON.stringify(rule.predicate).slice(0, 50)}
                          </code>
                        </TableCell>
                        <TableCell>
                          <Badge variant="secondary">
                            {rule.action?.category_name || 'Unknown'}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline">{rule.priority}</Badge>
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex justify-end gap-1">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => applyRule.mutate(rule.id)}
                              disabled={applyRule.isPending}
                            >
                              <Play className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleDelete(rule.id)}
                              disabled={deleteRule.isPending}
                            >
                              <Trash2 className="h-4 w-4 text-red-500 hover:text-red-600" />
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                    {rules?.length === 0 && (
                      <TableRow>
                        <TableCell colSpan={4} className="text-center py-8 text-muted-foreground italic">
                          No custom rules defined yet. Create one below or adopt an AI suggestion.
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </div>
            )}

            {/* Quick Create Form */}
            <div className="mt-6 pt-6 border-t">
              <h4 className="text-sm font-medium mb-3">Quick Create Rule</h4>
              <div className="flex gap-2">
                <Input
                  placeholder="Pattern (e.g., starbucks, amazon)"
                  value={newPattern}
                  onChange={(e) => setNewPattern(e.target.value)}
                  className="flex-1"
                />
                <select
                  value={selectedCategory}
                  onChange={(e) => setSelectedCategory(e.target.value)}
                  className="border rounded-md px-3 py-2 text-sm bg-background"
                >
                  <option value="">Select category...</option>
                  {categories?.map((cat: any) => (
                    <option key={cat.id} value={cat.id}>{cat.name}</option>
                  ))}
                </select>
                <Button
                  onClick={handleQuickCreate}
                  disabled={!newPattern.trim() || !selectedCategory || createRule.isPending}
                >
                  {createRule.isPending ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Plus className="h-4 w-4" />
                  )}
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* AI Suggestions Sidebar */}
        <Card className="bg-slate-50 border-dashed border-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-amber-500" />
              AI Suggestions
            </CardTitle>
            <CardDescription>
              Based on your uncategorized transactions
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 max-h-[400px] overflow-y-auto">
            {suggestions?.length === 0 ? (
              <p className="text-center text-sm text-muted-foreground py-4 italic">
                AI is still learning your patterns...
              </p>
            ) : (
              suggestions?.slice(0, 8).map((suggestion: any, i: number) => (
                <div key={i} className="bg-white p-4 rounded-lg border shadow-sm space-y-3">
                  <div className="flex items-start justify-between">
                    <div className="text-xs font-medium text-muted-foreground">
                      "{suggestion.payee}"
                    </div>
                    <Badge variant="outline" className="text-xs">
                      {suggestion.count} txns
                    </Badge>
                  </div>
                  <div className="text-xs">
                    <code className="bg-muted px-1 py-0.5 rounded">
                      {suggestion.recommended_predicate?.description_regex}
                    </code>
                  </div>
                  <div className="flex gap-2">
                    <select
                      className="flex-1 border rounded px-2 py-1 text-xs bg-background"
                      value={selectedCategory}
                      onChange={(e) => setSelectedCategory(e.target.value)}
                    >
                      <option value="">Category...</option>
                      {categories?.map((cat: any) => (
                        <option key={cat.id} value={cat.id}>{cat.name}</option>
                      ))}
                    </select>
                    <Button
                      size="sm"
                      variant="outline"
                      className="text-xs"
                      onClick={() => handleCreateFromSuggestion(suggestion)}
                      disabled={!selectedCategory || createRule.isPending}
                    >
                      <Zap className="h-3 w-3 mr-1" />
                      Adopt
                    </Button>
                  </div>
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
