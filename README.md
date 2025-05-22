# Sensay Replica Manager 🤖

This Streamlit application provides a web-based interface to manage and interact with [Sensay.io](https://sensay.io/) AI Replicas. It allows users to:

*   **Configure** API credentials for Sensay and Supabase.
*   **Create** new Sensay Replicas, defining their properties like name, owner, and LLM.
*   **List and View** existing Replicas within a Sensay organization, with filtering options.
*   **Train (or Retrain)** Replicas using text data (e.g., Slack messages) stored in a Supabase database.
*   **Test and Chat** interactively with trained Replicas directly within the application.

The primary use case demonstrated is training Replicas based on Slack user messages archived in Supabase, effectively creating AI digital twins or knowledge repositories.

## 📸 Screenshots

![image](https://github.com/user-attachments/assets/7df6dffe-44e5-42f7-9cc0-84d3fcd2e7b8)

![image](https://github.com/user-attachments/assets/300ef471-85c7-4cdc-9fd5-38f3a8241724)


## ✨ Features

*   **Centralized Configuration:** Securely input and manage API keys for Sensay and Supabase via a sidebar.
*   **Replica Lifecycle Management:**
    *   Create new Replicas with customizable names, slugs, greetings, and LLM settings.
    *   Automatically creates or confirms the Sensay User (owner) for the Replica.
    *   List existing Replicas with options to filter by owner.
    *   View detailed JSON data for each Replica.
*   **Data-Driven Training:**
    *   Connects to a Supabase table containing text data (e.g., Slack messages).
    *   Fetches unprocessed messages for a specific user (linked to the Replica owner).
    *   Iteratively trains the selected Replica by creating knowledge base entries in Sensay for each message.
    *   Tracks processed messages in Supabase to avoid redundant training.
    *   Provides progress bars and logs during the training process.
*   **Interactive Replica Testing:**
    *   Select any listed Replica to chat with.
    *   Uses Streamlit's modern chat elements (`st.chat_message`, `st.chat_input`).
    *   Maintains separate chat histories for each Replica within the session.
    *   Automatically uses the Replica's greeting message.
    *   Handles creation of a default test user in Sensay if needed for chat.
*   **User-Friendly Interface:** Built with Streamlit for a clean and responsive web UI.
*   **Error Handling & Feedback:** Provides spinners, success/error/warning messages for API interactions.

## 🛠️ Setup Guide

### Prerequisites

*   Python 3.8+
*   A [Sensay.io](https://sensay.io/) account with an **Organization Secret** and desired **API Version**.
*   A [Supabase](https://supabase.com/) account and project.
*   (Optional but Recommended) Data from a Slack bot (like the one described in previous interactions) stored in a Supabase table.

### 1. Clone the Repository (or Create Files)

```bash
git clone https://github.com/Deshi-AI/Sensay-Replica-Manager.git
cd Sensay-Replica-Manager
