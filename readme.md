# with spacy
### Requisitos
- `pip install spacy pandas`
- `pip install text2num openpyxl`
- `pip install pydantic-settings` read .env
- Validar cual usar _sm, _md o _lg
    - `python -m spacy download es_core_news_sm` 12 MB
    - `python -m spacy download es_core_news_md` 40 MB
    - `python -m spacy download es_core_news_lg` 570 MB

# with ollama
### Requisitos
-  `pip install fastmcp ollama mcp`

### Instalar ollama en Windows
- `https://ollama.com/download/windows` 
- `ollama --version`
- `ollama pull llama3.1`

### Crea el bot ollama con las instrucciones
- `ollama create mesero-bot -f ./capa_inteligencia/Modelfile`

### Levanta el servicio MCP
Se debe lanzar en una terminal y dejar corriendo
- `"C:\Users\MichaelPage\AppData\Local\Programs\Python\Python311\Scripts\fastmcp.exe" run C:/Workspace/repos/github/python-mcp/capa_negocio/servidor_catalogo.py --transport sse`

### Levanta el chat-CLI
- `python ./capa_cliente/chat_local.py`

