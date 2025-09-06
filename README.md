# 🏌️ Golfstar Booker

A Python application for finding and booking available tee times at Golfstar golf courses.

## Features

- **List Courses**: Browse all available Golfstar golf courses with a beautiful terminal interface
- **Search**: Filter courses by name
- **Course Details**: Get detailed information about specific courses including booking rules and important information
- **Availability Search**: Check tee time availability across multiple courses simultaneously
  - Search by course IDs, names, or all courses
  - Specify date/time ranges and number of players
  - Beautiful table-based display using Rich
  - Smart layout adaptation: consolidated tables, side-by-side course views, or summary tables
  - Visual indicators for availability status with color coding
  - Automatic filtering of competition times (tävling)
- **Rich Terminal UI**: Beautiful, interactive terminal interface using Rich
- **Type Safety**: Fully typed codebase using Pydantic models

## Installation

This project uses `uv` as the package manager. To install dependencies:

```bash
uv pip install -e .
```

## Usage

After installation, you can use the `golfstar` command or run the module directly:

```bash
# Using the command
golfstar --help

# Or using Python module
python -m golfstar_booker --help
```

### Available Commands

#### List all courses

```bash
golfstar list-courses

# With search filter
golfstar list-courses --search "Bromma"

# Limit results
golfstar list-courses --limit 10

# Sort by different fields
golfstar list-courses --sort id --desc
```

#### Get course details

```bash
golfstar course-info 903
```

#### Check availability

```bash
# Check specific course by ID
golfstar availability --id 903 --start 2025-01-15 --players 4

# Check multiple courses by name
golfstar availability --name "Bromma" --name "Bodaholm" --start 2025-01-15

# Check all Golfstar courses
golfstar availability --all --start 2025-01-15

# Check with specific time range
golfstar availability --id 903 --start "2025-01-15 08:00" --end "2025-01-15 12:00"

# With authentication token
golfstar availability --id 903 --start 2025-01-15 --token "YOUR_JWT_TOKEN"
export GOLFSTAR_TOKEN="YOUR_JWT_TOKEN"  # Or use environment variable

```

## Project Structure

```
golfstar_booker/
├── api/           # API client for Sweetspot/Golfstar
├── models/        # Pydantic data models
└── cli/           # CLI application using Typer and Rich
```

## Technologies Used

- **httpx**: Modern HTTP client with async support
- **Pydantic**: Data validation and settings management
- **Typer**: Modern CLI framework
- **Rich**: Beautiful terminal formatting
- **uv**: Fast Python package manager

## Future Features

- [x] Tee time availability checking ✅
- [ ] Booking functionality
- [x] Price information display ✅
- [x] Multi-day availability overview ✅
- [ ] Export availability to calendar format
- [ ] Notifications for available slots
- [ ] Automatic authentication token retrieval
- [ ] Save favorite courses
- [ ] Historical availability tracking

## Authentication

The availability search feature requires authentication. You can provide authentication in two ways:

1. **Environment Variable** (recommended):

   ```bash
   export GOLFSTAR_TOKEN="your_jwt_token_here"
   golfstar availability --id 903 --start 2025-01-15
   ```

2. **Command Line Parameter**:
   ```bash
   golfstar availability --id 903 --start 2025-01-15 --token "your_jwt_token_here"
   ```

### Obtaining the Token

To get your authentication token:

1. Log in to https://book.sweetspot.io
2. Open browser developer tools (F12)
3. Go to Network tab
4. Make any request and look for the `Authorization: Bearer` header
5. Copy the JWT token (everything after "Bearer ")

**Note**: Tokens expire after some time, so you may need to refresh them periodically.

## API Information

This application interfaces with the Sweetspot middleware API used by Golfstar. The Golfstar club ID is `275`.

## Contributing

This is a hobby project. Feel free to submit issues or pull requests if you find bugs or have suggestions for improvements.
