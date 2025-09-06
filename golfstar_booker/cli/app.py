"""Main CLI application for Golfstar Booker."""

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import box
from typing import Optional, List, Dict
from datetime import datetime, time, date
from zoneinfo import ZoneInfo
import dateutil.parser

from ..api.client import GolfstarAPIClient
from ..models.course import Course
from ..models.teetime import TeeTime, TeeTimeCourse


app = typer.Typer(
    name="golfstar-booker",
    help="🏌️ Find and book available tee times at Golfstar golf courses",
    add_completion=False,
)
console = Console()


def format_course_info(course: Course) -> str:
    """Format course information for display."""
    info_lines = []

    if course.description:
        # Truncate long descriptions
        desc = (
            course.description[:200] + "..."
            if len(course.description) > 200
            else course.description
        )
        info_lines.append(f"[dim]{desc}[/dim]")

    info_lines.append(f"📍 Location: {course.lonlat.lat:.4f}, {course.lonlat.lon:.4f}")
    info_lines.append(f"⏰ Timezone: {course.timezone}")
    info_lines.append(f"📅 Book up to {course.display_tee_time_days} days in advance")

    if course.booking_cancellation_limit_hours:
        info_lines.append(
            f"🚫 Cancel up to {course.booking_cancellation_limit_hours} hours before"
        )

    status_color = "green" if course.is_active else "red"
    info_lines.append(f"✅ Status: [{status_color}]{course.state}[/{status_color}]")

    return "\n".join(info_lines)


@app.command()
def list_courses(
    search: Optional[str] = typer.Option(
        None, "--search", "-s", help="Search for courses by name"
    ),
    limit: Optional[int] = typer.Option(
        None, "--limit", "-l", help="Limit number of results"
    ),
    sort_by: str = typer.Option("name", "--sort", help="Sort by field (name, id)"),
    desc: bool = typer.Option(False, "--desc", help="Sort in descending order"),
):
    """List all available Golfstar golf courses."""
    console.print(
        Panel.fit("🏌️ [bold cyan]Golfstar Course Finder[/bold cyan] 🏌️", padding=(1, 2))
    )

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        progress.add_task("Fetching courses from Golfstar...", total=None)

        try:
            with GolfstarAPIClient() as client:
                courses = client.get_courses(
                    search=search,
                    limit=limit,
                    order_by=sort_by,
                    order_direction="desc" if desc else "asc",
                )
        except Exception as e:
            console.print(f"[red]Error fetching courses: {e}[/red]")
            raise typer.Exit(code=1)

    if not courses:
        console.print("[yellow]No courses found matching your criteria.[/yellow]")
        return

    # Create a rich table
    table = Table(
        title=f"Found {len(courses)} Golfstar Courses",
        show_header=True,
        header_style="bold magenta",
        title_style="bold white",
        show_lines=True,
    )

    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Name", style="green", no_wrap=False)
    table.add_column("Club", style="blue")
    table.add_column("Active", justify="center")
    table.add_column("Booking Days", justify="center")

    for course in courses:
        active_icon = "✅" if course.is_active else "❌"
        table.add_row(
            str(course.id),
            course.name,
            course.club.name,
            active_icon,
            str(course.display_tee_time_days),
        )

    console.print(table)

    # Show search info if applicable
    if search:
        console.print(f"\n[dim]Filtered by search term: '{search}'[/dim]")


@app.command()
def course_info(
    course_id: int = typer.Argument(
        ..., help="Course ID to get detailed information for"
    ),
):
    """Get detailed information about a specific course."""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        progress.add_task(f"Fetching course {course_id} details...", total=None)

        try:
            with GolfstarAPIClient() as client:
                courses = client.get_courses()
                course = next((c for c in courses if c.id == course_id), None)
        except Exception as e:
            console.print(f"[red]Error fetching course details: {e}[/red]")
            raise typer.Exit(code=1)

    if not course:
        console.print(f"[red]Course with ID {course_id} not found.[/red]")
        raise typer.Exit(code=1)

    # Display course details in a nice panel
    panel_content = format_course_info(course)
    console.print(
        Panel(
            panel_content,
            title=f"[bold cyan]{course.name}[/bold cyan]",
            subtitle=f"[dim]{course.club.name}[/dim]",
            border_style="cyan",
        )
    )

    # Show booking information if available
    if course.booking_information:
        console.print("\n[bold]Booking Information:[/bold]")
        console.print(Panel(course.booking_information, border_style="yellow"))

    if course.custom_email_information:
        console.print("\n[bold]Important Information:[/bold]")
        console.print(Panel(course.custom_email_information, border_style="red"))


def parse_datetime_arg(date_str: str, default_time: Optional[time] = None) -> datetime:
    """Parse date string with optional time, using default time if not specified.

    All times are interpreted as Stockholm time (Europe/Stockholm).
    """
    stockholm_tz = ZoneInfo("Europe/Stockholm")

    try:
        # Try to parse as datetime first
        dt = dateutil.parser.parse(date_str)
        # If no timezone info, assume Stockholm time
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=stockholm_tz)
        return dt
    except Exception:
        # If that fails, try as date only
        try:
            d = datetime.strptime(date_str, "%Y-%m-%d").date()
            if default_time:
                dt = datetime.combine(d, default_time)
            else:
                dt = datetime.combine(d, time.min)
            # Set Stockholm timezone
            return dt.replace(tzinfo=stockholm_tz)
        except ValueError:
            raise typer.BadParameter(
                f"Invalid date format: {date_str}. Use YYYY-MM-DD or YYYY-MM-DD HH:MM"
            )


def get_courses_by_criteria(
    client: GolfstarAPIClient,
    course_ids: Optional[List[int]] = None,
    course_names: Optional[List[str]] = None,
    all_courses: bool = False,
) -> List[Course]:
    """Get courses based on selection criteria."""
    # Get all Golfstar courses
    all_golfstar_courses = client.get_courses()

    if all_courses:
        return all_golfstar_courses

    selected_courses = []

    # Filter by IDs
    if course_ids:
        for course_id in course_ids:
            course = next((c for c in all_golfstar_courses if c.id == course_id), None)
            if course:
                selected_courses.append(course)
            else:
                console.print(
                    f"[yellow]Warning: Course ID {course_id} not found[/yellow]"
                )

    # Filter by names (search)
    if course_names:
        for name_query in course_names:
            matches = [
                c for c in all_golfstar_courses if name_query.lower() in c.name.lower()
            ]
            if matches:
                selected_courses.extend(matches)
            else:
                console.print(
                    f"[yellow]Warning: No courses found matching '{name_query}'[/yellow]"
                )

    # Remove duplicates while preserving order
    seen = set()
    unique_courses = []
    for course in selected_courses:
        if course.id not in seen:
            seen.add(course.id)
            unique_courses.append(course)

    return unique_courses


def format_availability_by_course(tee_times: List[TeeTime]) -> Dict[str, List[TeeTime]]:
    """Group tee times by course for display."""
    from collections import defaultdict

    grouped = defaultdict(list)

    for tee_time in tee_times:
        course_key = tee_time.course.name if tee_time.course else "Unknown Course"
        grouped[course_key].append(tee_time)

    # Sort tee times within each course by time
    for course in grouped:
        grouped[course].sort(key=lambda t: t.from_time if t.from_time else datetime.min)

    return dict(grouped)


def create_availability_table(
    tee_times: List[TeeTime], grouped_by_course: bool = True
) -> Table:
    """Create a table showing tee time availability."""
    # Create table with appropriate columns
    if grouped_by_course:
        table = Table(
            title="⛳ Available Tee Times",
            box=box.ROUNDED,
            header_style="bold cyan",
            title_style="bold white",
            show_lines=True,
            expand=True,
        )

        table.add_column("Time", style="white", no_wrap=True, width=12)
        table.add_column("Course", style="bright_blue", max_width=30)
        table.add_column("Available", justify="center", style="white", width=10)

        # Group by date
        by_date = {}
        for tt in tee_times:
            if tt.from_time:
                date_key = tt.from_time.date()
                if date_key not in by_date:
                    by_date[date_key] = []
                by_date[date_key].append(tt)

        # Sort dates
        for date_key in sorted(by_date.keys()):
            times = by_date[date_key]
            # Add date separator
            table.add_row(
                f"[bold yellow]{date_key.strftime('%A, %B %d, %Y')}[/bold yellow]",
                "",
                "",
                style="on grey23",
            )

            # Sort times
            times.sort(key=lambda t: t.from_time if t.from_time else datetime.min)

            for tt in times:
                # Format time using the time_display property which handles timezone conversion
                time_str = tt.time_display

                # Format course name
                course_name = tt.course.name if tt.course else "Unknown"

                # Format availability
                slots = tt.available_slots or 0
                max_slots = tt.max_slots or 0
                avail_str = f"{slots}/{max_slots}"

                # Determine status and style based on exact slot count
                if slots == 4:
                    status = "⬤ Full"
                    avail_style = "bright_green"
                elif slots == 3:
                    status = "◉ Good"
                    avail_style = "cyan"
                elif slots == 2:
                    status = "◐ Fair"
                    avail_style = "yellow"
                elif slots == 1:
                    status = "◔ Low"
                    avail_style = "bright_red"
                else:
                    status = "○ None"
                    avail_style = "red dim"

                # Add row
                table.add_row(
                    time_str,
                    course_name,
                    f"[{avail_style}]{avail_str}[/{avail_style}]",
                )

    else:
        # Single course table
        table = Table(
            box=box.SIMPLE,
            header_style="bold cyan",
            show_lines=False,
            expand=True,
            padding=(0, 1),
        )

        table.add_column("Time", style="white", no_wrap=True)
        table.add_column("Slots", justify="center", style="white")
        table.add_column("Price", justify="right", style="green")

        for tt in tee_times:
            time_str = tt.time_display

            slots = tt.available_slots or 0
            max_slots = tt.max_slots or 0

            # Determine color based on exact slot count
            if slots == 4:
                slot_style = "bright_green"
            elif slots == 3:
                slot_style = "cyan"
            elif slots == 2:
                slot_style = "yellow"
            elif slots == 1:
                slot_style = "bright_red"
            else:
                slot_style = "red dim"

            table.add_row(
                time_str,
                f"[{slot_style}]{slots}/{max_slots}[/{slot_style}]",
                tt.price_display if tt.price_display != "N/A" else "-",
            )

    return table


def create_course_tables(grouped_tee_times: Dict[str, List[TeeTime]]) -> List[Table]:
    """Create individual tables for each course."""
    tables = []

    for course_name in sorted(grouped_tee_times.keys()):
        tee_times = grouped_tee_times[course_name]

        # Create a compact table for each course
        table = Table(
            title=f"[bold cyan]{course_name}[/bold cyan]",
            box=box.ROUNDED,
            header_style="bold white on blue",
            show_lines=False,
            expand=False,
            width=45,
        )

        table.add_column("Time", style="white", no_wrap=True, width=10)
        table.add_column("Available", justify="center", width=10)
        table.add_column("Price", justify="right", style="green", width=12)

        # Group by date within course
        by_date = {}
        for tt in tee_times:
            if tt.from_time:
                date_key = tt.from_time.date()
                if date_key not in by_date:
                    by_date[date_key] = []
                by_date[date_key].append(tt)

        for date_key in sorted(by_date.keys()):
            # Add subtle date row
            table.add_row(
                f"[dim]{date_key.strftime('%b %d')}[/dim]", "", "", style="italic"
            )

            times = sorted(
                by_date[date_key],
                key=lambda t: t.from_time if t.from_time else datetime.min,
            )

            for tt in times:
                time_str = tt.time_display

                slots = tt.available_slots or 0
                max_slots = tt.max_slots or 0

                # Create visual indicator
                if slots == 0:
                    indicator = "⬤"
                    color = "red"
                elif slots == max_slots:
                    indicator = "⬤"
                    color = "green"
                elif slots >= max_slots * 0.5:
                    indicator = "◐"
                    color = "yellow"
                else:
                    indicator = "◔"
                    color = "orange1"

                table.add_row(
                    f"  {time_str}",
                    f"[{color}]{indicator}[/{color}] {slots}/{max_slots}",
                    tt.price_display if tt.price_display != "N/A" else "-",
                )

        tables.append(table)

    return tables


@app.command()
def availability(
    course_ids: Optional[List[int]] = typer.Option(
        None, "--id", "-i", help="Course ID(s) to check"
    ),
    course_names: Optional[List[str]] = typer.Option(
        None, "--name", "-n", help="Course name(s) to search for"
    ),
    all_courses: bool = typer.Option(
        False, "--all", "-a", help="Check all Golfstar courses"
    ),
    start: str = typer.Option(
        None, "--start", "-s", help="Start date/time (YYYY-MM-DD or YYYY-MM-DD HH:MM)"
    ),
    end: str = typer.Option(
        None, "--end", "-e", help="End date/time (YYYY-MM-DD or YYYY-MM-DD HH:MM)"
    ),
    players: int = typer.Option(1, "--players", "-p", help="Number of players"),
    auth_token: Optional[str] = typer.Option(
        None,
        "--token",
        "-t",
        help="Authorization token (if required)",
        envvar="GOLFSTAR_TOKEN",
    ),
):
    """Check tee time availability across multiple courses.

    Examples:
        # Check specific course by ID
        golfstar availability --id 903 --start 2025-01-15

        # Check multiple courses by name
        golfstar availability --name "Bromma" --name "Bodaholm" --start 2025-01-15

        # Check all courses for tomorrow
        golfstar availability --all --start tomorrow

        # Check with specific time range
        golfstar availability --id 903 --start "2025-01-15 08:00" --end "2025-01-15 12:00"
    """
    # Validate inputs
    if not any([course_ids, course_names, all_courses]):
        console.print(
            "[red]Error: You must specify courses using --id, --name, or --all[/red]"
        )
        raise typer.Exit(code=1)

    # Parse dates
    if not start:
        start_dt = datetime.combine(date.today(), time.min)
    else:
        start_dt = parse_datetime_arg(start, time.min)

    if not end:
        # Default to end of start day
        end_dt = datetime.combine(start_dt.date(), time(23, 59, 59))
    else:
        end_dt = parse_datetime_arg(end, time(23, 59, 59))

    # Validate date range
    if end_dt < start_dt:
        console.print("[red]Error: End date must be after start date[/red]")
        raise typer.Exit(code=1)

    console.print(
        Panel.fit(
            f"🏌️ [bold cyan]Searching Tee Times[/bold cyan] 🏌️\n"
            f"📅 {start_dt.strftime('%a %b %d, %Y %H:%M')} - {end_dt.strftime('%a %b %d, %Y %H:%M')}\n"
            f"👥 {players} player{'s' if players > 1 else ''}",
            padding=(1, 2),
        )
    )

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("Fetching courses...", total=None)

        try:
            with GolfstarAPIClient(auth_token=auth_token) as client:
                # Get selected courses
                courses = get_courses_by_criteria(
                    client, course_ids, course_names, all_courses
                )

                if not courses:
                    console.print("[red]No courses found matching your criteria[/red]")
                    raise typer.Exit(code=1)

                progress.update(
                    task,
                    description=f"Checking availability for {len(courses)} courses...",
                )

                # Get course UUIDs and create mapping
                course_uuids = [course.uuid for course in courses]
                course_map = {course.uuid: course for course in courses}

                # Fetch availability
                try:
                    tee_times = client.get_available_times(
                        course_uuids=course_uuids,
                        start_datetime=start_dt,
                        end_datetime=end_dt,
                        players=players,
                    )

                    # Map course information to tee times
                    for tt in tee_times:
                        # Find the course UUID from the tee time
                        course_uuid = None
                        if tt.course and tt.course.uuid:
                            course_uuid = tt.course.uuid
                        elif hasattr(tt, "_course_uuid"):
                            course_uuid = tt._course_uuid

                        # Map full course info if we found the UUID
                        if course_uuid and course_uuid in course_map:
                            course = course_map[course_uuid]
                            tt.course = TeeTimeCourse(
                                id=course.id,
                                uuid=course.uuid,
                                name=course.name,
                                club_name=course.club.name,
                            )
                except Exception as e:
                    if "401" in str(e) or "JWT" in str(e):
                        console.print("\n[red]Error: Authorization required.[/red]")
                        console.print(
                            "\n[yellow]This endpoint requires authentication. Options:[/yellow]"
                        )
                        console.print("1. Set GOLFSTAR_TOKEN environment variable")
                        console.print("2. Use --token parameter")
                        console.print(
                            "\n[dim]Note: The token can be obtained from browser developer tools[/dim]"
                        )
                        console.print("[dim]while logged into book.sweetspot.io[/dim]")
                        raise typer.Exit(code=1)
                    else:
                        raise

        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            raise typer.Exit(code=1)

    # Display results
    if not tee_times:
        console.print(
            "\n[yellow]No available tee times found for your criteria.[/yellow]"
        )
        return

    # Group by course
    grouped = format_availability_by_course(tee_times)
    num_courses = len(grouped)

    console.print()

    # Choose display format based on number of courses
    if num_courses == 1:
        # Single course - show detailed table
        table = create_availability_table(tee_times, grouped_by_course=True)
        console.print(table)
    else:
        # Many courses - show summary table
        console.print(
            f"[bold]Found {len(tee_times)} available tee times across {len(courses)} courses searched[/bold]\n"
        )

        # Create a summary table
        summary_table = Table(
            title="📊 Availability Summary by Course",
            box=box.ROUNDED,
            header_style="bold cyan",
            show_lines=True,
        )

        summary_table.add_column("Course", style="bright_blue", no_wrap=True)
        summary_table.add_column("Slots", justify="center", style="white", width=8)
        summary_table.add_column("Available Times", style="white", max_width=60)

        # Show all courses, including those with no availability
        for course in sorted(courses, key=lambda c: c.name):
            course_name = course.name
            times = grouped.get(course_name, [])

            # Sort times
            sorted_times = sorted(
                times, key=lambda t: t.from_time if t.from_time else datetime.min
            )

            # Format actual times for display
            time_strs = []
            for tt in sorted_times:
                if tt.from_time:
                    time_str = tt.time_display
                    slots = tt.available_slots or 0

                    # Add color based on number of available slots
                    if slots == 4:
                        time_strs.append(f"[bright_green]{time_str}[/bright_green]")
                    elif slots == 3:
                        time_strs.append(f"[cyan]{time_str}[/cyan]")
                    elif slots == 2:
                        time_strs.append(f"[yellow]{time_str}[/yellow]")
                    elif slots == 1:
                        time_strs.append(f"[bright_red]{time_str}[/bright_red]")
                    else:
                        time_strs.append(f"[red dim]{time_str}[/red dim]")

            # Join times with appropriate separators
            if len(time_strs) > 10:
                # Show first 8 and indicate more
                times_display = (
                    ", ".join(time_strs[:8])
                    + f" [dim]... +{len(time_strs) - 8} more[/dim]"
                )
            else:
                times_display = ", ".join(time_strs)

            # Format count with color
            count = len(times)
            if count == 0:
                count_display = "[red]0[/red]"
            elif count <= 5:
                count_display = f"[yellow]{count}[/yellow]"
            else:
                count_display = f"[green]{count}[/green]"

            summary_table.add_row(
                course_name,
                count_display,
                times_display if times_display else "[dim]No times available[/dim]",
            )

        console.print(summary_table)
        console.print(
            "\n[dim]Use fewer courses or a smaller time range to see detailed times[/dim]"
        )

    # Legend
    console.print(
        "\n[dim]Time colors: [bright_green]4 slots[/bright_green] · [cyan]3 slots[/cyan] · [yellow]2 slots[/yellow] · [bright_red]1 slot[/bright_red][/dim]"
    )


@app.callback()
def main(version: bool = typer.Option(False, "--version", "-v", help="Show version")):
    """🏌️ Golfstar Booker - Find and book tee times at Golfstar golf courses."""
    if version:
        console.print("[cyan]Golfstar Booker v0.1.0[/cyan]")
        raise typer.Exit()


if __name__ == "__main__":
    app()
