import streamlit as st
import snowflake.connector
import json

# --- Page config ---
st.set_page_config(page_title="Retail Knowledge Base Chat", page_icon="🧠", layout="wide")
st.title("🧠 Retail Knowledge Base Assistant")

# --- Connect to Snowflake ---
@st.cache_resource
def init_connection():
    return snowflake.connector.connect(
        user='YOUR_USER',
        password='YOUR_PASSWORD',
        account='YOUR_ACCOUNT',
        warehouse='COMPUTE_WH',
        database='RAG',
        schema='PUBLIC',
        role='RAG_ROLE'
    )

try:
    conn = init_connection()
except Exception as e:
    st.error(f"Failed to connect to Snowflake. Please check credentials and connection settings: {e}")
    st.stop()


# --- Input box ---
query_input = st.text_input("Ask a question about store policies, returns, shipping, etc.", "")

if st.button("Search"):
    if not query_input.strip():
        st.warning("Please enter a question.")
    else:
        # Step 1: Run Cortex Search Preview
        search_sql = f"""
        SELECT PARSE_JSON(
            SNOWFLAKE.CORTEX.SEARCH_PREVIEW(
                'RAG.PUBLIC.RETAIL_KB_SEARCH',
                '{{"query":"{query_input}", "columns":["id","title","url","source_type","body"], "limit":5}}'
            )
        )['results'] AS results;
        """

        raw_results = []
        try:
            with conn.cursor() as cur:
                cur.execute(search_sql)
                rows = cur.fetchall()
                raw_results = rows[0][0] if rows else []
        except Exception as e:
            st.error(f"Error executing Cortex Search Preview: {e}")
            
        # Step 2: Flatten and parse results safely
        docs = []
        if raw_results:
            if isinstance(raw_results, str):
                try:
                    parsed = json.loads(raw_results)
                    if isinstance(parsed, list):
                        docs = [d for d in parsed if isinstance(d, dict)]
                except json.JSONDecodeError:
                    st.error("Error parsing Cortex search results: Invalid JSON string.")
                except Exception:
                    st.error("Error parsing Cortex search results.")
            elif isinstance(raw_results, list):
                docs = [d for d in raw_results if isinstance(d, dict)]

        # Optional: Filter only Policies
        docs = [d for d in docs if d.get('source_type') == 'Policy']

        if not docs:
            st.error("No relevant documents (Policies) found.")
        else:
            # Step 3: Build context snippets
            context_snippets = [
                f"[{doc.get('id')}] {doc.get('title')}\n{doc.get('body','')[:500]}"
                for doc in docs
            ]

            # Step 4: Build message array for Arctic model
            messages = [
                {"role": "system", "content": "Answer using ONLY the provided CONTEXT. Cite sources by their [id]."},
                {"role": "user", "content": query_input},
            ]
            for snippet in context_snippets:
                messages.append({"role": "user", "content": snippet})

            # Step 5: Prepare JSON and the SQL template using INSERT INTO ... SELECT
            messages_json = json.dumps(messages)
            insert_sql_template = "INSERT INTO RAG_CHAT_MESSAGES (id, messages) SELECT 'MSG1', PARSE_JSON(?)"
            
            raw_llm_response = None
            llm_answer = None
            
            try:
                with conn.cursor() as cur:
                    # Execute INSERT using the bind variable
                    cur.execute(insert_sql_template, (messages_json,))
    
                    # Step 6: Call Cortex COMPLETE
                    cur.execute("""
                        SELECT SNOWFLAKE.CORTEX.COMPLETE(
                            'snowflake-arctic',
                            messages,
                            OBJECT_CONSTRUCT('max_tokens', 300, 'guardrails', TRUE)
                        )
                        FROM RAG_CHAT_MESSAGES
                        WHERE id='MSG1';
                    """)
                    raw_llm_response = cur.fetchone()[0] # Fetch the raw JSON object
    
                    # Step 7: Clean up
                    cur.execute("DELETE FROM RAG_CHAT_MESSAGES WHERE id='MSG1';")
                    
                # --- NEW Step 8: Parse the LLM's JSON Output ---
                if raw_llm_response:
                    # Ensure the result is a dictionary, parsing from string if necessary
                    if isinstance(raw_llm_response, str):
                        parsed_response = json.loads(raw_llm_response)
                    else:
                        parsed_response = raw_llm_response
    
                    # Extract the answer text, which is nested in choices[0].messages
                    llm_answer = parsed_response['choices'][0]['messages']
    
            except Exception as e:
                st.error(f"Error during database operation or LLM call/parsing: {e}")
                # Attempt to clean up
                try:
                    with conn.cursor() as cur:
                        cur.execute("DELETE FROM RAG_CHAT_MESSAGES WHERE id='MSG1';")
                except:
                    pass 

            # Step 9: Display results
            if llm_answer:
                st.subheader("💬 Answer")
                st.write(llm_answer)
            elif raw_llm_response:
                 st.subheader("💬 Raw LLM Response (Could not parse)")
                 st.write(raw_llm_response)
    
            if docs:
                with st.expander("📚 Retrieved Context"):
                    for doc in docs:
                        url = doc.get('url', '#')
                        url = url if isinstance(url, str) and url.startswith(('http://', 'https://', '#')) else '#'

                        st.markdown(
                            f"**[{doc.get('id')}] {doc.get('title')}** \n"
                            f"{doc.get('body','')[:300]}...  \n"
                            f"[Read more]({url})"
                        )

st.caption("Powered by Snowflake Cortex Search + Arctic 🧊")