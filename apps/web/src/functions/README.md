# Functions Directory

This directory contains utility functions and business logic organized by functionality.

## Structure

- **error_handling/** - Error handling utilities and middleware
  - `index.ts` - Main error handling functions and custom error classes

## Usage

### Error Handling

```typescript
import { handleApiError, errors } from '@/functions/error_handling'

// In API routes
export async function POST(request: NextRequest) {
  try {
    // Your logic here
    if (!valid) {
      throw errors.badRequest('Invalid input')
    }
    
    return NextResponse.json({ success: true })
  } catch (error) {
    return handleApiError(error)
  }
}
```

### Custom Errors

```typescript
import { createApiError } from '@/functions/error_handling'

// Create custom errors
throw createApiError('Custom error message', 422, 'CUSTOM_ERROR')
```

## Adding New Functions

1. Create a new subdirectory for your function category
2. Add an `index.ts` file with your exports
3. Update this README with usage examples