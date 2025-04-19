# Kafka Websocket Communication Protocol

This protocol describes how the frontend communicates with the backend via the `/ws` websocket endpoint. All messages are JSON objects.

## Actions

### 1. Generate Code (Prompt)
**Client → Server:**
```json
{
  "action": "prompt",
  "prompt": "Describe your agent idea here.",
  "filename": "agent.based" // optional, to save code to a file
}
```
**Server → Client:**
```json
{
  "status": "success",
  "action": "prompt",
  "code": "...generated Based code...",
  "session": { ... }
}
```

### 2. Generate Diff
**Client → Server:**
```json
{
  "action": "generate_diff",
  "prompt": "Describe your change.",
  "current_code": "...current Based code..."
}
```
**Server → Client:**
```json
{
  "status": "success",
  "action": "generate_diff",
  "diff": "...unified diff...",
  "session": { ... }
}
```

### 3. Apply Diff
**Client → Server:**
```json
{
  "action": "apply_diff",
  "filename": "agent.based",
  "diff": "...unified diff..."
}
```
**Server → Client:**
```json
{
  "status": "success",
  "action": "apply_diff",
  "filename": "agent.based",
  "new_code": "...updated code..."
}
```

### 4. Upload File
**Client → Server:**
```json
{
  "action": "upload_file",
  "filename": "myfile.based",
  "content": "...file content..."
}
```
**Server → Client:**
```json
{
  "status": "success",
  "action": "upload_file",
  "filename": "myfile.based"
}
```

### 5. List Files
**Client → Server:**
```json
{
  "action": "list_files"
}
```
**Server → Client:**
```json
{
  "status": "success",
  "action": "list_files",
  "files": ["agent.based", "myfile.based"]
}
```

### 6. Read File
**Client → Server:**
```json
{
  "action": "read_file",
  "filename": "agent.based"
}
```
**Server → Client:**
```json
{
  "status": "success",
  "action": "read_file",
  "filename": "agent.based",
  "content": "...file content..."
}
```

### 7. Update Context
**Client → Server:**
```json
{
  "action": "update_context",
  "context": { "key": "value" }
}
```
**Server → Client:**
```json
{
  "status": "success",
  "action": "update_context",
  "context": { "key": "value" }
}
```

## Error Response
**Server → Client:**
```json
{
  "status": "error",
  "error": "Description of the error."
}
```

---

**Note:**
- All actions and responses are per websocket session.
- The frontend should review diffs before sending `apply_diff`.
- The `session` object in responses contains the current session state (messages, workspace, context). 