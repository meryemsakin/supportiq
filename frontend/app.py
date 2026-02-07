"""
Intelligent Support Router - Streamlit Dashboard
Modern and user-friendly support ticket management interface
"""

import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from typing import Optional
import json
import time
import streamlit.components.v1 as components

# Page configuration
st.set_page_config(
    page_title="🎯 Intelligent Support Router",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API Base URL
API_URL = "http://localhost:8000/api/v1"

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1f2937;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1rem;
        color: #6b7280;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 1rem;
        color: white;
    }
    .ticket-card {
        background: #f9fafb;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #3b82f6;
        margin-bottom: 0.5rem;
    }
    .priority-critical { border-left-color: #ef4444 !important; }
    .priority-high { border-left-color: #f97316 !important; }
    .priority-medium { border-left-color: #eab308 !important; }
    .priority-low { border-left-color: #22c55e !important; }
    .sentiment-positive { color: #22c55e; }
    .sentiment-negative { color: #ef4444; }
    .sentiment-neutral { color: #6b7280; }
    .stButton>button {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)


# =============================================================================
# API Helper Functions
# =============================================================================

def api_get(endpoint: str, params: dict = None) -> Optional[dict]:
    """GET request to API"""
    try:
        response = requests.get(f"{API_URL}/{endpoint}", params=params, timeout=10)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        st.error(f"API Error: {e}")
        return None


def api_post(endpoint: str, data: dict) -> Optional[dict]:
    """POST request to API"""
    try:
        response = requests.post(f"{API_URL}/{endpoint}", json=data, timeout=30)
        return response.json()
    except Exception as e:
        st.error(f"API Error: {e}")
        return None


def check_api_health() -> bool:
    """Check if API is healthy"""
    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        return response.status_code == 200
    except:
        return False


# =============================================================================
# UI Components
# =============================================================================

def render_metric_card(title: str, value: str, delta: str = None, icon: str = "📊"):
    """Render a metric card"""
    delta_html = f'<p style="color: #22c55e; margin: 0;">{delta}</p>' if delta else ''
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                padding: 1.2rem; border-radius: 1rem; color: white; text-align: center;">
        <p style="font-size: 2rem; margin: 0;">{icon}</p>
        <p style="font-size: 2rem; font-weight: bold; margin: 0.5rem 0;">{value}</p>
        <p style="font-size: 0.9rem; opacity: 0.9; margin: 0;">{title}</p>
        {delta_html}
    </div>
    """, unsafe_allow_html=True)


def get_priority_color(priority: int) -> str:
    """Get color for priority level"""
    colors = {5: "#ef4444", 4: "#f97316", 3: "#eab308", 2: "#22c55e", 1: "#3b82f6"}
    return colors.get(priority, "#6b7280")


def get_sentiment_emoji(sentiment: str) -> str:
    """Get emoji for sentiment"""
    emojis = {"positive": "😊", "neutral": "😐", "negative": "😤", "angry": "🔥"}
    return emojis.get(sentiment, "❓")


def get_priority_emoji(priority: int) -> str:
    """Get emoji for priority"""
    emojis = {5: "🔴", 4: "🟠", 3: "🟡", 2: "🟢", 1: "🔵"}
    return emojis.get(priority, "⚪")


# =============================================================================
# Pages
# =============================================================================

def page_dashboard():
    """Main Dashboard Page"""
    st.markdown('<h1 class="main-header">🎯 Support Dashboard</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Real-time ticket status and performance metrics</p>', unsafe_allow_html=True)
    
    # API Health Check
    if not check_api_health():
        st.error("⚠️ Cannot connect to API! Please make sure the backend is running.")
        st.code("docker compose up -d app")
        return
    
    # Fetch tickets
    tickets_data = api_get("tickets", {"limit": 100})
    
    if not tickets_data:
        st.warning("No tickets found yet.")
        return
    
    tickets = tickets_data.get("items", [])
    total = tickets_data.get("total", 0)
    
    # Metrics Row
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        render_metric_card("Total Tickets", str(total), icon="📋")
    
    with col2:
        open_count = len([t for t in tickets if t.get("status") in ["new", "open", "pending"]])
        render_metric_card("Open Tickets", str(open_count), icon="📬")
    
    with col3:
        critical_count = len([t for t in tickets if t.get("priority") == 5])
        render_metric_card("Critical", str(critical_count), icon="🚨")
    
    with col4:
        negative_count = len([t for t in tickets if t.get("sentiment") in ["negative", "angry"]])
        render_metric_card("Negative Sentiment", str(negative_count), icon="😤")
    
    with col5:
        processed = len([t for t in tickets if t.get("is_processed")])
        rate = int((processed / total) * 100) if total > 0 else 0
        render_metric_card("Processing Rate", f"{rate}%", icon="✅")
    
    st.markdown("---")
    
    # Charts Row
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Category Distribution")
        if tickets:
            category_counts = {}
            for t in tickets:
                cat = t.get("category", "unknown")
                category_counts[cat] = category_counts.get(cat, 0) + 1
            
            fig = px.pie(
                values=list(category_counts.values()),
                names=list(category_counts.keys()),
                hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            fig.update_layout(margin=dict(t=0, b=0, l=0, r=0))
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("📈 Priority Distribution")
        if tickets:
            priority_counts = {}
            priority_labels = {5: "Critical", 4: "High", 3: "Medium", 2: "Low", 1: "Minimal"}
            for t in tickets:
                pri = t.get("priority", 3)
                label = priority_labels.get(pri, f"P{pri}")
                priority_counts[label] = priority_counts.get(label, 0) + 1
            
            fig = px.bar(
                x=list(priority_counts.keys()),
                y=list(priority_counts.values()),
                color=list(priority_counts.keys()),
                color_discrete_map={
                    "Critical": "#ef4444", "High": "#f97316", 
                    "Medium": "#eab308", "Low": "#22c55e", "Minimal": "#3b82f6"
                }
            )
            fig.update_layout(showlegend=False, margin=dict(t=0, b=0, l=0, r=0))
            st.plotly_chart(fig, use_container_width=True)
    
    # Recent Tickets
    st.markdown("---")
    st.subheader("🕐 Recent Tickets")
    
    for ticket in tickets[:5]:
        priority = ticket.get("priority", 3)
        sentiment = ticket.get("sentiment", "neutral")
        
        col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
        
        with col1:
            st.markdown(f"""
            **{ticket.get('subject', 'No subject')}**  
            {ticket.get('content', '')[:100]}...
            """)
        with col2:
            st.markdown(f"📂 `{ticket.get('category', 'N/A')}`")
        with col3:
            st.markdown(f"{get_priority_emoji(priority)} **P{priority}**")
        with col4:
            st.markdown(f"{get_sentiment_emoji(sentiment)} {sentiment}")
        
        st.markdown("---")


def page_tickets():
    """Ticket Management Page"""
    st.markdown('<h1 class="main-header">📋 Ticket Management</h1>', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["📋 Ticket List", "➕ New Ticket"])
    
    with tab1:
        # Filters
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            status_filter = st.selectbox(
                "Status",
                ["All", "new", "open", "pending", "resolved", "closed"]
            )
        with col2:
            category_filter = st.selectbox(
                "Category",
                ["All", "technical_issue", "billing_question", "feature_request", 
                 "bug_report", "complaint", "general_inquiry"]
            )
        with col3:
            priority_filter = st.selectbox(
                "Priority",
                ["All", "5 - Critical", "4 - High", "3 - Medium", "2 - Low", "1 - Minimal"]
            )
        with col4:
            sentiment_filter = st.selectbox(
                "Sentiment",
                ["All", "positive", "neutral", "negative", "angry"]
            )
        
        # Build query params
        params = {"limit": 50}
        if status_filter != "All":
            params["status"] = status_filter
        if category_filter != "All":
            params["category"] = category_filter
        if priority_filter != "All":
            params["priority"] = int(priority_filter.split(" ")[0])
        if sentiment_filter != "All":
            params["sentiment"] = sentiment_filter
        
        # Fetch and display tickets
        tickets_data = api_get("tickets", params)
        
        if tickets_data and tickets_data.get("items"):
            for ticket in tickets_data["items"]:
                if not ticket:
                    continue
                    
                # Safe get for subject
                subject = ticket.get('subject') or 'No subject'
                subject = subject[:50] if subject else 'No subject'
                
                with st.expander(
                    f"{get_priority_emoji(ticket.get('priority', 3))} "
                    f"{subject} - "
                    f"{ticket.get('category', 'N/A')}"
                ):
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.markdown(f"**Content:**")
                        st.text_area("", ticket.get("content", ""), height=100, disabled=True, key=ticket.get("id", "unknown"))
                        
                        st.markdown(f"**Customer:** {ticket.get('customer_email', 'N/A')}")
                    
                    with col2:
                        confidence = ticket.get('category_confidence') or 0
                        created_at = ticket.get('created_at', '')
                        created_date = created_at[:10] if created_at else 'N/A'
                        
                        st.markdown(f"""
                        **📂 Category:** `{ticket.get('category', 'N/A')}`  
                        **📊 Confidence:** {confidence:.0%}  
                        **{get_sentiment_emoji(ticket.get('sentiment', 'neutral'))} Sentiment:** {ticket.get('sentiment', 'N/A')}  
                        **{get_priority_emoji(ticket.get('priority', 3))} Priority:** {ticket.get('priority', 'N/A')} ({ticket.get('priority_level', '')})  
                        **🏷️ Status:** {ticket.get('status', 'N/A')}  
                        **🌐 Language:** {ticket.get('language', 'N/A')}  
                        **📅 Date:** {created_date}
                        """)
                        
                        if ticket.get("priority_factors"):
                            st.markdown("**Priority Factors:**")
                            for factor in ticket.get("priority_factors", []):
                                st.markdown(f"• {factor}")
        else:
            st.info("No tickets found matching the filters.")
    
    with tab2:
        st.subheader("➕ Create New Ticket")
        
        with st.form("new_ticket_form"):
            subject = st.text_input("Subject", placeholder="Enter ticket subject...")
            content = st.text_area(
                "Content", 
                placeholder="Paste customer message here...",
                height=150
            )
            
            col1, col2 = st.columns(2)
            with col1:
                customer_email = st.text_input("Customer Email", placeholder="customer@example.com")
            with col2:
                customer_name = st.text_input("Customer Name (optional)", placeholder="John Doe")
            
            submitted = st.form_submit_button("🚀 Create Ticket", type="primary")
            
            if submitted:
                if not content:
                    st.error("Content field is required!")
                elif not customer_email:
                    st.error("Customer email is required!")
                else:
                    with st.spinner("Processing ticket..."):
                        data = {
                            "content": content,
                            "customer_email": customer_email,
                            "subject": subject or None,
                            "customer_name": customer_name or None
                        }
                        result = api_post("tickets", data)
                        
                        if result and result.get("ticket_id"):
                            st.success(f"✅ Ticket created! ID: {result['ticket_id']}")
                            st.balloons()
                            
                            # Wait for AI processing with progress bar
                            progress_bar = st.progress(0, text="🤖 AI is analyzing...")
                            ticket_detail = None
                            
                            for attempt in range(10):
                                time.sleep(2)
                                progress_bar.progress((attempt + 1) * 10, text=f"🤖 AI is analyzing... ({attempt + 1}/10)")
                                ticket_detail = api_get(f"tickets/{result['ticket_id']}")
                                if ticket_detail and ticket_detail.get("is_processed"):
                                    progress_bar.progress(100, text="✅ Analysis complete!")
                                    break
                            
                            time.sleep(0.5)
                            
                            if ticket_detail:
                                st.markdown("### 🎯 AI Analysis Results")
                                
                                # Get agent name if assigned
                                agent_name = "Not Assigned"
                                agent_id = ticket_detail.get("assigned_agent_id")
                                if agent_id:
                                    agent_data = api_get(f"agents/{agent_id}")
                                    if agent_data:
                                        agent_name = agent_data.get("name", "Unknown")
                                
                                col1, col2, col3, col4, col5 = st.columns(5)
                                
                                category = ticket_detail.get("category") or "Processing..."
                                sentiment = ticket_detail.get("sentiment") or "Processing..."
                                priority = ticket_detail.get("priority") or 0
                                
                                with col1:
                                    st.metric("📂 Category", category)
                                with col2:
                                    st.metric(f"{get_sentiment_emoji(sentiment)} Sentiment", sentiment)
                                with col3:
                                    st.metric(f"{get_priority_emoji(priority)} Priority", f"P{priority}" if priority else "N/A")
                                with col4:
                                    st.metric("🌐 Language", ticket_detail.get("language", "N/A"))
                                with col5:
                                    st.metric("👤 Assigned Agent", agent_name)
                                
                                # Additional details
                                if ticket_detail.get("assignment_reason"):
                                    st.info(f"📝 **Assignment Reason:** {ticket_detail.get('assignment_reason')}")
                                
                                if ticket_detail.get("priority_factors"):
                                    factors = ", ".join(ticket_detail.get("priority_factors", []))
                                    st.info(f"📋 **Priority Factors:** {factors}")
                        else:
                            st.error("Failed to create ticket!")


def page_analytics():
    """Analytics Page"""
    st.markdown('<h1 class="main-header">📊 Analytics</h1>', unsafe_allow_html=True)
    
    tickets_data = api_get("tickets", {"limit": 100})
    
    if not tickets_data or not tickets_data.get("items"):
        st.warning("Not enough data for analysis.")
        return
    
    tickets = tickets_data["items"]
    df = pd.DataFrame(tickets)
    
    # Summary Stats
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Tickets", len(df))
    with col2:
        avg_priority = df["priority"].mean() if "priority" in df else 0
        st.metric("Average Priority", f"{avg_priority:.1f}")
    with col3:
        negative_rate = len(df[df["sentiment"].isin(["negative", "angry"])]) / len(df) * 100 if len(df) > 0 else 0
        st.metric("Negative Sentiment Rate", f"{negative_rate:.1f}%")
    
    st.markdown("---")
    
    # Charts
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Category Distribution")
        if "category" in df:
            category_counts = df["category"].value_counts()
            fig = px.pie(
                values=category_counts.values,
                names=category_counts.index,
                hole=0.4
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("😊 Sentiment Distribution")
        if "sentiment" in df:
            sentiment_counts = df["sentiment"].value_counts()
            colors = {"positive": "#22c55e", "neutral": "#6b7280", "negative": "#f97316", "angry": "#ef4444"}
            fig = px.pie(
                values=sentiment_counts.values,
                names=sentiment_counts.index,
                hole=0.4,
                color=sentiment_counts.index,
                color_discrete_map=colors
            )
            st.plotly_chart(fig, use_container_width=True)
    
    # Priority by Category Heatmap
    st.subheader("🗺️ Category vs Priority Matrix")
    if "category" in df and "priority" in df:
        pivot = pd.crosstab(df["category"], df["priority"])
        fig = px.imshow(
            pivot,
            labels=dict(x="Priority", y="Category", color="Ticket Count"),
            color_continuous_scale="RdYlGn_r"
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Data Table
    st.subheader("📋 All Data")
    display_cols = ["subject", "category", "sentiment", "priority", "status", "customer_email", "created_at"]
    available_cols = [c for c in display_cols if c in df.columns]
    st.dataframe(df[available_cols], use_container_width=True)


def page_agents():
    """Agent Management Page"""
    st.markdown('<h1 class="main-header">👥 Agent Management</h1>', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["👥 Agent List", "➕ New Agent"])
    
    with tab1:
        agents_data = api_get("agents", {"limit": 50})
        
        # Get all tickets to match with agents
        all_tickets = api_get("tickets", {"limit": 200})
        tickets_by_agent = {}
        if all_tickets and all_tickets.get("items"):
            for t in all_tickets["items"]:
                agent_id = t.get("assigned_agent_id")
                if agent_id:
                    if agent_id not in tickets_by_agent:
                        tickets_by_agent[agent_id] = []
                    tickets_by_agent[agent_id].append(t)
        
        if agents_data and agents_data.get("items"):
            for agent in agents_data["items"]:
                agent_id = agent.get("id")
                assigned_tickets = tickets_by_agent.get(agent_id, [])
                ticket_count = len(assigned_tickets)
                
                status_emoji = "🟢" if agent.get("status") == "online" else "🔴"
                ticket_badge = f" 📬 {ticket_count}" if ticket_count > 0 else ""
                
                with st.expander(f"{status_emoji} {agent.get('name', 'Unnamed')} - {agent.get('email', '')}{ticket_badge}"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown(f"""
                        **👤 Name:** {agent.get('name', 'N/A')}  
                        **📧 Email:** {agent.get('email', 'N/A')}  
                        **🏷️ Role:** {agent.get('role', 'N/A')}  
                        **🏢 Team:** {agent.get('team', 'N/A')}  
                        **⚡ Status:** {agent.get('status', 'N/A')}
                        """)
                    
                    with col2:
                        skills = agent.get('skills', [])
                        languages = agent.get('languages', [])
                        
                        st.markdown(f"""
                        **🎯 Skills:** {', '.join(skills) if skills else 'None'}  
                        **🌐 Languages:** {', '.join(languages) if languages else 'None'}  
                        **📊 Load:** {agent.get('current_load', 0)}/{agent.get('max_load', 10)}  
                        **⭐ Experience:** {agent.get('experience_level', 1)}/5  
                        **🕐 Work Hours:** {agent.get('work_hours_start', '09:00')} - {agent.get('work_hours_end', '18:00')}
                        """)
                    
                    # Load bar
                    load_pct = (agent.get('current_load', 0) / agent.get('max_load', 10)) * 100
                    st.progress(int(load_pct), text=f"Load: {load_pct:.0f}%")
                    
                    # Show assigned tickets
                    if assigned_tickets:
                        st.markdown("---")
                        st.markdown(f"### 📬 Assigned Tickets ({ticket_count})")
                        
                        for ticket in assigned_tickets[:5]:  # Show max 5
                            ticket_id = ticket.get('id')
                            priority = ticket.get('priority', 3)
                            priority_emoji = get_priority_emoji(priority)
                            sentiment = ticket.get('sentiment', 'neutral')
                            sentiment_emoji = get_sentiment_emoji(sentiment)
                            
                            subject = ticket.get('subject') or ticket.get('content', '')[:50] + '...'
                            content = ticket.get('content', '')
                            category = ticket.get('category', 'N/A')
                            status = ticket.get('status', 'NEW')
                            customer_email = ticket.get('customer_email', 'N/A')
                            
                            status_colors = {
                                'NEW': '🆕',
                                'OPEN': '📂',
                                'IN_PROGRESS': '🔄',
                                'RESOLVED': '✅',
                                'CLOSED': '🔒'
                            }
                            status_icon = status_colors.get(status, '📋')
                            
                            # Ticket card
                            with st.container():
                                st.markdown(f"""
                                <div style="background: #1f2937; padding: 1rem; border-radius: 0.5rem; margin-bottom: 1rem; border-left: 4px solid {'#ef4444' if priority >= 4 else '#eab308' if priority == 3 else '#22c55e'};">
                                    <div style="display: flex; justify-content: space-between; align-items: center;">
                                        <span style="color: white; font-weight: bold;">{status_icon} {subject}</span>
                                        <span style="color: #9ca3af; font-size: 0.8rem;">#{ticket_id[:8] if ticket_id else 'N/A'}</span>
                                    </div>
                                    <p style="color: #d1d5db; margin: 0.5rem 0; font-size: 0.9rem;">{content[:100]}{'...' if len(content) > 100 else ''}</p>
                                    <div style="color: #9ca3af; font-size: 0.8rem;">
                                        {priority_emoji} P{priority} | {sentiment_emoji} {sentiment} | 📂 {category} | 📧 {customer_email}
                                    </div>
                                </div>
                                """, unsafe_allow_html=True)
                                
                                st.markdown("---")
                        
                        if ticket_count > 5:
                            st.info(f"... and {ticket_count - 5} more tickets")
                    else:
                        st.info("📭 No assigned tickets yet")
        else:
            st.info("No agents found yet.")
    
    with tab2:
        st.subheader("➕ Add New Agent")
        
        with st.form("new_agent_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                name = st.text_input("Name *", placeholder="John Doe")
                email = st.text_input("Email *", placeholder="john@company.com")
                team = st.text_input("Team", placeholder="Technical Support")
            
            with col2:
                experience = st.slider("Experience Level", 1, 5, 3)
                max_load = st.number_input("Max Load", 1, 50, 10)
                languages = st.multiselect(
                    "Languages",
                    ["en", "tr", "de", "fr", "es"],
                    default=["en"]
                )
            
            skills = st.multiselect(
                "Skills",
                ["technical_issue", "billing_question", "feature_request", 
                 "bug_report", "complaint", "general_inquiry", "account_management"],
                default=["general_inquiry"]
            )
            
            submitted = st.form_submit_button("👤 Add Agent", type="primary")
            
            if submitted:
                if not name or not email:
                    st.error("Name and email are required!")
                else:
                    data = {
                        "name": name,
                        "email": email,
                        "team": team or None,
                        "skills": skills,
                        "languages": languages,
                        "experience_level": experience,
                        "max_load": max_load
                    }
                    result = api_post("agents", data)
                    
                    if result and result.get("id"):
                        st.success(f"✅ Agent created!")
                        st.balloons()
                    else:
                        st.error("Failed to create agent!")


def page_landing():
    """Landing Page - Project Introduction"""
    
    # Hero Section
    st.markdown("""
    <div style="text-align: center; padding: 2rem 0;">
        <h1 style="font-size: 3.5rem; font-weight: 800; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 0.5rem;">
            🎯 Intelligent Support Router
        </h1>
        <p style="font-size: 1.5rem; color: #6b7280; margin-bottom: 2rem;">
            AI-Powered Customer Support Ticket Routing System
        </p>
        <p style="font-size: 1.1rem; color: #9ca3af; max-width: 800px; margin: 0 auto 2rem auto;">
            Automatically categorize, prioritize, and route customer requests using AI. 
            Open-source, self-hosted, and privacy-first.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Quick Stats from API
    col1, col2, col3, col4 = st.columns(4)
    
    tickets_data = api_get("tickets", {"limit": 100})
    agents_data = api_get("agents", {"limit": 50})
    
    total_tickets = tickets_data.get("total", 0) if tickets_data else 0
    total_agents = len(agents_data.get("items", [])) if agents_data else 0
    
    with col1:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 1.5rem; border-radius: 1rem; text-align: center;">
            <p style="font-size: 2.5rem; font-weight: bold; color: white; margin: 0;">""" + str(total_tickets) + """</p>
            <p style="color: rgba(255,255,255,0.8); margin: 0;">Tickets Processed</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); padding: 1.5rem; border-radius: 1rem; text-align: center;">
            <p style="font-size: 2.5rem; font-weight: bold; color: white; margin: 0;">""" + str(total_agents) + """</p>
            <p style="color: rgba(255,255,255,0.8); margin: 0;">Active Agents</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); padding: 1.5rem; border-radius: 1rem; text-align: center;">
            <p style="font-size: 2.5rem; font-weight: bold; color: white; margin: 0;">8</p>
            <p style="color: rgba(255,255,255,0.8); margin: 0;">Categories</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%); padding: 1.5rem; border-radius: 1rem; text-align: center;">
            <p style="font-size: 2.5rem; font-weight: bold; color: white; margin: 0;">&lt;2s</p>
            <p style="color: rgba(255,255,255,0.8); margin: 0;">Processing Time</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Features Section
    st.markdown("## ✨ Features")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div style="background: #1f2937; padding: 1.5rem; border-radius: 1rem; height: 100%;">
            <h3 style="color: white;">🤖 AI Classification</h3>
            <p style="color: #9ca3af;">
                Automatic ticket categorization using GPT-4. 
                Technical issues, billing, complaints, feature requests, and more.
            </p>
            <p style="color: #22c55e;">✓ 95%+ accuracy</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div style="background: #1f2937; padding: 1.5rem; border-radius: 1rem; height: 100%;">
            <h3 style="color: white;">😤 Sentiment Analysis</h3>
            <p style="color: #9ca3af;">
                Detect customer satisfaction in real-time. 
                Route angry customers with priority.
            </p>
            <p style="color: #22c55e;">✓ Multi-language support</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div style="background: #1f2937; padding: 1.5rem; border-radius: 1rem; height: 100%;">
            <h3 style="color: white;">🎯 Smart Routing</h3>
            <p style="color: #9ca3af;">
                Skill matching, load balancing, and priority-based 
                automatic agent assignment.
            </p>
            <p style="color: #22c55e;">✓ SLA tracking</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div style="background: #1f2937; padding: 1.5rem; border-radius: 1rem; height: 100%;">
            <h3 style="color: white;">📊 Priority Scoring</h3>
            <p style="color: #9ca3af;">
                Urgent keywords, sentiment, customer tier, and 
                category-based 1-5 priority calculation.
            </p>
            <p style="color: #22c55e;">✓ Customizable rules</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div style="background: #1f2937; padding: 1.5rem; border-radius: 1rem; height: 100%;">
            <h3 style="color: white;">🔌 Integrations</h3>
            <p style="color: #9ca3af;">
                Zendesk, Freshdesk, Email, and webhook support. 
                Connect to your existing systems easily.
            </p>
            <p style="color: #22c55e;">✓ REST API</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div style="background: #1f2937; padding: 1.5rem; border-radius: 1rem; height: 100%;">
            <h3 style="color: white;">🔒 Self-Hosted</h3>
            <p style="color: #9ca3af;">
                Keep your data on your servers. Run on your own 
                infrastructure with a single Docker command.
            </p>
            <p style="color: #22c55e;">✓ Open source (MIT)</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # How it works
    st.markdown("## 🔄 How It Works")
    
    st.markdown("""
    <div style="display: flex; justify-content: space-around; align-items: center; padding: 2rem 0; flex-wrap: wrap;">
        <div style="text-align: center; padding: 1rem;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); width: 80px; height: 80px; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 1rem auto;">
                <span style="font-size: 2rem;">📧</span>
            </div>
            <h4 style="color: white;">1. Ticket Arrives</h4>
            <p style="color: #9ca3af; font-size: 0.9rem;">API, webhook, or email</p>
        </div>
        <div style="color: #667eea; font-size: 2rem;">→</div>
        <div style="text-align: center; padding: 1rem;">
            <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); width: 80px; height: 80px; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 1rem auto;">
                <span style="font-size: 2rem;">🤖</span>
            </div>
            <h4 style="color: white;">2. AI Analysis</h4>
            <p style="color: #9ca3af; font-size: 0.9rem;">Category, sentiment, priority</p>
        </div>
        <div style="color: #667eea; font-size: 2rem;">→</div>
        <div style="text-align: center; padding: 1rem;">
            <div style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); width: 80px; height: 80px; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 1rem auto;">
                <span style="font-size: 2rem;">🎯</span>
            </div>
            <h4 style="color: white;">3. Routing</h4>
            <p style="color: #9ca3af; font-size: 0.9rem;">Assign to right agent</p>
        </div>
        <div style="color: #667eea; font-size: 2rem;">→</div>
        <div style="text-align: center; padding: 1rem;">
            <div style="background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%); width: 80px; height: 80px; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 1rem auto;">
                <span style="font-size: 2rem;">✅</span>
            </div>
            <h4 style="color: white;">4. Resolution</h4>
            <p style="color: #9ca3af; font-size: 0.9rem;">Fast customer satisfaction</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Categories showcase
    st.markdown("## 📂 Supported Categories")
    
    categories = [
        ("🔧", "Technical Issue", "App errors, crashes"),
        ("💰", "Billing Question", "Payments, charges"),
        ("✨", "Feature Request", "New feature suggestions"),
        ("🐛", "Bug Report", "Bug reports"),
        ("😤", "Complaint", "Customer complaints"),
        ("❓", "General Inquiry", "Information requests"),
        ("👤", "Account Management", "Profile, password"),
        ("↩️", "Return/Refund", "Product returns")
    ]
    
    cols = st.columns(4)
    for i, (icon, name, desc) in enumerate(categories):
        with cols[i % 4]:
            st.markdown(f"""
            <div style="background: #1f2937; padding: 1rem; border-radius: 0.5rem; margin-bottom: 1rem; text-align: center;">
                <span style="font-size: 2rem;">{icon}</span>
                <p style="color: white; font-weight: bold; margin: 0.5rem 0 0.25rem 0;">{name}</p>
                <p style="color: #6b7280; font-size: 0.8rem; margin: 0;">{desc}</p>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Tech Stack
    st.markdown("## 🛠️ Technology")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("""
        **Backend**
        - FastAPI
        - PostgreSQL
        - Redis
        - Celery
        """)
    
    with col2:
        st.markdown("""
        **AI/ML**
        - OpenAI GPT-4
        - Embeddings
        - ChromaDB
        - NLP
        """)
    
    with col3:
        st.markdown("""
        **DevOps**
        - Docker
        - GitHub Actions
        - Prometheus
        - Sentry
        """)
    
    with col4:
        st.markdown("""
        **Frontend**
        - Streamlit
        - Plotly
        - REST API
        - WebSocket
        """)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # CTA
    st.markdown("""
    <div style="text-align: center; padding: 2rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 1rem; margin-top: 2rem;">
        <h2 style="color: white; margin-bottom: 1rem;">🚀 Try It Now!</h2>
        <p style="color: rgba(255,255,255,0.9); margin-bottom: 1.5rem;">
            Click "🧪 Live Demo" in the sidebar to test the AI.
        </p>
    </div>
    """, unsafe_allow_html=True)


def page_test():
    """Live Demo Page"""
    
    # Initialize session state for persisting results
    if "last_ticket" not in st.session_state:
        st.session_state.last_ticket = None
    if "last_agent" not in st.session_state:
        st.session_state.last_agent = None
    
    # Hero
    st.markdown("""
    <div style="text-align: center; padding: 1rem 0 2rem 0;">
        <h1 style="font-size: 2.5rem; font-weight: 700; color: white;">🧪 Live Demo</h1>
        <p style="color: #9ca3af; font-size: 1.1rem;">
            Test how AI analyzes customer messages in real-time
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Preset messages with descriptions
    presets = {
        "🔧 Technical Issue": {
            "text": "Your app keeps crashing, I haven't been able to use it for 3 days! I'm using a Samsung Galaxy S23.",
            "expected": "technical_issue",
            "desc": "App error report"
        },
        "💰 Billing Issue": {
            "text": "There's an error on last month's invoice, I was overcharged. $199 was charged instead of $99.",
            "expected": "billing_question",
            "desc": "Invoice dispute"
        },
        "🔥 Angry Customer": {
            "text": "THIS IS OUTRAGEOUS!!! NO RESPONSE FOR 1 WEEK! REFUND MY MONEY!!! TERRIBLE SERVICE!!!",
            "expected": "complaint",
            "desc": "High priority complaint"
        },
        "✨ Feature Request": {
            "text": "Could you add dark mode to the mobile app? My eyes get tired when using it at night.",
            "expected": "feature_request",
            "desc": "New feature request"
        },
        "❓ General Question": {
            "text": "Hello, how long is the warranty on your products? I'd like to know before purchasing.",
            "expected": "general_inquiry",
            "desc": "Information request"
        },
        "↩️ Return Request": {
            "text": "I want to return the product I bought 15 days ago. Order number: #12345. The product was never used.",
            "expected": "return_refund",
            "desc": "Product return"
        },
        "🚨 Emergency": {
            "text": "URGENT!!! Our system has completely crashed, all our data is lost!!! We need help immediately!!!",
            "expected": "technical_issue",
            "desc": "Critical priority issue"
        },
        "😊 Positive Feedback": {
            "text": "You provide excellent service! My problem was solved in 10 minutes. Thank you so much, 5 stars!",
            "expected": "general_inquiry",
            "desc": "Customer appreciation"
        }
    }
    
    st.markdown("### 📝 Test Message")
    
    # Preset selection with nice cards
    selected_preset = st.selectbox(
        "Select a preset scenario or write your own message",
        ["✏️ Write My Own Message"] + list(presets.keys()),
        label_visibility="collapsed"
    )
    
    if selected_preset == "✏️ Write My Own Message":
        test_message = st.text_area(
            "Customer message",
            height=150, 
            placeholder="Enter customer support message here...\n\nExample: My order hasn't arrived in 3 days, where is it?",
            label_visibility="collapsed"
        )
    else:
        preset_data = presets[selected_preset]
        st.info(f"**Scenario:** {preset_data['desc']}")
        test_message = st.text_area(
            "Customer message",
            value=preset_data["text"], 
            height=150,
            label_visibility="collapsed"
        )
    
    if st.button("🚀 Analyze", type="primary"):
        if test_message:
            with st.spinner("AI is analyzing..."):
                result = api_post("tickets", {
                    "content": test_message,
                    "customer_email": "test@test.com",
                    "process_async": False
                })
                
                if result and result.get("ticket_id"):
                    # Wait for processing with retry
                    ticket = None
                    progress_bar = st.progress(0, text="AI is analyzing...")
                    
                    for attempt in range(10):
                        time.sleep(2)
                        progress_bar.progress((attempt + 1) * 10, text=f"AI is analyzing... ({attempt + 1}/10)")
                        ticket = api_get(f"tickets/{result['ticket_id']}")
                        if ticket and ticket.get("is_processed"):
                            progress_bar.progress(100, text="✅ Analysis complete!")
                            break
                    
                    time.sleep(0.5)  # Brief pause before showing results
                    
                    if ticket:
                        # Save to session state for persistence
                        st.session_state.last_ticket = ticket
                        
                        # Get agent data
                        agent_id = ticket.get("assigned_agent_id")
                        if agent_id:
                            agent_data = api_get(f"agents/{agent_id}")
                            st.session_state.last_agent = agent_data
                        else:
                            st.session_state.last_agent = None
    
    # Always show last results if available
    if st.session_state.last_ticket:
        ticket = st.session_state.last_ticket
        
        st.markdown("---")
        st.markdown("## 📊 Analysis Results")
        
        if ticket.get("is_processed"):
            st.success("✅ Analysis complete!")
        else:
            st.warning("⏳ Ticket is still processing, showing current results...")
        
        # Results
        rcol1, rcol2, rcol3, rcol4, rcol5 = st.columns(5)
        
        category = ticket.get("category") or "Processing..."
        sentiment = ticket.get("sentiment") or "Processing..."
        priority = ticket.get("priority") or 0
        language = ticket.get("language") or "N/A"
        
        # Get agent name from session state
        agent_name = "Not Assigned"
        if st.session_state.last_agent:
            agent_name = st.session_state.last_agent.get("name", "Unknown")
        
        with rcol1:
            st.metric("📂 Category", category)
        with rcol2:
            st.metric(f"{get_sentiment_emoji(sentiment)} Sentiment", sentiment)
        with rcol3:
            st.metric(f"{get_priority_emoji(priority)} Priority", f"P{priority}" if priority else "N/A")
        with rcol4:
            st.metric("🌐 Language", language)
        with rcol5:
            st.metric("👤 Assigned Agent", agent_name)
        
        # User-friendly details
        st.markdown("---")
        st.markdown("### 📋 Analysis Details")
        
        # Category card
        confidence = ticket.get("category_confidence") or 0
        confidence_pct = int(confidence * 100)
        confidence_color = "#22c55e" if confidence > 0.7 else "#eab308" if confidence > 0.4 else "#ef4444"
        
        category_names = {
            "technical_issue": "🔧 Technical Issue",
            "billing_question": "💰 Billing Question",
            "feature_request": "✨ Feature Request",
            "bug_report": "🐛 Bug Report",
            "complaint": "😤 Complaint",
            "general_inquiry": "❓ General Inquiry",
            "account_management": "👤 Account Management",
            "return_refund": "↩️ Return/Refund"
        }
        
        sentiment_info = {
            "positive": ("😊", "Positive", "#22c55e", "Customer seems satisfied"),
            "neutral": ("😐", "Neutral", "#6b7280", "Normal request"),
            "negative": ("😤", "Negative", "#f97316", "Customer is unsatisfied"),
            "angry": ("🔥", "Very Angry", "#ef4444", "Needs immediate attention!")
        }
        
        priority_info = {
            5: ("🔴", "Critical", "#ef4444", "Immediate action required"),
            4: ("🟠", "High", "#f97316", "Should be resolved today"),
            3: ("🟡", "Medium", "#eab308", "Normal processing time"),
            2: ("🟢", "Low", "#22c55e", "Not urgent"),
            1: ("🔵", "Minimal", "#3b82f6", "Can wait")
        }
        
        dcol1, dcol2, dcol3 = st.columns(3)
        
        with dcol1:
            cat_display = category_names.get(category, f"📂 {category}")
            st.markdown(f"""
            <div style="background: #1f2937; padding: 1rem; border-radius: 0.5rem; border-left: 4px solid {confidence_color};">
                <p style="color: #9ca3af; margin: 0; font-size: 0.8rem;">CATEGORY</p>
                <p style="color: white; margin: 0.5rem 0; font-size: 1.2rem; font-weight: bold;">{cat_display}</p>
                <p style="color: #9ca3af; margin: 0; font-size: 0.9rem;">Confidence: {confidence_pct}%</p>
                <div style="background: #374151; border-radius: 0.25rem; height: 6px; margin-top: 0.5rem;">
                    <div style="background: {confidence_color}; width: {confidence_pct}%; height: 100%; border-radius: 0.25rem;"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with dcol2:
            sent_emoji, sent_label, sent_color, sent_desc = sentiment_info.get(
                sentiment, ("❓", sentiment, "#6b7280", "")
            )
            sent_score = ticket.get("sentiment_score") or 0
            st.markdown(f"""
            <div style="background: #1f2937; padding: 1rem; border-radius: 0.5rem; border-left: 4px solid {sent_color};">
                <p style="color: #9ca3af; margin: 0; font-size: 0.8rem;">SENTIMENT</p>
                <p style="color: white; margin: 0.5rem 0; font-size: 1.2rem; font-weight: bold;">{sent_emoji} {sent_label}</p>
                <p style="color: #9ca3af; margin: 0; font-size: 0.9rem;">{sent_desc}</p>
                <p style="color: {sent_color}; margin: 0.5rem 0 0 0; font-size: 0.8rem;">Score: {sent_score:.2f}</p>
            </div>
            """, unsafe_allow_html=True)
        
        with dcol3:
            pri = ticket.get("priority") or 3
            pri_emoji, pri_label, pri_color, pri_desc = priority_info.get(
                pri, ("⚪", "Unknown", "#6b7280", "")
            )
            st.markdown(f"""
            <div style="background: #1f2937; padding: 1rem; border-radius: 0.5rem; border-left: 4px solid {pri_color};">
                <p style="color: #9ca3af; margin: 0; font-size: 0.8rem;">PRIORITY</p>
                <p style="color: white; margin: 0.5rem 0; font-size: 1.2rem; font-weight: bold;">{pri_emoji} {pri_label}</p>
                <p style="color: #9ca3af; margin: 0; font-size: 0.9rem;">{pri_desc}</p>
                <p style="color: {pri_color}; margin: 0.5rem 0 0 0; font-size: 0.8rem;">Level: P{pri}</p>
            </div>
            """, unsafe_allow_html=True)
        
        # Priority factors
        factors = ticket.get("priority_factors") or []
        if factors:
            st.markdown("#### 🎯 Priority Factors")
            factor_names = {
                "urgent_keyword_detected": "🚨 Urgent keyword detected",
                "high_priority_keyword": "⚡ High priority keyword",
                "sentiment_negative": "😤 Negative sentiment",
                "sentiment_angry": "🔥 Angry customer",
                "critical_category_technical_issue": "🔧 Critical category: Technical issue",
                "critical_category_complaint": "😤 Critical category: Complaint",
                "critical_category_bug_report": "🐛 Critical category: Bug",
                "customer_tier_vip": "⭐ VIP customer",
                "customer_tier_premium": "💎 Premium customer",
                "excessive_caps": "🔠 Excessive capitalization",
                "multiple_exclamations": "❗ Multiple exclamation marks",
                "deadline_mention": "⏰ Urgency mentioned",
                "low_priority_category_general_inquiry": "📝 Low priority: General inquiry",
                "low_priority_category_feature_request": "✨ Low priority: Feature request"
            }
            
            fcols = st.columns(min(len(factors), 3))
            for i, factor in enumerate(factors):
                with fcols[i % 3]:
                    display_name = factor_names.get(factor, factor.replace("_", " ").title())
                    st.info(display_name)
        
        # Reasoning
        reasoning = ticket.get("classification_reasoning")
        if reasoning:
            st.markdown("#### 💡 How Was It Classified?")
            if "Rule-based" in reasoning:
                st.warning("📋 Rule-based classification used (OpenAI API not active)")
            else:
                st.success(f"🤖 AI Analysis: {reasoning}")
        
        # Suggested Responses
        suggested = ticket.get("suggested_responses")
        if suggested and len(suggested) > 0:
            st.markdown("#### 💬 Suggested Responses")
            for i, response in enumerate(suggested, 1):
                with st.expander(f"📝 Response Option {i}", expanded=(i == 1)):
                    st.write(response)
        
        # Clear button
        if st.button("🗑️ Clear Results"):
            st.session_state.last_ticket = None
            st.session_state.last_agent = None
            st.rerun()


# =============================================================================
# Settings Page
# =============================================================================

def page_settings():
    """Settings & Configuration Page"""
    
    st.markdown('<h1 class="main-header">⚙️ Settings</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Manage categories, routing rules, and integrations</p>', unsafe_allow_html=True)
    
    tab1, tab2, tab3, tab4 = st.tabs(["📁 Categories", "🔀 Routing Rules", "🔌 Webhooks", "📚 Knowledge Base"])
    
    # =========================================================================
    # Categories Tab
    # =========================================================================
    with tab1:
        st.markdown("### Ticket Categories")
        
        categories = api_get("config/categories")
        
        if categories and "items" in categories:
            # Display categories in a grid
            cols = st.columns(3)
            for i, cat in enumerate(categories["items"]):
                with cols[i % 3]:
                    with st.container():
                        st.markdown(f"""
                        <div style="background: #1e293b; padding: 1rem; border-radius: 8px; margin-bottom: 1rem; border-left: 4px solid {cat.get('color', '#3b82f6')}">
                            <h4>{cat.get('icon', '📁')} {cat.get('display_name', cat.get('name'))}</h4>
                            <p style="color: #94a3b8; font-size: 0.9rem;">{cat.get('description', 'No description')[:100]}</p>
                            <p style="font-size: 0.8rem;">
                                <strong>Priority Boost:</strong> {cat.get('priority_boost', 0)} | 
                                <strong>SLA:</strong> {cat.get('sla_resolution_hours', 24)}h
                            </p>
                        </div>
                        """, unsafe_allow_html=True)
        else:
            st.warning("No categories found. Click below to seed default categories.")
        
        # Seed button
        col1, col2 = st.columns([1, 3])
        with col1:
            if st.button("🌱 Seed Default Categories", type="primary"):
                result = api_post("config/categories/seed", {})
                if result:
                    st.success(f"✅ Created {result.get('created', 0)} categories!")
                    st.rerun()
    
    # =========================================================================
    # Routing Rules Tab
    # =========================================================================
    with tab2:
        st.markdown("### Routing Rules")
        st.info("🔀 Rules determine how tickets are automatically routed to agents based on conditions.")
        
        rules = api_get("config/routing-rules")
        
        if rules and "items" in rules:
            for rule in rules["items"]:
                with st.expander(f"📋 {rule.get('name', 'Unnamed Rule')}", expanded=False):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Type:** {rule.get('rule_type', 'N/A')}")
                        st.write(f"**Action:** {rule.get('action', 'N/A')}")
                        st.write(f"**Priority:** {rule.get('priority', 0)}")
                    with col2:
                        st.write(f"**Active:** {'✅' if rule.get('is_active') else '❌'}")
                        st.write(f"**Triggered:** {rule.get('times_triggered', 0)} times")
                    
                    st.write("**Conditions:**")
                    st.json(rule.get("conditions", {}))
        else:
            st.warning("No routing rules found.")
        
        col1, col2 = st.columns([1, 3])
        with col1:
            if st.button("🌱 Seed Default Rules", type="primary"):
                result = api_post("config/routing-rules/seed", {})
                if result:
                    st.success(f"✅ Created {result.get('created', 0)} rules!")
                    st.rerun()
    
    # =========================================================================
    # Webhooks Tab
    # =========================================================================
    with tab3:
        st.markdown("### Webhook Endpoints")
        st.info("🔌 Use these endpoints to receive tickets from external systems.")
        
        base_url = "http://localhost:8000/api/v1/webhooks"
        
        webhook_data = [
            {
                "name": "Zendesk",
                "endpoint": f"{base_url}/zendesk",
                "icon": "🟢",
                "description": "Receive tickets from Zendesk",
                "fields": ["description", "subject", "requester.email", "requester.name"]
            },
            {
                "name": "Freshdesk", 
                "endpoint": f"{base_url}/freshdesk",
                "icon": "🔵",
                "description": "Receive tickets from Freshdesk",
                "fields": ["ticket_description", "ticket_subject", "ticket_requester_email"]
            },
            {
                "name": "Email",
                "endpoint": f"{base_url}/email",
                "icon": "📧",
                "description": "Forward emails (Mailgun, SendGrid, etc.)",
                "fields": ["from", "subject", "body-plain", "message-id"]
            },
            {
                "name": "Generic",
                "endpoint": f"{base_url}/generic",
                "icon": "🔗",
                "description": "Universal webhook for any system",
                "fields": ["content", "subject", "customer_email", "customer_name", "external_id"]
            }
        ]
        
        for wh in webhook_data:
            with st.expander(f"{wh['icon']} {wh['name']}", expanded=False):
                st.markdown(f"**{wh['description']}**")
                st.code(wh["endpoint"], language="text")
                st.write("**Expected Fields:**")
                st.write(", ".join([f"`{f}`" for f in wh["fields"]]))
                
                # Example payload
                if wh["name"] == "Generic":
                    st.write("**Example Payload:**")
                    st.json({
                        "content": "I need help with my order",
                        "subject": "Order Issue",
                        "customer_email": "customer@example.com",
                        "customer_name": "John Doe",
                        "external_id": "ORD-12345",
                        "source": "custom-system"
                    })
    
    # =========================================================================
    # Knowledge Base Tab
    # =========================================================================
    with tab4:
        st.markdown("### Knowledge Base")
        st.info("📚 Knowledge Base stores FAQ and resolved ticket data for AI-powered response suggestions.")
        
        # KB Stats
        stats = api_get("config/knowledge-base/stats")
        if stats:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("📄 Documents", stats.get("document_count", 0))
            with col2:
                st.metric("💾 Storage", stats.get("storage_type", "N/A"))
            with col3:
                st.metric("✅ Initialized", "Yes" if stats.get("initialized") else "No")
        else:
            st.warning("Could not fetch KB stats")
        
        st.markdown("---")
        
        # Seed button
        col1, col2 = st.columns([1, 3])
        with col1:
            if st.button("🌱 Seed Sample FAQs", type="primary"):
                result = api_post("config/knowledge-base/seed", {})
                if result:
                    st.success(f"✅ Added {result.get('added', 0)} FAQ entries to Knowledge Base!")
                    st.rerun()
        
        st.markdown("""        
        **Sample FAQs include:**
        - Warranty information
        - Return/refund policy
        - Shipping times
        - Payment methods
        - Password reset
        - Technical support
        - Complaint handling
        """)


# =============================================================================
# Main App
# =============================================================================

def main():
    # Sidebar
    st.sidebar.image("https://img.icons8.com/fluency/96/customer-support.png", width=80)
    st.sidebar.title("🎯 Support Router")
    st.sidebar.markdown("---")
    
    # Navigation
    page = st.sidebar.radio(
        "📍 Navigation",
        ["🚀 Home", "🏠 Dashboard", "📋 Tickets", "📊 Analytics", "👥 Agents", "🧪 Live Demo", "⚙️ Settings"]
    )
    
    # Reset scroll with JavaScript using a more aggressive approach 
    # that runs on every rerun (navigation)
    js = """
        <script>
            function scroll_to_top() {
                var body = window.parent.document.querySelector(".main");
                if (body) body.scrollTop = 0;
                
                var section = window.parent.document.querySelector("section.main");
                if (section) section.scrollTop = 0;
                
                window.parent.scrollTo(0, 0);
            }
            
            // Try immediately
            scroll_to_top();
            
            // Try again after a small delay to override Streamlit's restoration
            setTimeout(scroll_to_top, 50);
            setTimeout(scroll_to_top, 200);
        </script>
    """
    components.html(js, height=0)
    
    st.sidebar.markdown("---")
    
    # API Status
    api_healthy = check_api_health()
    if api_healthy:
        st.sidebar.success("✅ API Active")
    else:
        st.sidebar.error("❌ No API Connection")
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("""
    **Intelligent Support Router**  
    v0.1.0 | MIT License  
    
    [📖 Documentation](http://localhost:8000/docs)  
    [💻 GitHub](https://github.com/meryemsakin/supportiq)
    """)
    
    # Route to page
    if page == "🚀 Home":
        page_landing()
    elif page == "🏠 Dashboard":
        page_dashboard()
    elif page == "📋 Tickets":
        page_tickets()
    elif page == "📊 Analytics":
        page_analytics()
    elif page == "👥 Agents":
        page_agents()
    elif page == "🧪 Live Demo":
        page_test()
    elif page == "⚙️ Settings":
        page_settings()


if __name__ == "__main__":
    main()
