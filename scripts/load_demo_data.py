"""
Demo Data Loader
Loads sample agents, customers and tickets for demonstration
"""

import requests
import time
import random

API_URL = "http://localhost:8000/api/v1"

# Demo Agents
DEMO_AGENTS = [
    {
        "name": "Sarah Johnson",
        "email": "sarah.johnson@company.com",
        "skills": ["technical_issue", "bug_report"],
        "languages": ["en", "es"],
        "experience_level": 5,
        "max_load": 15,
        "team": "Technical Support",
        "department": "Customer Service"
    },
    {
        "name": "Michael Chen",
        "email": "michael.chen@company.com",
        "skills": ["billing_question", "return_refund"],
        "languages": ["en"],
        "experience_level": 4,
        "max_load": 12,
        "team": "Finance Support",
        "department": "Customer Service"
    },
    {
        "name": "Emily Davis",
        "email": "emily.davis@company.com",
        "skills": ["general_inquiry", "feature_request", "account_management"],
        "languages": ["en", "fr", "de"],
        "experience_level": 3,
        "max_load": 20,
        "team": "General Support",
        "department": "Customer Service"
    },
    {
        "name": "James Wilson",
        "email": "james.wilson@company.com",
        "skills": ["complaint", "technical_issue"],
        "languages": ["en", "es"],
        "experience_level": 5,
        "max_load": 10,
        "team": "Crisis Management",
        "department": "Customer Service"
    },
    {
        "name": "Lisa Anderson",
        "email": "lisa.anderson@company.com",
        "skills": ["technical_issue", "bug_report", "feature_request"],
        "languages": ["en"],
        "experience_level": 2,
        "max_load": 15,
        "team": "Technical Support",
        "department": "Customer Service"
    }
]

# Demo Tickets - Realistic English examples
DEMO_TICKETS = [
    # Technical Issues
    {
        "content": "Hello, your app keeps crashing on my Android phone. This issue started after the last update. I'm using a Samsung Galaxy S23 with Android 14. Can you help?",
        "customer_email": "john.smith@gmail.com",
        "subject": "App crashing issue"
    },
    {
        "content": "I can't log into the system. I'm entering my password correctly but I get an 'Invalid credentials' error. I've also reset my password but the same issue continues. I need an URGENT solution, I can't work!",
        "customer_email": "jane.doe@hotmail.com",
        "subject": "Cannot login - URGENT"
    },
    {
        "content": "We're having issues with the API integration. The webhooks aren't working, no requests are coming to our callback URLs. We followed the steps in the documentation but couldn't resolve it. We need technical support.",
        "customer_email": "dev@techstartup.io",
        "subject": "API Webhook issue"
    },
    
    # Billing Issues
    {
        "content": "I was charged twice on last month's invoice. $199 was deducted on January 15th, and again $199 on January 17th. Please refund the duplicate payment.",
        "customer_email": "mike.wilson@yahoo.com",
        "subject": "Duplicate billing charge"
    },
    {
        "content": "I switched from Premium to Basic plan but I'm still being charged the Premium rate. This has been going on for 3 months, I've overpaid by $450 total. Please fix this and issue a refund.",
        "customer_email": "sarah.brown@outlook.com",
        "subject": "Wrong plan charge"
    },
    
    # Complaints
    {
        "content": "THIS IS OUTRAGEOUS!!! I'VE BEEN WAITING FOR A WEEK FOR A RESPONSE TO MY SUPPORT REQUEST! Refund my money, I don't want to use this service anymore. TERRIBLE customer service!",
        "customer_email": "angry.customer@gmail.com",
        "subject": "COMPLAINT - Unanswered requests"
    },
    {
        "content": "My order hasn't arrived in 2 weeks. You didn't even give me a tracking number. Every time I call, you say something different. What kind of business practice is this? I'm going to file a consumer complaint!",
        "customer_email": "robert.clark@gmail.com",
        "subject": "Delayed order complaint"
    },
    
    # Feature Requests
    {
        "content": "Could you add a dark mode feature to the app? My eyes get very tired when using it at night. Most modern apps support this.",
        "customer_email": "david.miller@gmail.com",
        "subject": "Dark mode suggestion"
    },
    {
        "content": "Can you add Excel export functionality to the reporting module? Currently there's only PDF, but we need to process the data in Excel. It would be very helpful.",
        "customer_email": "finance@abccompany.com",
        "subject": "Excel export feature request"
    },
    
    # General Questions
    {
        "content": "Hello, what is the price of your enterprise package? We're a team of 50 people and we want to purchase a bulk license. Also, is there a discount for annual payment?",
        "customer_email": "sales@bigcorp.com",
        "subject": "Enterprise package pricing"
    },
    {
        "content": "What is the warranty period for your products? Also, what situations are not covered under warranty? I'd like to know before purchasing.",
        "customer_email": "amy.johnson@gmail.com",
        "subject": "Warranty information"
    },
    
    # Account Management
    {
        "content": "I want to change the email address registered to my account. Old email: old@mail.com, new email: new@mail.com. How can I do this?",
        "customer_email": "user123@gmail.com",
        "subject": "Email address change"
    },
    
    # Return Requests
    {
        "content": "I want to return the product I purchased 15 days ago. Order number: #12345. The product has never been used and is in original packaging. How does the return process work?",
        "customer_email": "return.request@gmail.com",
        "subject": "Product return request"
    },
    
    # Positive Feedback
    {
        "content": "You provide great service! You solved my issue yesterday in 10 minutes. Special thanks to Sarah, she was very helpful. 5 stars!",
        "customer_email": "happy.customer@gmail.com",
        "subject": "Thank you - Excellent service"
    },
    
    # Complex Issue
    {
        "content": "I have multiple issues: 1) The app runs slowly 2) Notifications aren't working 3) Sync isn't working. I'm using an iPhone 14 Pro with iOS 17.2. I'm a Premium member.",
        "customer_email": "vip.customer@enterprise.com",
        "subject": "Multiple issue report - Premium Customer"
    }
]


def create_agents():
    """Create demo agents"""
    print("\n👥 Creating agents...")
    created = 0
    
    for agent in DEMO_AGENTS:
        try:
            response = requests.post(f"{API_URL}/agents", json=agent, timeout=10)
            if response.status_code == 200:
                created += 1
                print(f"  ✅ {agent['name']} created")
            else:
                print(f"  ⚠️ {agent['name']} - {response.text[:100]}")
        except Exception as e:
            print(f"  ❌ {agent['name']} - Error: {e}")
    
    print(f"\n📊 {created}/{len(DEMO_AGENTS)} agents created")
    return created


def create_tickets():
    """Create demo tickets"""
    print("\n📋 Creating tickets...")
    created = 0
    
    for i, ticket in enumerate(DEMO_TICKETS):
        try:
            response = requests.post(f"{API_URL}/tickets", json=ticket, timeout=30)
            if response.status_code == 200:
                result = response.json()
                created += 1
                print(f"  ✅ Ticket {i+1}: {ticket['subject'][:40]}...")
                
                # Wait between tickets (for API rate limit)
                time.sleep(1)
            else:
                print(f"  ⚠️ Ticket {i+1} - {response.text[:100]}")
        except Exception as e:
            print(f"  ❌ Ticket {i+1} - Error: {e}")
    
    print(f"\n📊 {created}/{len(DEMO_TICKETS)} tickets created")
    return created


def check_api():
    """Check if API is running"""
    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        return response.status_code == 200
    except:
        return False


def main():
    print("=" * 60)
    print("🚀 Demo Data Loader")
    print("=" * 60)
    
    # API check
    print("\n🔍 Checking API...")
    if not check_api():
        print("❌ API is not running! Start it first:")
        print("   docker compose up -d app")
        return
    
    print("✅ API is running")
    
    # Create agents
    create_agents()
    
    # Short wait
    print("\n⏳ Waiting for AI processing...")
    time.sleep(3)
    
    # Create tickets
    create_tickets()
    
    # Summary
    print("\n" + "=" * 60)
    print("✅ Demo data loaded!")
    print("=" * 60)
    print("\n📍 Dashboard: http://localhost:8501")
    print("📍 API Docs: http://localhost:8000/docs")
    print("\n💡 Ticket processing may take a few minutes.")


if __name__ == "__main__":
    main()
