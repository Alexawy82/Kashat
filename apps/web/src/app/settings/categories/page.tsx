'use client'

import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription } from '@/components/ui/alert'
import {
  Tags, Plus, Trash2, Edit2, ChevronRight, Loader2,
  CheckCircle, AlertTriangle, FolderTree
} from 'lucide-react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { client } from '@/lib/api-client'

export default function CategoriesSettingsPage() {
  const [newCategoryName, setNewCategoryName] = useState('')
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editName, setEditName] = useState('')
  const queryClient = useQueryClient()

  // Fetch categories
  const { data: categoriesData, isLoading } = useQuery({
    queryKey: ['categories'],
    queryFn: async () => {
      const { data, error } = await client.get('/api/categories')
      if (error) throw new Error('Failed to fetch categories')
      return data as any[]
    },
  })

  // Fetch AI category stats
  const { data: statsData } = useQuery({
    queryKey: ['ai-category-stats'],
    queryFn: async () => {
      const { data, error } = await client.get('/api/ai/categories/usage-stats')
      if (error) return null
      return data as any
    },
  })

  // Fetch AI gap analysis
  const { data: gapData } = useQuery({
    queryKey: ['ai-category-gaps'],
    queryFn: async () => {
      const { data, error } = await client.get('/api/ai/categories/gap-analysis')
      if (error) return null
      return data as any
    },
  })

  // Create category
  const createCategory = useMutation({
    mutationFn: async (name: string) => {
      const { data, error } = await client.post('/api/categories', {
        body: { name }
      })
      if (error) throw new Error('Failed to create category')
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['categories'] })
      setNewCategoryName('')
    }
  })

  // Update category
  const updateCategory = useMutation({
    mutationFn: async ({ id, name }: { id: string; name: string }) => {
      const { data, error } = await client.patch('/api/categories/{category_id}', {
        params: { path: { category_id: id } },
        body: { name }
      })
      if (error) throw new Error('Failed to update category')
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['categories'] })
      setEditingId(null)
      setEditName('')
    }
  })

  // Delete category
  const deleteCategory = useMutation({
    mutationFn: async (id: string) => {
      const { error } = await client.delete('/api/categories/{category_id}', {
        params: { path: { category_id: id } }
      })
      if (error) throw new Error('Failed to delete category')
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['categories'] })
    }
  })

  // Bootstrap categories
  const bootstrapCategories = useMutation({
    mutationFn: async () => {
      const { data, error } = await client.post('/api/ai/categories/bootstrap')
      if (error) throw new Error('Failed to bootstrap categories')
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['categories'] })
      queryClient.invalidateQueries({ queryKey: ['ai-category-gaps'] })
    }
  })

  const categories = categoriesData || []
  const stats = statsData || {}
  const gaps = gapData || {}

  // Build category tree
  const rootCategories = categories.filter((c: any) => !c.parent_id)
  const childCategories = (parentId: string) =>
    categories.filter((c: any) => c.parent_id === parentId)

  const handleCreate = () => {
    if (newCategoryName.trim()) {
      createCategory.mutate(newCategoryName.trim())
    }
  }

  const handleUpdate = (id: string) => {
    if (editName.trim()) {
      updateCategory.mutate({ id, name: editName.trim() })
    }
  }

  const handleDelete = (id: string, name: string) => {
    if (confirm(`Delete category "${name}"? This cannot be undone.`)) {
      deleteCategory.mutate(id)
    }
  }

  const startEdit = (id: string, name: string) => {
    setEditingId(id)
    setEditName(name)
  }

  return (
    <div className="space-y-6">
      {/* Action Bar */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          Organize your transactions with custom categories.
        </p>
        {gaps.missing_count > 0 && (
          <Button
            onClick={() => bootstrapCategories.mutate()}
            disabled={bootstrapCategories.isPending}
            variant="outline"
            size="sm"
          >
            {bootstrapCategories.isPending ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Plus className="mr-2 h-4 w-4" />
            )}
            Bootstrap Standard Categories
          </Button>
        )}
      </div>

      {/* AI Stats Alert */}
      {gaps.success_rate !== undefined && gaps.success_rate < 70 && (
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>
            AI categorization success rate is low ({gaps.success_rate?.toFixed(1)}%).
            {gaps.missing_count > 0 && ` ${gaps.missing_count} suggested categories are missing.`}
            Consider bootstrapping standard categories to improve AI accuracy.
          </AlertDescription>
        </Alert>
      )}

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Category List */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FolderTree className="h-5 w-5" />
              All Categories
            </CardTitle>
            <CardDescription>
              {categories.length} categories total
            </CardDescription>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="flex justify-center p-8">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              </div>
            ) : categories.length === 0 ? (
              <div className="text-center p-8 text-muted-foreground">
                <Tags className="h-12 w-12 mx-auto mb-2 opacity-50" />
                <p className="text-sm">No categories yet</p>
                <p className="text-xs">Create your first category below</p>
              </div>
            ) : (
              <div className="space-y-2 max-h-[400px] overflow-y-auto">
                {rootCategories.map((category: any) => (
                  <div key={category.id}>
                    {/* Parent Category */}
                    <div className="flex items-center justify-between p-2 rounded-lg hover:bg-muted/50">
                      <div className="flex items-center gap-2">
                        <Tags className="h-4 w-4 text-muted-foreground" />
                        {editingId === category.id ? (
                          <Input
                            value={editName}
                            onChange={(e) => setEditName(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && handleUpdate(category.id)}
                            className="h-7 w-48"
                            autoFocus
                          />
                        ) : (
                          <span className="text-sm font-medium">{category.name}</span>
                        )}
                      </div>
                      <div className="flex items-center gap-1">
                        {editingId === category.id ? (
                          <Button size="sm" variant="ghost" onClick={() => handleUpdate(category.id)}>
                            <CheckCircle className="h-4 w-4 text-green-500" />
                          </Button>
                        ) : (
                          <>
                            <Button size="sm" variant="ghost" onClick={() => startEdit(category.id, category.name)}>
                              <Edit2 className="h-4 w-4" />
                            </Button>
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => handleDelete(category.id, category.name)}
                              className="text-red-500 hover:text-red-600"
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </>
                        )}
                      </div>
                    </div>

                    {/* Child Categories */}
                    {childCategories(category.id).map((child: any) => (
                      <div
                        key={child.id}
                        className="flex items-center justify-between p-2 pl-8 rounded-lg hover:bg-muted/50"
                      >
                        <div className="flex items-center gap-2">
                          <ChevronRight className="h-3 w-3 text-muted-foreground" />
                          {editingId === child.id ? (
                            <Input
                              value={editName}
                              onChange={(e) => setEditName(e.target.value)}
                              onKeyDown={(e) => e.key === 'Enter' && handleUpdate(child.id)}
                              className="h-7 w-40"
                              autoFocus
                            />
                          ) : (
                            <span className="text-sm">{child.name}</span>
                          )}
                        </div>
                        <div className="flex items-center gap-1">
                          {editingId === child.id ? (
                            <Button size="sm" variant="ghost" onClick={() => handleUpdate(child.id)}>
                              <CheckCircle className="h-4 w-4 text-green-500" />
                            </Button>
                          ) : (
                            <>
                              <Button size="sm" variant="ghost" onClick={() => startEdit(child.id, child.name)}>
                                <Edit2 className="h-3 w-3" />
                              </Button>
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => handleDelete(child.id, child.name)}
                                className="text-red-500 hover:text-red-600"
                              >
                                <Trash2 className="h-3 w-3" />
                              </Button>
                            </>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                ))}
              </div>
            )}

            {/* Add New Category */}
            <div className="mt-4 pt-4 border-t flex gap-2">
              <Input
                placeholder="New category name..."
                value={newCategoryName}
                onChange={(e) => setNewCategoryName(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
              />
              <Button onClick={handleCreate} disabled={createCategory.isPending || !newCategoryName.trim()}>
                {createCategory.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Plus className="h-4 w-4" />
                )}
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Stats Sidebar */}
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">AI Category Stats</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Total Categories</span>
                <span className="font-medium">{categories.length}</span>
              </div>
              {stats.top_categories && (
                <>
                  <div className="text-xs text-muted-foreground font-medium pt-2">Top Used</div>
                  {stats.top_categories.slice(0, 5).map((cat: any, i: number) => (
                    <div key={i} className="flex justify-between text-sm">
                      <span className="text-muted-foreground truncate max-w-[120px]">{cat.name}</span>
                      <Badge variant="secondary">{cat.count}</Badge>
                    </div>
                  ))}
                </>
              )}
            </CardContent>
          </Card>

          {gaps.missing_categories && gaps.missing_categories.length > 0 && (
            <Card className="border-orange-200">
              <CardHeader>
                <CardTitle className="text-sm flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4 text-orange-500" />
                  Missing Categories
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {gaps.missing_categories.slice(0, 8).map((cat: string, i: number) => (
                    <Badge key={i} variant="outline" className="mr-1 text-xs">
                      {cat}
                    </Badge>
                  ))}
                  {gaps.missing_categories.length > 8 && (
                    <p className="text-xs text-muted-foreground mt-2">
                      +{gaps.missing_categories.length - 8} more
                    </p>
                  )}
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}
