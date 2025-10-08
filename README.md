
# 🧠 Retail Knowledge Base Assistant

This Streamlit application demonstrates a **Retrieval-Augmented Generation (RAG)** pipeline built entirely within the **Snowflake AI Data Cloud**, leveraging **Snowflake Cortex Search** for retrieval and the **Snowflake Arctic LLM** for generating grounded answers.

The app provides a chat interface for querying an internal Knowledge Base (KB) of retail policies (returns, shipping, etc.).

---

## 🚀 Key Features

* **100% Snowflake Native RAG:** No external vector databases or search infrastructure required. All data processing, indexing, and LLM inference occur securely inside Snowflake.
* **Context Grounding:** Answers are generated using *only* the content retrieved from the internal policy documents, minimizing LLM hallucinations.
* **Hybrid Search:** Uses Snowflake Cortex Search for high-quality retrieval, combining semantic (vector) and keyword search.
* **Transparency:** Displays the source documents (Retrieved Context) used by the LLM to form its answer.

---

## 🛠️ Prerequisites

This application assumes you have already completed the RAG pipeline setup steps in your Snowflake environment.

### Snowflake Requirements:

1.  **Dedicated Role:** A role (e.g., `EYLON_RAG_ROLE`) with necessary privileges (`SNOWFLAKE.CORTEX_USER`, `USAGE` on the warehouse, etc.).
2.  **Documents Table:** A table named `RAG.PUBLIC.DOCS` containing your knowledge base articles (columns must include `id`, `title`, `url`, `source_type`, and `body`).
3.  **Cortex Search Service:** An active search service named `RAG.PUBLIC.RETAIL_KB_SEARCH` created on the `DOCS` table.
4.  **Chat Messages Table:** A temporary table named `RAG_CHAT_MESSAGES` (must be created with columns `id` and `messages` (VARIANT/OBJECT) for prompt orchestration).

### Python Requirements:

Install necessary Python libraries:

```bash
pip install streamlit snowflake-connector-python
````

-----

## ⚙️ Setup and Configuration

### 1\. Update Connection Details

Before running the application, you must update the placeholder connection details in the `init_connection` function within `streamlit_app.py`:

```python
@st.cache_resource
def init_connection():
    return snowflake.connector.connect(
        user='YOUR_USER',      # <- UPDATE THIS
        password='YOUR_PASSWORD', # <- UPDATE THIS
        account='YOUR_ACCOUNT',   # <- UPDATE THIS
        warehouse='COMPUTE_WH',
        database='RAG',
        schema='PUBLIC',
        role='RAG_ROLE'
    )
```

### 2\. Execution (Streamlit in Snowflake)

This application is optimized for deployment as a **Streamlit in Snowflake (SiS) Application**. When deployed, the connection parameters might be handled automatically by the Snowflake context.

### 3\. Execution (Local Development)

To run the application locally for testing:

```bash
streamlit run streamlit_app.py
```

-----

## 💡 How the Code Works (RAG Orchestration)

The core logic executes the RAG pipeline using only SQL and the Snowflake Python Connector:

1.  **Retrieval:** Uses `SNOWFLAKE.CORTEX.SEARCH_PREVIEW` to query the search index and return the top 5 relevant documents.
2.  **Prompt Assembly:** Documents are formatted with a system message and combined into a JSON array of chat messages.
3.  **Secure Insertion:** The prompt JSON is inserted into the `RAG_CHAT_MESSAGES` table using a **bind variable (`PARSE_JSON(?)`)** for SQL injection safety and compilation robustness.
4.  **Generation:** Calls the `SNOWFLAKE.CORTEX.COMPLETE('snowflake-arctic', messages, ...)` function to generate the answer.
5.  **Cleanup:** Immediately deletes the prompt entry from the temporary table.

-----

## 🤝 Project Structure

```
.
├── streamlit_app.py   # The core Streamlit application code
└── README.md          # This file
```

```
```

<img width="1612" height="608" alt="Screenshot 2025-10-08 004952" src="https://github.com/user-attachments/assets/2ca8615d-f8f9-4184-bd58-d3b62026ebda" />














