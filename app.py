import streamlit as st
import os
import requests
from supabase import create_client #, Client # Client annotation can be imported if needed for type hinting
from dotenv import load_dotenv
import time
import json # For pretty printing JSON responses

# --- Environment and Configuration ---
load_dotenv()

SENSAY_API_BASE_URL = "https://api.sensay.io/v1"
DEFAULT_SENSAY_API_VERSION = "2025-03-25"
DEFAULT_SUPABASE_TABLE_NAME = "slack_messages_for_sensay"
DEFAULT_TEST_CHAT_USER_ID = "streamlit_default_tester"

# --- Helper Functions for API Calls ---

def make_sensay_request(method, endpoint, sensay_org_secret, sensay_api_version, json_data=None, params=None, user_id=None):
    headers = {
        "X-ORGANIZATION-SECRET": sensay_org_secret,
        "X-API-Version": sensay_api_version,
        "Content-Type": "application/json"
    }
    if user_id:
        headers["X-USER-ID"] = user_id

    url = f"{SENSAY_API_BASE_URL}{endpoint}"
    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, params=params, timeout=30)
        elif method.upper() == "POST":
            response = requests.post(url, headers=headers, json=json_data, timeout=30)
        elif method.upper() == "PUT":
            response = requests.put(url, headers=headers, json=json_data, timeout=30)
        elif method.upper() == "DELETE":
            response = requests.delete(url, headers=headers, timeout=30)
        else:
            return None, {"error": "Unsupported HTTP method"}
        
        response.raise_for_status() # Will raise an HTTPError for bad responses (4XX or 5XX)
        return response.json(), None
    except requests.exceptions.HTTPError as http_err:
        error_content = {"error": f"HTTP error occurred: {http_err}", "status_code": http_err.response.status_code, "details": None}
        try:
            error_content["details"] = http_err.response.json()
        except ValueError: # If response is not JSON
            error_content["details"] = http_err.response.text
        return None, error_content
    except requests.exceptions.RequestException as req_err: # Catches network errors, timeouts, etc.
        return None, {"error": f"Request error occurred: {req_err}"}
    except Exception as err: # Catch-all for other unexpected errors
        return None, {"error": f"An unexpected error occurred: {err}"}

# --- Streamlit App ---

st.set_page_config(page_title="Sensay Replica Manager", layout="wide", initial_sidebar_state="expanded")
st.title("🤖 Sensay Replica Manager for Slack Data")
st.caption("Create, train, and test Sensay AI Replicas using Slack message data from Supabase.")

# --- Session State Initialization ---
# Configuration
if 'sensay_org_secret' not in st.session_state:
    st.session_state.sensay_org_secret = os.getenv("SENSAY_ORGANIZATION_SECRET", "")
if 'sensay_api_version' not in st.session_state:
    st.session_state.sensay_api_version = os.getenv("SENSAY_API_VERSION", DEFAULT_SENSAY_API_VERSION)
if 'supabase_url' not in st.session_state:
    st.session_state.supabase_url = os.getenv("SUPABASE_URL", "")
if 'supabase_service_key' not in st.session_state:
    st.session_state.supabase_service_key = os.getenv("SUPABASE_SERVICE_KEY", "")
if 'supabase_table_name' not in st.session_state:
    st.session_state.supabase_table_name = os.getenv("SUPABASE_TABLE_NAME", DEFAULT_SUPABASE_TABLE_NAME)
if 'test_chat_user_id' not in st.session_state:
    st.session_state.test_chat_user_id = os.getenv("DEFAULT_TEST_CHAT_USER_ID", DEFAULT_TEST_CHAT_USER_ID)

# App State
if 'supabase_client' not in st.session_state:
    st.session_state.supabase_client = None
if 'config_set' not in st.session_state:
    st.session_state.config_set = False
if 'replicas_list' not in st.session_state:
    st.session_state.replicas_list = []
if 'chat_histories' not in st.session_state: # For the chat tab
    st.session_state.chat_histories = {}
if 'selected_replica_for_chat_uuid' not in st.session_state:
    st.session_state.selected_replica_for_chat_uuid = None


# --- Configuration Sidebar ---
with st.sidebar:
    st.image("https://sdmntprnorthcentralus.oaiusercontent.com/files/00000000-11d0-622f-9f94-70ec0777c288/raw?se=2025-05-22T08%3A03%3A19Z&sp=r&sv=2024-08-04&sr=b&scid=c057c2d6-4bdb-5b12-8408-1f51fffdbe25&skoid=ea1de0bc-0467-43d6-873a-9a5cf0a9f835&sktid=a48cca56-e6da-484e-a814-9c849652bcb3&skt=2025-05-21T20%3A40%3A49Z&ske=2025-05-22T20%3A40%3A49Z&sks=b&skv=2024-08-04&sig=pXdB2tQok0RMHAou/PQEfZkZj4n5HjGUG0fz%2B%2Bz8QYE%3D", width=150)
    st.header("⚙️ API Configuration")
    
    with st.expander("Sensay API Settings", expanded=True):
        st.session_state.sensay_org_secret = st.text_input("Sensay Organization Secret", value=st.session_state.sensay_org_secret, type="password", help="Your organization's secret token for Sensay API.")
        st.session_state.sensay_api_version = st.text_input("Sensay API Version", value=st.session_state.sensay_api_version, help="E.g., 2025-03-25")

    with st.expander("Supabase API Settings", expanded=True):
        st.session_state.supabase_url = st.text_input("Supabase URL", value=st.session_state.supabase_url, help="Your Supabase project URL.")
        st.session_state.supabase_service_key = st.text_input("Supabase Service Key", value=st.session_state.supabase_service_key, type="password", help="Your Supabase service_role key.")
        st.session_state.supabase_table_name = st.text_input("Supabase Table Name", value=st.session_state.supabase_table_name, help="The table storing Slack messages.")
    
    with st.expander("Chat Test Settings", expanded=True):
        st.session_state.test_chat_user_id = st.text_input("Test User ID for Chatting", value=st.session_state.test_chat_user_id, help="A User ID to simulate chats with replicas. Will be created in Sensay if it doesn't exist.")

    if st.button("💾 Save Configuration & Initialize", use_container_width=True):
        if (st.session_state.sensay_org_secret and st.session_state.sensay_api_version and
            st.session_state.supabase_url and st.session_state.supabase_service_key and 
            st.session_state.supabase_table_name and st.session_state.test_chat_user_id):
            try:
                st.session_state.supabase_client = create_client(st.session_state.supabase_url, st.session_state.supabase_service_key)
                # Test Supabase connection (optional but good)
                st.session_state.supabase_client.table(st.session_state.supabase_table_name).select("id", head=True).limit(1).execute()
                st.session_state.config_set = True
                st.success("Configuration saved and Supabase client initialized!")
            except Exception as e:
                st.error(f"Initialization Failed: {e}")
                st.session_state.config_set = False
        else:
            st.warning("Please fill in all configuration fields.")
            st.session_state.config_set = False

if not st.session_state.config_set:
    st.error("🚨 Please configure API settings in the sidebar and click 'Save Configuration & Initialize'.")
    st.stop()

# --- Main Application Tabs ---

tab1, tab2, tab3 = st.tabs(["🚀 Create & Manage Replicas", "📚 Train Replicas", "💬 Test Replica"])

with tab1:
    st.subheader("✨ Create New Replica")
    
    with st.form("create_replica_form"):
        col_form_1, col_form_2 = st.columns(2)
        with col_form_1:
            slack_user_id_for_replica = st.text_input("Owner's Slack User ID", help="This ID will be used as the Sensay User ID and Replica Owner ID (e.g., UXXXXXXXXXX).")
            replica_name = st.text_input("Replica Name", placeholder="My Expert Assistant")
            replica_slug = st.text_input("Replica Slug", placeholder="my-expert-assistant", help="Unique, lowercase, no spaces, use hyphens.")
        with col_form_2:
            replica_short_description = st.text_input("Short Description (max 50 chars)", placeholder="AI version of our team lead.")
            replica_greeting = st.text_area("Greeting Message", placeholder="Hello! How can I assist you today?", help="What the replica says first.")
            llm_provider = st.selectbox("LLM Provider", ["openai"], index=0, help="Currently Sensay examples use OpenAI.")
            llm_model = st.text_input("LLM Model", value="gpt-4o", help="E.g., gpt-4o, gpt-3.5-turbo")
        
        submitted_create = st.form_submit_button("➕ Create Replica", use_container_width=True)

    if submitted_create:
        if not all([slack_user_id_for_replica, replica_name, replica_slug, replica_short_description, replica_greeting, llm_model]):
            st.error("Please fill all fields for replica creation.")
        else:
            with st.spinner("Verifying/Creating Sensay user and then replica..."):
                sensay_user_id = slack_user_id_for_replica
                user_data, user_error = make_sensay_request(
                    "GET", f"/users/{sensay_user_id}",
                    st.session_state.sensay_org_secret, st.session_state.sensay_api_version
                )
                if user_error and user_error.get("status_code") == 404: # User not found
                    st.write(f"Sensay user '{sensay_user_id}' not found, attempting to create...")
                    create_user_payload = {"id": sensay_user_id}
                    user_data, user_error = make_sensay_request(
                        "POST", "/users",
                        st.session_state.sensay_org_secret, st.session_state.sensay_api_version,
                        json_data=create_user_payload
                    )

                if user_error:
                    st.error(f"Error managing Sensay user '{sensay_user_id}': {user_error.get('details', user_error)}")
                else:
                    st.success(f"Sensay User '{sensay_user_id}' confirmed/created: {user_data.get('id')}")
                    
                    replica_payload = {
                        "name": replica_name, "shortDescription": replica_short_description,
                        "greeting": replica_greeting, "ownerID": sensay_user_id,
                        "private": False, "slug": replica_slug,
                        "llm": {"provider": llm_provider, "model": llm_model}
                    }
                    replica_data, replica_error = make_sensay_request(
                        "POST", "/replicas",
                        st.session_state.sensay_org_secret, st.session_state.sensay_api_version,
                        json_data=replica_payload
                    )
                    if replica_error:
                        st.error(f"Failed to create replica: {replica_error.get('details', replica_error)}")
                    elif replica_data and replica_data.get("success"):
                        st.success(f"Replica '{replica_name}' created successfully! UUID: {replica_data.get('uuid')}")
                        st.balloons()
                    else:
                        st.error(f"Replica creation response indicates failure or missing data: {replica_data}")

    st.divider()
    st.subheader("🗂️ Existing Replicas")
    
    owner_id_filter = st.text_input("Filter by Owner ID (Slack User ID / Sensay User ID)", 
                                    value=st.session_state.get("list_owner_filter_val", ""), 
                                    key="list_owner_filter_input")
    st.session_state.list_owner_filter_val = owner_id_filter # Persist filter value

    if st.button("🔄 Refresh Replicas List", use_container_width=True):
        params = {}
        if owner_id_filter: params["ownerID"] = owner_id_filter
        
        with st.spinner("Fetching replicas from Sensay..."):
            replicas_data, replicas_error = make_sensay_request(
                "GET", "/replicas",
                st.session_state.sensay_org_secret, st.session_state.sensay_api_version,
                params=params
            )
            if replicas_error:
                st.error(f"Failed to fetch replicas: {replicas_error.get('details', replicas_error)}")
                st.session_state.replicas_list = []
            elif replicas_data and replicas_data.get("success") and isinstance(replicas_data.get("items"), list):
                st.session_state.replicas_list = replicas_data["items"]
                st.success(f"Found {len(st.session_state.replicas_list)} replicas matching filter.")
                if not st.session_state.replicas_list and owner_id_filter:
                    st.info("No replicas found for the specified Owner ID.")
                elif not st.session_state.replicas_list:
                    st.info("No replicas found in your organization.")
            else:
                st.warning(f"No replicas found or unexpected response: {replicas_data}")
                st.session_state.replicas_list = []
    
    if st.session_state.replicas_list:
        for replica in st.session_state.replicas_list:
            with st.expander(f"👤 **{replica.get('name', 'N/A')}** (Slug: {replica.get('slug', 'N/A')}, UUID: `{replica.get('uuid', 'N/A')}`)", expanded=False):
                st.caption(f"Owner ID: {replica.get('ownerID', replica.get('owner_uuid', 'N/A'))} | LLM: {replica.get('llm', {}).get('model', 'N/A')}")
                st.code(json.dumps(replica, indent=2), language="json")
    elif not st.session_state.get("list_owner_filter_val"): # only show if no filter is active or initial load
        st.info("Click 'Refresh Replicas List' to load. You can filter by Owner ID.")

with tab2:
    st.subheader("🧠 Train Replica with Slack Data")

    if not st.session_state.replicas_list:
        st.warning("💡 Load or refresh replicas in the '🚀 Create & Manage Replicas' tab first to select one for training.")
    else:
        replica_options = {f"{r.get('name')} ({r.get('uuid')})": r for r in st.session_state.replicas_list}
        selected_replica_display_name = st.selectbox("Select Replica to Train", options=[""] + list(replica_options.keys()), index=0, format_func=lambda x: "Select a Replica..." if x == "" else x)

        if selected_replica_display_name:
            selected_replica_obj = replica_options[selected_replica_display_name]
            replica_uuid_to_train = selected_replica_obj.get("uuid")
            slack_user_id_for_training = selected_replica_obj.get("ownerID") # Crucial for fetching messages

            st.markdown(f"#### Training: **{selected_replica_obj.get('name')}**")
            st.caption(f"Replica UUID: `{replica_uuid_to_train}` | Training with messages from Slack User: `{slack_user_id_for_training}`")

            if st.button(f"💪 Start Training/Retraining for {selected_replica_obj.get('name')}", key=f"train_btn_{replica_uuid_to_train}", use_container_width=True):
                if not slack_user_id_for_training:
                    st.error("Cannot determine Slack User ID (ownerID) for this replica. Training aborted.")
                else:
                    training_log_area = st.empty()
                    progress_bar = st.progress(0, text="Initializing training...")
                    
                    with st.spinner(f"Fetching unprocessed Slack messages for '{slack_user_id_for_training}' from Supabase..."):
                        try:
                            # Select specific columns to be more efficient
                            response = st.session_state.supabase_client.table(st.session_state.supabase_table_name)\
                                .select("message_content, slack_message_ts, id")\
                                .eq("slack_user_id", slack_user_id_for_training)\
                                .eq("processed_for_sensay", False)\
                                .order("created_at", desc=False)\
                                .execute() # Fetch in chronological order
                            
                            messages_to_train = response.data
                            if not messages_to_train:
                                st.info(f"✅ No new messages found in Supabase for user '{slack_user_id_for_training}' to train with.")
                                progress_bar.empty()
                                training_log_area.empty()
                                st.stop()
                            
                            st.success(f"Found {len(messages_to_train)} new Slack messages to train with.")

                        except Exception as e:
                            st.error(f"Error fetching messages from Supabase: {e}")
                            progress_bar.empty()
                            training_log_area.empty()
                            st.stop()

                    total_messages = len(messages_to_train)
                    processed_count = 0
                    error_count = 0
                    training_logs = []

                    for i, msg_data in enumerate(messages_to_train):
                        message_content = msg_data.get("message_content")
                        message_ts = msg_data.get("slack_message_ts")
                        supabase_msg_id = msg_data.get("id")

                        progress_text = f"Processing message {i+1}/{total_messages}: '{message_content[:30].replace(chr(10), ' ')}...'"
                        progress_bar.progress((i + 1) / total_messages, text=progress_text)
                        
                        kb_entry_data, kb_entry_error = make_sensay_request(
                            "POST", f"/replicas/{replica_uuid_to_train}/training",
                            st.session_state.sensay_org_secret, st.session_state.sensay_api_version,
                            json_data={}
                        )

                        if kb_entry_error or not kb_entry_data or not kb_entry_data.get("success"):
                            log_line = f"❌ Failed to create Sensay KB entry for msg_ts {message_ts}: {kb_entry_error or kb_entry_data}"
                            training_logs.append(log_line)
                            error_count += 1
                            continue
                        
                        knowledge_base_id = kb_entry_data.get("knowledgeBaseID")
                        if not knowledge_base_id:
                            log_line = f"❌ Missing knowledgeBaseID for msg_ts {message_ts} after KB entry creation."
                            training_logs.append(log_line)
                            error_count +=1
                            continue

                        update_kb_payload = {"rawText": message_content}
                        update_kb_data, update_kb_error = make_sensay_request(
                            "PUT", f"/replicas/{replica_uuid_to_train}/training/{knowledge_base_id}",
                            st.session_state.sensay_org_secret, st.session_state.sensay_api_version,
                            json_data=update_kb_payload
                        )

                        if update_kb_error or not update_kb_data or not update_kb_data.get("success"):
                            log_line = f"❌ Failed to add text to Sensay KB entry {knowledge_base_id} (msg_ts {message_ts}): {update_kb_error or update_kb_data}"
                            training_logs.append(log_line)
                            error_count += 1
                        else:
                            try:
                                st.session_state.supabase_client.table(st.session_state.supabase_table_name)\
                                    .update({"processed_for_sensay": True})\
                                    .eq("id", supabase_msg_id)\
                                    .execute() # Use primary key for update
                                processed_count += 1
                                log_line = f"✅ Trained with Supabase Msg ID {supabase_msg_id} (KB ID: {knowledge_base_id})"
                                training_logs.append(log_line)
                            except Exception as e_supa_update:
                                log_line = f"⚠️ Trained Sensay with msg_ts {message_ts}, but FAILED to update Supabase: {e_supa_update}"
                                training_logs.append(log_line)
                                error_count += 1
                        
                        training_log_area.text_area("Training Log", value="\n".join(training_logs[-10:]), height=200, key=f"training_log_display_{replica_uuid_to_train}", disabled=True) # Show last 10 logs
                        time.sleep(0.2) # API politeness delay

                    progress_bar.empty()
                    training_log_area.text_area("Full Training Log", value="\n".join(training_logs), height=300, key=f"final_training_log_{replica_uuid_to_train}", disabled=True)
                    st.success(f"Training complete for '{selected_replica_obj.get('name')}'. Successfully trained: {processed_count}, Errors: {error_count}.")
                    if error_count > 0:
                        st.error("Some messages could not be processed. Check logs for details.")

with tab3:
    st.subheader("💬 Test Replica (Interactive Chat)")

    if not st.session_state.replicas_list:
        st.warning("💡 Load or refresh replicas in the '🚀 Create & Manage Replicas' tab first to select one for testing.")
    else:
        replica_options_chat = {f"{r.get('name')} ({r.get('uuid')})": r for r in st.session_state.replicas_list}
        
        # Use a selectbox that updates session state for the selected replica's UUID
        # This helps persist the selection across reruns if the user navigates away and back
        
        # Get current index for selectbox default
        current_selection_idx = 0
        if st.session_state.selected_replica_for_chat_uuid:
            try:
                current_selection_idx = [r.get('uuid') for r in st.session_state.replicas_list].index(st.session_state.selected_replica_for_chat_uuid) +1 # +1 because of the "Select..." option
            except ValueError:
                st.session_state.selected_replica_for_chat_uuid = None # Reset if not found

        selected_replica_display_name_chat = st.selectbox(
            "Select Replica to Chat With", 
            options=[""] + list(replica_options_chat.keys()), 
            index=current_selection_idx,
            format_func=lambda x: "Select a Replica..." if x == "" else x,
            key="chat_replica_selector"
        )

        if selected_replica_display_name_chat:
            selected_replica_obj_chat = replica_options_chat[selected_replica_display_name_chat]
            replica_uuid_to_test = selected_replica_obj_chat.get("uuid")
            st.session_state.selected_replica_for_chat_uuid = replica_uuid_to_test # Persist selection

            st.markdown(f"#### Chatting with: **{selected_replica_obj_chat.get('name')}**")
            st.caption(f"Replica UUID: `{replica_uuid_to_test}` | Test User ID: `{st.session_state.test_chat_user_id}`")

            # Initialize chat history for this replica if it doesn't exist
            if replica_uuid_to_test not in st.session_state.chat_histories:
                st.session_state.chat_histories[replica_uuid_to_test] = []
                # Prepend greeting if it exists and chat is new
                greeting = selected_replica_obj_chat.get("greeting")
                if greeting:
                    st.session_state.chat_histories[replica_uuid_to_test].append({"role": "assistant", "content": greeting})
            
            # Display existing chat messages
            for message in st.session_state.chat_histories[replica_uuid_to_test]:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

            # Chat input
            if prompt := st.chat_input(f"Ask {selected_replica_obj_chat.get('name', 'replica')}..."):
                # Add user message to session state and display
                st.session_state.chat_histories[replica_uuid_to_test].append({"role": "user", "content": prompt})
                with st.chat_message("user"):
                    st.markdown(prompt)

                with st.spinner("🤖 Thinking..."):
                    # Ensure test user exists in Sensay
                    test_user_id = st.session_state.test_chat_user_id
                    user_data, user_error = make_sensay_request(
                        "GET", f"/users/{test_user_id}",
                        st.session_state.sensay_org_secret, st.session_state.sensay_api_version
                    )
                    if user_error and user_error.get("status_code") == 404: # User not found
                        with st.chat_message("assistant"):
                            st.info(f"Test user '{test_user_id}' not found in Sensay. Attempting to create...")
                        create_user_payload = {"id": test_user_id}
                        user_data, user_error = make_sensay_request(
                            "POST", "/users",
                            st.session_state.sensay_org_secret, st.session_state.sensay_api_version,
                            json_data=create_user_payload
                        )
                    
                    if user_error:
                        err_msg_user = f"Error with test user '{test_user_id}': {user_error.get('details', user_error)}"
                        st.session_state.chat_histories[replica_uuid_to_test].append({"role": "assistant", "content": err_msg_user})
                        with st.chat_message("assistant"):
                            st.error(err_msg_user)
                    else: # User confirmed or created, proceed with chat
                        chat_payload = {"content": prompt}
                        response_data, response_error = make_sensay_request(
                            "POST", f"/replicas/{replica_uuid_to_test}/chat/completions",
                            st.session_state.sensay_org_secret, st.session_state.sensay_api_version,
                            json_data=chat_payload, user_id=test_user_id
                        )

                        if response_error:
                            err_msg_chat = response_error.get('details', response_error.get('error', 'Unknown chat error'))
                            st.session_state.chat_histories[replica_uuid_to_test].append({"role": "assistant", "content": f"Error: {err_msg_chat}"})
                            with st.chat_message("assistant"):
                                st.error(f"Chat API Error: {err_msg_chat}")
                        elif response_data and response_data.get("success"):
                            assistant_response = response_data.get("content", "I'm not sure how to respond to that.")
                            st.session_state.chat_histories[replica_uuid_to_test].append({"role": "assistant", "content": assistant_response})
                            with st.chat_message("assistant"):
                                st.markdown(assistant_response)
                        else:
                            final_err_msg = f"Sorry, I encountered an issue. Response: {response_data}"
                            st.session_state.chat_histories[replica_uuid_to_test].append({"role": "assistant", "content": final_err_msg})
                            with st.chat_message("assistant"):
                                st.warning(final_err_msg)
                # Streamlit will automatically rerun after chat_input and st.chat_message updates.
        else:
            st.info("Select a replica from the dropdown above to start chatting.")
