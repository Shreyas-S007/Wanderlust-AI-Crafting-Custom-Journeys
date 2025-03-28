import streamlit as st
import os
import google.generativeai as genai
from dotenv import load_dotenv
import datetime
from datetime import timedelta
import re  # Import the regular expression library

load_dotenv()

# Configure your Google API key
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    st.error("Please set your GOOGLE_API_KEY environment variable.")
    st.stop()
genai.configure(api_key=GOOGLE_API_KEY)


def get_claude_recommendations(user_inputs):
    """Generates personalized recommendations using Gemini API."""
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"""
        Generate a personalized travel itinerary based on the following user inputs:

        Destination: {user_inputs.get('destination', 'Unknown')}
        Travel Dates: {user_inputs.get('start_date', 'Unknown')} to {user_inputs.get('end_date', 'Unknown')}
        Budget: {user_inputs.get('budget', 'Unknown')}
        Trip Purpose: {user_inputs.get('purpose', 'Unknown')}
        Preferences: {', '.join(user_inputs.get('interests', []))}

        Provide a detailed itinerary with daily activities, restaurant recommendations, and attractions.
        Use Indian Rupees (₹) for showing expenses.
        """
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error generating recommendations: {e}"


def validate_travel_preferences(user_preferences):
    """Validates user travel preferences."""
    required_fields = ['destination', 'start_date', 'end_date']
    for field in required_fields:
        if not user_preferences.get(field):
            return None
    return user_preferences


def calculate_trip_budget(budget, trip_duration):
    """Calculates trip budget based on budget range and duration."""
    budget_ranges = {
        "Budget": 5000,  # Daily budget in INR
        "Mid-range": 15000,
        "Luxury": 30000,
    }
    daily_budget = budget_ranges.get(budget, 15000)

    # Simplified budget breakdown (customize as needed)
    budget_breakdown = {
        "daily_budget": daily_budget,
        "accommodation": daily_budget * 0.4,
        "food": daily_budget * 0.3,
        "activities": daily_budget * 0.2,
        "transportation": daily_budget * 0.1,
    }

    return budget_breakdown


def generate_trip_summary(itinerary):
    """Generates a summary of key attractions and experiences."""
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"""
        Summarize the following itinerary and extract key attractions and unique experiences:

        {itinerary}

        Return the information in the following format:
        key_attractions:
        - Attraction 1
        - Attraction 2

        unique_experiences:
        - Experience 1
        - Experience 2
        """
        response = model.generate_content(prompt)

        # Use regex to extract attractions and experiences
        attractions_match = re.findall(r"key_attractions:(.*?)unique_experiences:", response.text, re.DOTALL)
        experiences_match = re.findall(r"unique_experiences:(.*)", response.text, re.DOTALL)

        attractions = []
        experiences = []

        if attractions_match:
            attractions = [a.strip() for a in re.findall(r"- (.*?)(?=\n|$)", attractions_match[0])]
        if experiences_match:
            experiences = [e.strip() for e in re.findall(r"- (.*?)(?=\n|$)", experiences_match[0])]

        return {
            "key_attractions": attractions,
            "unique_experiences": experiences,
        }
    except Exception as e:
        print(f"Error in generate_trip_summary: {e}")
        return {"key_attractions": [], "unique_experiences": []}


def generate_response(question, chat_history):
    """Generate a response to user's question about the itinerary."""
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')

        # Construct chat context
        context = "\n".join([f"{msg['role'].upper()}: {msg['content']}" for msg in chat_history])

        prompt = f"""
        Given the following conversation history and itinerary context, 
        answer the user's question:

        {context}

        USER QUESTION: {question}

        Provide a helpful and detailed response.
        """

        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error generating response: {e}"


def main():
    """Main function to run the Streamlit app."""
    st.title("Travel Itinerary Planner")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    with st.form("travel_preferences"):
        st.subheader("Trip Details")

        col1, col2 = st.columns(2)

        with col1:
            destination = st.text_input("Destination", placeholder="e.g., Paris, France")

            # Date range selection
            today = datetime.datetime.now().date()
            start_date = st.date_input(
                "Trip Start Date",
                min_value=today,
                value=today
            )

            budget = st.selectbox("Budget Range",
                                  ["Budget", "Mid-range", "Luxury"])

        with col2:
            # Calculate max end date (30 days from start)
            max_end_date = start_date + timedelta(days=30)
            end_date = st.date_input(
                "Trip End Date",
                min_value=start_date,
                max_value=max_end_date,
                value=start_date + timedelta(days=7)
            )

            trip_purpose = st.selectbox("Trip Purpose",
                                        ["Leisure", "Business", "Adventure", "Cultural"])

            interests = st.multiselect("Select Interests",
                                       ["Historical Sites", "Food & Cuisine",
                                        "Nature", "Museums", "Shopping",
                                        "Nightlife", "Adventure",
                                        "Local Culture", "Photography"])

        # Additional details
        col3, col4 = st.columns(2)

        with col3:
            dietary_pref = st.selectbox("Dietary Preferences",
                                        ["None", "Vegetarian", "Vegan", "Gluten-free"])

        with col4:
            special_requirements = st.text_input("Special Requirements",
                                                 placeholder="Accessibility needs, etc.")

        # Submit button
        submitted = st.form_submit_button("Generate My Itinerary")

    # Process and generate itinerary
    if submitted:
        # Validate inputs
        if not destination:
            st.warning("Please enter a destination.")
            return

        # Prepare user preferences
        user_preferences = {
            "destination": destination,
            "start_date": start_date,
            "end_date": end_date,
            "budget": budget,
            "purpose": trip_purpose,
            "interests": interests,
            "dietary_preferences": dietary_pref,
            "special_requirements": special_requirements
        }

        # Validate preferences
        validated_preferences = validate_travel_preferences(user_preferences)
        if not validated_preferences:
            st.warning("Please fill in all required fields.")
            return

        # Calculate trip duration
        trip_duration = (end_date - start_date).days + 1

        # Estimate budget
        budget_breakdown = calculate_trip_budget(
            validated_preferences.get('budget', 'Mid-range'),
            trip_duration
        )

        # Show loading
        with st.spinner("Crafting your personalized travel experience..."):
            itinerary = get_claude_recommendations(validated_preferences)

        # Display results
        st.subheader(f"🗺️ Your Personalized {destination} Travel Itinerary")

        # Trip summary
        trip_summary = generate_trip_summary(itinerary)

        # Budget display
        st.subheader("💰 Trip Budget Overview")
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Total Budget", f"₹{budget_breakdown['daily_budget'] * trip_duration:,.2f}")
        with col2:
            st.metric("Daily Budget", f"₹{budget_breakdown['daily_budget']:,.2f}")
        with col3:
            st.metric("Trip Duration", f"{trip_duration} Days")

        # Detailed budget breakdown
        with st.expander("Budget Breakdown"):
            st.write("Estimated Expenses:")
            for category, amount in budget_breakdown.items():
                if category != 'daily_budget':
                    st.write(f"{category.replace('_', ' ').title()}: ₹{amount:,.2f}")

        # Attractions and Experiences
        st.subheader("🌟 Key Highlights")
        col1, col2 = st.columns(2)

        with col1:
            st.write("**Top Attractions:**")
            if trip_summary['key_attractions']:
                for attraction in trip_summary['key_attractions'][:5]:
                    st.write(f"- {attraction}")
            else:
                st.write("No top attractions found.")

        with col2:
            st.write("**Unique Experiences:**")
            if trip_summary['unique_experiences']:
                for experience in trip_summary['unique_experiences'][:5]:
                    st.write(f"- {experience}")
            else:
                st.write("No unique experiences found.")

        # Detailed Itinerary
        st.subheader("📅 Detailed Day-by-Day Itinerary")

        # Split itinerary into days
        days = itinerary.split("\n\nDay")
        for i, day in enumerate(days):
            with st.expander(f"Day {i + 1}" if i > 0 else "Day 1"):
                st.markdown(day)

        # Downloadable itinerary option
        st.download_button(
            label="Download Full Itinerary",
            data=itinerary,
            file_name=f"{destination}_travel_itinerary.txt",
            mime="text/plain"
        )
        st.session_state.chat_history.append({"role": "assistant", "content": itinerary})

    # Chatbot section
    st.subheader("💬 Ask a Question about the Itinerary")
    question = st.text_input("Your Question:", key="question_input")
    if question:
        with st.spinner("Thinking..."):
            response = generate_response(question, st.session_state.chat_history)
            st.write(response)
            st.session_state.chat_history.append({"role": "user", "content": question})
            st.session_state.chat_history.append({"role": "assistant", "content": response})


if __name__ == "__main__":
    main()