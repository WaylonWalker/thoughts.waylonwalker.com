from datetime import datetime, timedelta
from typing import Annotated
from urllib.parse import urlparse
import calendar
from statistics import mean

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse
from sqlmodel import Session, select

from thoughts.api.user import try_get_current_active_user
from thoughts.config import config, get_session
from thoughts.models.post import Post
from thoughts.models.user import User

analytics_router = APIRouter()


def get_contribution_colors(count: int, max_count: int) -> str:
    """Get the color for a contribution cell based on count"""
    if count == 0:
        return "#1e1e1e"  # Dark background for no contributions
    
    # Define color levels (using pink to match theme)
    colors = [
        "#2d1a21",  # Very light pink (almost dark)
        "#3d1f2d",  # Light pink
        "#4d2438",  # Medium pink
        "#5d2944",  # Dark pink
        "#6d2e4f",  # Very dark pink
    ]
    
    # Calculate which color to use based on the count relative to max
    if max_count <= 1:
        level = 0
    else:
        level = min(int((count / max_count) * len(colors)), len(colors) - 1)
    
    return colors[level]


def get_contribution_data(posts: list[Post], year: int) -> tuple[list, list, int, int]:
    """Generate GitHub-style contribution graph data for a specific year"""
    # Get date range for the specified year
    end_date = datetime(year, 12, 31)
    start_date = datetime(year, 1, 1)
    
    # Create a dict of post counts by date
    post_counts = {}
    max_count = 0
    total_posts = 0
    for post in posts:
        if start_date <= post.date <= end_date:
            date_str = post.date.strftime("%Y-%m-%d")
            post_counts[date_str] = post_counts.get(date_str, 0) + 1
            max_count = max(max_count, post_counts[date_str])
            total_posts += 1
    
    # Generate the grid data
    weeks = []
    current_date = start_date
    
    # Find the first Sunday to start the grid
    while current_date.weekday() != 6:  # 6 is Sunday
        current_date -= timedelta(days=1)
    
    while current_date <= end_date:
        week = []
        for _ in range(7):  # 7 days per week
            date_str = current_date.strftime("%Y-%m-%d")
            count = post_counts.get(date_str, 0)
            week.append({
                "date": date_str,
                "count": count,
                "color": get_contribution_colors(count, max_count)
            })
            current_date += timedelta(days=1)
        weeks.append(week)
    
    # Get the color scale for the legend
    colors = [get_contribution_colors(i, 4) for i in range(5)]
    
    return weeks, colors, max_count, total_posts


def get_analytics_data(session: Session):
    """Get all analytics data"""
    # Query all posts
    all_posts = session.exec(select(Post)).all()

    # Get all years from posts
    years = sorted(set(post.date.year for post in all_posts), reverse=True)
    
    # Get contribution graph data for each year
    contribution_graphs = []
    for year in years:
        data, colors, max_count, total_posts = get_contribution_data(all_posts, year)
        contribution_graphs.append({
            "year": year,
            "data": data,
            "colors": colors,
            "max_count": max_count,
            "total_posts": total_posts
        })

    # Posts per day for the last 30 days
    thirty_days_ago = datetime.now() - timedelta(days=30)

    # Filter posts to last 30 days
    posts = [p for p in all_posts if p.date >= thirty_days_ago]

    # Group posts by date
    date_counts = {}
    for post in posts:
        date_str = post.date.strftime("%Y-%m-%d")
        date_counts[date_str] = date_counts.get(date_str, 0) + 1

    # Fill in missing dates with zero counts
    posts_per_day = []
    current_date = thirty_days_ago
    while current_date <= datetime.now():
        date_str = current_date.strftime("%Y-%m-%d")
        posts_per_day.append({"date": date_str, "count": date_counts.get(date_str, 0)})
        current_date += timedelta(days=1)

    # Top 10 domains
    domain_counts = {}
    for post in all_posts:
        if post.link and post.link.lower() != "none":
            try:
                domain = urlparse(post.link).netloc
                if domain:
                    domain_counts[domain] = domain_counts.get(domain, 0) + 1
            except:
                continue

    top_domains = [
        {"domain": domain, "count": count}
        for domain, count in sorted(
            domain_counts.items(), key=lambda x: x[1], reverse=True
        )[:10]
    ]

    # Post length statistics
    posts_with_messages = [post for post in all_posts if post.message]
    message_lengths = [len(post.message or "") for post in posts_with_messages]
    avg_length = (
        round(mean(message_lengths)) if message_lengths else 0
    )

    # Top 10 longest posts
    longest_posts = sorted(
        posts_with_messages, key=lambda p: len(p.message or ""), reverse=True
    )[:10]
    longest_posts_data = [
        {
            "id": post.id,
            "title": post.title,
            "message": post.message[:100] + "..."
            if post.message and len(post.message) > 100
            else post.message,
            "length": len(post.message or ""),
            "date": post.date.strftime("%Y-%m-%d"),
        }
        for post in longest_posts
    ]

    # Posts with empty messages
    empty_posts = [
        {"id": post.id, "title": post.title, "date": post.date.strftime("%Y-%m-%d")}
        for post in all_posts
        if not post.message
    ]

    # Get tag statistics
    tag_stats = {}
    for post in all_posts:
        if post.tags:
            # Handle both string and list formats
            tags = post.tags if isinstance(post.tags, list) else [t.strip() for t in post.tags.split(',')]
            for tag in tags:
                if not tag:  # Skip empty tags
                    continue
                if tag in tag_stats:
                    tag_stats[tag]["count"] += 1
                    tag_stats[tag]["posts"].append({
                        "id": post.id,
                        "title": post.title,
                        "date": post.date.strftime("%Y-%m-%d")
                    })
                else:
                    tag_stats[tag] = {
                        "count": 1,
                        "posts": [{
                            "id": post.id,
                            "title": post.title,
                            "date": post.date.strftime("%Y-%m-%d")
                        }]
                    }
    
    # Sort tags by count and get top tags
    sorted_tags = sorted(
        [{"name": tag, **stats} for tag, stats in tag_stats.items()],
        key=lambda x: x["count"],
        reverse=True
    )

    return {
        "posts_per_day": posts_per_day,
        "top_domains": top_domains,
        "average_length": avg_length,
        "shortest_post": min(message_lengths) if message_lengths else 0,
        "longest_post": max(message_lengths) if message_lengths else 0,
        "longest_posts": longest_posts_data,
        "empty_posts": empty_posts,
        "contribution_graphs": contribution_graphs,
        "tag_stats": sorted_tags
    }


@analytics_router.get("/analytics", response_class=HTMLResponse)
async def analytics_page(
    request: Request,
    session: Session = Depends(get_session),
    current_user: Annotated[User | None, Depends(try_get_current_active_user)] = None,
):
    """Render the analytics page"""
    analytics_data = get_analytics_data(session)
    return config.templates.TemplateResponse(
        "analytics.html",
        {
            "request": request,
            "config": config,
            "current_user": current_user,
            **analytics_data,
        },
    )


@analytics_router.get("/api/analytics/timeseries")
async def get_analytics_timeseries(
    request: Request,
    session: Session = Depends(get_session),
    current_user: Annotated[User | None, Depends(try_get_current_active_user)] = None,
):
    """Get time series data for the analytics charts"""
    analytics_data = get_analytics_data(session)
    return JSONResponse({"posts_per_day": analytics_data["posts_per_day"]})


@analytics_router.get("/api/analytics/graph")
async def get_graph_data(
    session: Session = Depends(get_session),
    current_user: Annotated[User | None, Depends(try_get_current_active_user)] = None,
):
    """Get tag and post connection data for force-directed graph"""
    # Get all posts
    all_posts = session.exec(select(Post)).all()
    
    # Create nodes and links
    nodes = []
    links = []
    tag_ids = {}
    post_ids = {}
    current_id = 0

    # First pass: create nodes for tags and posts
    for post in all_posts:
        if not post.tags:
            continue
            
        # Add post node if not already added
        if post.id not in post_ids:
            post_ids[post.id] = current_id
            nodes.append({
                "id": current_id,
                "name": post.title[:50] + ("..." if len(post.title) > 50 else ""),
                "type": "post",
                "post_id": post.id  # Add post ID for linking
            })
            current_id += 1

        # Handle both string and list formats for tags
        tags = post.tags if isinstance(post.tags, list) else [t.strip() for t in post.tags.split(',')]
        for tag in tags:
            if not tag:  # Skip empty tags
                continue
                
            # Add tag node if not already added
            if tag not in tag_ids:
                tag_ids[tag] = current_id
                nodes.append({
                    "id": current_id,
                    "name": tag,
                    "type": "tag"
                })
                current_id += 1

            # Add link between post and tag
            links.append({
                "source": post_ids[post.id],
                "target": tag_ids[tag],
                "value": 1
            })

    return {
        "nodes": nodes,
        "links": links
    }
