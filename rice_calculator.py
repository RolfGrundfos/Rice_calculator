import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import gspread
from google.oauth2.service_account import Credentials

def calculate_rice_score(reach, impact, confidence, effort):
    """Calculate RICE score: (Reach × Impact × Confidence) / Effort"""
    if effort == 0:
        return 0
    return (reach * impact * confidence) / effort

@st.cache_resource
def init_gsheets():
    """Initialize Google Sheets connection"""
    try:
        # Try to use Streamlit secrets for credentials
        credentials_info = st.secrets["gcp_service_account"]
        credentials = Credentials.from_service_account_info(
            credentials_info,
            scopes=["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        )
        gc = gspread.authorize(credentials)
        return gc
    except:
        # Fallback: if no secrets, return None (will use demo mode)
        return None

def get_worksheet(gc, username):
    """Get or create worksheet for a user"""
    if gc is None:
        return None

    try:
        # Try to open the spreadsheet by URL or name
        spreadsheet_url = st.secrets.get("spreadsheet_url", "")
        if spreadsheet_url:
            sh = gc.open_by_url(spreadsheet_url)
        else:
            sh = gc.open("RICE Calculator Data")

        # Try to get the user's worksheet, create if it doesn't exist
        try:
            worksheet = sh.worksheet(username)
        except gspread.WorksheetNotFound:
            # Create new worksheet for the user
            worksheet = sh.add_worksheet(title=username, rows=1000, cols=10)
            # Add headers
            worksheet.append_row(["Project", "Reach (%)", "Impact", "Confidence (%)", "Effort (months)", "RICE Score"])

        return worksheet
    except Exception as e:
        st.error(f"Error accessing Google Sheets: {str(e)}")
        return None

def load_user_projects(username):
    """Load projects for a specific user from Google Sheets"""
    gc = init_gsheets()
    worksheet = get_worksheet(gc, username)

    if worksheet is None:
        # Return sample data if Google Sheets is not available
        return []

    try:
        # Get all records (skip header row)
        records = worksheet.get_all_records()
        return records
    except:
        return []

def save_user_projects(username, projects):
    """Save projects for a specific user to Google Sheets"""
    gc = init_gsheets()
    worksheet = get_worksheet(gc, username)

    if worksheet is None:
        # If Google Sheets is not available, show message but don't fail
        st.warning("Google Sheets not configured. Projects will only be saved for this session.")
        return True

    try:
        # Clear existing data (except header)
        worksheet.clear()
        # Add headers
        worksheet.append_row(["Project", "Reach (%)", "Impact", "Confidence (%)", "Effort (months)", "RICE Score"])

        # Add all projects
        if projects:
            for project in projects:
                worksheet.append_row([
                    project["Project"],
                    project["Reach (%)"],
                    project["Impact"],
                    project["Confidence (%)"],
                    project["Effort (months)"],
                    project["RICE Score"]
                ])
        return True
    except Exception as e:
        st.error(f"Error saving to Google Sheets: {str(e)}")
        return False

def main():
    st.set_page_config(
        page_title="RICE Prioritization Calculator",
        page_icon="📊",
        layout="wide"
    )

    st.title("📊 RICE Prioritization Calculator")

    # User selection
    users = ["Jonas", "Hanne", "Ferenc", "Rolf"]
    selected_user = st.selectbox("Select User:", users, key="user_selector")

    st.markdown(f"**Welcome, {selected_user}!** 👋")

    # Debug Google Sheets connection
    gc = init_gsheets()
    if gc is not None:
        st.success("✅ Google Sheets connected successfully!")
    else:
        st.warning("⚠️ Google Sheets not configured. Projects will only be saved for this session.")

    st.markdown("""
    **RICE** is a prioritization framework that helps you evaluate and rank projects based on four criteria:
    - **Reach**: How many people will this impact? (0-100%)
    - **Impact**: How much will this impact each person? (1-3 scale)
    - **Confidence**: How confident are you in your estimates? (0-100%)
    - **Effort**: How much work is required? (person-months)
    """)

    # Sidebar for adding new items
    with st.sidebar:
        st.header("Add New Project")

        project_name = st.text_input("Project Name", placeholder="e.g., Mobile App Feature")

        st.subheader("RICE Parameters")

        # Reach: Percentage of target audience
        reach = st.slider(
            "Reach (%)",
            min_value=0,
            max_value=100,
            value=50,
            help="What percentage of your target audience will this impact? (0-100%)"
        )

        # Impact: Scale from 1-3
        impact = st.select_slider(
            "Impact",
            options=[0.25, 0.5, 1, 2, 3],
            value=1,
            format_func=lambda x: {
                0.25: "Minimal (0.25)",
                0.5: "Low (0.5)",
                1: "Medium (1)",
                2: "High (2)",
                3: "Massive (3)"
            }[x],
            help="How much will this impact each person? Choose from Minimal (0.25) to Massive (3)"
        )

        # Confidence: Percentage
        confidence = st.slider(
            "Confidence (%)",
            min_value=0,
            max_value=100,
            value=80,
            help="How confident are you in your Reach and Impact estimates? (0-100%)"
        )

        # Effort: Person-months
        effort = st.number_input(
            "Effort (person-months)",
            min_value=0.1,
            max_value=100.0,
            value=2.0,
            step=0.5,
            help="How much work is required? (in person-months)"
        )

        if st.button("Add Project", type="primary"):
            if project_name:
                # Convert confidence from percentage to decimal
                confidence_decimal = confidence / 100
                rice_score = calculate_rice_score(reach, impact, confidence_decimal, effort)

                # Load existing projects for the current user
                user_projects = load_user_projects(selected_user)

                # Add new project
                new_project = {
                    'Project': project_name,
                    'Reach (%)': reach,
                    'Impact': impact,
                    'Confidence (%)': confidence,
                    'Effort (months)': effort,
                    'RICE Score': round(rice_score, 2)
                }
                user_projects.append(new_project)

                # Save projects back to file
                if save_user_projects(selected_user, user_projects):
                    st.success(f"Added '{project_name}' with RICE score: {rice_score:.2f}")
                    # Update session state for immediate display
                    st.session_state[f'projects_{selected_user}'] = user_projects
                    # Force refresh to show the new project
                    st.rerun()
                else:
                    st.error("Failed to save project. Please try again.")
            else:
                st.error("Please enter a project name")

    # Load user projects and ensure session state is updated
    user_projects = load_user_projects(selected_user)
    st.session_state[f'projects_{selected_user}'] = user_projects

    # Main content area
    if user_projects:
        df = pd.DataFrame(user_projects)

        # Sort by RICE score (highest first)
        df_sorted = df.sort_values('RICE Score', ascending=False).reset_index(drop=True)
        df_sorted.index += 1  # Start ranking from 1

        # Display results
        col1, col2 = st.columns([2, 1])

        with col1:
            st.subheader("Project Rankings")
            st.dataframe(
                df_sorted,
                use_container_width=True,
                hide_index=False
            )

        with col2:
            st.subheader("RICE Score Distribution")
            fig = px.bar(
                df_sorted.head(10),  # Top 10 projects
                x='RICE Score',
                y='Project',
                orientation='h',
                color='RICE Score',
                color_continuous_scale='viridis'
            )
            fig.update_layout(
                height=400,
                yaxis={'categoryorder': 'total ascending'}
            )
            st.plotly_chart(fig, use_container_width=True)

        # Summary statistics
        st.subheader("Summary Statistics")
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total Projects", len(df))
        with col2:
            st.metric("Highest RICE Score", f"{df['RICE Score'].max():.2f}")
        with col3:
            st.metric("Average RICE Score", f"{df['RICE Score'].mean():.2f}")
        with col4:
            st.metric("Total Effort", f"{df['Effort (months)'].sum():.1f} months")

        # Detailed breakdown chart
        st.subheader("RICE Components Breakdown")

        # Prepare data for radar chart of top project
        top_project = df_sorted.iloc[0]

        categories = ['Reach (%)', 'Impact (×20)', 'Confidence (%)', 'Effort (×5)']
        values = [
            top_project['Reach (%)'],
            top_project['Impact'] * 20,  # Scale for visualization
            top_project['Confidence (%)'],
            top_project['Effort (months)'] * 5  # Scale for visualization
        ]

        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(
            r=values,
            theta=categories,
            fill='toself',
            name=top_project['Project']
        ))

        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 100]
                )
            ),
            showlegend=True,
            title=f"RICE Components for Top Project: {top_project['Project']}"
        )

        st.plotly_chart(fig, use_container_width=True)

        # Option to clear all projects for current user
        if st.button(f"Clear All Projects for {selected_user}", type="secondary"):
            if save_user_projects(selected_user, []):
                st.session_state[f'projects_{selected_user}'] = []
                st.rerun()
            else:
                st.error("Failed to clear projects. Please try again.")

    else:
        st.info("👈 Add your first project using the sidebar to get started!")

        # Example calculation
        st.subheader("How RICE Works")
        st.markdown("""
        The RICE score is calculated as: **RICE = (Reach × Impact × Confidence) / Effort**

        **Example:**
        - Reach: 80% of users (80)
        - Impact: High impact (2)
        - Confidence: 90% confident (0.9)
        - Effort: 3 person-months

        **RICE Score = (80 × 2 × 0.9) / 3 = 48**
        """)

        # Sample data for demonstration
        sample_data = [
            {"Project": "Mobile App Redesign", "Reach (%)": 90, "Impact": 3, "Confidence (%)": 80, "Effort (months)": 6, "RICE Score": 36},
            {"Project": "Push Notifications", "Reach (%)": 70, "Impact": 2, "Confidence (%)": 95, "Effort (months)": 2, "RICE Score": 66.5},
            {"Project": "Dark Mode", "Reach (%)": 40, "Impact": 1, "Confidence (%)": 90, "Effort (months)": 1, "RICE Score": 36},
        ]

        st.subheader("Example Projects")
        sample_df = pd.DataFrame(sample_data)
        st.dataframe(sample_df, use_container_width=True)

if __name__ == "__main__":
    main()