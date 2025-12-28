# Workflow Foundation - Implementation Guide

## Overview

This workflow foundation provides a comprehensive orchestration system for your financial platform, transforming isolated features into an integrated, user-friendly experience. The system enables real-time workflow management, progress tracking, and seamless coordination between different parts of your application.

## Architecture Components

### 1. Core State Management (`types/workflow.ts`, `stores/workflow.store.ts`)
- **Workflow State Schema**: Comprehensive type definitions with states, transitions, and events
- **Zustand Store**: Centralized state management with persistence and optimistic updates
- **State Machine**: Workflow lifecycle management with validation and transitions

### 2. Real-time Integration (`services/websocket-manager.ts`, `hooks/useWebSocket.ts`)
- **WebSocket Manager**: Production-grade connection handling with auto-reconnect
- **Event Subscription**: Real-time updates and notification system
- **Connection Health**: Monitoring and fallback mechanisms

### 3. Persistence Layer (`services/workflow-persistence.ts`)
- **Multi-tier Storage**: IndexedDB + Server + Memory cache
- **Offline Capability**: Local storage with automatic sync when online
- **Conflict Resolution**: Smart merging of concurrent updates

### 4. UI Components (`components/workflow/`)
- **Progress Tracking**: Visual workflow progress with stepper and progress bars
- **Notification System**: Toast notifications and persistent alerts
- **Dashboard**: Central monitoring and management interface

### 5. Integration Layer (`providers/WorkflowProvider.tsx`)
- **Context Provider**: Unified API for workflow operations
- **Error Handling**: Comprehensive error recovery and user feedback
- **Development Tools**: Debug utilities and workflow export/import

## Quick Start

### 1. Setup the Provider

```tsx
// app/layout.tsx or your root component
import { WorkflowProvider } from './src/providers/WorkflowProvider'

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <WorkflowProvider 
          config={{
            wsUrl: process.env.NEXT_PUBLIC_WS_URL,
            persistenceEnabled: true,
            autoSync: true,
            debugMode: process.env.NODE_ENV === 'development'
          }}
        >
          {children}
        </WorkflowProvider>
      </body>
    </html>
  )
}
```

### 2. Create a Workflow

```tsx
import { useWorkflowContext } from './src/providers/WorkflowProvider'
import { WorkflowType } from './src/types/workflow'

function TransactionImportComponent() {
  const { createWorkflow, startWorkflow } = useWorkflowContext()

  const handleImport = async (file: File) => {
    // Create workflow
    const workflowId = await createWorkflow(WorkflowType.TRANSACTION_IMPORT, {
      fileName: file.name,
      fileSize: file.size
    })

    // Start the workflow
    await startWorkflow(workflowId)

    // Your existing import logic here...
  }

  return (
    <input type="file" onChange={(e) => {
      const file = e.target.files?.[0]
      if (file) handleImport(file)
    }} />
  )
}
```

### 3. Track Progress

```tsx
import { WorkflowStepper, ProgressBar } from './src/components/workflow/ProgressTracker'
import { useWorkflowContext } from './src/providers/WorkflowProvider'

function WorkflowMonitor({ workflowId }: { workflowId: string }) {
  const { getWorkflow } = useWorkflowContext()
  const workflow = getWorkflow(workflowId)

  if (!workflow) return null

  return (
    <div>
      <ProgressBar 
        progress={workflow.progress.overall}
        animated={workflow.status === 'running'}
      />
      <WorkflowStepper workflow={workflow} />
    </div>
  )
}
```

### 4. Dashboard Integration

```tsx
import { WorkflowDashboard } from './src/components/workflow/WorkflowDashboard'

function Dashboard() {
  return (
    <div>
      <h1>Financial Dashboard</h1>
      <WorkflowDashboard />
    </div>
  )
}
```

## Integration Patterns

### Pattern 1: Existing Feature Enhancement

Transform existing isolated features by wrapping them with workflow context:

```tsx
// Before: Isolated transaction import
function TransactionImport() {
  const [isLoading, setIsLoading] = useState(false)
  
  const handleImport = async (file: File) => {
    setIsLoading(true)
    await uploadFile(file) // No progress, no coordination
    setIsLoading(false)
  }
  
  return <FileUpload onUpload={handleImport} />
}

// After: Workflow-integrated import
function TransactionImport() {
  const { createWorkflow, getWorkflow } = useWorkflowContext()
  const [workflowId, setWorkflowId] = useState<string | null>(null)
  
  const workflow = workflowId ? getWorkflow(workflowId) : null
  
  const handleImport = async (file: File) => {
    const id = await createWorkflow(WorkflowType.TRANSACTION_IMPORT, { file })
    setWorkflowId(id)
    // Workflow handles progress, errors, and coordination
  }
  
  return (
    <div>
      <FileUpload onUpload={handleImport} />
      {workflow && <WorkflowStepper workflow={workflow} />}
    </div>
  )
}
```

### Pattern 2: Cross-Feature Coordination

Enable features to work together through shared workflow context:

```tsx
function AccountDashboard({ accountId }: { accountId: string }) {
  const { createWorkflow, getActiveWorkflows } = useWorkflowContext()
  
  // Check if reconciliation is in progress
  const activeReconciliation = getActiveWorkflows().find(
    w => w.type === WorkflowType.ACCOUNT_RECONCILIATION && 
         w.context?.accountId === accountId
  )
  
  return (
    <div>
      {activeReconciliation ? (
        <ReconciliationProgress workflow={activeReconciliation} />
      ) : (
        <button onClick={() => createWorkflow(WorkflowType.ACCOUNT_RECONCILIATION, { accountId })}>
          Start Reconciliation
        </button>
      )}
    </div>
  )
}
```

### Pattern 3: Optimistic UI Updates

Provide immediate feedback while maintaining data consistency:

```tsx
import { useOptimisticWorkflow } from './src/hooks/useOptimisticUpdates'

function ExpenseCategorizationForm({ expenseId }: { expenseId: string }) {
  const { optimisticUpdate } = useOptimisticWorkflow()
  
  const updateCategory = async (category: string) => {
    await optimisticUpdate(
      // Optimistic update
      (workflow) => ({
        context: { 
          ...workflow.context,
          categorizedExpenses: [...(workflow.context.categorizedExpenses || []), expenseId]
        }
      }),
      // API call
      () => fetch(`/api/expenses/${expenseId}/categorize`, {
        method: 'PATCH',
        body: JSON.stringify({ category })
      }),
      // Options
      {
        onError: (error) => console.error('Categorization failed:', error)
      }
    )
  }
  
  return <CategorySelector onSelect={updateCategory} />
}
```

## Real-time Features

### WebSocket Integration

The system automatically handles real-time updates:

```tsx
// Backend sends workflow events
websocket.send({
  type: 'workflow_event',
  data: {
    workflowId: 'wf-123',
    event: 'PROGRESS_UPDATE',
    data: { progress: { overall: 75, currentStage: 80 } }
  }
})

// Frontend automatically updates UI
// No additional code needed - handled by WorkflowProvider
```

### Notification System

Automatic user feedback for workflow events:

```tsx
// Notifications are automatically triggered by workflow events
// Customize notification behavior in the workflow store:

const customNotification = {
  type: 'success',
  title: 'Import Complete',
  message: `Successfully imported ${count} transactions`,
  persistent: false,
  actions: [
    { label: 'View Transactions', onClick: () => navigate('/transactions') }
  ]
}
```

## API Integration

### Backend Event Endpoints

Your backend should emit workflow events to keep the frontend synchronized:

```typescript
// Example Express.js endpoint
app.post('/api/transactions/import', async (req, res) => {
  const { workflowId, file } = req.body
  
  try {
    // Start processing
    websocket.broadcast({
      type: 'workflow_event',
      data: {
        workflowId,
        event: 'STAGE_START',
        data: { stage: 'PROCESSING' }
      }
    })
    
    // Process file with progress updates
    for (let i = 0; i < totalRows; i++) {
      // Process row...
      
      if (i % 100 === 0) {
        websocket.broadcast({
          type: 'workflow_event',
          data: {
            workflowId,
            event: 'PROGRESS_UPDATE',
            data: { progress: { overall: (i / totalRows) * 100 } }
          }
        })
      }
    }
    
    // Complete
    websocket.broadcast({
      type: 'workflow_event',
      data: {
        workflowId,
        event: 'STAGE_COMPLETE',
        data: { stage: 'PROCESSING', results: { importedCount: totalRows } }
      }
    })
    
    res.json({ success: true, workflowId })
  } catch (error) {
    websocket.broadcast({
      type: 'workflow_event',
      data: {
        workflowId,
        event: 'ERROR_OCCURRED',
        data: { error: { message: error.message } }
      }
    })
    
    res.status(500).json({ error: error.message })
  }
})
```

## Configuration

### Environment Variables

```bash
# .env.local
NEXT_PUBLIC_WS_URL=ws://localhost:8000/api/realtime/connect
NEXT_PUBLIC_API_URL=http://localhost:8000/api
```

### Workflow Types Configuration

Customize workflow stages for your specific use cases:

```typescript
// In your workflow configuration
const customWorkflowConfig = {
  [WorkflowType.TRANSACTION_IMPORT]: {
    stages: [
      { stage: 'UPLOAD', name: 'Upload File', estimatedDuration: 5000 },
      { stage: 'VALIDATION', name: 'Validate Data', estimatedDuration: 10000 },
      { stage: 'PROCESSING', name: 'Process Transactions', estimatedDuration: 30000 },
      { stage: 'CATEGORIZATION', name: 'Auto-Categorize', estimatedDuration: 15000 },
      { stage: 'COMPLETED', name: 'Import Complete', estimatedDuration: 0 }
    ]
  }
}
```

## Development Tools

### Debug Mode

Enable comprehensive logging in development:

```tsx
<WorkflowProvider config={{ debugMode: true }}>
  {/* Your app */}
</WorkflowProvider>
```

### Workflow Dev Tools

Access development utilities:

```tsx
import { useWorkflowDevTools } from './src/providers/WorkflowProvider'

function DevPanel() {
  const devTools = useWorkflowDevTools()
  
  if (!devTools) return null // Only in development
  
  return (
    <div>
      <h3>Workflow Dev Tools</h3>
      <p>Total: {devTools.stats.total}</p>
      <p>Active: {devTools.stats.active}</p>
      <button onClick={devTools.exportWorkflows}>Export Workflows</button>
      <button onClick={devTools.clearAllWorkflows}>Clear All</button>
    </div>
  )
}
```

## Best Practices

1. **Always use workflows for multi-step operations** that involve user feedback or coordination
2. **Implement optimistic updates** for immediate UI responsiveness
3. **Handle offline scenarios** - the persistence layer automatically manages this
4. **Provide meaningful progress feedback** using the progress tracking components
5. **Use notifications judiciously** - too many can overwhelm users
6. **Test workflow transitions** thoroughly, especially error scenarios
7. **Monitor workflow performance** using the built-in statistics

## Migration Guide

To integrate this workflow foundation into your existing app:

1. **Start with one feature** - choose your most complex or user-facing workflow
2. **Wrap existing components** with workflow context gradually
3. **Add progress tracking** to long-running operations
4. **Implement real-time updates** for operations that benefit from live feedback
5. **Extend to cross-feature coordination** once individual features are integrated

## Examples

See `examples/WorkflowIntegrationExamples.tsx` for complete implementation examples of:
- Transaction Import with file upload and progress tracking
- Account Reconciliation with real-time updates
- Budget Analysis with multi-stage processing
- Expense Categorization with AI integration

This workflow foundation transforms your financial platform from a collection of isolated features into a cohesive, user-friendly system that provides clear feedback, handles errors gracefully, and coordinates seamlessly between different operations.