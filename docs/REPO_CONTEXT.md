# Full Repository Context for PR Reviews

Enhance PR reviews by analyzing the entire repository, not just the diff. This feature clones repositories, analyzes dependencies, and includes related files in the review context.

## Overview

Traditional PR reviews only see the changed lines (diff). This feature provides:
- **Full file context**: Complete content of changed files
- **Dependency analysis**: Related files through imports/function calls
- **Language-specific resolution**: Python, JavaScript, TypeScript, Java, Go support
- **Smart relevance scoring**: Prioritize most relevant related files

## Configuration

Add to your `.pr_agent.toml`:

```toml
[repo_context]
enable_full_context = true
clone_depth = 1  # Shallow clone for performance
clone_cache_dir = "/tmp/pr-agent-repos"
max_related_files = 20
max_context_tokens = 10000
supported_languages = ["python", "javascript", "typescript", "java", "go"]
```

## Configuration Options

- **`enable_full_context`**: Enable repository context analysis (default: `false`)
- **`clone_depth`**: Git clone depth, 1 for shallow clone (default: `1`)
- **`clone_cache_dir`**: Directory for cloned repositories (default: `/tmp/pr-agent-repos`)
- **`max_related_files`**: Maximum related files to include (default: `20`)
- **`max_context_tokens`**: Token budget for additional context (default: `10000`)
- **`supported_languages`**: Languages to analyze (default: `["python", "javascript", "typescript", "java", "go"]`)

## How It Works

### 1. Repository Cloning

When a PR is reviewed:
1. Clone repository to local cache (or update if exists)
2. Checkout the PR's target branch
3. Cache persists across reviews for performance

### 2. Dependency Resolution

For each changed file:
1. Detect language from file extension
2. Parse file for imports/dependencies
3. Resolve import paths to actual files
4. Score relevance (direct imports = high score)

### 3. Context Assembly

1. Load full content of changed files
2. Load related files (within token budget)
3. Add to review context with relevance scores
4. Prioritize: direct imports > transitive dependencies

### 4. Review Enhancement

The LLM receives:
- Full changed file content (not just diff)
- Related files that import/use changed code
- Context about dependencies and callers

## Supported Languages

### Python

**Detects**:
- `import module`
- `from package import module`
- Relative imports

**Resolves**:
- `.py` files
- `__init__.py` packages
- Relative paths from current file

**Example**:
```python
# Changed file: utils/helpers.py
from .validators import validate_email  # Resolves to utils/validators.py
import config  # Resolves to config.py
```

### JavaScript/TypeScript

**Detects**:
- `import ... from 'module'`
- `require('module')`
- `import('module')` (dynamic)
- `import type { ... }` (TypeScript)

**Resolves**:
- `.js`, `.jsx`, `.ts`, `.tsx`, `.mjs` extensions
- `index.js` in directories
- Relative paths (`./`, `../`)

**Example**:
```javascript
// Changed file: components/Button.jsx
import { theme } from '../styles/theme';  // Resolves to styles/theme.js
import React from 'react';  // Skipped (external package)
```

### Java

**Detects**:
- `import package.Class;`
- `import static package.Class.method;`

**Resolves**:
- Maven structure: `src/main/java/`
- Simple structure: `src/`
- Converts package names to paths

**Example**:
```java
// Changed file: com/example/UserService.java
import com.example.model.User;  // Resolves to src/main/java/com/example/model/User.java
import java.util.List;  // Skipped (standard library)
```

### Go

**Detects**:
- `import "package"`
- Grouped imports

**Resolves**:
- Internal packages only
- Finds `.go` files in package directory

**Example**:
```go
// Changed file: main.go
import "github.com/user/repo/utils"  // Resolves to utils/*.go
import "fmt"  // Skipped (standard library)
```

## Usage Example

### Before (Diff-Only Review)

```diff
// components/Button.jsx
- const handleClick = () => {
+ const handleClick = (event) => {
+   event.preventDefault();
    onClick();
  }
```

**Review sees**: Only the changed lines

### After (Full Context Review)

**Changed file** (full content):
```javascript
import { theme } from '../styles/theme';
import { trackEvent } from '../analytics';

export const Button = ({ onClick, children }) => {
  const handleClick = (event) => {
    event.preventDefault();
    onClick();
  };
  
  return <button onClick={handleClick}>{children}</button>;
};
```

**Related files**:
- `styles/theme.js` (imported by Button)
- `analytics.js` (imported by Button)
- `pages/Home.jsx` (imports Button)

**Review can now**:
- See full Button implementation
- Check theme usage
- Verify analytics integration
- Identify breaking changes for Home.jsx

## Performance Considerations

### Clone Caching

- Repositories cached locally after first clone
- Subsequent reviews update existing clone (fast)
- Shallow clones (depth=1) minimize disk usage

### Token Budget

- `max_context_tokens` limits additional context
- Related files sorted by relevance
- Only top N files included (configurable)

### Cleanup

Automatic cleanup of old clones:
```python
from pr_agent.algo.repo_context_analyzer import RepoContextAnalyzer

analyzer = RepoContextAnalyzer()
analyzer.cleanup_old_clones(max_age_days=7)
```

## Integration with PR Review

The repository context is automatically integrated when enabled:

1. **PR received** → Clone repository
2. **Get changed files** → Analyze dependencies
3. **Load related files** → Within token budget
4. **Generate review** → With full context

No code changes needed in review tools - context is added transparently.

## Troubleshooting

### Clone failures

**Error**: "Failed to clone repository"

**Solutions**:
- Check git credentials/authentication
- Verify repository URL is accessible
- Ensure sufficient disk space
- Check network connectivity

### Missing dependencies

**Error**: Related files not detected

**Solutions**:
- Verify language is in `supported_languages`
- Check import syntax is standard
- Ensure files exist in repository
- Review resolver logs for errors

### Token budget exceeded

**Warning**: "Insufficient tokens for all related files"

**Solutions**:
- Increase `max_context_tokens`
- Reduce `max_related_files`
- Use shorter file paths
- Optimize changed file size

## Testing

Run unit tests:

```bash
# Test dependency resolvers
PYTHONPATH=. pytest tests/unittest/test_dependency_resolver.py -v

# Test repository analyzer
PYTHONPATH=. pytest tests/unittest/test_repo_context_analyzer.py -v
```

## Example Configuration

### Minimal (Small Projects)

```toml
[repo_context]
enable_full_context = true
max_related_files = 10
max_context_tokens = 5000
```

### Balanced (Medium Projects)

```toml
[repo_context]
enable_full_context = true
clone_depth = 1
clone_cache_dir = "/var/lib/pr-agent/repos"
max_related_files = 20
max_context_tokens = 10000
supported_languages = ["python", "javascript", "typescript"]
```

### Comprehensive (Large Projects)

```toml
[repo_context]
enable_full_context = true
clone_depth = 1
clone_cache_dir = "/var/lib/pr-agent/repos"
max_related_files = 30
max_context_tokens = 15000
supported_languages = ["python", "javascript", "typescript", "java", "go"]
```

## Benefits

### Better Reviews

- **Catch breaking changes**: See callers of modified functions
- **Understand context**: Full file content, not just diff
- **Verify consistency**: Check related code follows same patterns
- **Detect side effects**: Identify impacted dependencies

### Reduced False Positives

- **No "where is this defined?"**: Full context available
- **No "is this used?"**: See callers and importers
- **No "what does this do?"**: Complete function/class visible

### Improved Suggestions

- **Contextual recommendations**: Based on full codebase
- **Consistent patterns**: Match existing code style
- **Better refactoring**: Understand full impact

## Limitations

- **Token budget**: Large codebases may exceed limits
- **Language support**: Only 5 languages currently supported
- **External dependencies**: Only analyzes repository code
- **Performance**: Initial clone can be slow for large repos

## Future Enhancements

- Support for more languages (C++, C#, Ruby, PHP)
- Semantic code search (find similar patterns)
- Call graph analysis (who calls this function?)
- Test coverage mapping (which tests cover this code?)
- Historical context (how has this code evolved?)
