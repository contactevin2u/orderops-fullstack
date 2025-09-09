# OrderOps System Version & Field Documentation

## Current Version
**Version**: 1.0.0  
**Last Updated**: September 8, 2025  
**Database Migration Head**: `002_add_priority_lorry_id`

## Recent Changes

### Database Schema Updates
- **Priority Lorry Assignment**: Added `priority_lorry_id` field to drivers table for lorry management system
- **Migration Chain**: Resolved complex migration dependencies with ghost revisions for production stability

## Core Database Fields

### Driver Model (`drivers` table)
| Field | Type | Description | Required | Index |
|-------|------|-------------|----------|-------|
| `id` | Integer | Primary key | ✓ | ✓ |
| `name` | String(100) | Driver name | ✓ | - |
| `phone` | String(20) | Contact number | ✓ | ✓ |
| `employee_id` | String(50) | Unique employee identifier | ✓ | ✓ |
| `license_number` | String(50) | Driving license number | ✓ | - |
| `vehicle_plate` | String(20) | Assigned vehicle plate | - | - |
| `is_active` | Boolean | Driver status | ✓ | ✓ |
| `device_id` | String(255) | Mobile device identifier | - | ✓ |
| `firebase_token` | Text | Push notification token | - | - |
| `priority_lorry_id` | String(50) | **NEW**: Preferred lorry assignment | - | ✓ |
| `created_at` | DateTime | Record creation timestamp | ✓ | - |
| `updated_at` | DateTime | Last modification timestamp | ✓ | - |

### Lorry Model (`lorries` table)
| Field | Type | Description | Required | Index |
|-------|------|-------------|----------|-------|
| `id` | Integer | Primary key | ✓ | ✓ |
| `lorry_id` | String(50) | Unique lorry identifier | ✓ | ✓ |
| `plate_number` | String(20) | Vehicle plate number | - | - |
| `model` | String(100) | Vehicle model | - | - |
| `capacity` | String(50) | Load capacity | - | - |
| `base_warehouse` | String(50) | Home warehouse location | ✓ | - |
| `is_active` | Boolean | Lorry operational status | ✓ | ✓ |
| `is_available` | Boolean | Current availability | ✓ | ✓ |
| `current_location` | String(100) | Last known location | - | - |
| `last_maintenance_date` | Date | Maintenance schedule | - | - |
| `notes` | Text | Additional information | - | - |
| `created_at` | DateTime | Record creation timestamp | ✓ | - |
| `updated_at` | DateTime | Last modification timestamp | ✓ | - |

### Lorry Assignment Model (`lorry_assignments` table)
| Field | Type | Description | Required | Index |
|-------|------|-------------|----------|-------|
| `id` | Integer | Primary key | ✓ | ✓ |
| `driver_id` | Integer | Foreign key to drivers | ✓ | ✓ |
| `lorry_id` | String(50) | Assigned lorry identifier | ✓ | ✓ |
| `assignment_date` | Date | Assignment date | ✓ | ✓ |
| `status` | String(20) | Assignment status | ✓ | - |
| `notes` | Text | Assignment notes | - | - |
| `created_at` | DateTime | Record creation timestamp | ✓ | - |
| `updated_at` | DateTime | Last modification timestamp | ✓ | - |

## API Endpoints

### Lorry Management
- **Base URL**: `/lorry-management`
- **Authentication**: Required for all endpoints

#### Core Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/status` | System status and lorry counts |
| `GET` | `/lorries` | List all lorries |
| `POST` | `/lorries` | Create new lorry |
| `GET` | `/assignments` | List lorry assignments |
| `POST` | `/assignments` | Create lorry assignment |
| `GET` | `/my-assignment` | Get driver's current assignment |
| `GET` | `/drivers` | List drivers with priority lorries |

#### Stock Management
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/stock/{lorry_id}` | Get lorry current stock |
| `POST` | `/stock/{lorry_id}/load` | Load stock to lorry |
| `POST` | `/stock/{lorry_id}/unload` | Unload stock from lorry |
| `GET` | `/stock/transactions` | Stock transaction history |
| `GET` | `/stock/summary` | All lorries inventory summary |

## Migration History

### Active Migrations
- `002_add_priority_lorry_id`: Adds priority lorry assignment to drivers
- `0015_merge_heads`: Merge point for multiple development branches
- `20250908_stock_txns`: Stock transaction system
- `20250907_lorry_models`: Lorry management models

### Ghost Migrations
The system uses ghost migrations (no-op placeholders) to maintain database consistency across environments:
- `0001_init_fullstack` through `0014_enhance_uid_system`: Historical migration placeholders
- `bg_jobs_001`, `drv_base_wh`, `a3c70e9437fe`: Branch merge placeholders

## System Architecture

### Backend
- **Framework**: FastAPI
- **Database**: PostgreSQL with Alembic migrations
- **Authentication**: JWT-based with role management

### Frontend  
- **Framework**: Next.js with TypeScript
- **Styling**: Tailwind CSS
- **State Management**: React Context/Hooks

### Mobile App
- **Platform**: Android (Kotlin + Jetpack Compose)
- **Architecture**: Offline-first with AsyncStorage outbox
- **Backend Integration**: Firebase ID token authentication

## Development Notes

### Migration Best Practices
1. Always create backup before running migrations in production
2. Ghost migrations are used for database consistency - do not modify
3. New schema changes should follow the established naming convention
4. Test migrations locally before deployment

### Field Validation
- `priority_lorry_id`: Must reference existing lorry or be null
- `employee_id`: Must be unique across all drivers
- `lorry_id`: Must be unique across all lorries
- Phone numbers should follow E.164 format when possible

## Support
For database migration issues or field-related questions, refer to the main project documentation in `CLAUDE.md`.