# Audio Transcription & Summarization Workflow

## Overview
This is the core workflow of Sonic Brief, automating the process from audio upload to summarized report delivery.

### Steps
1. **User Uploads Recording**: Via the React frontend (Azure Static Web App).
2. **File Storage & Trigger**: File is stored in Azure Blob Storage, triggering an Azure Function.
3. **Transcription**: Azure Function submits the file to Azure Speech-to-Text, stores the result, and updates CosmosDB.
4. **Summarization**: The function retrieves a prompt and sends the transcription to Azure OpenAI GPT-4o for summarization.
5. **Report Storage**: Summary is stored in Blob Storage and CosmosDB is updated.
6. **Frontend Retrieval**: UI fetches and displays the transcript and summary, allowing download.

### Technologies
- Azure Static Web Apps (React)
- Azure App Service (FastAPI)
- Azure Blob Storage
- Azure Functions (Python)
- Azure Speech-to-Text
- Azure OpenAI GPT-4o
- CosmosDB

### Diagram
See `README.md` for architecture and workflow diagrams.
