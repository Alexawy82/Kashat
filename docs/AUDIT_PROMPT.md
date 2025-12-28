# COMPREHENSIVE CODEBASE AUDIT PROMPT
## For AI Coding Assistants (Claude Code, Cursor, Windsurf, Codex, etc.)

---

## MISSION BRIEF

You are a senior software architect taking over an existing personal finance application called **LedgerLoop** (also known as **Flos**). You have ZERO prior knowledge of this codebase. Your task is to produce a COMPLETE technical audit report that documents EVERYTHING about how this system works.

**Codebase Location**: `C:\Users\Marwan\Desktop\AI\Flos`

**Your output must be exhaustive** - treat this like you're writing documentation for a team of developers who will maintain this code for the next 5 years. Leave nothing undocumented.

---

## PART 1: CODEBASE STRUCTURE ANALYSIS

### 1.1 Directory Tree
Generate a complete directory tree with annotations explaining what each folder contains.

### 1.2 File Inventory
For EVERY file in the codebase, document:
- File path
- File size (lines of code)
- Primary purpose (1 sentence)
- Key exports (functions, classes, constants)
- Dependencies (imports from other project files)
- External dependencies (npm packages, pip packages)

### 1.3 Architecture Pattern
Identify and document:
- What architectural pattern is used? (MVC, Clean Architecture, Hexagonal, etc.)
- Is it followed consistently?
- Where does it deviate?

---

## PART 2: BACKEND DEEP DIVE

### 2.1 Entry Points
Document every entry point to the application:
- Main application file
- CLI scripts
- Background workers
- Scheduled tasks

### 2.2 Database Schema Analysis
For EVERY table in the database:
```
Table: [table_name]
Purpose: [what data it stores]
Columns:
  - column_name: type | nullable | default | description
  - ...
Relationships:
  - Foreign key to [table] via [column]
  - Referenced by [table] via [column]
Indexes:
  - index_name: columns, unique?
Sample queries that use this table:
  - [list common query patterns]
```

### 2.3 API Route Inventory
For EVERY API endpoint, document:
```
Endpoint: [METHOD] [path]
Router file: [file path]
Function name: [handler function]
Purpose: [what it does]
Request:
  - Query params: [list with types]
  - Path params: [list with types]
  - Body schema: [JSON schema or Pydantic model]
  - Headers required: [list]
Response:
  - Success (200): [schema]
  - Error codes: [list with conditions]
Database operations:
  - Reads from: [tables]
  - Writes to: [tables]
Calls to other functions:
  - [function_name] in [file]
AI/ML involvement: [yes/no, details if yes]
Authentication: [required/optional/none]
Rate limiting: [details]
Example request/response:
  - Request: [curl example]
  - Response: [JSON example]
```

### 2.4 Module-by-Module Analysis
For EVERY Python module (.py file), document:

```
Module: [file path]
Lines of code: [count]
Purpose: [detailed description]

Classes:
  [ClassName]:
    Purpose: [description]
    Attributes:
      - attr_name: type | description
    Methods:
      - method_name(params) -> return_type
        Purpose: [what it does]
        Called by: [list of callers]
        Calls: [list of callees]
        Side effects: [database, files, external APIs]

Functions:
  [function_name](params) -> return_type:
    Purpose: [description]
    Algorithm: [step-by-step logic]
    Called by: [list of callers]
    Calls: [list of callees]
    Side effects: [list]
    Error handling: [how errors are handled]
    Edge cases: [known edge cases]

Constants/Configuration:
  - CONSTANT_NAME: value | purpose

Dependencies:
  - Internal: [list of project imports]
  - External: [list of package imports]

Known issues/TODOs:
  - [list any TODO comments or obvious issues]
```

### 2.5 Data Flow Diagrams
Create detailed data flow diagrams for:

1. **Transaction Import Flow**
   - From file upload to database insert
   - Every function called in order
   - Every transformation applied
   - Every decision point

2. **Categorization Flow**
   - All paths a transaction can take to get categorized
   - Priority order of categorization methods
   - Fallback logic

3. **AI Processing Flow**
   - When is AI called?
   - What data is sent to AI?
   - How is AI response processed?
   - Fallback when AI fails

4. **Transfer Detection Flow**
   - How are transfers identified?
   - What algorithms are used?
   - How are matches confirmed?

5. **Recurring Detection Flow**
   - How are patterns identified?
   - What thresholds are used?
   - How is cadence calculated?

---

## PART 3: AI/ML LAYER ANALYSIS

### 3.1 AI Module Inventory
For EVERY AI-related module:
```
Module: [file path]
AI Provider(s): [OpenAI, LMStudio, Local, etc.]
Purpose: [what AI task it performs]

Prompts used:
  - Prompt name/location: [identifier]
  - Full prompt text: [exact text]
  - Variables injected: [list]
  - Expected response format: [JSON schema]

Models used:
  - Model name: [e.g., gpt-4o-mini]
  - Temperature: [value]
  - Max tokens: [value]
  - Other parameters: [list]

Fallback behavior:
  - What happens if AI fails?
  - What happens if confidence is low?

Caching:
  - Is response cached? [yes/no]
  - Cache key: [how it's generated]
  - Cache TTL: [duration]

Performance:
  - Average latency: [if measurable]
  - Rate limits: [if any]
  - Batching: [is batching used?]
```

### 3.2 Pattern Matching Systems
Document ALL pattern matching/regex systems:
```
Pattern Set: [name/location]
Purpose: [what it matches]
Number of patterns: [count]
Pattern format: [regex, keyword, etc.]

Sample patterns:
  - Pattern: [regex]
    Matches: [example matches]
    Category/Action: [what happens on match]
    Confidence: [if applicable]

Conflicts with other pattern sets:
  - [list any overlapping/conflicting patterns]
```

### 3.3 Merchant Intelligence
Document the merchant extraction/normalization system:
- How are merchant names extracted?
- How are they normalized?
- What is the merchant memory system?
- How does it learn from user corrections?

### 3.4 Categorization Logic
Create a complete decision tree for categorization:
```
START: New transaction arrives
  │
  ├─► Check 1: [condition]
  │     ├─► True: [action]
  │     └─► False: Continue
  │
  ├─► Check 2: [condition]
  │     ├─► True: [action]
  │     └─► False: Continue
  │
  ... [complete tree]
  │
  └─► Final fallback: [action]
```

---

## PART 4: FRONTEND ANALYSIS

### 4.1 Page Inventory
For EVERY page/route:
```
Route: [URL path]
File: [file path]
Purpose: [what the page does]

Components used:
  - [ComponentName]: [purpose]

API calls made:
  - [endpoint]: [when called, what data used]

State management:
  - Local state: [useState, useReducer usage]
  - Global state: [Zustand, context usage]
  - Server state: [React Query usage]

User interactions:
  - [action]: [what happens]

Error handling:
  - [how errors are displayed]

Loading states:
  - [how loading is handled]
```

### 4.2 Component Inventory
For EVERY React component:
```
Component: [name]
File: [path]
Purpose: [description]
Props:
  - propName: type | required | description
Children: [what can be passed as children]
State: [internal state description]
Effects: [useEffect descriptions]
Event handlers: [list]
API calls: [if any]
Styling: [Tailwind classes, CSS modules, etc.]
Accessibility: [ARIA labels, keyboard nav, etc.]
```

### 4.3 Custom Hooks
For EVERY custom hook:
```
Hook: [name]
File: [path]
Purpose: [description]
Parameters: [list with types]
Returns: [structure]
API endpoints used: [list]
Caching strategy: [React Query config]
Error handling: [how errors bubble up]
```

### 4.4 API Client
Document the API client layer:
- How is the API base URL configured?
- How are requests authenticated?
- How are errors handled globally?
- Is there request/response transformation?
- What is the generated OpenAPI client structure?

---

## PART 5: CONFIGURATION & ENVIRONMENT

### 5.1 Environment Variables
List ALL environment variables:
```
Variable: [NAME]
Used in: [file(s)]
Purpose: [description]
Default value: [if any]
Required: [yes/no]
Example: [sample value]
```

### 5.2 Configuration Files
Document every config file:
- package.json (frontend)
- requirements.txt (backend)
- pyproject.toml
- tsconfig.json
- tailwind.config.js
- next.config.js
- docker-compose.yml
- Dockerfile(s)
- pytest.ini
- .env.example

### 5.3 Settings System
Document the runtime settings system:
- Where are settings stored?
- How are they loaded?
- What settings are available?
- How do they affect behavior?

---

## PART 6: DATA PIPELINES

### 6.1 Import Pipeline
Document the complete import flow:
```
Step 1: [File received]
  Function: [name]
  Input: [what comes in]
  Process: [what happens]
  Output: [what goes out]
  Errors: [what can go wrong]

Step 2: [Parsing]
  ...

[Continue for every step until data is in database]
```

### 6.2 Export Pipeline
Document all export functionality:
- CSV export
- Parquet export
- What data is included?
- What transformations are applied?

### 6.3 Background Processing
Document all background tasks:
- What triggers them?
- What do they do?
- How long do they take?
- What happens if they fail?

---

## PART 7: TESTING ANALYSIS

### 7.1 Test Inventory
For EVERY test file:
```
File: [path]
Tests: [count]
Type: [unit/integration/e2e]
Coverage: [what code it covers]

Test cases:
  - test_name: [what it tests]
```

### 7.2 Test Coverage Gaps
Identify code that is NOT tested:
- Untested functions
- Untested edge cases
- Untested error paths

### 7.3 Test Data/Fixtures
Document all test fixtures and mock data.

---

## PART 8: DEPENDENCIES ANALYSIS

### 8.1 Backend Dependencies
For EVERY pip package:
```
Package: [name]
Version: [version]
Purpose: [why it's used]
Used in: [files]
Can be replaced by: [alternatives, if any]
Security status: [any known vulnerabilities]
```

### 8.2 Frontend Dependencies
For EVERY npm package:
```
Package: [name]
Version: [version]
Purpose: [why it's used]
Used in: [files]
Bundle size impact: [if significant]
Can be replaced by: [alternatives, if any]
```

### 8.3 Dependency Graph
Create a visual dependency graph showing:
- Which modules depend on which
- Circular dependencies (if any)
- Heavily depended-upon modules

---

## PART 9: TECHNICAL DEBT & ISSUES

### 9.1 Code Smells
Identify and document:
- Duplicate code
- Dead code
- Overly complex functions (cyclomatic complexity > 10)
- Functions that are too long (> 50 lines)
- Poor naming
- Missing error handling
- Hardcoded values that should be config

### 9.2 Inconsistencies
Document all inconsistencies found:
- Naming conventions (camelCase vs snake_case)
- Error handling patterns
- API response formats
- Logging patterns
- Comment styles

### 9.3 Security Concerns
Identify potential security issues:
- SQL injection vulnerabilities
- XSS vulnerabilities
- Authentication/authorization gaps
- Sensitive data exposure
- Rate limiting gaps

### 9.4 Performance Concerns
Identify potential performance issues:
- N+1 query patterns
- Missing indexes
- Large payload responses
- Unoptimized loops
- Memory leaks

---

## PART 10: RECOMMENDATIONS

### 10.1 Critical Fixes (Do Now)
List issues that MUST be fixed immediately:
- Data corruption risks
- Security vulnerabilities
- Breaking bugs

### 10.2 High Priority (Do This Week)
List important improvements:
- Performance issues
- Data accuracy problems
- Missing error handling

### 10.3 Medium Priority (Do This Month)
List quality improvements:
- Code organization
- Test coverage
- Documentation

### 10.4 Low Priority (Backlog)
List nice-to-have improvements:
- Refactoring
- New features
- Technical debt cleanup

### 10.5 Architecture Recommendations
Suggest architectural improvements:
- What should be refactored?
- What should be consolidated?
- What should be separated?
- What patterns should be adopted?

---

## OUTPUT FORMAT

Generate your report as a set of Markdown files:

```
docs/audit/
├── 00_EXECUTIVE_SUMMARY.md      # High-level overview for decision makers
├── 01_CODEBASE_STRUCTURE.md     # Part 1
├── 02_BACKEND_MODULES.md        # Part 2.4 (all modules)
├── 03_API_REFERENCE.md          # Part 2.3 (all endpoints)
├── 04_DATABASE_SCHEMA.md        # Part 2.2
├── 05_DATA_FLOWS.md             # Part 2.5 (with diagrams)
├── 06_AI_LAYER.md               # Part 3 (complete AI analysis)
├── 07_FRONTEND.md               # Part 4
├── 08_CONFIGURATION.md          # Part 5
├── 09_TESTING.md                # Part 7
├── 10_DEPENDENCIES.md           # Part 8
├── 11_TECHNICAL_DEBT.md         # Part 9
├── 12_RECOMMENDATIONS.md        # Part 10
└── 99_APPENDIX.md               # Raw data, full pattern lists, etc.
```

---

## EXECUTION INSTRUCTIONS

1. **Start by reading ALL files** in the codebase. Do not skip any file.

2. **Create the audit/ directory** at `C:\Users\Marwan\Desktop\AI\Flos\docs\audit\`

3. **Generate each report file** with COMPLETE information. Do not summarize or abbreviate.

4. **Include code snippets** where helpful to illustrate points.

5. **Create diagrams** using Mermaid markdown syntax for data flows.

6. **Be brutally honest** about issues found. This is not a code review to make someone feel good - it's a technical audit to understand the system.

7. **Quantify everything possible**:
   - Lines of code per module
   - Number of API endpoints
   - Number of database tables
   - Number of test cases
   - Percentage of code covered by tests
   - Number of TODO/FIXME comments

8. **Cross-reference everything**:
   - When documenting a function, note where it's called from
   - When documenting an API endpoint, note which frontend pages use it
   - When documenting a database table, note which modules read/write it

---

## VERIFICATION CHECKLIST

Before considering the audit complete, verify:

- [ ] Every .py file in backend is documented
- [ ] Every .ts/.tsx file in frontend is documented
- [ ] Every API endpoint is documented
- [ ] Every database table is documented
- [ ] Every environment variable is documented
- [ ] Every test file is documented
- [ ] All data flows are diagrammed
- [ ] All AI prompts are captured verbatim
- [ ] All pattern dictionaries are listed
- [ ] All dependencies are listed
- [ ] All configuration files are documented
- [ ] All issues/recommendations are categorized by priority

---

## START NOW

Begin the audit. Read every file. Document everything. Be thorough.
