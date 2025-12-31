'use client'

import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter,
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { useConfirm } from '@/components/ui/ConfirmDialog'
import { toast } from '@/components/ui/Toaster'
import {
  Plus,
  Trash2,
  Edit2,
  CreditCard,
  Wallet,
  Building2,
  PiggyBank,
  Loader2,
  DollarSign,
  Calendar,
  Hash,
} from 'lucide-react'
import {
  useAccounts,
  useCreateAccount,
  useUpdateAccount,
  useDeleteAccount,
  type Account,
  type AccountCreate,
} from '@/hooks/useAccounts'
import { format } from 'date-fns'
import { cn } from '@/lib/utils'
import { PageHeader } from '@/components/ui/page-header'

const ACCOUNT_TYPES = [
  { value: 'checking', label: 'Checking', icon: Wallet },
  { value: 'savings', label: 'Savings', icon: PiggyBank },
  { value: 'credit', label: 'Credit Card', icon: CreditCard },
  { value: 'investment', label: 'Investment', icon: Building2 },
]

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
  }).format(value)
}

function AccountTypeIcon({ type }: { type: string }) {
  const accountType = ACCOUNT_TYPES.find(t => t.value === type) || ACCOUNT_TYPES[0]
  const Icon = accountType.icon
  return <Icon className="h-5 w-5" />
}

export default function AccountsPage() {
  const { data: accounts, isLoading } = useAccounts()
  const createAccount = useCreateAccount()
  const updateAccount = useUpdateAccount()
  const deleteAccount = useDeleteAccount()
  const { confirm, ConfirmDialog } = useConfirm()

  const [addDialogOpen, setAddDialogOpen] = useState(false)
  const [editingAccount, setEditingAccount] = useState<Account | null>(null)
  const [formData, setFormData] = useState<AccountCreate>({
    name: '',
    type: 'checking',
    last4: '',
    currency: 'USD',
  })

  const resetForm = () => {
    setFormData({
      name: '',
      type: 'checking',
      last4: '',
      currency: 'USD',
    })
  }

  const handleOpenAdd = () => {
    resetForm()
    setEditingAccount(null)
    setAddDialogOpen(true)
  }

  const handleOpenEdit = (account: Account) => {
    setFormData({
      name: account.name,
      type: account.type,
      last4: account.last4 || '',
      currency: account.currency,
    })
    setEditingAccount(account)
    setAddDialogOpen(true)
  }

  const handleSubmit = async () => {
    if (!formData.name.trim()) {
      toast.error('Account name is required')
      return
    }

    try {
      if (editingAccount) {
        await updateAccount.mutateAsync({
          id: editingAccount.id,
          ...formData,
        })
        toast.success('Account updated')
      } else {
        await createAccount.mutateAsync(formData)
        toast.success('Account created')
      }
      setAddDialogOpen(false)
      resetForm()
      setEditingAccount(null)
    } catch (error) {
      toast.error(editingAccount ? 'Failed to update account' : 'Failed to create account')
    }
  }

  const handleDelete = async (account: Account) => {
    const hasTransactions = account.transaction_count > 0
    const confirmed = await confirm({
      title: 'Delete Account',
      description: hasTransactions
        ? `This account has ${account.transaction_count} transactions. Deleting it will unlink those transactions. Continue?`
        : `Are you sure you want to delete "${account.name}"?`,
      confirmLabel: 'Delete',
      variant: 'destructive',
    })

    if (!confirmed) return

    try {
      await deleteAccount.mutateAsync({ id: account.id, force: hasTransactions })
      toast.success('Account deleted')
    } catch (error) {
      toast.error('Failed to delete account')
    }
  }

  const totalBalance = accounts?.reduce((sum, acc) => sum + (acc.balance || 0), 0) || 0
  const totalTransactions = accounts?.reduce((sum, acc) => sum + acc.transaction_count, 0) || 0

  return (
    <div className="container mx-auto py-6 space-y-6">
      <PageHeader
        title="Accounts"
        description="Manage your bank accounts and credit cards"
        helpItems={[
          "Add accounts to organize your transactions by source",
          "Accounts are auto-detected when you import bank statements",
          "Each account shows balance calculated from all transactions",
          "Use last 4 digits to help identify accounts on statements",
          "Deleting an account will unlink its transactions (not delete them)"
        ]}
        action={
          <Button onClick={handleOpenAdd}>
            <Plus className="h-4 w-4 mr-2" />
            Add Account
          </Button>
        }
      />

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Total Accounts
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{accounts?.length || 0}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Net Balance
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className={cn(
              "text-2xl font-bold",
              totalBalance >= 0 ? "text-green-600" : "text-red-600"
            )}>
              {formatCurrency(totalBalance)}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Total Transactions
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{totalTransactions.toLocaleString()}</div>
          </CardContent>
        </Card>
      </div>

      {/* Accounts Table */}
      <Card>
        <CardHeader>
          <CardTitle>All Accounts</CardTitle>
          <CardDescription>
            Your connected bank accounts and credit cards
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : accounts?.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <Wallet className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>No accounts yet</p>
              <p className="text-sm">Add your first account to get started</p>
              <Button onClick={handleOpenAdd} className="mt-4">
                <Plus className="h-4 w-4 mr-2" />
                Add Account
              </Button>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Account</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Last 4</TableHead>
                  <TableHead className="text-right">Balance</TableHead>
                  <TableHead className="text-right">Transactions</TableHead>
                  <TableHead>Last Activity</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {accounts?.map((account) => (
                  <TableRow key={account.id}>
                    <TableCell>
                      <div className="flex items-center gap-3">
                        <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center">
                          <AccountTypeIcon type={account.type} />
                        </div>
                        <div>
                          <div className="font-medium">{account.name}</div>
                          <div className="text-xs text-muted-foreground">
                            {account.currency}
                          </div>
                        </div>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline" className="capitalize">
                        {account.type || 'checking'}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      {account.last4 ? (
                        <span className="font-mono text-sm">****{account.last4}</span>
                      ) : (
                        <span className="text-muted-foreground">-</span>
                      )}
                    </TableCell>
                    <TableCell className="text-right">
                      <span className={cn(
                        "font-medium",
                        account.balance >= 0 ? "text-green-600" : "text-red-600"
                      )}>
                        {formatCurrency(account.balance)}
                      </span>
                    </TableCell>
                    <TableCell className="text-right">
                      {account.transaction_count.toLocaleString()}
                    </TableCell>
                    <TableCell>
                      {account.last_tx_date ? (
                        <span className="text-sm text-muted-foreground">
                          {format(new Date(account.last_tx_date), 'MMM d, yyyy')}
                        </span>
                      ) : (
                        <span className="text-muted-foreground">-</span>
                      )}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-1">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleOpenEdit(account)}
                        >
                          <Edit2 className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDelete(account)}
                          className="text-red-600 hover:text-red-700"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Add/Edit Dialog */}
      <Dialog open={addDialogOpen} onOpenChange={setAddDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {editingAccount ? 'Edit Account' : 'Add New Account'}
            </DialogTitle>
            <DialogDescription>
              {editingAccount
                ? 'Update the account details below.'
                : 'Enter the details for your new account.'}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="name">Account Name</Label>
              <Input
                id="name"
                placeholder="e.g., Chase Checking"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="type">Account Type</Label>
              <Select
                value={formData.type}
                onValueChange={(value) => setFormData({ ...formData, type: value })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select type" />
                </SelectTrigger>
                <SelectContent>
                  {ACCOUNT_TYPES.map((type) => (
                    <SelectItem key={type.value} value={type.value}>
                      <div className="flex items-center gap-2">
                        <type.icon className="h-4 w-4" />
                        {type.label}
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="last4">Last 4 Digits (optional)</Label>
                <Input
                  id="last4"
                  placeholder="1234"
                  maxLength={4}
                  value={formData.last4}
                  onChange={(e) => setFormData({ ...formData, last4: e.target.value.replace(/\D/g, '') })}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="currency">Currency</Label>
                <Select
                  value={formData.currency}
                  onValueChange={(value) => setFormData({ ...formData, currency: value })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="USD">USD</SelectItem>
                    <SelectItem value="EUR">EUR</SelectItem>
                    <SelectItem value="GBP">GBP</SelectItem>
                    <SelectItem value="CAD">CAD</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setAddDialogOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleSubmit}
              disabled={createAccount.isPending || updateAccount.isPending}
            >
              {(createAccount.isPending || updateAccount.isPending) && (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              )}
              {editingAccount ? 'Save Changes' : 'Add Account'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <ConfirmDialog />
    </div>
  )
}
